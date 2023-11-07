from enum import Enum
from resp import *


class Mapcode(Enum):#player 放置炸弹状态是否编码？？
    #矩阵中值对应的含义
    BlockRemovable = 2
    BlockUnRemovable = -2
    #bomb 爆炸范围为range 对应矩阵值为BombBase+range
    BombBase = 10
    NullBlock = 0 
    BombedBlock = 9 #爆炸格
    ItemHp = 3
    ItemNum = 4
    ItemShield = 5
    ItemBombRange = 6
    ItemInvencible = 7
    #ItemSpeed = 8 初赛不设置
    # players
    enemy = -1
    me = 1


    def calulate(obj:Obj, enemy =False,last_bomb = False) -> None:
        if last_bomb:
            value = Mapcode.BombedBlock.value
        
        elif obj is None or obj.type == ObjType.Null:
            value = Mapcode.NullBlock.value
        
        elif obj.type == ObjType.Player:
            if enemy:
                value = Mapcode.enemy.value
            else :
                value = Mapcode.me.value

        elif obj.type== ObjType.Bomb:
            value = Mapcode.BombBase.value+obj.property.bomb_range
        
        elif obj.type == ObjType.Block:
            if obj.property.removable :
                value = Mapcode.BlockRemovable.value
            elif not obj.property.removable:
                value = Mapcode.BlockUnRemovable.value
        
        elif obj.type == ObjType.Item:
            if obj.property.item_type == 1 :
                value = Mapcode.ItemBombRange.value
            elif obj.property.item_type == 2 :
                value = Mapcode.ItemNum.value
            elif obj.property.item_type == 3:
                value = Mapcode.ItemHp.value
            elif obj.property.item_type == 4:
                value = Mapcode.ItemInvencible.value
            else :
                value = Mapcode.ItemShield.value
        return value
    @property
    def value(self):
        return self._value_