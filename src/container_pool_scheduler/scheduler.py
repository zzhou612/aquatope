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

from full_inference import inference

from owlib.container_pool import load_container_pool, update_container_pool

SCHED_INTERVAL = 1


class ContainerPoolScheduler:
    def __init__(
        self, n_input_steps: int, n_output_steps: int, workflow_config: dict
    ) -> None:
        self.n_input_steps = n_input_steps
        self.n_output_steps = n_output_steps
        self.workflow_config = workflow_config
        self._sched_loop()
        self.x = []
        self.external = []

    def get_external_features(self):
        now = datetime.utcnow()
        hour_of_day_sin = np.sin(2 * np.pi * (float(now.hour) / 24))
        hour_of_day_cos = np.cos(2 * np.pi * (float(now.hour) / 24))
        day_of_week_sin = np.sin(2 * np.pi * (float(now.day) / 7))
        day_of_week_cos = np.cos(2 * np.pi * (float(now.day) / 7))
        return [hour_of_day_sin, hour_of_day_cos, day_of_week_sin, day_of_week_cos]

    def _sched_loop(self):
        gevent.spawn_later(SCHED_INTERVAL, self._sched_loop)
        gevent.spawn(self.update_task)
        if len(self.x) >= self.n_input_steps:
            gevent.spawn(self.sched_task)

    def update_task(self):
        container_pool_config = load_container_pool()
        t = []
        for fn in self.workflow_config["functions"]:
            t.append(container_pool_config.get(fn, 0))
        self.x.append(t)
        while len(self.x) > self.n_input_steps:
            self.x.pop(0)
        external = self.get_external_features()
        self.external = external

    def sched_task(self):
        res, _ = inference(x=self.x, external=self.external)
        update_config = {}
        i = 0
        for fn in self.workflow_config["functions"]:
            update_config[fn] = res[i]
            i += 1
        update_container_pool(update_config=update_config)


def shutdown():
    raise KeyboardInterrupt


def main():
    parser = argparse.ArgumentParser(description="Container pool scheduler")
    parser.add_argument("--n_input_steps", action="store", type=int)
    parser.add_argument("--n_output_steps", action="store", type=int)
    parser.add_argument("--workflow_config", action="store", type=str)

    args = parser.parse_args()
    n_input_steps = args.n_input_steps
    n_output_steps = args.n_output_steps
    workflow_config_path = args.workflow_config
    with open(workflow_config_path, "r") as f:
        workflow_config = json.load(f)
    scheduler = ContainerPoolScheduler(
        n_input_steps=n_input_steps,
        n_output_steps=n_output_steps,
        workflow_config=workflow_config,
    )
    gevent.signal_handler(signal.SIGTERM, shutdown)
    try:
        gevent.wait()
    except KeyboardInterrupt:
        exit(0)


if __name__ == "__main__":
    main()
