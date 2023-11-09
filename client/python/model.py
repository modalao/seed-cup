import torch


class MLP(torch.nn.Module):

    def __init__(self, obs_size, n_act):
        super().__init__()
        self.mlp = self.__mlp(obs_size, n_act)

    def __mlp(self, obs_size, n_act):
        return torch.nn.Sequential(
            torch.nn.Linear(obs_size, 512),
            torch.nn.ReLU(),
            torch.nn.Linear(512, 256),
            torch.nn.ReLU(),
            torch.nn.Linear(256, n_act)
        )

    def forward(self, x):
        return self.mlp(x)

if __name__ == '__main__':
    pass