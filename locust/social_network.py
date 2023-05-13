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


class ServerlessUser(FastHttpUser):
    host = APIHOST

    def wait_time(self):
        global rng
        return rng.exponential(scale=1)

    @tag("social_network")
    @task(2)
    def compose_post(self):
        global dbs

        user_id = random.randint(1, 962)
        username = "username_" + str(user_id)
        text = "".join(random.choices(string.ascii_letters + string.digits, k=100))
        num_user_mentions = random.randint(0, 3)
        user_mention_ids = list()
        for _ in range(num_user_mentions):
            while True:
                user_mention_id = random.randint(1, 962)
                if (
                    user_mention_id != user_id
                    and user_mention_id not in user_mention_ids
                ):
                    user_mention_ids.append(user_mention_id)
                    break
        for user_mention_id in user_mention_ids:
            text = text + " @username_" + str(user_mention_id)
        num_medias = random.randint(0, 5)
        media_ids = list()
        media_types = list()
        for _ in range(num_medias):
            media_ids.append(random.randint(1, sys.maxsize))
            media_types.append("PIC")

        action_name = "compose_post"
        action_params = {
            "compose_post": {
                "username": username,
                "user_id": user_id,
                "text": text,
                "media_ids": media_ids,
                "media_types": media_types,
                "post_type": "POST",
                "dbs": dbs,
            }
        }
        url_params = {"blocking": "true", "result": "false"}
        self.client.post(
            url="/api/v1/namespaces/" + NAMESPACE + "/actions/" + action_name,
            params=url_params,
            json=action_params,
            auth=(USER_PASS[0], USER_PASS[1]),
            verify=False,
            name=action_name,
        )

    @tag("social_network")
    @task(4)
    def read_home_timeline(self):
        global dbs

        action_name = "read_home_timeline_pipeline"
        user_id = random.randint(1, 962)
        start = random.randint(0, 100)
        stop = start + 10
        action_params = {
            "read_home_timeline": {
                "user_id": user_id,
                "start": start,
                "stop": stop,
                "dbs": dbs,
            }
        }
        url_params = {"blocking": "true", "result": "false"}
        self.client.post(
            url="/api/v1/namespaces/" + NAMESPACE + "/actions/" + action_name,
            params=url_params,
            json=action_params,
            auth=(USER_PASS[0], USER_PASS[1]),
            verify=False,
            name=action_name,
        )

    @tag("social_network")
    @task(4)
    def read_user_timeline(self):
        global dbs

        action_name = "read_user_timeline_pipeline"
        user_id = random.randint(1, 962)
        start = random.randint(0, 100)
        stop = start + 10
        action_params = {
            "read_user_timeline": {
                "user_id": user_id,
                "start": start,
                "stop": stop,
                "dbs": dbs,
            }
        }
        url_params = {"blocking": "true", "result": "false"}
        self.client.post(
            url="/api/v1/namespaces/" + NAMESPACE + "/actions/" + action_name,
            params=url_params,
            json=action_params,
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
