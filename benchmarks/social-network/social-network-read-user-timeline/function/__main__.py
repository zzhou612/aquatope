import random

from pymongo import MongoClient

mongo_client = None


def main(args):
    global mongo_client

    # --------------------------------------------------------------------------
    # Parse args
    # --------------------------------------------------------------------------
    user_id = args.get('user_id', random.randint(1, 962))
    start = args.get('start', 0)
    stop = args.get('stop', 10)
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
    user_timeline = user_timeline_collection.find_one(
        filter={'user_id': user_id})
    post_ids = list()
    if user_timeline is not None:
        for post in user_timeline['posts']:
            post_ids.append(post['post_id'])
        if 0 <= start and start < stop:
            post_ids = post_ids[start:stop]

    # --------------------------------------------------------------------------
    # Return result
    # --------------------------------------------------------------------------
    return {'post_ids': post_ids}
