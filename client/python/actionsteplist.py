from mapcode import Mapcode
from resp import *
from req import *


class ActionStepList:
    #记录
    def __init__(self,num):
        self.stepnum = num #保存action的个数
        self.actionsteplist=[(ActionType.SILENT,ActionType.SILENT)] * num
        
    def update(self,actiontuple:tuple = (ActionType.SILENT,ActionType.SILENT)):
        #更新一个操作
        self.actionsteplist.append(actiontuple)
        self.actionsteplist.remove(self.actionsteplist[0])
    
    def BombStep(self)->bool:
        """
        动作列表中，是否存在炸弹
        """
        for action in self.actionsteplist:
            action1 = action[0]
            action2 = action[1]
            if action1 == ActionType.PLACED or action2 == ActionType.PLACED:
                return True
        return False