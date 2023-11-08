import copy
from playerInfo import PlayerInfo
from mapcode import Mapcode
from resp import PacketResp
from req import *
from config import *
from actionresp import *


#上下左右移动
next_position = [[1,-1],[-1,1],[1,1],[-1,-1]]


    
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
    靠近道具reward
    '''
    #TODO

    return 0
    
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
        return -10
    px1,py1 = nextPositionActual(cur_player_me.position_x,cur_player_me.position_y,action1,cur_map)
    if px1==0 and action2 == ActionType.MOVE_UP or px1 == config.get("map_size")-1 and action2 == ActionType.MOVE_DOWN or \
    py1 == 0 and action2 == ActionType.MOVE_LEFT or py1 == config.get("map_size")-1 and action2 == ActionType.MOVE_RIGHT:
        return -10
    #TODO:装block判断,bomb,unremoveblock,removeblock
    
    return 0

def awayFromPlayer(cur_resp:PacketResp,next_resp:PacketResp,action:tuple,cur_map,cur_player_me:PlayerInfo,cur_player_enemy:PlayerInfo)->int:
        #防守型
    '''
    防守型，和敌人保持一段距离
    '''    
    #TODO
    
    return 0