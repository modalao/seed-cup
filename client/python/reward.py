
from playerInfo import PlayerInfo
from mapcode import Mapcode
from resp import PacketResp

#TODO
#reward 范围[10,100],[-100,-10]
#形参为cur_resp当前resp报文，next_resp下一回合resp报文，action为该回合的两个动作，cur_map 当前状态地图信息,cur_player_me 我方信息，cur_player_enemy 敌方信息
def rewardBomb(cur_resp:PacketResp,next_resp:PacketResp,action:tuple,cur_map:Mapcode,cur_player_me:PlayerInfo,cur_player_enemy:PlayerInfo)->int:
        
        return 0
    
def rewardItem(cur_resp:PacketResp,next_resp:PacketResp,action:tuple,cur_map:Mapcode,cur_player_me:PlayerInfo,cur_player_enemy:PlayerInfo)->int:
        
        return 0
    
def awayFromBomb(cur_resp:PacketResp,next_resp:PacketResp,action:tuple,cur_map:Mapcode,cur_player_me:PlayerInfo,cur_player_enemy:PlayerInfo)->int:
        
        return 0

def nearItem(cur_resp:PacketResp,next_resp:PacketResp,action:tuple,cur_map:Mapcode,cur_player_me:PlayerInfo,cur_player_enemy:PlayerInfo)->int:
        
        return 0
    