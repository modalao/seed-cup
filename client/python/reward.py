import copy
from playerInfo import PlayerInfo
from mapcode import Mapcode
from resp import PacketResp
from req import *
from config import *
from actionresp import *


#上下左右移动
next_position = [[1,-1],[-1,1],[1,1],[-1,-1]]
SAFEDISTANCE = 7
BombMinNum = 10

    
#reward 范围[10,100],[-100,-10]
#按照优先级写，优先级高的先写，并且直接返回奖惩,如果无奖惩，返回0
#形参为cur_resp当前resp报文，action为该回合的两个动作，cur_map 当前状态地图信息,cur_player_me 我方信息，cur_player_enemy 敌方信息
def rewardBomb(cur_resp:PacketResp,next_resp:PacketResp,action:tuple,cur_map,cur_player_me:PlayerInfo,cur_player_enemy:PlayerInfo)->int:
    '''
    炸弹相关reward
    '''
    action1 = action[0]
    action2 = action[1]
    x=cur_player_me.position_x
    y=cur_player_me.position_y
    #first step
    px1,py1 = nextPositionActual(cur_player_me.position_x,cur_player_me.position_y,action1,cur_map)
    
    #炸道具惩罚
    if action1 == ActionType.PLACED:
        for next_item in next_position:
            tx = x+next_item[0]
            ty = y+next_item[1]
            if checkoutofrange(tx,ty)  :
                continue
            if cur_map[tx][ty] in (Mapcode.ItemBombRange,Mapcode.ItemHp,Mapcode.ItemInvencible,Mapcode.ItemNum,Mapcode.ItemShield):
                return -30
            
    if action2 == ActionType.PLACED:
        for next_item in next_position:
            tx = px1+next_item[0]
            ty = py1+next_item[1]
            if checkoutofrange(tx,ty):
                continue
            if cur_map[tx][ty] in (Mapcode.ItemBombRange,Mapcode.ItemHp,Mapcode.ItemInvencible,Mapcode.ItemNum,Mapcode.ItemShield):
                return -30   
    #炸removable障碍物奖励
    if action1 == ActionType.PLACED:
        for next_item in next_position:
            tx = x+next_item[0]
            ty = y+next_item[1]
            if checkoutofrange(tx,ty):
                continue
            if cur_map[tx][ty] == Mapcode.BlockRemovable:
                return 10
    if action2 == ActionType.PLACED:
        for next_item in next_position:
            tx = px1+next_item[0]
            ty = py1+next_item[1]
            if checkoutofrange(tx,ty):
                continue
            if cur_map[tx][ty] == Mapcode.BlockRemovable:
                return 10
    #TODO 其他 
    
    return 0
    
def awayFromBomb(cur_resp:PacketResp,next_resp:PacketResp,action:tuple,cur_map,cur_player_me:PlayerInfo,cur_player_enemy:PlayerInfo)->int:
    '''
    远离炸弹reward
    '''    
    
    action1 = action[0]
    action2 = action[1]
    x=cur_player_me.position_x
    y=cur_player_me.position_y
    px1,py1 = nextPositionActual(cur_player_me.position_x,cur_player_me.position_y,action1,cur_map)
    tem_map = actionStepMap(action1,cur_map,x,y,cur_player_me.bomb_range)
    px2,py2 = nextPositionActual(px1,py1,action2,tem_map)
    now_map = actionStepMap(action2,tem_map,px1,py1,cur_player_me.bomb_range)
    bomb_before = checkPersonInBombRange(cur_map,x,y,cur_player_me.bomb_range)
    bomb_after = checkPersonInBombRange(now_map,px2,py2,cur_player_me.bomb_range)
    if bomb_before == False and bomb_after == True:
        return -40
    elif bomb_before == True and bomb_after == False:
        return 40
    #TODO 更精确/更好的判断
    
    return 0

def nearItem(cur_resp:PacketResp,next_resp:PacketResp,action:tuple,cur_map,cur_player_me:PlayerInfo,cur_player_enemy:PlayerInfo)->int:
    '''
    剪道具reward
    '''
    action1=action[0]
    action2=action[1]
    x = cur_player_me.position_x
    y = cur_player_me.position_y
    px1,py1 = nextPositionActual(cur_player_me.position_x,cur_player_me.position_y,action1,cur_map)  #action1后我的位置
    reward1=0
    if cur_map[px1][py1] in (Mapcode.ItemBombRange,Mapcode.ItemHp,Mapcode.ItemInvencible,Mapcode.ItemNum,Mapcode.ItemShield):
        reward1+=30  #action1就捡到了道具，非常好
    else:
        reward1+=0
    now_map = actionStepMap(action1,cur_map,x,y,cur_player_me.bomb_range) #action1后地图
    px2,py2 = nextPositionActual(px1,py1,action2,now_map)  #action2后我的位置
    if cur_map[px2][py2] in (Mapcode.ItemBombRange,Mapcode.ItemHp,Mapcode.ItemInvencible,Mapcode.ItemNum,Mapcode.ItemShield):
        reward1+=30  #action2捡到道具，非常好
    else: 
        reward1+=0
    return reward1
    #TODO 实现靠近道具
    
def collideWall(cur_resp:PacketResp,next_resp:PacketResp,action:tuple,cur_map,cur_player_me:PlayerInfo,cur_player_enemy:PlayerInfo)->int:
    '''
    撞墙reward
    '''
    action1 = action[0]
    action2 = action[1]
    x = cur_player_me.position_x
    y = cur_player_me.position_y
    #两步的边界判断
    if x==0 and action1 == ActionType.MOVE_UP or x == config.get("map_size")-1 and action1 == ActionType.MOVE_DOWN or \
    y == 0 and action1 == ActionType.MOVE_LEFT or y == config.get("map_size")-1 and action1 == ActionType.MOVE_RIGHT:
        return -20
    px1,py1 = nextPositionActual(cur_player_me.position_x,cur_player_me.position_y,action1,cur_map)
    if px1==0 and action2 == ActionType.MOVE_UP or px1 == config.get("map_size")-1 and action2 == ActionType.MOVE_DOWN or \
    py1 == 0 and action2 == ActionType.MOVE_LEFT or py1 == config.get("map_size")-1 and action2 == ActionType.MOVE_RIGHT:
        return -20
    #撞block判断,bomb,unremoveblock,removeblock
    reward1=0
    if action1 == ActionType.MOVE_UP:
        if cur_map[x-1][y] in (Mapcode.BlockRemovable,Mapcode.BlockUnRemovable): #撞障碍物
            reward1+=-20
        elif cur_map[x-1][y]>=BombMinNum:  #撞炸弹
            reward1+=-30    
    elif action1 == ActionType.MOVE_LEFT:
        if cur_map[x][y-1] in (Mapcode.BlockRemovable,Mapcode.BlockUnRemovable): #撞障碍物
            reward1+=-20
        elif cur_map[x][y-1]>=BombMinNum:  #撞炸弹
            reward1+=-30    
    elif action1 == ActionType.MOVE_RIGHT:
        if cur_map[x][y+1] in (Mapcode.BlockRemovable,Mapcode.BlockUnRemovable): #撞障碍物
            reward1+=-20
        elif cur_map[x][y+1]>=BombMinNum:  #撞炸弹
            reward1+=-30    
    elif action1 == ActionType.MOVE_DOWN:
        if cur_map[x+1][y] in (Mapcode.BlockRemovable,Mapcode.BlockUnRemovable): #撞障碍物
            reward1+=-20
        elif cur_map[x+1][y]>=BombMinNum:  #撞炸弹
            reward1+=-30    
        
    #第二步
    if action2 == ActionType.MOVE_UP:
        if cur_map[px1-1][py1] in (Mapcode.BlockRemovable,Mapcode.BlockUnRemovable): #撞障碍物
            reward1+=-20
        elif cur_map[px1-1][py1]>=BombMinNum:  #撞炸弹
            reward1+=-30    
    elif action2 == ActionType.MOVE_LEFT:
        if cur_map[px1][py1-1] in (Mapcode.BlockRemovable,Mapcode.BlockUnRemovable): #撞障碍物
            reward1+=-20
        elif cur_map[px1][py1-1]>=BombMinNum:  #撞炸弹
            reward1+=-30    
    elif action2 == ActionType.MOVE_RIGHT:
        if cur_map[px1][py1+1] in (Mapcode.BlockRemovable,Mapcode.BlockUnRemovable): #撞障碍物
            reward1+=-20
        elif cur_map[px1][py1+1]>=BombMinNum:  #撞炸弹
            reward1+=-30    
    elif action1 == ActionType.MOVE_DOWN:
        if cur_map[px1+1][py1] in (Mapcode.BlockRemovable,Mapcode.BlockUnRemovable): #撞障碍物
            reward1+=-20
        elif cur_map[px1+1][py1]>=BombMinNum:  #撞炸弹
            reward1+=-30    

    return reward1


def awayFromPlayer(cur_resp:PacketResp,next_resp:PacketResp,action:tuple,cur_map,cur_player_me:PlayerInfo,cur_player_enemy:PlayerInfo)->int:
    '''
    防守型，和敌人保持一段距离
    '''    
    action1 = action[0]
    action2 = action[1]
    x1=cur_player_me.position_x
    y1=cur_player_me.position_y   #当前自己位置 
    x = cur_player_enemy.position_x
    y = cur_player_enemy.position_y  #当前敌人位置
    px1,py1 = nextPositionActual(cur_player_me.position_x,cur_player_me.position_y,action1,cur_map)  #action1后我的位置
    now_map = actionStepMap(action1,cur_map,x1,y1,cur_player_me.bomb_range) #action1后地图
    px2,py2=nextPositionActual(px1,py1,action2,now_map) #action2后我的位置
    distance1=distance(x1,y1,x,y) #移动前敌我距离
    distance2=distance(px2,py2,x,y) #移动后敌我距离
    if distance1>=SAFEDISTANCE and distance2>=SAFEDISTANCE:
        return 0
    elif distance1>distance2:  #靠近了不合适
        return -30
    elif distance1<distance2:  #远离了合适
        return 30
    else:
        return 0