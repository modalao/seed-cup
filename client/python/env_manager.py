import json
import socket
from base import *
from req import *
from resp import *
from config import config
from ui import UI
import subprocess
import logging
import threading
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

action_list = [ActionType.MOVE_DOWN, ActionType.MOVE_LEFT, ActionType.MOVE_RIGHT, ActionType.MOVE_UP, 
                    ActionType.PLACED, ActionType.SILENT]



class EnvManager():  # add your var and method under the class.
    def __init__(self) -> None:
        self.ui = None
        self.next_resp: PacketResp = None  # NOTE: when you use it, this var should be read only
        self.cur_resp: PacketResp = None  # last_resp = resp before update self.resp
        
        self.cur_action: tuple[ActionType, ActionType] = None  # action to take in this round
        self.cur_round = 0  # round_num of this round

        self.t_game = None  # thread for game.
        self.t_ui = None  # thread for recvAndRefresh

        self.lock_interaction = threading.Lock()  # lock for action/resp

        # init new action list(36 actions total)
        self.new_action_list = []
        for ac1 in action_list:
            for ac2 in action_list:
                self.new_action_list.append((ac1, ac2))
        self.n_act = len(self.new_action_list)

        # with open("env.log", "w") as self.log:
        #     self.log.write("init")
        f.write("init")

        

        
    def step(self, action:tuple):
        """
        handle 1 action and return response
        you should only return the response when the response round changed.
        """
        f.write("enter step\n")
        while self.next_resp is None or self.next_resp.data.round == self.cur_round:
            # if self.next_resp is not None:
            #     print(self.next_resp.data.round)
            continue
        
        self.lock_interaction.acquire()  # avoid the competence
        f.write("enter step lock\n")
        # encode  
        self.cur_action = action
        reward = self.calculateReward(self.cur_resp, self.next_resp, self.cur_action)  # TODO
        cur_state = self.encode_state(self.cur_resp)  # TODO
        next_state = self.encode_state(self.next_resp)  # TODO
        is_over = self.next_resp.type == PacketType.GameOver
        # update
        self.cur_round = self.next_resp.data.round
        self.cur_resp = copy.deepcopy(self.next_resp)  # NOTE: deepcopy.
        self.lock_interaction.release()  # avoid the competence
        f.write("leave step\n")
        # return
        return cur_state, next_state, reward, is_over
    

    def start(self):
        self.t_game = Thread(target=self.start_game)
        self.t_game.start()


    def reset(self):#return ?
        """
        restart the game
        """
        global gContext
        # 设置终止标志
        gContext["gameOverFlag"]= True
        # close threads
        if self.t_ui is not None:
            self.t_ui.join()
        if self.t_game is not None:
            self.t_game.join()

        # 重新启动
        self.ui = None
        self.next_resp = None
        self.cur_resp = None
        self.cur_action = None
        self.cur_round = 0
        gContext["gameOverFlag"] = False
        gContext["gameBeginFlag"] = False
        gContext["playerID"] = -1
        self.start()


    def calculateReward(self, cur_resp:PacketResp, next_resp:PacketResp, cur_action:tuple):
        return None
    
    
    def encode_state(self, resp:PacketResp):
        return None


    def cliGetInitReq(self):
        """Get init request from user input."""
        # input("enter to start!")
        return InitReq(config.get("player_name"))


    def recvAndRefresh(self, client: Client):
        """Recv packet and refresh ui."""
        global gContext
        self.next_resp = client.recv()

        if self.next_resp.type == PacketType.ActionResp:
            gContext["gameBeginFlag"] = True
            gContext["playerID"] = self.next_resp.data.player_id
            self.ui.player_id = gContext["playerID"]

        while self.next_resp.type != PacketType.GameOver:
            if gContext["gameOverFlag"]: #add
                break
            subprocess.run(["clear"])
            self.ui.refresh(self.next_resp.data)
            self.ui.display()
            self.next_resp = client.recv()

        print(f"Game Over!")
        print(f"Final scores \33[1m{self.next_resp.data.scores}\33[0m")

        if gContext["playerID"] in self.next_resp.data.winner_ids:
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
    

    def getActionFromModel(self, newActionType:tuple=None):
        while self.cur_action is None:
            continue

        self.lock_interaction.acquire()
        action1 = ActionReq(gContext["playerID"], self.cur_action[0])
        action2 = ActionReq(gContext["playerID"], self.cur_action[1])
        self.cur_action = None
        self.lock_interaction.release()

        return action1, action2


    def start_game(self):
        self.ui = UI()  # create new ui
    
        with Client() as client:
            client.connect()

            initPacket = PacketReq(PacketType.InitReq, self.cliGetInitReq())
            client.send(initPacket)

            # IO thread to display UI
            self.t_ui = Thread(target=self.recvAndRefresh, args=(client,))
            self.t_ui.start()

            print(gContext["prompt"])
            for c in cycle(gContext["steps"]):
                if gContext["gameBeginFlag"]:
                    break
                print(
                    f"\r\033[0;32m{c}\033[0m \33[1mWaiting for the other player to connect...\033[0m",
                    flush=True,
                    end="",
                )
                sleep(0.1)

            while not gContext["gameOverFlag"]:
                ######### IO mode ##########
                # action = self.getActionFromIO()  # this need time.
                # if gContext["gameOverFlag"]:
                #     break
                # actionPacket = PacketReq(PacketType.ActionReq, action)
                # client.send(actionPacket)

                ####### model mode ########
                action1, action2 = self.getActionFromModel()  # need time

                if gContext["gameOverFlag"]:
                    break

                actionPacket = PacketReq(PacketType.ActionReq, action1)  # need time
                client.send(actionPacket)
                # print("send action1")

                if gContext["gameOverFlag"]:
                    break

                actionPacket = PacketReq(PacketType.ActionReq, action2)  # need time
                client.send(actionPacket)
                # print("send action2")




# test
with open("env.log", "w") as f:
    env = EnvManager()
    action_list = [(ActionType.MOVE_LEFT, ActionType.SILENT), 
                   (ActionType.MOVE_RIGHT, ActionType.SILENT),
                   (ActionType.MOVE_LEFT, ActionType.SILENT), 
                   (ActionType.MOVE_RIGHT, ActionType.SILENT),
                   (ActionType.MOVE_LEFT, ActionType.SILENT), 
                   (ActionType.MOVE_RIGHT, ActionType.SILENT),
                   (ActionType.MOVE_LEFT, ActionType.SILENT), 
                   (ActionType.MOVE_RIGHT, ActionType.SILENT)]
    env.start()
    while True:
        _, _, _, _ = env.step((ActionType.MOVE_LEFT, ActionType.SILENT))
        _, _, _, _ = env.step((ActionType.MOVE_RIGHT, ActionType.SILENT))