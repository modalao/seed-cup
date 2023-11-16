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
from train import TrainManager
import os
import torch
import traceback
from actionsteplist import ActionStepList
import pickle
import actionresp

inter_lock = threading.Lock()

rewardPriority={
    2:reward.rewardBomb,
    # 5:reward.awayFromPlayer,
    1:reward.awayFromBomb,
    3:reward.nearItem,
    4:reward.collideWall,
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

maxtotreward = 20 #奖励分母，用来归一化 最大约为15+4+10+6+5 

action_list = [ActionType.MOVE_DOWN, ActionType.MOVE_LEFT, ActionType.MOVE_RIGHT, ActionType.MOVE_UP, 
                    ActionType.PLACED, ActionType.SILENT]
transform_map_size = 7 #15*15->7*7
MinBombPlaced = 10 #必须在MinBombPlaced回合内放置炸弹
class EnvManager():  # add your var and method under the class.
    def __init__(self) -> None:
        self.ui = None
        self.resp: PacketResp = None  # NOTE: when you use it, this var should be read only
        self.cur_round = 1  # round_num of this round

        self.t_ui = None  # thread for recvAndRefresh
        # self.lock_interaction = threading.Lock()  # lock for action/resp

        # init new action list(36 actions total)
        self.new_action_list = []
        for ac1 in action_list:
            for ac2 in action_list:
                self.new_action_list.append((ac1, ac2))
        self.n_act = len(self.new_action_list)

        # encode shape
        # self.encode_shape = 15 * 15 + 15

        # process to be controled
        self.process_server = None
        self.process_bot = None

        self.train_manager = TrainManager(
            n_action=self.n_act,
            batch_size=32,
            num_steps=4,
            memory_size=20000,
            replay_start_size=400,
            update_target_steps=200
        )
        self.action_step_list = ActionStepList(MinBombPlaced) #记录动作的个数
        self.max_score = -2000 #所有轮中最大分数
        # log
        f.write("init\n")


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
            range_x = config.get("map_size")
            range_y = config.get("map_size")
            return [[Mapcode.NullBlock.value for _ in range(range_x)] for __ in range(range_y)]
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
                    me_obj:Obj = None
                    enemy_obj:Obj = None
                    for obj in map.objs:
                        if obj.type == ObjType.Bomb:
                            BombFlag = True
                        if not obj.type == ObjType.Player:
                            continue 
                        #me
                        if myplayer_id == obj.property.player_id and obj.property.alive:
                            me = True
                            freshed = True
                            me_obj = copy.deepcopy(obj)

                        #enemy  玩家可以重叠**
                        if myplayer_id != obj.property.player_id and obj.property.alive:
                            enemy = True
                            freshed = True
                            enemy_obj = copy.deepcopy(obj)
                        
                    if not freshed: #不是人，
                        mapcode[map.x][map.y]=Mapcode.calulate(map.objs[0])
                    else :
                        if not BombFlag:#纯人，补充了两个人位置重叠
                            if enemy :
                                mapcode[map.x][map.y]=Mapcode.calulate(enemy_obj,True)
                            if me :
                                mapcode[map.x][map.y]=Mapcode.calulate(me_obj,False)
                        else :#人 炸弹一起
                            if enemy :
                                mapcode[map.x][map.y]=Mapcode.calulate(None,True,False,True)
                            if me :
                                mapcode[map.x][map.y]=Mapcode.calulate(None,False,False,True)
                else: 
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
                                                   bomb_now_num = obj.property.bomb_max_num-obj.property.bomb_now_num,
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
                                                    bomb_now_num=obj.property.bomb_max_num-obj.property.bomb_now_num,
                                                    speed=obj.property.speed)
                if flag and enemy_id != -1:
                    break
        return my_player, enemy_player
    
    
    def calculateReward_(self,cur_resp:PacketResp,action:tuple,cur_map,cur_player_me:PlayerInfo,cur_player_enemy:PlayerInfo)->int:
        #形参为cur_resp当前resp报文(动作前），action为该回合的两个动作，cur_map 当前状态地图信息,cur_player_me 我方信息，cur_player_enemy 敌方信息
        #可利用形参计算当前操作reward函数,根据实际情况奖惩，
        reward1:int = 0
        reward.optimize(cur_player_me.position_x,cur_player_me.position_y,cur_map,action[0],action[1],cur_player_me)
        for i in sorted(rewardPriority.keys()):  # 按键值排序，先调用优先级高的，返回reward
            # reward=rewardPriority[i](cur_resp,action,cur_map,cur_player_me,cur_player_enemy)
            # if reward != 0:
            #     return reward
            tem=rewardPriority[i](cur_resp,action,cur_map,cur_player_me,cur_player_enemy)
            # print(f"{rewardPriority[i]} reward: {tem}")
            reward1+=tem
        return reward1
    

    def calculateReward(self, resp:PacketResp, action):
        cur_state = self.encode_state(self.resp)
        cur_player_my_state, cur_player_enemy_state = self.playerState(self.resp)
        reward1 = self.calculateReward_(self.resp, 
                                       action, 
                                       cur_state, 
                                       cur_player_my_state, 
                                       cur_player_enemy_state)
        if reward1 == 0:
            reward1 = reward.rewardValue["reward1"] #给适当奖励
        return reward1


    def cliGetInitReq(self):
        """Get init request from user input."""
        # input("enter to start!")
        return InitReq("python-client")


    def uiRefresh(self):
        global gContext
        global inter_lock

        self.ui = UI()
        while gContext["gameBeginFlag"] == False:
            continue

        while True:
            # inter_lock.acquire()
            if gContext["gameOverFlag"] == True:
                # inter_lock.release()
                break
            # subprocess.run(["clear"])
            # try:
            #     self.ui.refresh(self.resp.data)
            #     self.ui.display()
            # except:
            #     # inter_lock.release()
            #     break
        print('ui thread exit success.')


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

        action1 = ActionReq(gContext["playerID"], self.cur_action[0])
        action2 = ActionReq(gContext["playerID"], self.cur_action[1])
        self.cur_action = None

        return action1, action2
    

    def to_tensor(self, obs_state, player_state:PlayerInfo):
        state_tensor = torch.Tensor(obs_state).reshape((1, -1)).squeeze()
        player_tensor = player_state.to_tensor()
        return torch.cat([state_tensor, player_tensor])
    

    def state2Tuple(self, obs_state, player_state:PlayerInfo):
        return (torch.Tensor(obs_state), player_state.to_tensor())

    
    def transform(self,next_obs_state,next_player_my_state:PlayerInfo):
        #缩小地图范围
        next_obs_state1=[[Mapcode.NullBlock.value for _ in range(transform_map_size)] for __ in range(transform_map_size)]
        x=next_player_my_state.position_x
        y=next_player_my_state.position_y
        size = int(transform_map_size/2)
        for i in range(x-size,x+size+1):
            for j in range(y-size,y+size+1):
                if(i>=0 and i<config.get("map_size") and j>=0 and j<config.get("map_size")):
                    next_obs_state1[i-x+size][j-y+size]=next_obs_state[i][j]
                else:
                    next_obs_state1[i-x+size][j-y+size]=Mapcode.Border.value
        return next_obs_state1
    

    def start_train(self):
        global gContext
        global inter_lock

        with Client() as client:
            client.connect()
            initPacket = PacketReq(PacketType.InitReq, self.cliGetInitReq())
            client.send(initPacket)

            self.t_ui = Thread(target=self.uiRefresh)
            self.t_ui.start()

            print('waiting for connection...')
            self.resp = client.recv()

            if self.resp.type == PacketType.ActionResp:
                print('connection success! game start!')
                gContext["gameBeginFlag"] = True
                gContext["playerID"] = self.resp.data.player_id
                self.ui.player_id = gContext["playerID"]

                # init obs in train_manager
                cur_obs_state = self.encode_state(self.resp)
                cur_player_my_state, cur_player_enemy_state = self.playerState(self.resp)
                cur_state = self.state2Tuple(cur_obs_state, cur_player_my_state)
                self.train_manager.init_obs(cur_state)

            while self.resp.type != PacketType.GameOver:
                if gContext["gameOverFlag"]: #add
                    break

                # NOTE: the train code is added here.
                print(f'round {self.resp.data.round}: ')

                action_idx = self.train_manager.get_action()
                new_action = self.new_action_list[action_idx]
                action1 = ActionReq(gContext["playerID"], new_action[0])
                action2 = ActionReq(gContext["playerID"], new_action[1])

                # for test
                # action1 = ActionReq(gContext["playerID"], ActionType.PLACED)
                # action2 = ActionReq(gContext["playerID"], ActionType.SILENT)

                # calculate reward
                reward1 = self.calculateReward(self.resp, new_action)
                # print(f'reward now :{reward1}')
                # send action
                actionPacket = PacketReq(PacketType.ActionReq, [action1, action2])  # need time
                client.send(actionPacket)
                print(f'send action: {action1.actionType}, {action2.actionType}')
                # f.write(str(action1.actionType)+"   "+str(action2.actionType)+'\n')
                # action前map输出
                # f.write("map before action\n")
                # map=self.encode_state(self.resp)
                # for i in range(config.get("map_size")):
                #     for j in range(config.get("map_size")):
                #         f.write(str(map[i][j])+"  ")
                #     f.write('\n')
                # print("map before action\n")
                # actionresp.outputMap(self.encode_state(self.resp))
                
                self.action_step_list.update((action1.actionType,action2.actionType))#更新动作

                self.resp = client.recv()
                print(f'receive resp, type={self.resp.type}')

                # print(f'cur_round :{self.cur_round}')
                #死亡扣分
                if self.resp.type == PacketType.GameOver:
                    reward1 += reward.rewardValue["reward-5"]              
                #10回合不放炸弹扣分
                if self.action_step_list.WhetherBombStep() == False and self.cur_round >=MinBombPlaced:
                    reward1 += reward.rewardValue["reward-4"]
                #重复动作扣分
                if self.action_step_list.repeatStep() and self.cur_round >=MinBombPlaced:
                    reward1 += reward.rewardValue["reward-3"] 
                # self.action_step_list.outputList()
                
                # calculate state
                next_obs_state = self.encode_state(self.resp)
                next_player_my_state, next_player_enemy_state = self.playerState(self.resp)
                next_obs_state1 = self.transform(next_obs_state,next_player_my_state)
                #测试transform map是否正确
                # print("transform map:")
                # for i in range(7):
                #     for j in range(7):
                #         print(next_obs_state1[i][j],end=' ')
                #     print('')
                    
                # next_state = self.to_tensor(next_obs_state, next_player_my_state)
                next_state = self.state2Tuple(next_obs_state1, next_player_my_state)
                is_over = self.resp.type == PacketType.GameOver
                if self.resp.type != PacketType.GameOver:
                    self.cur_round = self.resp.data.round  #更新cur_round

                # #综合score后的reward
                # if gContext["gameOverFlag"] :
                #     pass
                # else:
                #     reward1 = reward1*0.95 + next_player_my_state.score*0.05
                reward1 = reward1*1.0/maxtotreward #归一化
                print(f'now step reward: {reward1}')
                
                # action后map输出
                # f.write("map after action\n")
                # print("map after action\n")
                # actionresp.outputMap(next_obs_state)
                # map=next_obs_state
                # for i in range(config.get("map_size")):
                #     for j in range(config.get("map_size")):
                #         f.write(str(map[i][j])+"  ")
                #     f.write('\n')
                # train
                self.train_manager.train_one_step(action_idx, 
                                                  reward1, 
                                                  next_state,
                                                  is_over)
                
                

            print(f"Game Over!")
            print(f"Final scores \33[1m{self.resp.data.scores}\33[0m")

            for score in self.resp.data.scores:
                if gContext["playerID"] == score["player_id"]:
                    self.max_score= max(self.max_score,score["score"])
                    
            if gContext["playerID"] in self.resp.data.winner_ids:
                print("\33[1mCongratulations! You win! \33[0m")
            else:
                print(
                    "\33[1mThe goddess of victory is not on your side this time, but there is still a chance next time!\33[0m"
                )

            gContext["gameOverFlag"] = True


    
    def train(self, episodes):
        global gContext

        for i in range(episodes):
            self.train_manager.train_mode()

            # initialize gContext
            self.resp = None
            gContext["gameOverFlag"] = False
            gContext["gameBeginFlag"] = False
            gContext["playerID"] = -1

            # restart server and bot
            target_directory = "../../bin"
            cur_dir = os.getcwd()
            os.chdir(target_directory)
            with open("server_tmp.log", "w") as server_log:
                self.process_server = subprocess.Popen("./server", stdout=server_log, stderr=server_log)
            self.process_bot = subprocess.Popen("./silly-bot")
            sleep(2)  # waiting
            os.chdir(cur_dir)

            print(f'========== episode {i} begin ==========')
            print(f'epsilon: {self.train_manager.agent.epsilon}')
            self.start_train()
            if self.process_server is not None:
                print(f'kill ./server')
                self.process_server.kill()
                self.process_server.wait()
            if self.process_bot is not None:
                print(f'kill ./silly-bot')
                self.process_bot.kill()
                self.process_bot.wait()
            sleep(1)  # waiting for the exit of threads and process
            self.train_manager.agent.decay()
            print(f'========== episode {i} finish ==========')

            if i != 0 and i % 100 == 0:
                self.train_manager.eval_mode()

                # initialize gContext
                self.resp = None
                gContext["gameOverFlag"] = False
                gContext["gameBeginFlag"] = False
                gContext["playerID"] = -1

                # restart server and bot
                target_directory = "../../bin"
                cur_dir = os.getcwd()
                os.chdir(target_directory)
                with open("server_tmp.log", "w") as server_log:
                    self.process_server = subprocess.Popen("./server", stdout=server_log, stderr=server_log)
                self.process_bot = subprocess.Popen("./silly-bot")
                sleep(2)  # waiting
                os.chdir(cur_dir)

                print(f'========== test begin ==========')
                self.start_train()
                if self.process_server is not None:
                    print(f'kill ./server')
                    self.process_server.kill()
                    self.process_server.wait()
                if self.process_bot is not None:
                    print(f'kill ./silly-bot')
                    self.process_bot.kill()
                    self.process_bot.wait()
                sleep(1)  # waiting for the exit of threads and process
                print(f'========== test finish ==========')
            print(f'max score :{self.max_score}')






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
    
    try:
        env.train(2000)
        torch.save(env.train_manager.agent.pred_func.state_dict(), './checkpoint_mlp_2000.pt')
        bin_file = open('./replay_buffer.bin', 'wb')
        pickle.dump(env.train_manager.agent.rb, bin_file)
    except:
        traceback.print_exc()  # 打印详细的错误信息堆栈
        print(f'error occured!')
        torch.save(env.train_manager.agent.pred_func.state_dict(), './checkpoint_mlp_2000.pt')
        bin_file = open('./replay_buffer.bin', 'wb')
        pickle.dump(env.train_manager.agent.rb, bin_file)
        if env.process_server is not None:
            print(f'kill ./server')
            env.process_server.kill()
            env.process_server.wait()
        if env.process_bot is not None:
            print(f'kill ./silly-bot')
            env.process_bot.kill()
            env.process_bot.wait()
        exit(-1)

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
    
    
        
        