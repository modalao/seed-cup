import torch

class PlayerInfo:
    #记录个人信息,用于神经网络和reward计算
    def __init__(
        self,
        position_x :int =0,
        position_y :int =0,
        position :int =0,# x*15+y
        game_over:bool =False,# whether game over
        player_id: int = -1,
        player_is_me : bool =False ,#is me or enemy
        alive: bool = True,
        hp: int = 1,
        shield_time: int = 0,
        invincible_time: int = 0,  
        score: int = 0,           
        bomb_range: int = 1,       
        bomb_max_num: int = 2, #最多可使用的bomb    
        bomb_now_num: int = 2,#当前可用炸弹数bomb
        speed: int = 2,  
    ) -> None:
        self.position_x=position_x
        self.position_y = position_y
        self.position = position
        self.player_is_me = player_is_me
        self.player_id = player_id
        self.alive = alive
        self.hp = hp
        self.shield_time = shield_time
        self.invincible_time = invincible_time
        self.score = score
        self.bomb_range = bomb_range
        self.bomb_max_num = bomb_max_num
        self.bomb_now_num = bomb_now_num
        self.speed = speed
        self.game_over =game_over
    
    def update(
        self,
        position_x :int =0,
        position_y :int =0,
        position :int =0,# x*15+y
        game_over:bool =False,# whether game over
        player_id: int = -1,
        player_is_me : bool =False ,#is me or enemy
        alive: bool = True,
        hp: int = 1,
        shield_time: int = 0,
        invincible_time: int = 0,  
        score: int = 0,           
        bomb_range: int = 1,       
        bomb_max_num: int = 2, #最多可使用的bomb    
        bomb_now_num: int = 0,#当前用了多少bomb
        speed: int = 2,  
    ):
        self.position_x=position_x
        self.position_y = position_y
        self.position = position
        self.player_is_me = player_is_me
        self.player_id = player_id
        self.alive = alive
        self.hp = hp
        self.shield_time = shield_time
        self.invincible_time = invincible_time
        self.score = score
        self.bomb_range = bomb_range
        self.bomb_max_num = bomb_max_num
        self.bomb_now_num = bomb_now_num
        self.speed = speed
        self.game_over =game_over


    def to_tensor(self):
        info_list = [self.position_x,
                     self.position_y,
                     self.position,
                     self.player_is_me,
                     self.player_id,
                     self.alive,
                     self.hp,
                     self.shield_time,
                     self.invincible_time,
                     self.score,
                     self.bomb_range,
                     self.bomb_max_num,
                     self.bomb_now_num,
                     self.speed,
                     self.game_over]
        return torch.Tensor(info_list)
    