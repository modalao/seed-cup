import copy
from playerInfo import PlayerInfo
from mapcode import Mapcode
from resp import PacketResp
from req import *
from config import *
from actionresp import *


#上下左右移动
next_position = [[0,-1],[0,1],[1,0],[-1,0]]
SAFEDISTANCE = 7  #和敌人保持的安全距离
BombMinNum = Mapcode.BombBase.value #炸弹的最小编号
px1=0
py1=0
px2=0
py2=0
range_x = config.get("map_size")
range_y = config.get("map_size")
tem_map = [[Mapcode.NullBlock.value for _ in range(range_x)] for __ in range(range_y)]
now_map=[[Mapcode.NullBlock.value for _ in range(range_x)] for __ in range(range_y)]
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
    "reward10" : 10,
    "reward-10" : -10,
}


def optimize(x:int,y:int,cur_map,action1,action2,cur_player_me:PlayerInfo):
    px1,py1 = nextPositionActual(x,y,action1,cur_map) #action1后我的位置
    tem_map = actionStepMap(action1,cur_map,x,y,cur_player_me.bomb_range) #action1后的地图
    # print('action1 map:')
    # outputMap(tem_map)
    px2,py2 = nextPositionActual(px1,py1,action2,tem_map) #action2后我的位置
    now_map = actionStepMap(action2,tem_map,px1,py1,cur_player_me.bomb_range) #action2后的地图
    # print('action2 map:')
    # outputMap(now_map)

#2    
#形参为cur_resp当前resp报文，action为该回合的两个动作，cur_map 当前状态地图信息,cur_player_me 我方信息，cur_player_enemy 敌方信息
def rewardBomb(cur_resp:PacketResp,action:tuple,cur_map,cur_player_me:PlayerInfo,cur_player_enemy:PlayerInfo)->int:
    '''
    炸弹相关reward
    '''
    reward1 = 0
    action1 = action[0]
    action2 = action[1]
    x=cur_player_me.position_x
    y=cur_player_me.position_y
    #first step
    #px1,py1 = nextPositionActual(cur_player_me.position_x,cur_player_me.position_y,action1,cur_map)
    #tem_map = actionStepMap(action1,cur_map,x,y,cur_player_me.bomb_range) #action1后的地图
    #px2,py2 = nextPositionActual(px1,py1,action2,tem_map)
    #只能放一个炸弹，暂时限制
    if cur_player_me.bomb_max_num - cur_player_me.bomb_now_num == 1 and (action1 == ActionType.PLACED or action2 == ActionType.PLACED):
        return rewardValue["reward-10"]
    #没有炸弹时，不要放炸弹
    if(cur_player_me.bomb_now_num ==0 and (action1 == ActionType.PLACED or action2 ==ActionType.PLACED)):
        return rewardValue["reward-10"]
    #有炸弹的位置不能重复放炸弹
    if cur_map[x][y] == Mapcode.BombMyHuman.value and action1 == ActionType.PLACED:
        return rewardValue["reward-10"]
    if action1 == ActionType.PLACED  and action2 == ActionType.PLACED:
        return rewardValue["reward-10"]
    if tem_map[px1][py1] == Mapcode.BombMyHuman.value and action2 == ActionType.PLACED:
        return rewardValue["reward-10"]
    
    elif action1 == ActionType.PLACED and (px2 != px1 or py2 != py1):#放了炸弹并且走开了
        reward1+=rewardValue["reward5"]
    elif action1 == ActionType.PLACED and px1 == px2 and py2 == py1 :#放了炸弹但是没有走开
        reward1+=rewardValue["reward-3"]
    #炸道具惩罚
    if action1 == ActionType.PLACED:
        for next_item in next_position:
            tx = x+next_item[0]
            ty = y+next_item[1]
            if checkoutofrange(tx,ty)  :
                continue
            if cur_map[tx][ty] in (Mapcode.ItemBombRange.value,Mapcode.ItemHp.value,Mapcode.ItemInvencible.value,Mapcode.ItemNum.value,Mapcode.ItemShield.value):
                reward1 += rewardValue["reward-2"]
            
    if action2 == ActionType.PLACED:
        for next_item in next_position:
            tx = px1+next_item[0]
            ty = py1+next_item[1]
            if checkoutofrange(tx,ty):
                continue
            if tem_map[tx][ty] in (Mapcode.ItemBombRange.value,Mapcode.ItemHp.value,Mapcode.ItemInvencible.value,Mapcode.ItemNum.value,Mapcode.ItemShield.value):
                reward1 +=  rewardValue["reward-2"]  
    #炸removable障碍物奖励
    if action1 == ActionType.PLACED:
        for next_item in next_position:
            tx = x+next_item[0]
            ty = y+next_item[1]
            if checkoutofrange(tx,ty):
                continue
            if cur_map[tx][ty] == Mapcode.BlockRemovable.value:
                reward1 += rewardValue["reward4"]
    if action2 == ActionType.PLACED:
        for next_item in next_position:
            tx = px1+next_item[0]
            ty = py1+next_item[1]
            if checkoutofrange(tx,ty):
                continue
            if tem_map[tx][ty] == Mapcode.BlockRemovable.value:
                reward1 += rewardValue["reward4"]
    #TODO 其他 
    
    return reward1

#1    
def awayFromBomb(cur_resp:PacketResp,action:tuple,cur_map,cur_player_me:PlayerInfo,cur_player_enemy:PlayerInfo)->int:
    '''
    远离炸弹reward,不考虑放炸弹的情况，只考虑有炸弹躲炸弹
    '''    
    action1 = action[0]
    action2 = action[1]
    x=cur_player_me.position_x
    y=cur_player_me.position_y
    
    #遍历地图，找到action之前的炸弹
    size=config.get("map_size")
    m_distance1=0 #action之前的曼氏距离，若累计和为0则表示不在爆炸范围内
    flag1 = 0
    m_distance2=0 #同上
    flag2 = 0 
    reward1=0
    for i in range(size):
        for j in range(size):
            if(cur_map[i][j]>=Mapcode.BombBase.value): #找到炸弹
                range1 = (cur_map[i][j]- Mapcode.BombBase.value)/Mapcode.BombDelta.value #炸弹范围
                if (x>=i-range1 and x<=i+range1 and y==j or x==i and y>=j-range1 and y<=j+range1):
                    flag1 = 1 #在被炸范围内
                    m_distance1+=distance(i,j,x,y)
    #遍历地图，找到action之后的炸弹
    for i in range(size):
        for j in range(size):
            if(now_map[i][j]>=Mapcode.BombBase.value): #找到炸弹
                range1 = (now_map[i][j]- Mapcode.BombBase.value)/Mapcode.BombDelta.value #炸弹范围
                if (px2>=i-range1 and px2<=i+range1 and py2==j or px2==i and py2>=j-range1 and py2<=j+range1):
                    flag2 = 1
                    m_distance2+=distance(i,j,px2,py2)  
    #case 
    if(flag1 ==0 and flag2==0): 
        reward1+=0
    elif(flag1>0 and flag2==0):
        reward1+=rewardValue["reward4"]
    elif(flag1==0 and flag2>0):
        if action1 == ActionType.PLACED or action2 == ActionType.PLACED:#如果是当前动作放的炸弹，则不扣分
            pass
        else :
            reward1+=rewardValue["reward-3"]
    else:
        if(m_distance1>=m_distance2):
            reward1+=rewardValue["reward-3"]
        elif(m_distance1<m_distance2):
            reward1+=rewardValue["reward4"]
    return reward1        

#3
def nearItem(cur_resp:PacketResp,action:tuple,cur_map,cur_player_me:PlayerInfo,cur_player_enemy:PlayerInfo)->int:
    '''
    捡道具reward
    '''
    action1=action[0]
    action2=action[1]  
    x = cur_player_me.position_x
    y = cur_player_me.position_y
    #px1,py1 = nextPositionActual(cur_player_me.position_x,cur_player_me.position_y,action1,cur_map)  #action1后我的位置
    reward1=0
    if cur_map[px1][py1] in (Mapcode.ItemBombRange.value,Mapcode.ItemHp.value,Mapcode.ItemInvencible.value,Mapcode.ItemNum.value,Mapcode.ItemShield.value):
        reward1+=rewardValue["reward5"]  #action1就捡到了道具，非常好
    else:
        reward1+=0
    #now_map = actionStepMap(action1,cur_map,x,y,cur_player_me.bomb_range) #action1后地图
    #px2,py2 = nextPositionActual(px1,py1,action2,now_map)  #action2后我的位置
    if tem_map[px2][py2] in (Mapcode.ItemBombRange.value,Mapcode.ItemHp.value,Mapcode.ItemInvencible.value,Mapcode.ItemNum.value,Mapcode.ItemShield.value):
        reward1+=rewardValue["reward5"]  #action2捡到道具，非常好
    else: 
        reward1+=0
    return reward1
    #TODO 实现靠近道具

#4    
def collideWall(cur_resp:PacketResp,action:tuple,cur_map,cur_player_me:PlayerInfo,cur_player_enemy:PlayerInfo)->int:
    '''
    撞墙reward
    '''
    reward1=0
    # print("collideWall")
    action1 = action[0]
    action2 = action[1]
    x = cur_player_me.position_x
    y = cur_player_me.position_y
    #两步的边界判断
    #px1,py1 = nextPositionActual(cur_player_me.position_x,cur_player_me.position_y,action1,cur_map)
    #now_map = actionStepMap(action1,cur_map,x,y,cur_player_me.bomb_range)

    #撞block判断,bomb,unremoveblock,removeblock
    if x==0 and action1 == ActionType.MOVE_UP or x == config.get("map_size")-1 and action1 == ActionType.MOVE_DOWN or \
    y == 0 and action1 == ActionType.MOVE_LEFT or y == config.get("map_size")-1 and action1 == ActionType.MOVE_RIGHT:
        # print("map border")
        reward1+=rewardValue["reward-2"]
    elif action1 == ActionType.MOVE_UP:
        if cur_map[x-1][y] in (Mapcode.BlockRemovable.value,Mapcode.BlockUnRemovable.value): #撞障碍物
            reward1+=rewardValue["reward-2"]
        elif cur_map[x-1][y]>=BombMinNum or cur_map[x-1][y]==Mapcode.BombEnemyHuman.value:  #撞炸弹
            reward1+=rewardValue["reward-3"]
        # print("up collide block")    
    elif action1 == ActionType.MOVE_LEFT:
        if cur_map[x][y-1] in (Mapcode.BlockRemovable.value,Mapcode.BlockUnRemovable.value) : #撞障碍物
            reward1+=rewardValue["reward-2"]
        elif cur_map[x][y-1]>=BombMinNum or cur_map[x][y-1]==Mapcode.BombEnemyHuman.value:  #撞炸弹
            reward1+=rewardValue["reward-3"]    
        # print("left collide block")    
    elif action1 == ActionType.MOVE_RIGHT:
        if cur_map[x][y+1] in (Mapcode.BlockRemovable.value,Mapcode.BlockUnRemovable.value): #撞障碍物
            reward1+=rewardValue["reward-2"]
        elif cur_map[x][y+1]>=BombMinNum or cur_map[x][y+1]==Mapcode.BombEnemyHuman.value:  #撞炸弹
            reward1+=rewardValue["reward-3"]  
        # print("right collide block")      
    elif action1 == ActionType.MOVE_DOWN:
        if cur_map[x+1][y] in (Mapcode.BlockRemovable.value,Mapcode.BlockUnRemovable.value): #撞障碍物
            reward1+=rewardValue["reward-2"]
        elif cur_map[x+1][y]>=BombMinNum or cur_map[x+1][y]==Mapcode.BombEnemyHuman.value:  #撞炸弹
            reward1+=rewardValue["reward-3"]    
        # print("down collide block")    
    #第二步
    if px1==0 and action2 == ActionType.MOVE_UP or px1 == config.get("map_size")-1 and action2 == ActionType.MOVE_DOWN or \
    py1 == 0 and action2 == ActionType.MOVE_LEFT or py1 == config.get("map_size")-1 and action2 == ActionType.MOVE_RIGHT:
        # print("map border")
        reward1+=rewardValue["reward-2"]
    elif action2 == ActionType.MOVE_UP:
        if tem_map[px1-1][py1] in (Mapcode.BlockRemovable.value,Mapcode.BlockUnRemovable.value): #撞障碍物
            reward1+=rewardValue["reward-2"]
            # print("collide block -2")
        elif tem_map[px1-1][py1]>=BombMinNum or tem_map[px1-1][py1]==Mapcode.BombEnemyHuman.value:  #撞炸弹
            reward1+=rewardValue["reward-3"]   
        # print("up collide block")     
    elif action2 == ActionType.MOVE_LEFT:
        if tem_map[px1][py1-1] in (Mapcode.BlockRemovable.value,Mapcode.BlockUnRemovable.value): #撞障碍物
            reward1+=rewardValue["reward-2"]
            # print("collide block -2")
        elif tem_map[px1][py1-1]>=BombMinNum or tem_map[px1][py1-1]==Mapcode.BombEnemyHuman.value:  #撞炸弹
            reward1+=rewardValue["reward-3"]    
        # print("left collide block")    
    elif action2 == ActionType.MOVE_RIGHT:
        if tem_map[px1][py1+1] in (Mapcode.BlockRemovable.value,Mapcode.BlockUnRemovable.value): #撞障碍物
            reward1+=rewardValue["reward-2"]
            # print("collide block -2")
        elif tem_map[px1][py1+1]>=BombMinNum or tem_map[px1][py1+1]==Mapcode.BombEnemyHuman.value:  #撞炸弹
            reward1+=rewardValue["reward-3"]  
        # print("right collide block")     
    elif action2 == ActionType.MOVE_DOWN:
        if tem_map[px1+1][py1] in (Mapcode.BlockRemovable.value,Mapcode.BlockUnRemovable.value): #撞障碍物
            reward1+=rewardValue["reward-2"]
            # print("collide block -2")
        elif tem_map[px1+1][py1]>=BombMinNum or tem_map[px1+1][py1]==Mapcode.BombEnemyHuman.value:  #撞炸弹
            reward1+=rewardValue["reward-3"]    
        # print("down collide block")    
    # print(f'reward = {reward1}')
    return reward1

#5
def awayFromPlayer(cur_resp:PacketResp,action:tuple,cur_map,cur_player_me:PlayerInfo,cur_player_enemy:PlayerInfo)->int:
    '''
    防守型，和敌人保持一段距离
    '''    
    action1 = action[0]
    action2 = action[1]
    x=cur_player_me.position_x
    y=cur_player_me.position_y   #当前自己位置 
    x1 = cur_player_enemy.position_x
    y1 = cur_player_enemy.position_y  #当前敌人位置
    #px1,py1 = nextPositionActual(cur_player_me.position_x,cur_player_me.position_y,action1,cur_map)  #action1后我的位置
    #now_map = actionStepMap(action1,cur_map,x1,y1,cur_player_me.bomb_range) #action1后地图
    #px2,py2=nextPositionActual(px1,py1,action2,now_map) #action2后我的位置
    distance1=distance(x,y,x1,y1) #移动前敌我距离
    distance2=distance(px2,py2,x1,y1) #移动后敌我距离
    if distance1>=SAFEDISTANCE and distance2>=SAFEDISTANCE:
        return 0
    elif distance1>distance2:  #靠近了不合适
        return rewardValue["reward-2"]
    elif distance1<distance2:  #远离了合适
        return rewardValue["reward2"]
    else:
        return 0