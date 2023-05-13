import base64
import json
import subprocess
import sys
import time
from pathlib import Path

import requests
import urllib3

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_DIR))
from utils.config import CONTROLLER_CHANGE_RUNTIME_URL, GET_RUNTIME_URL, USER_PASS


def load_container_pool():
    response = requests.get(
        url=GET_RUNTIME_URL,
        auth=(USER_PASS[0], USER_PASS[1]),
        verify=False,
    )
    runtime_config = json.loads(response.text)
    container_pool_config = {}
    for action_runtime in runtime_config["blackboxes"]:
        action_name = action_runtime["name"]
        count = action_runtime["stemCells"][0]["count"]
        container_pool_config[action_name] = count
    return container_pool_config


def update_container_pool(update_config: dict):
    response = requests.get(
        url=GET_RUNTIME_URL,
        auth=(USER_PASS[0], USER_PASS[1]),
        verify=False,
    )
    runtime_config = json.loads(response.text)
    for action_runtime in runtime_config["blackboxes"]:
        action_name = action_runtime["name"]
        if action_name in update_config:
            action_runtime["stemCells"] = [{"count": update_config[action_name]}]
    response = requests.post(
        url=CONTROLLER_CHANGE_RUNTIME_URL,
        json=runtime_config,
        auth=(USER_PASS[0], USER_PASS[1]),
        verify=False,
    )
