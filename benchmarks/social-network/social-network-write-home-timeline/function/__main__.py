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
    post_id = args.get('post_id', random.randint(1, sys.maxsize))
    post_timestamp = args.get('post_timestamp', get_timestamp_ms())
    home_timeline_ids = args.get('home_timeline_ids', list())
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
    home_timeline_collection = social_network_db['home_timeline']
    home_timeline_collection.create_index('user_id', unique=True)
    for home_timeline_id in home_timeline_ids:
        home_timeline_collection.find_one_and_update(
            filter={'user_id': home_timeline_id},
            update={'$push': {
                'posts': {
                    'post_id': post_id,
                    'timestamp': post_timestamp
                }
            }},
            upsert=True
        )

    # --------------------------------------------------------------------------
    # Return result
    # --------------------------------------------------------------------------
    return {'write_home_timeline_ok': True}
