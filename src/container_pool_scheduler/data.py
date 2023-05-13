import os
import subprocess
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset


class AzureFunctionDataset(Dataset):
    """
    PyTorch Dataset class for Metro Traffic dataset
    """

    def __init__(self, samples: dict, n_input_steps: int,
                 key: str = 'train', pretraining: bool = True):
        # calculate normalisation parameters for columns `invocation_rate`
        # from training data
        self.X_train = samples['train'][:, :n_input_steps, :].copy()

        cols_to_normalise = [0]
        self.train_mu, self.train_sigma = [], []
        for c in cols_to_normalise:
            self.train_mu.append(np.mean(np.hstack([self.X_train[:, 0, c],
                                                    self.X_train[-1, 1:, c]])))
            self.train_sigma.append(np.std(np.hstack([self.X_train[:, 0, c],
                                                      self.X_train[-1, 1:, c]])))

        # normalise dataset
        self.X = samples[key][:, :n_input_steps, :].copy()
        self.y = samples[key][:, n_input_steps:, :].copy()
        for c, col in enumerate(cols_to_normalise):
            self.X[:, :, col] = (self.X[:, :, col] -
                                 self.train_mu[c]) / (self.train_sigma[c])
            self.y[:, :, col] = (self.y[:, :, col] -
                                 self.train_mu[c]) / (self.train_sigma[c])

        # provide external features for prediction network
        self.pretraining = pretraining
        self.prediction_cols = [1, 2, 3, 4]

    def __len__(self) -> int:
        return len(self.y)

    def __getitem__(self, idx) -> Tuple[torch.Tensor, torch.Tensor]:
        invocation_idx = 0
        x = torch.Tensor(self.X[idx, :, :]).float()
        if self.pretraining:
            y = torch.Tensor(self.y[idx, :, invocation_idx] -
                             self.X[idx, 0, invocation_idx]).float()
        else:
            y = self.y[idx, :, :].copy()
            y[:, invocation_idx] -= self.X[idx, 0, invocation_idx]
            y = torch.Tensor(
                y[:, [invocation_idx] + self.prediction_cols]).float()

        return x, y


def get_datasets(samples: dict, n_input_steps: int, pretraining=True) -> dict:
    datasets = {}
    for key, sample in samples.items():
        datasets[key] = AzureFunctionDataset(
            samples, n_input_steps, key, pretraining)

    return datasets


def get_dataloaders(datasets: dict, train_batch_size: int) -> dict:
    dataloaders = {}
    for key, dataset in datasets.items():
        if key == 'train':
            dataloaders[key] = DataLoader(dataset,
                                          batch_size=train_batch_size,
                                          shuffle=True)
        else:
            dataloaders[key] = DataLoader(dataset,
                                          batch_size=len(dataset),
                                          shuffle=False)

    return dataloaders


def pipeline(n_input_steps: int, n_pred_steps: int,
             hash_function: str,
             dataset_dir: str,
             num_days: int) -> Tuple[pd.DataFrame, dict, dict]:
    df = load_dataset(hash_function=hash_function, dataset_dir=dataset_dir,
                      num_days=num_days)
    split_dfs = split_dataframe(df)
    samples = create_samples(split_dfs, n_input_steps, n_pred_steps)

    return df, split_dfs, samples


def full_pipeline(params):
    # run the data preprocessing pipeline to create dataset
    df, split_dfs, samples = pipeline(
        n_input_steps=params['data']['n_input_steps'],
        n_pred_steps=params['models']['prediction']['n_output_steps'],
        dataset_dir='../data')

    # we modify the get_datasets function to return external features in the y labels
    datasets = get_datasets(
        samples, params['data']['n_input_steps'], pretraining=False)

    dataloaders = get_dataloaders(datasets, train_batch_size=256)

    return df, dataloaders


def load_dataset(hash_function: str,
                 dataset_dir: str,
                 num_days: int) -> pd.DataFrame:
    df = pd.DataFrame(columns=['invocation_rate'], dtype=np.float64)
    for day in range(1, num_days + 1):
        invocations_per_function = dataset_dir + \
            'invocations_per_function_md.anon.d0' + str(day) + '.csv'
        df_t = pd.read_csv(invocations_per_function)
        hash_function_df = df_t[df_t['HashFunction'] == hash_function]
        values_list = hash_function_df.values.flatten().tolist()[4:]
        df_t = pd.DataFrame(values_list, columns=[
                            'invocation_rate'], dtype=np.float64)
        df = pd.concat([df, df_t], ignore_index=True)

    start_t = pd.Timestamp('2021-01-01 00:00:00')
    end_t = pd.Timestamp('2021-01-01 23:59:00') + \
        pd.Timedelta(days=num_days - 1)
    t = pd.date_range(start=start_t,
                      end=end_t,
                      freq='min')
    df['date'] = t
    df = df.set_index('date')
    hour_of_day_sin = np.sin(2 * np.pi * (df.index.hour.values / 24))
    hour_of_day_cos = np.cos(2 * np.pi * (df.index.hour.values / 24))
    df['hour_of_day_sin'] = hour_of_day_sin
    df['hour_of_day_cos'] = hour_of_day_cos
    day_of_week_sin = np.sin(2 * np.pi * (df.index.isocalendar().day / 7))
    day_of_week_cos = np.cos(2 * np.pi * (df.index.isocalendar().day / 7))
    df['day_of_week_sin'] = day_of_week_sin
    df['day_of_week_cos'] = day_of_week_cos
    return df


def split_dataframe(df: pd.DataFrame) -> dict:
    datasets = {}
    train_split = 0.8
    n_train = int(train_split * len(df))
    test_split = 0.1
    n_test = int((train_split + test_split) * len(df))
    valid_split = 0.1
    datasets['train'] = df.iloc[:n_train]
    datasets['valid'] = df.iloc[n_train:n_test]
    datasets['test'] = df.iloc[n_test:]

    for key, dataset in datasets.items():
        print(dataset.shape[0], key)

    return datasets


def create_samples(datasets: dict, n_input_steps: int, n_pred_steps: int) -> dict:
    data = {}
    for key, dataset in datasets.items():
        dataset = datasets[key]
        n_cols = dataset.shape[1]
        dataset = dataset.values.astype(np.float64)

        idxs = np.arange(dataset.shape[0])
        n_timesteps = n_input_steps + n_pred_steps
        n_samples = dataset.shape[0] - n_timesteps + 1
        stride = idxs.strides[0]
        sample_idxs = np.lib.stride_tricks.as_strided(
            idxs, shape=(n_samples, n_timesteps), strides=(stride, stride))

        samples = dataset[sample_idxs]
        useable = np.all(
            ~np.isnan(samples.reshape(-1, n_timesteps * n_cols)), axis=-1)
        data[key] = samples[useable]

        # print(data[key].shape)
        print(data[key].shape[0],
              f'samples of {n_input_steps} input steps and {n_pred_steps} output steps in', key)

    return data


if __name__ == "__main__":
    pipeline()
