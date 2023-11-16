import random
import collections
from torch import FloatTensor
import torch

class ReplayBuffer(object):
    def __init__(self, max_size, num_steps=1, seqnum=5):
        self.buffer = collections.deque(maxlen=max_size)
        self.num_steps  = num_steps
        self.seqnum = seqnum

    def append(self, exp):
        self.buffer.append(exp)

    def sample(self, batch_size):
        print('sample from buffer')
        map_states, player_states, actions, rewards, \
        next_map_states, next_player_states, dones = [], [], [], [], [], [], []
        for i in range(batch_size):
            finish = random.randint(self.seqnum, len(self.buffer) - 1)
            begin = finish - self.seqnum
            data = list(self.buffer)[begin:finish]
            map_state, player_state, action, reward, next_map_state, next_player_state, done = zip(*data)

            map_states.append(torch.stack(map_state, dim=0))
            player_states.append(torch.stack(player_state, dim=0))
            next_map_states.append(torch.stack(next_map_state, dim=0))
            next_player_states.append(torch.stack(next_player_state, dim=0))
            actions.append(action)
            rewards.append(reward)
            dones.append(done)
            
        return torch.stack(map_states, dim=0), torch.stack(player_states, dim=0), \
            torch.FloatTensor(actions), torch.FloatTensor(rewards), \
                torch.stack(next_map_states, dim=0), torch.stack(next_player_states, dim=0), \
                    torch.FloatTensor(dones)

        start_index = random.randint(0, len(self.buffer) - batch_size)
        mini_batch = list(self.buffer)[start_index:start_index + batch_size + 1]
        # mini_batch = random.sample(self.buffer, batch_size)
        map_state, player_state, action, reward, next_map_state, next_player_state, done = zip(*mini_batch)
        map_state = torch.stack(map_state, dim=0)
        player_state = torch.stack(player_state, dim=0)
        next_map_state = torch.stack(next_map_state, dim=0)
        next_player_state = torch.stack(next_player_state, dim=0)
        action = torch.FloatTensor(action)
        reward = torch.FloatTensor(reward)
        done = torch.FloatTensor(done)
        return map_state, player_state, action, reward, next_map_state, next_player_state, done

    def __len__(self):
        return len(self.buffer)

if __name__ == '__main__':
    a=collections.deque(maxlen=3)
    print(a)
    a.append((1,1))
    a.append((2,2))
    a.append((3,3))
    a.append((4,4))
    print(a)
    state, action = zip(*a)
    print(state, action)
