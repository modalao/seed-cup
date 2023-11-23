#不可越过物体
import copy
from req import ActionType
from mapcode import Mapcode
from config import *


unmovable_block = [Mapcode.BlockRemovable.value,Mapcode.BlockUnRemovable.value,Mapcode.BombEnemyHuman.value]
unmovable_block.extend([c for c in range(Mapcode.BombBase.value,Mapcode.BombBase.value+20)])


#上下左右移动 next position和next action对应移动
next_position = [[0,-1],[0,1],[1,0],[-1,0]]
next_action = [ActionType.MOVE_LEFT,ActionType.MOVE_RIGHT,ActionType.MOVE_DOWN,ActionType.MOVE_UP]
def outputMap(map):
    '''
    输出map
    '''
    for i in range(config.get("map_size")):
        for j in range(config.get("map_size")):
            print(f'{map[i][j]:>5d} ',end='')
        print()


def nextPositionIdeal(x:int, y:int, action:ActionType):
    '''
    经过动作后坐标x,y,可能不是实际坐标，因为有边界和障碍物
    '''
    if action == ActionType.MOVE_DOWN:
        return x + 1, y
    elif action == ActionType.MOVE_UP:
        return x - 1, y
    elif action == ActionType.MOVE_LEFT:
        return x, y - 1
    elif action == ActionType.MOVE_RIGHT:
        return x, y + 1
    else :
        return x, y
    
def nextPositionActual(x:int, y:int, action:ActionType,cur_map):
    '''
    经过动作后坐标x,y,实际坐标
    '''
    # global unmovable_block
    # print(unmovable_block)#
    if action == ActionType.SILENT:
        return x,y
    elif action == ActionType.PLACED:
        return x,y
    elif action == ActionType.MOVE_DOWN:
        if x == config.get("map_size")-1 or cur_map[x+1][y] in unmovable_block:
            return x,y
        else :
            return x+1,y
    elif action == ActionType.MOVE_UP:
        if x == 0 or cur_map[x-1][y] in unmovable_block:
            return x,y
        else :
           return x-1,y
    elif action == ActionType.MOVE_LEFT:
        # print(unmovable_block)#
        if y == 0 or cur_map[x][y-1] in unmovable_block:
            return x,y
        else :
            return x,y-1
    else :
        if y == config.get("map_size")-1 or cur_map[x][y+1] in unmovable_block:
            return x,y
        else :
            return x,y+1

def actionStepMap(action:ActionType,cur_map,x:int,y:int,bomb_range:int):#action动作，cur_map地图，x,y玩家坐标,map需要深拷贝
    '''
    经过一个动作后的map图
    '''
    now_map = copy.deepcopy(cur_map)
    if action == ActionType.SILENT:
        return now_map
    elif action == ActionType.PLACED:
        now_map[x][y] = Mapcode.BombMyHuman.value
    elif action == ActionType.MOVE_DOWN:
        if x == config.get("map_size")-1 or now_map[x+1][y] in unmovable_block:
            pass
        else :
            now_map[x+1][y] = Mapcode.me.value
            if now_map[x][y] == Mapcode.BombMyHuman.value:
                now_map[x][y] = Mapcode.BombBase.value + bomb_range*Mapcode.BombDelta.value
            else :
                now_map[x][y] = Mapcode.NullBlock.value
    elif action == ActionType.MOVE_UP:
        if x == 0 or now_map[x-1][y] in unmovable_block:
            pass
        else :
            now_map[x-1][y] = Mapcode.me.value
            if now_map[x][y] == Mapcode.BombMyHuman.value:
                now_map[x][y] = Mapcode.BombBase.value + bomb_range*Mapcode.BombDelta.value
            else :
                now_map[x][y] = Mapcode.NullBlock.value
    elif action == ActionType.MOVE_LEFT:
        if y == 0 or now_map[x][y-1] in unmovable_block:
            pass
        else :
            now_map[x][y-1] = Mapcode.me.value
            if now_map[x][y] == Mapcode.BombMyHuman.value:
                now_map[x][y] = Mapcode.BombBase.value + bomb_range*Mapcode.BombDelta.value
            else :
                now_map[x][y] = Mapcode.NullBlock.value
    else :
        if y == config.get("map_size")-1 or now_map[x][y+1] in unmovable_block:
            pass
        else :
            now_map[x][y+1] = Mapcode.me.value
            if now_map[x][y] == Mapcode.BombMyHuman.value:
                now_map[x][y] = Mapcode.BombBase.value + bomb_range*Mapcode.BombDelta.value
            else :
                now_map[x][y] = Mapcode.NullBlock.value
    return now_map

def checkoutofrange(x:int,y:int)->bool:
    if x<0 or y < 0 or x >=config.get("map_size") or y >=config.get("map_size"):
        return True
    return False


def distance(me_x:int,me_y:int,enemy_x:int,enemy_y:int)->int:
    '''
    计算敌人和自己的距离
    '''
    if me_x>=enemy_x:
        dis_x=me_x-enemy_x
    else: 
        dis_x=enemy_x-me_x
    if me_y>=enemy_y:
        dis_y=me_y-enemy_y
    else:
        dis_y=enemy_y-me_y
    return dis_x+dis_y


def checkBombValid(map,player_x:int,player_y:int,bomb_x:int,bomb_y:int,bomb_range:int)->bool:
    '''
    判断当前player位置是否可以通过移动躲掉炸弹
    '''
    #先判断当前是否可以炸到
    flag = 0
    length = config.get("map_size")
    #炸弹炸的到的地方为1，否则为0
    bomb_map = [[0 for _ in range(length)] for __ in range(length)]
    bomb_map[bomb_x][bomb_y]= 1 
    for i in range(len(next_position)):
        next = next_position[i]
        deltax = next[0]
        deltay = next[1]
        for dis in range(1,bomb_range+1):
            tx = bomb_x+deltax*dis
            ty = bomb_y+deltay*dis
            if checkoutofrange(tx,ty) or map[tx][ty] in unmovable_block:
                #中间是否有障碍物隔着
                break
            bomb_map[tx][ty] = 1
            if tx == player_x and ty == player_y:
                #能炸到
                flag = 1 
                break
    if player_x == bomb_x and player_y == bomb_y:
        flag=1
    #初始位置就炸不到
    if flag == 0:
        return True        
    
    #炸的到，判断是否可以躲掉炸弹
    for i in range(len(next_position)):
        next = next_position[i]
        deltax = next[0]
        deltay = next[1]
        for dis in range(1,bomb_range+1):
            tx = player_x+deltax*dis
            ty = player_y+deltay*dis
            if checkoutofrange(tx,ty) or map[tx][ty] in unmovable_block:
                #中间是否有障碍物隔着
                break
            if bomb_map[tx][ty] == 0:
                #可以往一个方向走躲掉炸弹
                return True
            #该点向四周扩展一步，是否可以躲掉
            for next_temp in next_position:
                temx = tx+next_temp[0]
                temy = ty+next_temp[1]
                if checkoutofrange(temx,temy) or map[temx][temy] in unmovable_block:
                #中间是否有障碍物隔着
                    continue
                if bomb_map[temx][temy] == 0:
                    return True
    return False


def checkMovableBlock(map,bomb_x:int,bomb_y:int,bomb_range:int)->bool:
    '''
    检查放置了炸弹后是否可以得分
    '''
    for i in range(len(next_position)):
        next = next_position[i]
        deltax = next[0]
        deltay = next[1]
        for dis in range(1,bomb_range+1):
            tx = bomb_x+deltax*dis
            ty = bomb_y+deltay*dis
            #如果超出范围或者不可炸
            if checkoutofrange(tx,ty) or map[tx][ty] == Mapcode.BlockUnRemovable.value:
                break
            if map[tx][ty] == Mapcode.BlockRemovable.value:
                #遇到了可以炸的障碍物
                return True    
            
    return False
             

def checkItemAround(map,player_x,player_y)->ActionType:
    '''
    如果周围有道具，则直接捡
    '''
    distance = 3 #定义检测道具的范围
   
    for i in range(len(next_position)):
        for dis in range(1,distance+1):
            next = next_position[i]
            tx = player_x+next[0]*dis
            ty = player_y+next[1]*dis
            if checkoutofrange(tx,ty) or map[tx][ty] == Mapcode.BlockUnRemovable.value:
                break    
            if map[tx][ty] in (Mapcode.ItemBombRange.value,Mapcode.ItemHp.value,Mapcode.ItemInvencible.value,Mapcode.ItemNum.value,Mapcode.ItemShield.value):
                return  next_action[i]
    return ActionType.SILENT