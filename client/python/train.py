from model import MLP, SimpleCNN
import replay_buffers
import agents

import torch
import copy

class TrainManager():

    def __init__(self,
                 n_action,
                 conv_output_dim = 256, 
                 fc_output_dim = 32,
                 input_shape = 240,
                 batch_size = 32,  #每一批次的数量
                 num_steps = 4,  #进行学习的频次
                 memory_size = 2000,  #经验回放池的容量
                 replay_start_size = 200,  #开始回放的次数
                 update_target_steps = 200,#同步参数的次数
                 lr = 0.001,  #学习率
                 gamma = 0.9,  #收益衰减率
                 e_greed = 0.5  #探索与利用中的探索概率
                 ):
        self.n_action = n_action
        self.conv_output_dim = conv_output_dim
        self.fc_output_dim = fc_output_dim
        self.input_shape = input_shape
        self.cur_episode = 0
        self.obs = None
        self.total_reward = 0
        self.eval = False

        q_func = SimpleCNN(self.conv_output_dim, self.fc_output_dim, self.n_action)
        optimizer = torch.optim.AdamW(q_func.parameters(), lr=lr)
        rb = replay_buffers.ReplayBuffer(memory_size, num_steps)

        self.agent = agents.DQNAgent(
            q_func = q_func,
            optimizer = optimizer,
            replay_buffer = rb,
            batch_size = batch_size,
            replay_start_size = replay_start_size,
            update_target_steps = update_target_steps,
            n_act = self.n_action,
            gamma = gamma,
            e_greed = e_greed)
        
    
    def agent_act(self):
        return self.agent.act(self.obs)
    
    
    def agent_predict(self):
        return self.agent.predict(self.obs)
    

    def get_action(self):
        if self.eval:
            print(f'get action with no epsilon')
            return self.agent_predict()
        else:
            print(f'get action with epsilon')
            return self.agent_act()
        
    
    def eval_mode(self):
        self.eval = True

    def train_mode(self):
        self.eval = False


    def init_obs(self, first_obs):
        self.obs = first_obs

    def train_one_step(self, action, reward, next_obs, done):
        if self.eval:
            self.total_reward += reward
            self.obs = copy.deepcopy(next_obs)
        else:
            self.total_reward += reward
            self.agent.learn(self.obs, action, reward, next_obs, done)
            self.obs = copy.deepcopy(next_obs)
        if done:
            if self.eval:
                print('test reward = %.1f' % (self.total_reward))
            else:
                print('train reward = %.1f' % (self.total_reward))
            self.total_reward = 0


    # 训练一轮游戏
    def train_episode(self):
        total_reward = 0
        obs = self.env.reset()  # TODO: according to EnvManager
        while True:
            action = self.agent.act(obs)
            next_obs, reward, done = self.env.step(action)
            total_reward += reward
            self.agent.learn(obs, action, reward, next_obs, done)
            obs = next_obs  # TODO: don't need cur_obs in step() ?
            if done: break
        return total_reward
    

    # 测试一轮游戏
    def test_episode(self):
        total_reward = 0
        obs = self.env.reset()  # TODO: according to EnvManager
        while True:
            action = self.agent.predict(obs)
            cur_obs, next_obs, reward, done = self.env.step(action)
            total_reward += reward
            obs = next_obs  # TODO: don't need cur_obs in step() ?
            # self.env.render()  # TODO: according to EnvManager
            if done: break
        return total_reward


    def train(self):
        for e in range(self.episodes):
            ep_reward = self.train_episode()
            print('Episode %s: reward = %.1f' % (e, ep_reward))

            if e % 100 == 0:
                test_reward = self.test_episode()
                print('test reward = %.1f' % (test_reward))


if __name__ == '__main__':
    # env = env_manager.EnvManager()
    # tm = TrainManager(env)
    # tm.train()
    pass