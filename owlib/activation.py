import base64
import json
import subprocess
import sys
from pathlib import Path

import requests
import urllib3

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_DIR))
from utils.config import DB_HOST, DB_PASSWORD, DB_PORT, DB_PROTOCOL, DB_USERNAME

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_activations(timestamp_since, limit=25):
    timestamp_milli = timestamp_since * 1000
    res = requests.post(
        url=DB_PROTOCOL
        + "://"
        + DB_HOST
        + ":"
        + DB_PORT
        + "/"
        + "local_activations/_find",
        json={
            "selector": {"start": {"$gt": timestamp_milli}},
            "limit": limit,
            "execution_stats": True,
        },
        auth=(DB_USERNAME, DB_PASSWORD),
    )
    activations = json.loads(res.text)["docs"]
    return activations


def get_activation_by_id(activation_id):
    res = requests.post(
        url=DB_PROTOCOL
        + "://"
        + DB_HOST
        + ":"
        + DB_PORT
        + "/"
        + "test_activations/_find",
        # + "local_activations/_find",
        json={
            "selector": {"activationId": {"$eq": activation_id}},
            "execution_stats": True,
        },
        auth=(DB_USERNAME, DB_PASSWORD),
    )
    activations = json.loads(res.text)["docs"]
    if not activations:
        return None
    return activations[0]
