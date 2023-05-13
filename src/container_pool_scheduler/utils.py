import json
import sys
from pathlib import Path
from typing import Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from models.encoder_decoder_dropout import *
from torch.utils.data import DataLoader

SCHED_DIR = Path(__file__).resolve().parents[0]
sys.path.append(str(SCHED_DIR))

import data


def get_device() -> str:
    if torch.cuda.is_available():
        device = "cuda:0"
    else:
        device = "cpu"

    return torch.device(device)


def train_encoder_decoder(
    device: str,
    model: nn.Module,
    datasets: dict,
    num_epochs: int,
    batch_size: int,
    learning_rate: float,
    use_tqdm: bool = False,
) -> Tuple[nn.Module, dict]:
    model.to(device)
    optimiser = optim.Adam(lr=learning_rate, params=model.parameters())
    dataloaders = data.get_dataloaders(datasets=datasets, train_batch_size=batch_size)

    loss_fn = F.mse_loss
    losses = {}
    losses["train"] = []
    losses["valid"] = []
    valid_loss = np.nan

    epochs = range(num_epochs)
    if use_tqdm:
        from tqdm.auto import tqdm

        epochs = tqdm(epochs)

    for epoch in epochs:
        model.train()
        for i, (x, y) in enumerate(dataloaders["train"]):
            x, y = x.to(device), y.to(device)
            out = model(x)

            optimiser.zero_grad()
            loss = loss_fn(out, y)
            loss.backward()
            optimiser.step()

            step = i * batch_size + len(x)
            losses["train"].append(
                [epoch * len(dataloaders["train"].dataset) + step, loss.item()]
            )

            if use_tqdm:
                epochs.set_description(
                    "Epoch={0} | [{1:>5}|{2}]\ttrain. loss={3:.4f}\tvalid. loss={4:.4f}".format(
                        epoch,
                        step,
                        len(dataloaders["train"].dataset),
                        losses["train"][-1][1],
                        valid_loss,
                    )
                )
        valid_loss = lstm_evaluate(device, model, dataloaders["valid"])["loss"]
        losses["valid"].append(
            [epoch * len(dataloaders["train"].dataset) + step, valid_loss]
        )

    return model, losses


def lstm_evaluate(device: str, model: nn.Module, valid_loader: DataLoader):
    loss_fn = F.mse_loss
    model = model.eval().to(device)
    for i, (x, y) in enumerate(valid_loader):
        x, y = x.to(device), y.to(device)
        out = model(x)
        loss = loss_fn(out, y)

    return {"loss": np.float32(loss.cpu().detach().numpy())}


def train_prediction_network(
    device: str,
    datasets: dict,
    prediction_network: nn.Module,
    num_epochs: int,
    batch_size: int,
    learning_rate: float,
    use_tqdm: bool = True,
):
    dataloaders = data.get_dataloaders(datasets=datasets, train_batch_size=batch_size)

    prediction_network.to(device)

    optimiser = optim.Adam(
        lr=learning_rate, params=prediction_network.model.parameters()
    )
    loss_fn = F.mse_loss
    losses = {}
    losses["train"] = []
    losses["valid"] = []
    valid_loss = np.nan

    epochs = range(num_epochs)
    if use_tqdm:
        from tqdm import tqdm

        epochs = tqdm(epochs)

    for epoch in epochs:
        for i, (x, y) in enumerate(dataloaders["train"]):
            prediction_network.train()
            x, y = x.to(device), y.to(device)
            out = prediction_network((x, y[:, 0, 1:]))

            optimiser.zero_grad()
            loss = loss_fn(out, y[:, :, 0])
            loss.backward()
            optimiser.step()

            step = i * batch_size + len(x)
            losses["train"].append(
                [epoch * len(dataloaders["train"].dataset) + step, loss.item()]
            )
            if use_tqdm:
                epochs.set_description(
                    "Epoch={0} | [{1:>5}|{2}]\ttrain. loss={3:.4f}\tvalid. loss={4:.4f}".format(
                        epoch,
                        step,
                        len(dataloaders["train"].dataset),
                        losses["train"][-1][1],
                        valid_loss,
                    )
                )

        valid_loss = evaluate_prediction_network(
            device, prediction_network, dataloaders["valid"]
        )
        losses["valid"].append(
            [epoch * len(dataloaders["train"].dataset) + step, valid_loss]
        )

    return prediction_network, losses


def evaluate_prediction_network(
    device: str, model: nn.Module, valid_loader: DataLoader
):
    loss_fn = F.mse_loss
    model = model.eval().to(device)
    for i, (x, y) in enumerate(valid_loader):
        break
    x, y = x.to(device), y.to(device)
    out = model((x, y[:, 0, 1:]))
    loss = loss_fn(out, y[:, :, 0])

    return np.float32(loss.cpu().detach().numpy())


def save(model: nn.Module, name: str, path: str):
    Path(path).mkdir(parents=True, exist_ok=True)
    model_path = Path(path) / "{}.pt".format(name)
    torch.save(model, model_path)
    print(f"PyTorch model saved at {model_path}")


def read_json_params(path):
    with open(path) as json_file:
        params = json.load(json_file)
    return params
