from pymongo import MongoClient

mongo_client = None


def main(args):
    global mongo_client

    # --------------------------------------------------------------------------
    # Parse args
    # --------------------------------------------------------------------------
    post_ids = args.get('post_ids', list())
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
    post_collection = social_network_db['post']
    posts = list()
    for post_id in post_ids:
        post = post_collection.find_one(filter={'post_id': post_id})
        post.pop('_id', None)  # '_id': ObjectId('5fa8ade6949bf3bd67ed5aaf')
        posts.append(post)

    # --------------------------------------------------------------------------
    # Return result
    # --------------------------------------------------------------------------
    return {'posts': posts}
