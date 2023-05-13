import argparse
import os
import sys
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

import data
from models.predict import *

import utils


def main():
    # --------------------------------------------------------------------------
    # Parse args
    # --------------------------------------------------------------------------
    parser = argparse.ArgumentParser(description="Train prediction network")
    parser.add_argument("--n_input_steps", action="store", type=int)
    parser.add_argument("--n_output_steps", action="store", type=int)
    parser.add_argument("--num_days", action="store", type=int)
    parser.add_argument("--num_epochs", action="store", type=int)
    parser.add_argument("--batch_size", action="store", type=int)
    parser.add_argument("--learning_rate", action="store", type=float)
    parser.add_argument("--dropout_p", action="store", type=float)
    parser.add_argument("--trace_id", action="store", type=str)
    parser.add_argument("--dataset_dir", action="store", type=str)

    args = parser.parse_args()
    n_input_steps = args.n_input_steps
    n_output_steps = args.n_output_steps
    num_days = args.num_days
    trace_id = args.trace_id
    dataset_dir = args.dataset_dir
    model_artifacts_dir = SCHED_DIR / "model_artifacts"
    num_epochs = args.num_epochs
    batch_size = args.batch_size
    learning_rate = args.learning_rate
    dropout_p = args.dropout_p

    # --------------------------------------------------------------------------
    # Load datasets
    # --------------------------------------------------------------------------
    df, split_dfs, samples = data.pipeline(
        n_input_steps=n_input_steps,
        n_pred_steps=n_output_steps,
        hash_function=trace_id,
        dataset_dir=dataset_dir,
        num_days=num_days,
    )

    datasets = data.get_datasets(
        samples=samples, n_input_steps=n_input_steps, pretraining=False
    )

    # --------------------------------------------------------------------------
    # Train LSTM encoder decoder
    # --------------------------------------------------------------------------
    device = utils.get_device()
    encoder_decoder_loc = model_artifacts_dir / "lstm_encoder_decoder.pt"
    encoder_decoder = torch.load(encoder_decoder_loc)
    prediction_network = Predict(
        n_extracted_features=n_input_steps,
        n_external_features=4,
        n_output_steps=n_output_steps,
        p=0.2,
        encoder_decoder=encoder_decoder,
    )

    model, losses = utils.train_prediction_network(
        device=device,
        datasets=datasets,
        prediction_network=prediction_network,
        num_epochs=num_epochs,
        batch_size=batch_size,
        learning_rate=learning_rate,
        use_tqdm=True,
    )

    utils.save(model, name="predict", path=model_artifacts_dir)


if __name__ == "__main__":
    main()
