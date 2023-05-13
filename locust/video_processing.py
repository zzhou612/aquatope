import base64
import json
import logging
import os
import pickle
import random
import string
import sys
import time
import uuid
from pathlib import Path

import numpy as np
import urllib3

import locust.stats
from locust import HttpUser, LoadTestShape, TaskSet, between, constant, tag, task
from locust.contrib.fasthttp import FastHttpUser

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_DIR))
from utils.config import (
    APIHOST,
    BUCKET,
    DB_HOST,
    DB_PASSWORD,
    DB_PORT,
    DB_PROTOCOL,
    DB_USERNAME,
    NAMESPACE,
    USER_PASS,
)

locust.stats.CSV_STATS_INTERVAL_SEC = 1  # second
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
random.seed(time.time())
logging.basicConfig(level=logging.INFO)

VIDEO_PIPELINE = "video_pipeline"
images = []


class ServerlessUser(FastHttpUser):
    host = APIHOST

    def wait_time(self):
        global rng
        return rng.exponential(scale=1)

    @tag("ml_pipeline")
    @task(10)
    def ml_pipeline(self):
        global images
        global VIDEO_PIPELINE

        action_name = VIDEO_PIPELINE
        x_uuid = str(uuid.uuid4())
        y_uuid = str(uuid.uuid4())
        z_uuid = str(uuid.uuid4())
        params = {
            "video_name": "480P.mov",
            "input_bucket": BUCKET,
            "output_bucket": BUCKET,
            "segment_time": 10,
            "pipeline": VIDEO_PIPELINE,
            # params for pipeline actions
            "fmt": ".mp4",
        }
        url_params = {"blocking": "true", "result": "false"}
        self.client.post(
            url="/api/v1/namespaces/" + NAMESPACE + "/actions/" + action_name,
            params=url_params,
            json=params,
            auth=(USER_PASS[0], USER_PASS[1]),
            verify=False,
            name=action_name,
        )


class StagesShape(LoadTestShape):
    # stages = [
    #     {"duration": 30, "users": 500, "spawn_rate": 100},
    #     {"duration": 60, "users": 600, "spawn_rate": 100},
    #     {"duration": 90, "users": 700, "spawn_rate": 100},
    #     {"duration": 120, "users": 800, "spawn_rate": 100},
    #     {"duration": 150, "users": 900, "spawn_rate": 100},
    #     {"duration": 180, "users": 1000, "spawn_rate": 100},
    # ]
    with open("/mnt/locust/trace.pickle", "rb") as fp:  # Unpickling
        stages = pickle.load(fp)

    def tick(self):
        run_time = self.get_run_time()

        self.stages = self.stages
        for stage in self.stages:
            if run_time < stage["duration"]:
                tick_data = (stage["users"], stage["spawn_rate"])
                return tick_data

        return None
