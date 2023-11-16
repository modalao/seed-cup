import torch
import torch.nn as nn


class MLP(torch.nn.Module):

    def __init__(self, obs_size, n_act):
        super().__init__()
        self.mlp = self.__mlp(obs_size, n_act)

    def __mlp(self, obs_size, n_act):
        return torch.nn.Sequential(
            torch.nn.Linear(obs_size, 128),
            torch.nn.ReLU(),
            torch.nn.Linear(128, 64),
            torch.nn.ReLU(),
            torch.nn.Linear(64, n_act)
        )

    def forward(self, x_map, x_player):
        """
        x_map: (B, 15, 15)
        x_player: (B, 15)
        """
        # x_map = torch.stack(x_map, dim=0)  # (B, 15, 15)
        print(x_map.shape)
        B = x_map.shape[0]
        x_map = x_map.reshape((B, 1, -1)).squeeze(dim=1)  # (B, 225)
        # print(x_map.shape)
        # x_player = torch.stack(x_player, dim=0)  # (B, 15)
        # print(x_player.shape)
        x = torch.concat((x_map, x_player), dim=1)
        # print(x.shape)

        return self.mlp(x)


class SimpleCNN(nn.Module):
    def __init__(self, conv_output_dim, fc_output_dim, n_act) -> None:
        super().__init__()
        self.conv_output_dim = conv_output_dim
        self.fc_output_dim = fc_output_dim

        self.conv1 = nn.Conv2d(in_channels=1, out_channels=3, kernel_size=2, stride=1)
        self.relu = nn.ReLU()
        self.maxpool = nn.MaxPool2d(kernel_size=2, stride=2)
        self.fc1 = nn.Linear(3 * 7 * 7, conv_output_dim)  # Adjust the output size based on your requirements

        self.fc2 = torch.nn.Linear(15, fc_output_dim)
        self.relu2 = torch.nn.ReLU()

        self.final_fc1 = nn.Linear(self.fc_output_dim + self.conv_output_dim, 128)
        self.final_relu1 = nn.ReLU()
        self.final_fc2 = nn.Linear(128, n_act)


    def cnn(self, x):
        """
        x:(B, 15, 15)
        """
        B = x.shape[0]
        x = x.view(B, 1, 15, 15)
        x = self.conv1(x)
        x = self.relu(x)
        x = self.maxpool(x)
        x = x.view(x.size(0), -1)  # Flatten the tensor
        x = self.fc1(x)
        return x
    
    def fc(self, x):
        """
        x: (B, 15)
        """
        return self.relu2(self.fc2(x))

    def final_fc(self, x):
        return self.final_fc2(self.final_relu1(self.final_fc1(x)))
    
    def forward(self, x_map, x_player):
        """
        x_map: (B, 15, 15)
        x_player: (B, 15)
        """
        x_map_flat = self.cnn(x_map)  # (B, conv_output_dim)
        x_player = self.fc(x_player)  # (B, fc_output_dim)

        x = torch.concat((x_map_flat, x_player), dim=1)  # (B, conv_output_dim+fc_output_dim)
        return self.final_fc(x)


        


if __name__ == '__main__':
    net = MLP(240, 36)
    B = 3
    x_map = tuple([torch.rand(size=(15, 15)) for _ in range(B)])
    x_player = tuple([torch.rand(15) for _ in range(B)])
    res = net(x_map, x_player)