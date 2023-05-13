import random
import string
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
    timestamp = args.get('timestamp', get_timestamp_ms())
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
    user_timeline_collection = social_network_db['user_timeline']
    user_timeline_collection.create_index('user_id', unique=True)
    user_timeline_collection.find_one_and_update(filter={'user_id': user_id},
                                                 update={'$push': {
                                                     'posts': {
                                                         'post_id': post_id,
                                                         'timestamp': timestamp
                                                     }
                                                 }},
                                                 upsert=True)

    # --------------------------------------------------------------------------
    # Return result
    # --------------------------------------------------------------------------
    return {'write_user_timeline_ok': True}
