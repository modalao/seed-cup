from model import MLP
import replay_buffers
import agents
import env_manager

import torch

class TrainManager():

    def __init__(self,
                 env,  #环境
                 episodes = 1000,  #轮次数量
                 batch_size = 32,  #每一批次的数量
                 num_steps = 4,  #进行学习的频次
                 memory_size = 2000,  #经验回放池的容量
                 replay_start_size = 200,  #开始回放的次数
                 lr = 0.001,  #学习率
                 gamma = 0.9,  #收益衰减率
                 e_greed = 0.5  #探索与利用中的探索概率
                 ):
        self.env = env
        self.episodes = episodes

        n_act = env.n_act
        input_shape = env.encode_shape  # TODO: according to EnvManager
        q_func = MLP(input_shape, n_act)
        optimizer = torch.optim.AdamW(q_func.parameters(), lr=lr)
        rb = replay_buffers.ReplayBuffer(memory_size, num_steps)

        self.agent = agents.DQNAgent(
            q_func = q_func,
            optimizer = optimizer,
            replay_buffer = rb,
            batch_size = batch_size,
            replay_start_size = replay_start_size,
            n_act = n_act,
            gamma = gamma,
            e_greed = e_greed)

    # 训练一轮游戏
    def train_episode(self):
        total_reward = 0
        obs = self.env.reset()  # TODO: according to EnvManager
        while True:
            action = self.agent.act(obs)
            cur_obs, next_obs, reward, done = self.env.step(action)
            total_reward += reward
            self.agent.learn(cur_obs, action, reward, next_obs, done)
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
    env = env_manager.EnvManager()
    tm = TrainManager(env)
    tm.train()