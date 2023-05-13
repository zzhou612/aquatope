import gevent  # isort:skip
from gevent import monkey  # isort:skip

monkey.patch_all()  # isort:skip
import base64
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Tuple

import requests
import urllib3

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_DIR))
from owlib.activation import get_activation_by_id
from utils.config import APIHOST, AUTH_KEY, NAMESPACE, USER_PASS, WSK

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def invoke_sequence(sequence_name: str, params: dict) -> Tuple[dict, float, dict]:
    url_params = dict()
    url_params["blocking"] = "true"
    start_t = time.monotonic()
    response = requests.post(
        url=APIHOST + "/api/v1/namespaces/" + NAMESPACE + "/actions/" + sequence_name,
        json=params,
        params=url_params,
        auth=(USER_PASS[0], USER_PASS[1]),
        verify=False,
    )
    end_t = time.monotonic()
    e2e_latency = end_t - start_t
    seq_activation = json.loads(response.text)

    latencies = dict()
    for activation_id in seq_activation["logs"]:
        activation = get_activation_by_id(activation_id=activation_id)
        latencies[activation["name"]] = activation["duration"] / 1000

    return seq_activation, e2e_latency, latencies
