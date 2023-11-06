import json
import socket
from base import *
from req import *
from resp import *
from config import config
from ui import UI
import subprocess
import logging
from threading import Thread
from itertools import cycle
from time import sleep
from logger import logger

from main import Client

import sys
import termios
import tty
import copy


key2ActionReq = {
    'w': ActionType.MOVE_UP,
    's': ActionType.MOVE_DOWN,
    'a': ActionType.MOVE_LEFT,
    'd': ActionType.MOVE_RIGHT,
    ' ': ActionType.PLACED,
}

gContext = {
    "playerID": -1,
    "gameOverFlag": False,
    "prompt": (
        "Take actions!\n"
        "'w': move up\n"
        "'s': move down\n"
        "'a': move left\n"
        "'d': move right\n"
        "'blank': place bomb\n"
    ),
    "steps": ["⢿", "⣻", "⣽", "⣾", "⣷", "⣯", "⣟", "⡿"],
    "gameBeginFlag": False,
}



class EnvManager():  # add your var and method under the class.
    def __init__(self) -> None:
        self.ui = UI()
        self.resp: PacketResp = None  # NOTE: when you use it, this var should be read only
        # reference for zrx
        self.cur_action: tuple[ActionType, ActionType] = None
        self.cur_map = None
        self.next_map = None
        self.cur_round = 0

    
    def step(self, action):
        """
        handle 1 action and return response
        you should only return the response when the response round changed.
        """
        self.cur_action = action
        if self.resp.type is not PacketType.ActionResp:
            pass  # you should finish this method
        while self.resp.data.round == self.cur_round:  # ??
            pass  # you should finish this method

    def reset(self):
        """
        restart the game
        """


    def cliGetInitReq(self):
        """Get init request from user input."""
        input("enter to start!")
        return InitReq(config.get("player_name"))


    def recvAndRefresh(self, client: Client):
        """Recv packet and refresh ui."""
        global gContext
        self.resp = client.recv()

        if self.resp.type == PacketType.ActionResp:
            gContext["gameBeginFlag"] = True
            gContext["playerID"] = self.resp.data.player_id
            self.ui.player_id = gContext["playerID"]

        while self.resp.type != PacketType.GameOver:
            subprocess.run(["clear"])
            self.ui.refresh(self.resp.data)
            self.ui.display()
            self.resp = client.recv()

        print(f"Game Over!")
        print(f"Final scores \33[1m{self.resp.data.scores}\33[0m")

        if gContext["playerID"] in self.resp.data.winner_ids:
            print("\33[1mCongratulations! You win! \33[0m")
        else:
            print(
                "\33[1mThe goddess of victory is not on your side this time, but there is still a chance next time!\33[0m"
            )

        gContext["gameOverFlag"] = True
        print("press any key to quit")


    def getActionFromIO(self):
        # key = scr.getch()
        old_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
        key = sys.stdin.read(1)
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

        if key in key2ActionReq.keys():
            action = ActionReq(gContext["playerID"], key2ActionReq[key])
        else:
            action = ActionReq(gContext["playerID"], ActionType.SILENT)

        return action
    

    def getActionFromModel(self, newActionType):
        action1 = ActionReq(gContext["playerID"], newActionType[0])
        action2 = ActionReq(gContext["playerID"], newActionType[1])
        return action1, action2


    def start_game(self):
        self.ui = UI()  # create new ui
    
        with Client() as client:
            client.connect()

            initPacket = PacketReq(PacketType.InitReq, self.cliGetInitReq())
            client.send(initPacket)

            # IO thread to display UI
            t = Thread(target=self.recvAndRefresh, args=(client,))
            t.start()

            print(gContext["prompt"])
            for c in cycle(gContext["steps"]):
                if gContext["gameBeginFlag"]:
                    break
                print(
                    f"\r\033[0;32m{c}\033[0m \33[1mWaiting for the other player to connect...\033[0m",
                    flush=True,
                    end="",
                )
                print(gContext["gameBeginFlag"])
                sleep(0.1)

            while not gContext["gameOverFlag"]:
                ######### IO mode ##########
                action = self.getActionFromIO()  # this need time.
                if gContext["gameOverFlag"]:
                    break
                actionPacket = PacketReq(PacketType.ActionReq, action)
                client.send(actionPacket)

                ####### model mode ########
                # action1, action2 = self.getActionFromModel(self.cur_action)  # need time

                # if gContext["gameOverFlag"]:
                #     break

                # actionPacket = PacketReq(PacketType.ActionReq, action1)  # need time
                # client.send(actionPacket)
                # print("send action1")

                # if gContext["gameOverFlag"]:
                #     break

                # actionPacket = PacketReq(PacketType.ActionReq, action2)  # need time
                # client.send(actionPacket)
                # print("send action2")




# test
env = EnvManager()
env.start_game()