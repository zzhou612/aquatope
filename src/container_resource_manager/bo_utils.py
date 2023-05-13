import gevent  # isort:skip
from gevent import monkey  # isort:skip

monkey.patch_all()  # isort:skip
import sys
from pathlib import Path

import torch

PROJECT_DIR = Path(__file__).resolve().parents[2]
SCHED_DIR = Path(__file__).resolve().parents[0]
sys.path.append(str(PROJECT_DIR))
sys.path.append(str(SCHED_DIR))
from manager import WORKFLOW_CONFIG

from owlib.action import update_action_limits
from owlib.sequence import invoke_sequence
from utils.config import (
    CPU_MAX,
    CPU_MIN,
    CPU_UNIT_COST,
    MEMORY_MAX,
    MEMORY_MIN,
    MEMORY_UNIT_COST,
    NUM_RESOURCES,
)

CACHE = dict()
device = torch.device("cuda:3" if torch.cuda.is_available() else "cpu")
dtype = torch.double


def from_x_to_resource_config(x: torch.tensor) -> dict:
    x_list = x.tolist()
    num_stages = int(len(x_list) / NUM_RESOURCES)
    resource_config = [[CPU_MIN, MEMORY_MIN] for _ in range(num_stages)]
    for i in range(int(len(x_list) / 2)):
        scaled_cpu = x_list[i * 2]
        scaled_memory = x_list[i * 2 + 1]
        resource_config[i][0] = round(scaled_cpu * (CPU_MAX - CPU_MIN) + CPU_MIN, 1)
        resource_config[i][1] = round(
            scaled_memory * (MEMORY_MAX - MEMORY_MIN) + MEMORY_MIN, 0
        )
    return resource_config


def calc_cost(functions: list, resource_config: list, latencies: dict) -> float:
    cost = 0
    for i, config in enumerate(resource_config):
        cpu, memory = config
        fn = functions[i]
        duration = latencies[fn]
        cost += cpu * duration * CPU_UNIT_COST + memory * duration * MEMORY_UNIT_COST
    return cost


def update_resource_config(functions: list, resource_config: list):
    for i, fn in enumerate(functions):
        cpu, memory = resource_config[i]
        update_action_limits(action_name=fn, cpu=cpu, memory=memory)


def sample_cost(x: torch.tensor):
    resource_config = from_x_to_resource_config(x)
    hash_id = hash(str(resource_config))
    if hash_id not in CACHE:
        update_resource_config(
            functions=WORKFLOW_CONFIG["functions"], resource_config=resource_config
        )
        seq_activation, e2e_latency, latencies = invoke_sequence(
            sequence_name=WORKFLOW_CONFIG["name"],
            params=WORKFLOW_CONFIG["params"],
        )
        cost = calc_cost(
            functions=WORKFLOW_CONFIG["functions"],
            resource_config=resource_config,
            latencies=latencies,
        )
        CACHE[hash_id] = dict()
        CACHE[hash_id]["cost"] = cost
        CACHE[hash_id]["duration"] = e2e_latency
    cost = CACHE[hash_id]["cost"]
    return torch.tensor([cost], dtype=dtype)


def sample_duration(x: torch.tensor):
    resource_config = from_x_to_resource_config(x)
    hash_id = hash(str(resource_config))
    cost = 0
    if hash_id not in CACHE:
        update_resource_config(
            functions=WORKFLOW_CONFIG["functions"], resource_config=resource_config
        )
        seq_activation, e2e_latency, latencies = invoke_sequence(
            sequence_name=WORKFLOW_CONFIG["name"],
            params=WORKFLOW_CONFIG["params"],
        )
        CACHE[hash_id] = dict()
        CACHE[hash_id]["cost"] = cost
        CACHE[hash_id]["duration"] = e2e_latency
    duration = CACHE[hash_id]["duration"]
    return torch.tensor([duration], dtype=dtype)


def sample_cost_parallel(X: torch.tensor):
    jobs = []
    for x in X:
        job = gevent.spawn(sample_cost, x=x)
        jobs.append(job)
    gevent.joinall(jobs)
    res = torch.tensor([job.value for job in jobs], dtype=dtype)
    return res


def sample_duration_parallel(X: torch.tensor):
    jobs = []
    for x in X:
        job = gevent.spawn(sample_duration, x=x)
        jobs.append(job)
    gevent.joinall(jobs)
    res = torch.tensor([job.value for job in jobs], dtype=dtype)
    return res


# n = 3
# rand_x = torch.rand(n, 6)
# res = sample_cost_parallel(rand_x)
# print(res)
