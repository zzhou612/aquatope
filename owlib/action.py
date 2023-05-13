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
from owlib.activation import get_activation_by_id
from utils.config import APIHOST, AUTH_KEY, NAMESPACE, USER_PASS, WSK

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def create_action(
    action_name,
    app_file,
    cpu=1.0,
    memory=256,
    timeout=1800000,
    docker_image="zzhou612/synthetic-runtime",
):
    # TODO: probe action kind by app file ext, support zip
    with open(app_file, "rb") as f:
        code = f.read()
    if Path(app_file).suffix == ".zip":
        code = base64.b64encode(code)
    code = code.decode("utf-8")
    response = requests.put(
        url=APIHOST + "/api/v1/namespaces/" + NAMESPACE + "/actions/" + action_name,
        json={
            "namespace": NAMESPACE,
            "name": action_name,
            "exec": {"kind": "blackbox", "code": code, "image": docker_image},
            "limits": {"cpu": cpu, "memory": memory, "timeout": timeout},
        },
        params={"overwrite": "true"},
        auth=(USER_PASS[0], USER_PASS[1]),
        verify=False,
    )
    return response


def update_action_limits(action_name, cpu=None, memory=None, timeout=None):
    limits = {}
    if cpu is None and memory is None and timeout is None:
        return
    if cpu is not None:
        limits["cpu"] = cpu
    if memory is not None:
        limits["memory"] = memory
    if timeout is not None:
        limits["timeout"] = timeout
    response = requests.put(
        url=APIHOST + "/api/v1/namespaces/" + NAMESPACE + "/actions/" + action_name,
        json={"limits": limits},
        params={"overwrite": "true"},
        auth=(USER_PASS[0], USER_PASS[1]),
        verify=False,
    )
    return response


def create_sequence(sequence_name, action_list=[]):
    response = requests.put(
        url=APIHOST + "/api/v1/namespaces/" + NAMESPACE + "/actions/" + sequence_name,
        json={
            "namespace": NAMESPACE,
            "name": sequence_name,
            "exec": {
                "kind": "sequence",
                "components": [
                    "/" + NAMESPACE + "/" + action for action in action_list
                ],
            },
        },
        params={"overwrite": "true"},
        auth=(USER_PASS[0], USER_PASS[1]),
        verify=False,
    )
    return response


def invoke_action(action_name, params, blocking=False, result=False, poll_interval=1):
    if not blocking and result:
        raise Exception("result cannot be true when blocking is false")
    url_params = dict()
    url_params["blocking"] = str(blocking).lower()
    url_params["result"] = str(result).lower()

    response = requests.post(
        url=APIHOST + "/api/v1/namespaces/" + NAMESPACE + "/actions/" + action_name,
        json=params,
        params=url_params,
        auth=(USER_PASS[0], USER_PASS[1]),
        verify=False,
    )
    if result:
        return json.loads(response.text)
    else:
        activation_id = json.loads(response.text)["activationId"]
        if blocking and "reponse" not in json.loads(response.text):
            while get_activation_by_id(activation_id=activation_id) is None:
                time.sleep(poll_interval)
        return activation_id
