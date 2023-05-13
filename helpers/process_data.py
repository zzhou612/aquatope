import random
import socket
import string
import sys
import time
import uuid
import zipfile
from datetime import datetime, timezone
from distutils.dir_util import copy_tree
from pathlib import Path
from threading import Thread

import docker
import numpy as np
import pandas as pd
import pymongo
import requests
from minio import Minio
from minio.error import BucketAlreadyExists, BucketAlreadyOwnedByYou, ResponseError
from pymongo import MongoClient
from tqdm import tqdm

from locust import HttpUser, constant_pacing, tag, task
from locust.env import Environment
from locust.log import setup_logging
from locust.stats import StatsCSVFileWriter, stats_history, stats_printer

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_DIR))

from owlib.activation import get_activation_by_id, get_activations


def collect_and_process_data(timestamp_since, enable_concurrency=False):
    global logger

    logger.info("fetch activation record")

    activations = get_activations(timestamp_since=timestamp_since, limit=200)
    activations.sort(key=lambda action: action["start"])

    # add cause field for sequence activation record, collect activation_id of sequences
    sequences = []
    for i, activation in enumerate(activations):
        annotations = dict()
        for key_val in activation["annotations"]:
            annotations.update({key_val["key"]: key_val["value"]})
        kind = annotations["kind"]
        if kind == "sequence":
            activation_id = activation["activationId"]
            activations[i]["cause"] = activation_id
            sequences.append(activation_id)

    data = []
    # for sequence_id in sequences:
    #     tot_t = 0
    #     for activation in [x for x in activations if x['cause'] == sequence_id]:
    for activation in activations:
        # parse annotations
        annotations = dict()
        for key_val in activation["annotations"]:
            annotations.update({key_val["key"]: key_val["value"]})
        action_name = annotations["path"]
        kind = annotations["kind"]
        limits = annotations["limits"]
        cpu = limits["cpu"]
        if kind == "sequence":
            cpu = 0
        memory_limit = limits["memory"]
        cold_start = 0
        if "initTime" in annotations:
            cold_start = annotations["initTime"]
        # finish parsing annotations

        activation_id = activation["activationId"]
        cpu_util = activation["cpuUtil"]
        duration = activation["duration"]
        # tot_t += duration
        status_codes = [
            "success",
            "application error",
            "developer error",
            "internal error",
        ]
        if activation["response"]["statusCode"] != 0:
            print(
                "{status}: {error}".format(
                    status=status_codes[activation["response"]["statusCode"]],
                    error=activation["response"]["result"]["error"],
                )
            )
            continue

        if "timestamps" in activation["response"]["result"] and kind != "sequence":
            main_start_ms = activation["response"]["result"]["timestamps"][
                "main_start_ms"
            ]
            main_end_ms = activation["response"]["result"]["timestamps"]["main_end_ms"]
            start_t = main_start_ms - activation["start"]
            end_t = activation["end"] - main_end_ms

            get_t = activation["response"]["result"]["timestamps"]["minio_get_ms"]
            put_t = activation["response"]["result"]["timestamps"]["minio_put_ms"]

            exec_t = (main_end_ms - main_start_ms) - (get_t + put_t)
        else:
            start_t = end_t = exec_t = get_t = put_t = 0

        data.append(
            [
                action_name,
                cpu,
                cpu_util,
                duration,
                cold_start,
                start_t,
                end_t,
                exec_t,
                get_t,
                put_t,
            ]
        )
    df = pd.DataFrame(
        data=data,
        columns=[
            "action",
            "cpu",
            "cpu_util",
            "duration",
            "cold_start",
            "start",
            "end",
            "exec",
            "get",
            "put",
        ],
    )
    df["cpu_time"] = df["cpu"] * df["duration"]
    if enable_concurrency:
        df["concurrency"] = 1
        df = df.groupby(by=["action", "cpu"], as_index=False).agg(
            {
                "cpu_util": "mean",
                "duration": "mean",
                "cold_start": "mean",
                "cpu_time": "sum",
                "concurrency": "count",
            }
        )

    df.sort_values(by=["action", "cpu"], inplace=True, ignore_index=True)
    if enable_concurrency:
        df = df.reindex(
            columns=[
                "action",
                "cpu",
                "cpu_util",
                "duration",
                "cold_start",
                "cpu_time",
                "concurrency",
            ]
        )
    else:
        df = df.reindex(
            columns=["action", "cpu", "cpu_util", "duration", "cold_start", "cpu_time"]
        )
    return df
