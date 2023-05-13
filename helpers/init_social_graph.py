import logging
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

logger = logging.getLogger()


def init_social_graph(social_graph_path):
    global logger
    global social_graph_client

    logger.info("init social graph")
    user_db = social_graph_client["user"]
    user_collection = user_db["user"]
    user_collection.create_index(
        [("user_id", pymongo.ASCENDING)], name="user_id", unique=True
    )

    social_graph_db = social_graph_client["social_graph"]
    social_graph_collection = social_graph_db["social_graph"]
    social_graph_collection.create_index(
        [("user_id", pymongo.ASCENDING)], name="user_id", unique=True
    )

    def get_nodes(file):
        line = file.readline()
        word = line.split()[0]
        return int(word)

    def get_edges(file):
        edges = []
        lines = file.readlines()
        for line in lines:
            edges.append(line.split())
        return edges

    def register(user_id=None):
        if user_id is None:
            user_id = random.getrandbits(64)
        first_name = ("first_name_" + str(user_id),)
        last_name = ("last_name_" + str(user_id),)
        username = ("username_" + str(user_id),)
        password = ("password_" + str(user_id),)
        user_id = user_id
        document = {
            "first_name": first_name,
            "last_name": last_name,
            "username": username,
            "password": password,
            "user_id": user_id,
        }
        user_collection.insert_one(document)

    def follow(user_id, followee_id):
        social_graph_collection.find_one_and_update(
            filter={"user_id": user_id},
            update={"$push": {"followees": followee_id}},
            upsert=True,
        )

    nodes = None
    edges = None
    with open(social_graph_path, "r") as file:
        nodes = get_nodes(file)
        edges = get_edges(file)

    logger.info("upload user nodes")
    for i in tqdm(range(1, nodes + 1)):
        register(user_id=i)

    logger.info("upload user edges")
    for edge in tqdm(edges):
        follow(user_id=edge[0], followee_id=edge[1])
        follow(user_id=edge[1], followee_id=edge[0])
    logger.info("finish uploading social graph")
