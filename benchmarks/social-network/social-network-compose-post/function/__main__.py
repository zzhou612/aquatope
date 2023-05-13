import random
import re
import sys
from datetime import datetime, timezone


def get_timestamp_ms() -> int:
    return int(round(datetime.now(timezone.utc).timestamp() * 1000))


def main(args):
    # --------------------------------------------------------------------------
    # Parse args
    # --------------------------------------------------------------------------
    username = args.get('username', 'username_1')
    user_id = args.get('user_id', 1)
    text = args.get('text', 'Forge ahead till the end we pray.')
    media_ids = args.get('media_ids', [random.randint(1, sys.maxsize)])
    media_types = args.get('media_types', ['png'])
    post_type = args.get('post_type', 'POST')
    mongo_config = args.get('mongo_config', {
        'mongodb_addr': 'mongodb.faas.svc.cluster.local',
        'mongodb_port': 27017
    })
    # --------------------------------------------------------------------------
    # Function
    # --------------------------------------------------------------------------
    # construct post
    post_timestamp = get_timestamp_ms()
    post_id = random.getrandbits(63)
    author = {
        'user_id': user_id,
        'username': username
    }
    medias = list()
    for i in range(len(media_ids)):
        medias.append({
            'media_id': media_ids[i],
            'media_type': media_types[i]
        })
    post = {
        'post_id': post_id,
        'author': author,
        'text': text,
        'medias': medias,
        'timestamp': post_timestamp,
        'post_type': post_type
    }

    # parse user mentions
    user_mention_names = [username[1:]
                          for username in re.findall('@[a-zA-Z0-9-_]+', text)]

    # --------------------------------------------------------------------------
    # Return result
    # --------------------------------------------------------------------------
    return {
        # Store Post
        'post': post,
        # Read social graph
        'user_id': user_id,
        'post_id': post_id,
        'post_timestamp': post_timestamp,
        'user_mention_names': user_mention_names,
        # Common
        'mongo_config': mongo_config
    }
