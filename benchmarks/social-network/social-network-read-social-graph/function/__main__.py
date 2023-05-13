import random
import sys
from datetime import datetime, timezone

from pymongo import MongoClient

mongo_client = None


def get_timestamp_ms() -> int:
    return int(round(datetime.now(timezone.utc).timestamp() * 1000))


def main(args):
    global mongo_client

    # --------------------------------------------------------------------------
    # Parse args
    # --------------------------------------------------------------------------
    user_id = args.get('user_id', random.randint(1, 962))
    post_id = args.get('post_id', random.randint(1, sys.maxsize))
    post_timestamp = args.get('post_timestamp', get_timestamp_ms())
    user_mention_names = args.get('user_mention_names', list())
    mongo_config = args.get('mongo_config', dict())
    mongodb_addr = mongo_config.get('mongodb_addr',
                                    'mongodb.faas.svc.cluster.local')
    mongodb_port = mongo_config.get('mongodb_port', 27017)

    # --------------------------------------------------------------------------
    # Function
    # --------------------------------------------------------------------------
    if mongo_client is None:
        mongo_client = MongoClient(mongodb_addr, mongodb_port)

    social_network_db = mongo_client['social_network']
    user_collection = social_network_db['user']
    social_graph_collection = social_network_db['social_graph']

    home_timeline_ids = list()
    # mentioned users
    for user_mention_name in user_mention_names:
        doc = user_collection.find_one(filter={'username': user_mention_name})
        if doc is None:
            continue
        user_mention_id = doc['user_id']
        home_timeline_ids.append(user_mention_id)
    # followers
    cursor = social_graph_collection.find(filter={'followees': user_id})
    for doc in cursor:
        follower_id = doc['user_id']
        home_timeline_ids.append(follower_id)

    # --------------------------------------------------------------------------
    # Return result
    # --------------------------------------------------------------------------
    return {
        'post_id': post_id,
        'post_timestamp': post_timestamp,
        'home_timeline_ids': home_timeline_ids
    }
