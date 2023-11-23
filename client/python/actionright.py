from mapcode import Mapcode
from resp import *
from req import *
from actionresp import *
from playerInfo import PlayerInfo
from reward import *

action_list = [ActionType.MOVE_DOWN, ActionType.MOVE_LEFT, ActionType.MOVE_RIGHT, ActionType.MOVE_UP, 
                    ActionType.PLACED, ActionType.SILENT]
class ActionRight:
    #根据15*15地图判断正确应该走的动作，只加了重要的放炸弹和躲炸弹动作，其他情况返回空
    def __init__(self,size=15) -> None:
        self.mapsize = size
        self.map = None
        self.player:PlayerInfo = None
    
    
    def update(self,map,player):
        #更新
        self.map = map
        self.player = player
        
        
    def tuple_to_code(self,tuple)->int:
        #将动作二元组转成env_manager.pyz中action_list中的动作编码
        action1 = int(tuple[0])
        action2 = int(tuple[1])
        # print(f"actual action1:{action1},action2:{action2}")
        for i in range(len(action_list)):
            if action1 == action_list[i]:
                ans_action1 = i
        for i in range(len(action_list)):
            if action2 == action_list[i]:
                ans_action2 = i
        return ans_action1*6+ans_action2
    
    
    def action_away_from_bomb(self,player_x,player_y,bomb_x,bomb_y,bomb_range)->ActionType:
        '''
        行动躲炸弹,返回一个动作
        '''
        # print(f"player_x:{player_x},player_y:{player_y}")
        # print(f"bomb_x:{bomb_x},bomb_y:{bomb_y}")
        # print(f"range:{bomb_range}")
        if player_x==bomb_x and player_y==bomb_y:
            #炸弹和人在同一个位置
            for i in range(len(next_position)):
                next = next_position[i]
                tx,ty = nextPositionActual(player_x,player_y,next_action[i],self.map)
                if checkoutofrange(tx,ty) or (tx == player_x and ty == player_y):
                    continue
                if checkBombValid(self.map,tx,ty,bomb_x,bomb_y,bomb_range):
                    #向这个方向移动可以找到躲炸弹的方法
                    return next_action[i]
            #没有办法躲掉炸弹，死了算了
            return ActionType.SILENT
        elif player_x>=bomb_x-bomb_range and player_x<=bomb_x+bomb_range and player_y==bomb_y:
            #在炸弹上下方向
            if player_y-1>=0 and self.map[player_x][player_y-1] not in unmovable_block:
                #向左走可以躲炸弹
                return ActionType.MOVE_LEFT
            elif player_y+1<self.mapsize and self.map[player_x][player_y+1] not in unmovable_block:
                #向右走可以躲炸弹
                return ActionType.MOVE_RIGHT
            elif player_x>bomb_x:
                #向下走一步
                return ActionType.MOVE_DOWN
            elif player_x<bomb_x:
                #向上走一步
                return ActionType.MOVE_UP
        elif  player_x==bomb_x and player_y>=bomb_y-bomb_range and player_y<=bomb_y+bomb_range: 
            #在炸弹左右方向
            if player_x-1>=0 and self.map[player_x-1][player_y] not in unmovable_block:
                #向上走可以躲炸弹
                return ActionType.MOVE_UP
            elif player_x+1<self.mapsize and self.map[player_x+1][player_y] not in unmovable_block:
                #向下走可以躲炸弹
                return ActionType.MOVE_DOWN
            elif player_y>bomb_y:
                #向右走一步
                return ActionType.MOVE_RIGHT
            elif player_y<bomb_y:
                #向左走一步
                return ActionType.MOVE_LEFT
        else:
            #如果附近有道具，则捡
            action = checkItemAround(self.map,player_x,player_y)
            #不在炸弹范围，不乱动
            return action
    
    def cal_correct_action(self): 
        '''
        人为判断动作走向，只添加了放置炸弹和躲炸弹和捡道具，没有加入主动靠近道具
        '''
        x=self.player.position_x
        y=self.player.position_y
        if self.player.bomb_max_num -self.player.bomb_now_num>=1:
            #放过炸弹，需要躲
            for i in range(self.mapsize):
                for j in range(self.mapsize):
                    if(self.map[i][j]>=Mapcode.BombBase.value): #找到炸弹
                        range1 = int((self.map[i][j]- Mapcode.BombBase.value)/Mapcode.BombDelta.value) #炸弹范围
                        if range1 == 0 :
                            range1 = self.player.bomb_range
                        action1 = self.action_away_from_bomb(x,y,i,j,range1)
                        tx,ty = nextPositionActual(x,y,action1,self.map)
                        action2 = self.action_away_from_bomb(tx,ty,i,j,range1)
                        return self.tuple_to_code((action1,action2))
        else:
            #没放过炸弹，可以放炸弹,并且要有奖励才放
            if checkBombValid(self.map,x,y,x,y,self.player.bomb_range) and checkMovableBlock(self.map,x,y,self.player.bomb_range):
                #根据地图判断该位置放完炸弹是否可以躲掉
                #可以躲掉
                action2 = self.action_away_from_bomb(x,y,x,y,self.player.bomb_range)
                return self.tuple_to_code((ActionType.PLACED,action2))
            else:
                #向四个方向寻找放炸弹的路径
                for i in range(len(next_position)):
                    next = next_position[i]
                    tx,ty = nextPositionActual(x,y,next_action[i],self.map)
                    if checkoutofrange(tx,ty) or (tx == x and ty == y):
                        continue
                    if checkBombValid(self.map,tx,ty,tx,ty,self.player.bomb_range) and checkMovableBlock(self.map,tx,ty,self.player.bomb_range):
                        #如果向上下左右走可以放炸弹
                        return self.tuple_to_code((next_action[i],ActionType.PLACED))        
        #返回不存在的编码，按照随机或者经验获取下一个动作
        return 37