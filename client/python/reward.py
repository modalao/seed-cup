import copy
from playerInfo import PlayerInfo
from mapcode import Mapcode
from resp import PacketResp
from req import *
from config import *
from actionresp import *


#上下左右移动
next_position = [[1,-1],[-1,1],[1,1],[-1,-1]]
SAFEDISTANCE = 7  #和敌人保持的安全距离
BombMinNum = Mapcode.BombBase.value #炸弹的最小编号

rewardValue ={
    "reward5" : 5,
    "reward4" : 4,
    "reward3" : 3,
    "reward2" : 2,
    "reward1" : 1,
    "reward-1" : -1,
    "reward-2" : -2,
    "reward-3" : -3,
    "reward-4" : -4,
    "reward-5" : -5,
}
    
#reward 范围[10,100],[-100,-10]
#按照优先级写，优先级高的先写，并且直接返回奖惩,如果无奖惩，返回0
#形参为cur_resp当前resp报文，action为该回合的两个动作，cur_map 当前状态地图信息,cur_player_me 我方信息，cur_player_enemy 敌方信息
def rewardBomb(cur_resp:PacketResp,action:tuple,cur_map,cur_player_me:PlayerInfo,cur_player_enemy:PlayerInfo)->int:
    '''
    炸弹相关reward
    '''
    action1 = action[0]
    action2 = action[1]
    x=cur_player_me.position_x
    y=cur_player_me.position_y
    #first step
    px1,py1 = nextPositionActual(cur_player_me.position_x,cur_player_me.position_y,action1,cur_map)
    
    #没有炸弹时，不要放炸弹
    if(cur_player_me.bomb_now_num ==0 and (action1 == ActionType.PLACED or action2 ==ActionType.PLACED)):
        return rewardValue["reward-3"]
    if action1 == ActionType.PLACED and action2 == ActionType.PLACED:#同一个位置不能重复放炸弹
        return rewardValue["reward-2"]
    #炸道具惩罚
    if action1 == ActionType.PLACED:
        for next_item in next_position:
            tx = x+next_item[0]
            ty = y+next_item[1]
            if checkoutofrange(tx,ty)  :
                continue
            if cur_map[tx][ty] in (Mapcode.ItemBombRange,Mapcode.ItemHp,Mapcode.ItemInvencible,Mapcode.ItemNum,Mapcode.ItemShield):
                return rewardValue["reward-2"]
            
    if action2 == ActionType.PLACED:
        for next_item in next_position:
            tx = px1+next_item[0]
            ty = py1+next_item[1]
            if checkoutofrange(tx,ty):
                continue
            if cur_map[tx][ty] in (Mapcode.ItemBombRange,Mapcode.ItemHp,Mapcode.ItemInvencible,Mapcode.ItemNum,Mapcode.ItemShield):
                return rewardValue["reward-2"]  
    #炸removable障碍物奖励
    if action1 == ActionType.PLACED:
        for next_item in next_position:
            tx = x+next_item[0]
            ty = y+next_item[1]
            if checkoutofrange(tx,ty):
                continue
            if cur_map[tx][ty] == Mapcode.BlockRemovable:
                return rewardValue["reward1"]
    if action2 == ActionType.PLACED:
        for next_item in next_position:
            tx = px1+next_item[0]
            ty = py1+next_item[1]
            if checkoutofrange(tx,ty):
                continue
            if cur_map[tx][ty] == Mapcode.BlockRemovable:
                return rewardValue["reward1"]
    #TODO 其他 
    
    return 0
    
def awayFromBomb(cur_resp:PacketResp,action:tuple,cur_map,cur_player_me:PlayerInfo,cur_player_enemy:PlayerInfo)->int:
    '''
    远离炸弹reward
    '''    

    action1 = action[0]
    action2 = action[1]
    x=cur_player_me.position_x
    y=cur_player_me.position_y
    px1,py1 = nextPositionActual(x,y,action1,cur_map) #action1后我的位置
    tem_map = actionStepMap(action1,cur_map,x,y,cur_player_me.bomb_range) #action1后的地图
    px2,py2 = nextPositionActual(px1,py1,action2,tem_map) #action2后我的位置
    now_map = actionStepMap(action2,tem_map,px1,py1,cur_player_me.bomb_range) #action2后的地图
    #遍历地图，找到action之前的炸弹
    size=config.get("map_size")
    m_distance1=0 #action之前的曼氏距离，若累计和为0则表示不在爆炸范围内
    m_distance2=0 #同上
    reward1=0
    for i in range(size):
        for j in range(size):
            if(cur_map[i][j]>=Mapcode.BombBase.value): #找到炸弹
                range1 = (cur_map[i][j]- Mapcode.BombBase.value)/Mapcode.BombDelta.value #炸弹范围
                if (x>=i-range1 and x<=i+range1 and y==j or x==i and y>=j-range1 and y<=j+range1):
                    m_distance1+=distance(i,j,x,y)
    #遍历地图，找到action之后的炸弹
    for i in range(size):
        for j in range(size):
            if(now_map[i][j]>=Mapcode.BombBase.value): #找到炸弹
                range1 = (now_map[i][j]- Mapcode.BombBase.value)/Mapcode.BombDelta.value #炸弹范围
                if (px2>=i-range1 and px2<=i+range1 and py2==j or px2==i and py2>=j-range1 and py2<=j+range1):
                    m_distance2+=distance(i,j,px2,py2)  
    #case 
    if(m_distance1 ==0 and m_distance2==0): 
        reward1+=0
    elif(m_distance1>0 and m_distance2==0):
        reward1+=rewardValue["reward3"]
    elif(m_distance1==0 and m_distance2>0):
        reward1+=rewardValue["reward-3"]
    else:
        if(m_distance1>m_distance2):
            reward1+=rewardValue["reward-3"]
        elif(m_distance1<m_distance2):
            reward1+=rewardValue["reward3"]
        else:
            reward1+=0
    return reward1        

def nearItem(cur_resp:PacketResp,action:tuple,cur_map,cur_player_me:PlayerInfo,cur_player_enemy:PlayerInfo)->int:
    '''
    捡道具reward
    '''
    action1=action[0]
    action2=action[1]  
    x = cur_player_me.position_x
    y = cur_player_me.position_y
    px1,py1 = nextPositionActual(cur_player_me.position_x,cur_player_me.position_y,action1,cur_map)  #action1后我的位置
    reward1=0
    if cur_map[px1][py1] in (Mapcode.ItemBombRange,Mapcode.ItemHp,Mapcode.ItemInvencible,Mapcode.ItemNum,Mapcode.ItemShield):
        reward1+=rewardValue["reward2"]  #action1就捡到了道具，非常好
    else:
        reward1+=0
    now_map = actionStepMap(action1,cur_map,x,y,cur_player_me.bomb_range) #action1后地图
    px2,py2 = nextPositionActual(px1,py1,action2,now_map)  #action2后我的位置
    if cur_map[px2][py2] in (Mapcode.ItemBombRange,Mapcode.ItemHp,Mapcode.ItemInvencible,Mapcode.ItemNum,Mapcode.ItemShield):
        reward1+=rewardValue["reward2"]  #action2捡到道具，非常好
    else: 
        reward1+=0
    return reward1
    #TODO 实现靠近道具
    
def collideWall(cur_resp:PacketResp,action:tuple,cur_map,cur_player_me:PlayerInfo,cur_player_enemy:PlayerInfo)->int:
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
        return rewardValue["reward-1"]
    px1,py1 = nextPositionActual(cur_player_me.position_x,cur_player_me.position_y,action1,cur_map)
    if px1==0 and action2 == ActionType.MOVE_UP or px1 == config.get("map_size")-1 and action2 == ActionType.MOVE_DOWN or \
    py1 == 0 and action2 == ActionType.MOVE_LEFT or py1 == config.get("map_size")-1 and action2 == ActionType.MOVE_RIGHT:
        return rewardValue["reward-1"]
    #撞block判断,bomb,unremoveblock,removeblock
    reward1=0
    if action1 == ActionType.MOVE_UP:
        if cur_map[x-1][y] in (Mapcode.BlockRemovable,Mapcode.BlockUnRemovable): #撞障碍物
            reward1+=rewardValue["reward-2"]
        elif cur_map[x-1][y]>=BombMinNum or cur_map[x-1][y]==Mapcode.BombEnemyHuman.value:  #撞炸弹
            reward1+=rewardValue["reward-3"]    
    elif action1 == ActionType.MOVE_LEFT:
        if cur_map[x][y-1] in (Mapcode.BlockRemovable,Mapcode.BlockUnRemovable) : #撞障碍物
            reward1+=rewardValue["reward-2"]
        elif cur_map[x][y-1]>=BombMinNum or cur_map[x][y-1]==Mapcode.BombEnemyHuman.value:  #撞炸弹
            reward1+=rewardValue["reward-3"]    
    elif action1 == ActionType.MOVE_RIGHT:
        if cur_map[x][y+1] in (Mapcode.BlockRemovable,Mapcode.BlockUnRemovable): #撞障碍物
            reward1+=rewardValue["reward-2"]
        elif cur_map[x][y+1]>=BombMinNum or cur_map[x][y+1]==Mapcode.BombEnemyHuman.value:  #撞炸弹
            reward1+=rewardValue["reward-3"]    
    elif action1 == ActionType.MOVE_DOWN:
        if cur_map[x+1][y] in (Mapcode.BlockRemovable,Mapcode.BlockUnRemovable): #撞障碍物
            reward1+=rewardValue["reward-2"]
        elif cur_map[x+1][y]>=BombMinNum or cur_map[x+1][y]==Mapcode.BombEnemyHuman.value:  #撞炸弹
            reward1+=rewardValue["reward-3"]    
        
    #第二步
    if action2 == ActionType.MOVE_UP:
        if cur_map[px1-1][py1] in (Mapcode.BlockRemovable,Mapcode.BlockUnRemovable): #撞障碍物
            reward1+=rewardValue["reward-2"]
        elif cur_map[px1-1][py1]>=BombMinNum or cur_map[px1-1][py1]==Mapcode.BombEnemyHuman.value:  #撞炸弹
            reward1+=rewardValue["reward-3"]    
    elif action2 == ActionType.MOVE_LEFT:
        if cur_map[px1][py1-1] in (Mapcode.BlockRemovable,Mapcode.BlockUnRemovable): #撞障碍物
            reward1+=rewardValue["reward-2"]
        elif cur_map[px1][py1-1]>=BombMinNum or cur_map[px1][py1-1]==Mapcode.BombEnemyHuman.value:  #撞炸弹
            reward1+=rewardValue["reward-3"]    
    elif action2 == ActionType.MOVE_RIGHT:
        if cur_map[px1][py1+1] in (Mapcode.BlockRemovable,Mapcode.BlockUnRemovable): #撞障碍物
            reward1+=rewardValue["reward-2"]
        elif cur_map[px1][py1+1]>=BombMinNum or cur_map[px1][py1+1]==Mapcode.BombEnemyHuman.value:  #撞炸弹
            reward1+=rewardValue["reward-3"]    
    elif action2 == ActionType.MOVE_DOWN:
        if cur_map[px1+1][py1] in (Mapcode.BlockRemovable,Mapcode.BlockUnRemovable): #撞障碍物
            reward1+=rewardValue["reward-2"]
        elif cur_map[px1+1][py1]>=BombMinNum or cur_map[px1+1][py1]==Mapcode.BombEnemyHuman.value:  #撞炸弹
            reward1+=rewardValue["reward-3"]    
    
    return reward1


def awayFromPlayer(cur_resp:PacketResp,action:tuple,cur_map,cur_player_me:PlayerInfo,cur_player_enemy:PlayerInfo)->int:
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
        return rewardValue["reward-2"]
    elif distance1<distance2:  #远离了合适
        return rewardValue["reward2"]
    else:
        return 0