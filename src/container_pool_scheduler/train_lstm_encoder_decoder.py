import argparse
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]
SCHED_DIR = Path(__file__).resolve().parents[0]
sys.path.append(str(PROJECT_DIR))
sys.path.append(str(SCHED_DIR))
import data
from models.encoder_decoder_dropout import *

import utils


def main():
    # --------------------------------------------------------------------------
    # Parse args
    # --------------------------------------------------------------------------
    parser = argparse.ArgumentParser(description="Train LSTM encoder decoder")
    parser.add_argument("--n_input_steps", action="store", type=int)
    parser.add_argument("--n_output_steps", action="store", type=int)
    parser.add_argument("--num_days", action="store", type=int)
    parser.add_argument("--num_epochs", action="store", type=int)
    parser.add_argument("--batch_size", action="store", type=int)
    parser.add_argument("--learning_rate", action="store", type=float)
    parser.add_argument("--variational_dropout_p", action="store", type=float)
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
    variational_dropout_p = args.variational_dropout_p

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
        samples=samples, n_input_steps=n_input_steps, pretraining=True
    )
    encoder_in_features = datasets["train"].X.shape[-1]  # 5
    device = utils.get_device()

    # --------------------------------------------------------------------------
    # Train LSTM encoder decoder
    # --------------------------------------------------------------------------
    model = VDEncoderDecoder(
        in_features=encoder_in_features,
        input_steps=n_input_steps,
        output_steps=n_output_steps,
        p=variational_dropout_p,
    )
    model, losses = utils.train_encoder_decoder(
        device=device,
        model=model,
        datasets=datasets,
        num_epochs=num_epochs,
        batch_size=batch_size,
        learning_rate=learning_rate,
        use_tqdm=True,
    )
    utils.save(model, name="lstm_encoder_decoder", path=model_artifacts_dir)


if __name__ == "__main__":
    main()
