import torch
import torch.nn as nn
from models import variational_dropout as vd


class VDEncoder(nn.Module):
    def __init__(self, in_features, out_features, p):
        super(VDEncoder, self).__init__()
        self.model = nn.ModuleDict(
            {
                "lstm1": vd.LSTM(in_features, 64, dropouto=p, batch_first=True),
                "lstm2": vd.LSTM(64, out_features, dropouto=p, batch_first=True),
                "relu": nn.ReLU(),
            }
        )

    def forward(self, x):
        out, _ = self.model["lstm1"](x)
        out, _ = self.model["lstm2"](out)
        out = self.model["relu"](out)

        return out


class VDDecoder(nn.Module):
    def __init__(self, p):
        super(VDDecoder, self).__init__()
        self.model = nn.ModuleDict(
            {
                "lstm1": vd.LSTM(1, 16, dropouto=p, batch_first=True),
                "lstm2": vd.LSTM(16, 1, dropouto=p, batch_first=True),
            }
        )

    def forward(self, x):
        out, _ = self.model["lstm1"](x)
        out, _ = self.model["lstm2"](out)

        return out


class VDEncoderDecoder(nn.Module):
    def __init__(self, in_features, input_steps, output_steps, p):
        super(VDEncoderDecoder, self).__init__()
        self.enc_in_features = in_features
        self.input_steps = input_steps
        self.output_steps = output_steps
        self.enc_out_features = 1
        self.invocation_col = 0
        self.p = p

        self.model = nn.ModuleDict(
            {
                "encoder": VDEncoder(
                    self.enc_in_features, self.enc_out_features, self.p
                ),
                "decoder": VDDecoder(self.p),
                "fc1": nn.Linear(self.input_steps + self.output_steps, 32),
                "fc2": nn.Linear(32, self.output_steps),
            }
        )

    def forward(self, x):
        out = self.model["encoder"](x)

        x_auxiliary = x[:, -self.output_steps :, [self.invocation_col]]
        decoder_input = torch.cat([out, x_auxiliary], dim=1)

        out = self.model["decoder"](decoder_input)
        out = self.model["fc1"](out.view(-1, self.input_steps + self.output_steps))
        out = self.model["fc2"](out)

        return out
