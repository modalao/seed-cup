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
from mapcode import Mapcode
from main import Client
from playerInfo import PlayerInfo
import sys
import termios
import tty
import copy
import reward



rewardPriority={
    2:reward.rewardBomb,
    5:reward.awayFromPlayer,
    1:reward.awayFromBomb,
    4:reward.nearItem,
    3:reward.collideWall
}

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
        self.resp: PacketResp = None  # NOTE: when you use it, this var should be read only
        
        self.cur_action: tuple[ActionType, ActionType] = None  # action to take in this round
        self.cur_round = 1  # round_num of this round

        self.t_game = None  # thread for game.
        self.t_ui = None  # thread for recvAndRefresh

        self.lock_interaction = threading.Lock()  # lock for action/resp

        # init new action list(36 actions total)
        self.new_action_list = []
        for ac1 in action_list:
            for ac2 in action_list:
                self.new_action_list.append((ac1, ac2))
        self.n_act = len(self.new_action_list)

        # encode shape
        self.encode_shape = 15 * 15 + 15

        # process to be controled
        self.process_server = None
        self.process_bot = None
        
        # log
        f.write("init\n")


    def step(self, action:tuple):#TODO:add bomb time?
        """
        handle 1 action and return response
        you should only return the response when the response round changed.
        """
        f.write("enter step\n")
            
        while self.resp is None:  # execute only once 
            continue
        
        self.lock_interaction.acquire()  ###### avoid the competence
        assert self.resp.data.round == self.cur_round
        f.write("enter step lock\n")
        self.cur_action = action
        cur_state = self.encode_state(self.resp)
        cur_player_my_state, cur_player_enemy_state = self.playerState(self.resp)
        reward = self.calculateReward(self.resp, 
                                      self.cur_action, 
                                      cur_state, 
                                      cur_player_my_state, 
                                      cur_player_enemy_state)  # TODO: change it.
        self.lock_interaction.release()  ###### avoid the competence
        
        # print(self.resp.type is PacketType.GameOver)
        while True:  # update resp
            self.lock_interaction.acquire()
            flag = self.resp.type is PacketType.ActionResp and self.resp.data.round == self.cur_round
            self.lock_interaction.release()
            if flag:
                continue
            else:
                break
            
        self.lock_interaction.acquire()  ###### avoid the competence
        next_state = self.encode_state(self.resp)  # map state
        if self.resp.type != PacketType.GameOver:
            self.cur_round = self.resp.data.round  # update round
        is_over = self.resp.type == PacketType.GameOver

        # f.write(str(self.resp.data.round))
        # f.write("\n")
        # f.write(str(self.resp.data.round))
        self.lock_interaction.release()  ###### avoid the competence
        
            
        f.write("leave step\n")

        # return
        return next_state, reward, is_over
    

    def start(self):
        self.t_game = Thread(target=self.start_game)
        self.t_game.start()


    def reset(self):
        """
        restart the game
        """
        target_directory = "../../bin"
        process_server = subprocess.Popen(["server"], cwd=target_directory)
        process_bot = subprocess.Popen(["silly-bot"], ced=target_directory)
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
        self.resp = None
        self.cur_action = None
        self.cur_round = 0
        gContext["gameOverFlag"] = False
        gContext["gameBeginFlag"] = False
        gContext["playerID"] = -1
        self.start()


    def encode_state(self, resp:PacketResp):
        #game over返回None，或者前一个地图
        if resp == None:
            return None
        if resp.type==PacketType.GameOver:
            return None
        else:
            range_x = config.get("map_size")
            range_y = config.get("map_size")
            mapcode = [[Mapcode.NullBlock.value for _ in range(range_x)] for __ in range(range_y)]
            actionResp:ActionResp=resp.data
            #refresh each block
            myplayer_id = actionResp.player_id
            for map in actionResp.map:
                freshed = False
                if len(map.objs):
                    BombFlag = False
                    enemy = False
                    me = False
                    for obj in map.objs:
                        if obj.type == ObjType.Bomb:
                            BombFlag = True
                        if not obj.type == ObjType.Player:
                            continue 
                        #me
                        if myplayer_id == obj.property.player_id and obj.property.alive:
                            me = True
                            freshed = True

                        #enemy  玩家可以重叠**
                        if myplayer_id != obj.property.player_id and obj.property.alive:
                            enemy = True
                            freshed = True
                        
                    if not freshed:
                        mapcode[map.x][map.y]=Mapcode.calulate(map.objs[0])
                    else :
                        if not BombFlag:
                            if enemy :
                                mapcode[map.x][map.y]=Mapcode.calulate(obj,True)
                            if me :
                                mapcode[map.x][map.y]=Mapcode.calulate(obj,False)
                        else :#人 炸弹一起
                            if enemy :
                                mapcode[map.x][map.y]=Mapcode.calulate(obj,True,False,True)
                            if me :
                                mapcode[map.x][map.y]=Mapcode.calulate(obj,False,False,True)
                else: #爆炸
                    mapcode[map.x][map.y]=Mapcode.calulate(None,False, actionResp.round == map.last_bomb_round)
            return mapcode
        

    def playerState(self, resp:PacketResp):
        #计算当前player状态
        my_player :PlayerInfo = None
        enemy_player :PlayerInfo = None
        if resp == None:
            return my_player,enemy_player
        my_id = gContext["playerID"]
        enemy_id = -1
        if resp.type == PacketType.GameOver:#GameOver 对应的PlayerInfo
            enemy_id = resp.data.scores[0]["player_id"]+resp.data.scores[1]["player_id"]-my_id
            if gContext["playerID"] in resp.data.winner_ids:
                my_player = PlayerInfo(game_over=True,player_is_me=True,player_id=my_id,alive=True)
                enemy_player = PlayerInfo(game_over=True,player_is_me=False,player_id=enemy_id,alive=False)
            else :
                my_player = PlayerInfo(game_over=True,player_is_me=True,player_id=my_id,alive=False)
                enemy_player = PlayerInfo(game_over=True,player_is_me=False,player_id=enemy_id,alive=True)
        else :#ActionResp 对应的PlayerInfo
            for map in resp.data.map:
                flag = False
                for obj in map.objs:
                    if obj.type == ObjType.Player:
                        if obj.property.player_id == my_id:
                            my_player = PlayerInfo(position_x = map.x, 
                                                   position_y = map.y, 
                                                   position = map.x*15 + map.y,
                                                   player_id = my_id, 
                                                   player_is_me = True, 
                                                   alive = obj.property.alive,
                                                   hp = obj.property.hp,
                                                   shield_time = obj.property.shield_time,
                                                   invincible_time = obj.property.invincible_time,
                                                   score = obj.property.score,
                                                   bomb_range = obj.property.bomb_range,
                                                   bomb_max_num = obj.property.bomb_max_num,
                                                   bomb_now_num = obj.property.bomb_now_num,
                                                   speed = obj.property.speed)
                            flag = True
                        if obj.property.player_id != my_id:
                            enemy_id=obj.property.player_id
                            enemy_player=PlayerInfo(position_x=map.x,
                                                    position_y=map.y,
                                                    position=map.x*15+map.y,
                                                    player_id=enemy_id,
                                                    player_is_me=False,
                                                    alive=obj.property.alive,
                                                    hp=obj.property.hp,
                                                    shield_time=obj.property.shield_time,
                                                    invincible_time=obj.property.invincible_time,
                                                    score=obj.property.score,
                                                    bomb_range=obj.property.bomb_range,
                                                    bomb_max_num=obj.property.bomb_max_num,
                                                    bomb_now_num=obj.property.bomb_now_num,
                                                    speed=obj.property.speed)
                if flag and enemy_id != -1:
                    break
        return my_player,enemy_player
    
    
    def calculateReward(self,cur_resp:PacketResp,action:tuple,cur_map,cur_player_me:PlayerInfo,cur_player_enemy:PlayerInfo)->int:
        #形参为cur_resp当前resp报文(动作前），action为该回合的两个动作，cur_map 当前状态地图信息,cur_player_me 我方信息，cur_player_enemy 敌方信息
        #可利用形参计算当前操作reward函数,根据实际情况奖惩，
        #TODO 填写rewardBomb，rewardItem，awayFromBomb，nearItem函数
        
        reward:int = 0
        for i in sorted(rewardPriority.keys()):  # 按键值排序，先调用优先级高的，返回reward
            reward=rewardPriority[i](cur_resp,action,cur_map,cur_player_me,cur_player_enemy)
            if reward != 0:
                return reward
        return reward


    def cliGetInitReq(self):
        """Get init request from user input."""
        # input("enter to start!")
        return InitReq(config.get("player_name"))


    def recvAndRefresh(self, client: Client):
        """Recv packet and refresh ui."""
        global gContext
        self.resp = client.recv()
        # print(self.next_resp.data.round)

        if self.resp.type == PacketType.ActionResp:
            gContext["gameBeginFlag"] = True
            gContext["playerID"] = self.resp.data.player_id
            self.ui.player_id = gContext["playerID"]

        while self.resp.type != PacketType.GameOver:
            if gContext["gameOverFlag"]: #add
                break
            subprocess.run(["clear"])
            self.lock_interaction.acquire()  # add lock
            self.ui.refresh(self.resp.data)
            self.ui.display()
            self.lock_interaction.release()
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
        cur_state1, reward1, is_over1 = env.step((ActionType.PLACED, ActionType.SILENT))
        # cur_state2, reward2, is_over2 = env.step((ActionType.MOVE_RIGHT, ActionType.SILENT))
    # f.write(str(reward1))
    # f.write("\n")
    # f.write(str(is_over1))
    # f.write("\n")
    # for x in range(15):
    #     for y in range(15):
    #         f.write(str(cur_state1[x][y])) 
    #         f.write(" ")
    #     f.write("\n")
    # f.write("\n")
    # for x in range(15):
    #     for y in range(15):
    #         f.write(str(next_state1[x][y])) 
    #         f.write(" ")
    #     f.write("\n")
    # f.write("\n")
    # for x in range(15):
    #     for y in range(15):
    #         f.write(str(cur_state2[x][y])) 
    #         f.write(" ")
    #     f.write("\n")
    # f.write("\n")
    # for x in range(15):
    #     for y in range(15):
    #         f.write(str(next_state2[x][y])) 
    #         f.write(" ")
    #     f.write("\n")
    
    
        
        