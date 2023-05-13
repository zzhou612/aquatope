import torch
import torch.nn as nn


class Predict(nn.Module):
    def __init__(
        self,
        n_extracted_features: int,
        n_external_features: int,
        n_output_steps: int,
        p: float,
        encoder_decoder: nn.Module,
    ):
        super(Predict, self).__init__()
        self.n_extracted_features = n_extracted_features
        self.encoder = encoder_decoder.model["encoder"].eval()
        self.model = nn.Sequential(
            nn.Linear(
                self.n_extracted_features + n_external_features,
                64,
            ),
            nn.Dropout(p),
            nn.ReLU(),
            nn.Dropout(p),
            nn.Linear(64, 16),
            nn.ReLU(),
            nn.Dropout(p),
            nn.Linear(16, n_output_steps),
        )

    def forward(self, x):
        x_input, external = x
        extracted = self.encoder(x_input).view(-1, self.n_extracted_features)
        # print("self.encoder(x_input).shape: ", self.encoder(x_input).shape)
        # print("extracted.shape: ", extracted.shape)
        # print("external.shape: ", external.shape)
        x_concat = torch.cat([extracted, external], dim=-1)
        out = self.model(x_concat)
        return out
