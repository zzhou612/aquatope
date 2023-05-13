import gevent  # isort:skip
from gevent import monkey  # isort:skip

monkey.patch_all()  # isort:skip
import argparse
import json
import logging
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np

PROJECT_DIR = Path(__file__).resolve().parents[2]
SCHED_DIR = Path(__file__).resolve().parents[0]
sys.path.append(str(PROJECT_DIR))
sys.path.append(str(SCHED_DIR))

import bayesian_optimization

from owlib.container_pool import load_container_pool, update_container_pool

# WORKFLOW_CONFIG = {
#     "name": "hello-world-seq",
#     "functions": ["hello-world-0", "hello-world-1", "hello-world-2"],
#     "params": {"name": "Azem", "place": "Elpis"},
# }
WORKFLOW_CONFIG = dict()


def main():
    global WORKFLOW_CONFIG

    parser = argparse.ArgumentParser(description="Container pool scheduler")
    parser.add_argument("--n_init", action="store", type=int)
    parser.add_argument("--n_batch", action="store", type=int)
    parser.add_argument("--mc_samples", action="store", type=int)
    parser.add_argument("--batch_size", action="store", type=int)
    parser.add_argument("--num_restarts", action="store", type=int)
    parser.add_argument("--raw_samples", action="store", type=int)
    parser.add_argument("--infeasible_cost", action="store", type=float)
    parser.add_argument("--anomaly_detection", action="store_true")
    parser.add_argument("--confidence", action="store", type=float)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--workflow_config", action="store", type=str)

    args = parser.parse_args()
    n_init = args.n_init
    n_batch = args.n_batch
    mc_samples = args.mc_samples
    batch_size = args.batch_size
    num_restarts = args.num_restarts
    raw_samples = args.raw_samples
    infeasible_cost = args.infeasible_cost
    anomaly_detection = args.anomaly_detection
    confidence = args.confidence
    verbose = args.verbose
    workflow_config_path = args.workflow_config

    with open(workflow_config_path, "r") as f:
        WORKFLOW_CONFIG = json.load(f)

    best_cost, resource_config = bayesian_optimization.bo_loop(
        n_init=n_init,
        n_batch=n_batch,
        mc_samples=mc_samples,
        batch_size=batch_size,
        num_restarts=num_restarts,
        raw_samples=raw_samples,
        infeasible_cost=infeasible_cost,
        anomaly_detection=anomaly_detection,
        confidence=confidence,
        verbose=verbose,
    )


if __name__ == "__main__":
    main()
    # bayesian_optimization.bo_loop()
