import argparse
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import DataLoader

PROJECT_DIR = Path(__file__).resolve().parents[2]
SCHED_DIR = Path(__file__).resolve().parents[0]
sys.path.append(str(PROJECT_DIR))
sys.path.append(str(SCHED_DIR))

import models.variational_dropout as vd
from models.predict import *

import data
import utils

cpu = lambda x: x.cpu().detach().numpy()

MODEL = None
MODEL_ARTIFACTS_DIR = SCHED_DIR / "model_artifacts"


def load_trained_model(model_artifacts_dir: str, device: str):
    predict_loc = os.path.join(model_artifacts_dir, "predict.pt")
    predict = torch.load(predict_loc, map_location=device).eval()
    return predict.to(device)


def dropout_on(m: nn.Module):
    if type(m) in [torch.nn.Dropout, vd.LSTM]:
        m.train()


def dropout_off(m: nn.Module):
    if type(m) in [torch.nn.Dropout, vd.LSTM]:
        m.eval()


def inference(x: list, external: list, mc_dropout: bool = False, batch_size: int = 1):
    global MODEL

    device = utils.get_device()
    if MODEL is None:
        MODEL = load_trained_model(
            model_artifacts_dir=MODEL_ARTIFACTS_DIR, device=device
        )
    if mc_dropout:
        MODEL = MODEL.apply(dropout_on)
    else:
        MODEL = MODEL.apply(dropout_off)

    x = np.expand_dims(x, axis=0)
    external = np.expand_dims(external, axis=0)
    x = torch.tensor(np.array(x, dtype=np.float32), device=device)
    external = torch.tensor(np.array(external, dtype=np.float32), device=device)

    res = []
    for _ in range(batch_size):
        res.append(MODEL((x, external)).to(device).item())
    mean = np.mean(res)
    var = np.var(res)
    return mean, var


def main():
    # --------------------------------------------------------------------------
    # Parse args
    # --------------------------------------------------------------------------
    parser = argparse.ArgumentParser(description="Train prediction network")
    parser.add_argument(dest="filenames", metavar="filename", nargs="*")
    parser.add_argument("--n_input_steps", action="store", type=int)
    parser.add_argument("--n_output_steps", action="store", type=int)

    args = parser.parse_args()
    n_input_steps = args.n_input_steps
    n_output_steps = args.n_output_steps
    model_artifacts_dir = SCHED_DIR / "model_artifacts"

    device = utils.get_device()
    predict = load_trained_model(model_artifacts_dir=model_artifacts_dir, device=device)

    x = []
    for _ in range(n_input_steps):
        x.append([0, 0, 0, 0, 0])
    external = [0, 0, 0, 0]
    start = time.time()
    mean, var = inference(x=x, external=external, mc_dropout=True, batch_size=128)
    end = time.time()
    print("time:", end - start)
    print(mean, var)


if __name__ == "__main__":
    main()
