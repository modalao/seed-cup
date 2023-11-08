#不可越过物体
import copy
from req import ActionType
from mapcode import Mapcode
from config import *


unmovable_block = [Mapcode.BlockRemovable,Mapcode.BlockUnRemovable,Mapcode.BombBase]

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
    
def nextPositionActual(x:int, y:int, action:ActionType,cur_map:Mapcode):
    '''
    经过动作后坐标x,y,实际坐标
    '''
    if action == ActionType.SILENT:
        return x,y
    elif action == ActionType.PLACED:
        return x,y
    elif action == ActionType.MOVE_DOWN:
        if x == config.get("map_size")-1 or cur_map[x+1][y] in unmovable_block:
            return x,y
        else :
            return x-1,y
    elif action == ActionType.MOVE_UP:
        if x == 0 or cur_map[x-1][y] in unmovable_block:
            return x,y
        else :
           return x+1,y
    elif action == ActionType.MOVE_LEFT:
        if y == 0 or cur_map[x][y-1] in unmovable_block:
            return x,y
        else :
            return x,y-1
    else :
        if y == Config.get("map_size")-1 or cur_map[x][y+1] in unmovable_block:
            return x,y
        else :
            return x,y+1

def actionStepMap(action:ActionType,cur_map:Mapcode,x:int,y:int,bomb_range:int):#action动作，cur_map地图，x,y玩家坐标,map需要深拷贝
    '''
    经过一个动作后的map图
    '''
    now_map = copy.deepcopy(cur_map)
    if action == ActionType.SILENT:
        return now_map
    elif action == ActionType.PLACED:
        now_map[x][y] = Mapcode.BombHuman
    elif action == ActionType.MOVE_DOWN:
        if x == config.get("map_size")-1 or now_map[x+1][y] in unmovable_block:
            pass
        else :
            now_map[x+1][y] = Mapcode.me.value
            if now_map[x][y] == Mapcode.BombHuman:
                now_map[x][y] = Mapcode.BombBase.value + bomb_range
            else :
                now_map[x][y] = Mapcode.NullBlock
    elif action == ActionType.MOVE_UP:
        if x == 0 or now_map[x-1][y] in unmovable_block:
            pass
        else :
            now_map[x-1][y] = Mapcode.me.value
            if now_map[x][y] == Mapcode.BombHuman:
                now_map[x][y] = Mapcode.BombBase.value + bomb_range
            else :
                now_map[x][y] = Mapcode.NullBlock
    elif action == ActionType.MOVE_LEFT:
        if y == 0 or now_map[x][y-1] in unmovable_block:
            pass
        else :
            now_map[x][y-1] = Mapcode.me.value
            if now_map[x][y] == Mapcode.BombHuman:
                now_map[x][y] = Mapcode.BombBase.value + bomb_range
            else :
                now_map[x][y] = Mapcode.NullBlock
    else :
        if y == config.get("map_size")-1 or now_map[x][y+1] in unmovable_block:
            pass
        else :
            now_map[x][y+1] = Mapcode.me.value
            if now_map[x][y] == Mapcode.BombHuman:
                now_map[x][y] = Mapcode.BombBase.value + bomb_range
            else :
                now_map[x][y] = Mapcode.NullBlock
    return cur_map