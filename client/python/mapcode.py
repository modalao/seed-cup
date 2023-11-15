from enum import Enum
from resp import *


class Mapcode(Enum):#player  炸弹爆炸的时间没有编码？
    #矩阵中值对应的含义
    BlockRemovable = 20
    BlockUnRemovable = 21
    #bomb 爆炸范围为range 对应矩阵值为BombBase+bombrane*BombDelta
    #炸弹
    BombBase = 40 
    BombDelta = 1
    
    BombMyHuman = 40 #my 人和炸弹在同一个位置
    BombEnemyHuman = -40 #enemy 人和炸弹在一个位置
    
    NullBlock = 0 
    BombedBlock = 1 #爆炸格
    ItemHp = 11
    ItemNum = 11
    ItemShield = 11
    ItemBombRange = 11
    ItemInvencible = 11
    # ItemHp = 11
    # ItemNum = 12
    # ItemShield = 13
    # ItemBombRange = 14
    # ItemInvencible = 15
    #ItemSpeed = 8 初赛不设置
    
    # players 人物
    enemy = -30
    me = 30


    def calulate(obj:Obj, enemy =False,last_bomb = False,HumanBomb=False) -> int:
        if HumanBomb: #人和炸弹
            if enemy:
                value = Mapcode.BombEnemyHuman.value
            else :
                value = Mapcode.BombMyHuman.value
        elif last_bomb:#爆炸
            value = Mapcode.BombedBlock.value
        
        elif obj is None or obj.type == ObjType.Null:
            value = Mapcode.NullBlock.value
        
        elif obj.type == ObjType.Player:
            if enemy:
                value = Mapcode.enemy.value
            else :
                value = Mapcode.me.value

        elif obj.type== ObjType.Bomb:
            value = Mapcode.BombBase.value+obj.property.bomb_range*Mapcode.BombDelta.value
        
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