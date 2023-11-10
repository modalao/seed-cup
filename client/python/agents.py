import numpy as np
import torch
from utils import torchUtils
import copy

class DQNAgent(object):

    def __init__(self,q_func, optimizer, replay_buffer, batch_size, replay_start_size,update_target_steps, n_act, gamma=0.9, e_greed=0.1, e_greed_decay=0.995):
        '''
        :param q_func: Q函数
        :param optimizer: 优化器
        :param replay_buffer: 经验回放器
        :param batch_size:批次数量
        :param replay_start_size:开始回放的次数
        :param update_target_steps: 同步参数的次数
        :param n_act:动作数量
        :param gamma: 收益衰减率
        :param e_greed: 探索与利用中的探索概率
        '''
        self.pred_func = q_func
        self.target_func = copy.deepcopy(q_func)
        self.update_target_steps = update_target_steps

        self.global_step = 0

        self.rb = replay_buffer
        self.batch_size = batch_size
        self.replay_start_size = replay_start_size

        self.optimizer = optimizer
        self.criterion = torch.nn.MSELoss()

        self.n_act = n_act  # 动作数量
        self.gamma = gamma  # 收益衰减率
        self.epsilon = e_greed  # 探索与利用中的探索概率
        self.e_greed_decay = e_greed_decay
        
    def decay(self):
        self.epsilon = self.epsilon * self.e_greed_decay

    # 根据经验得到action
    def predict(self, obs):
        # obs = torch.FloatTensor(obs)
        Q_list = self.pred_func(obs[0].unsqueeze(0), obs[1].unsqueeze(0))
        action = int(torch.argmax(Q_list).detach().numpy())
        return action

    # 根据探索与利用得到action
    def act(self, obs):
        if np.random.uniform(0, 1) < self.epsilon:  #探索
            action = np.random.choice(self.n_act)
        else: # 利用
            action = self.predict(obs)
        return action

    def learn_batch(self, batch_map_state, batch_player_state, batch_action, batch_reward, 
                    batch_next_map_state, batch_next_player_state, batch_done):
        """
        batch_obs: ((tensor(15*15), tensor(15)), (), (), ...)
        """
        # predict_Q
        pred_Vs = self.pred_func(batch_map_state, batch_player_state)  # (B, n_act)
        # print(f'pred_Vs: {pred_Vs.shape}')
        action_onehot = torchUtils.one_hot(batch_action, self.n_act)  # (B, n_act)
        predict_Q = (pred_Vs * action_onehot).sum(1)  #(B)
        # print(f'predict_Q: {predict_Q.shape}')
        # target_Q
        next_pred_Vs = self.target_func(batch_next_map_state, batch_next_player_state)  # (B, n_act)
        # print(f'next_pred_Vs: {next_pred_Vs.shape}')
        best_V = next_pred_Vs.max(1)[0]  # (B)
        # print(f'best_V: {best_V.shape}')
        target_Q = batch_reward + (1 - batch_done) * self.gamma * best_V  # (B)
        # print(f'target_Q: {target_Q.shape}')

        # 更新参数
        self.optimizer.zero_grad()
        loss = self.criterion(predict_Q, target_Q)
        loss.backward()
        self.optimizer.step()

    
    def preprocess_rb_data(self, obs:tuple, action, reward, next_obs:tuple, done):
        """
        return value are all tensors
        """
        # print(obs)
        map_state, player_state = obs
        next_map_state, next_player_state = next_obs
        done = int(done)
        return (map_state, player_state, action, reward, next_map_state, next_player_state, done)
        

    def learn(self, obs, action, reward, next_obs, done):
        self.global_step += 1
        self.rb.append(self.preprocess_rb_data(obs, action, reward, next_obs, done))
        if len(self.rb) > self.replay_start_size and self.global_step % self.rb.num_steps == 0:
            self.learn_batch(*self.rb.sample(self.batch_size))
        if self.global_step % self.update_target_steps==0:
            self.sync_target()

    def sync_target(self):
        for target_param, param in zip(self.target_func.parameters(), self.pred_func.parameters()):
            target_param.data.copy_(param.data)

