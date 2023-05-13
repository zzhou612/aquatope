import io
import json
import pickle
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from cloudant.client import CouchDB
from PIL import Image

from config import (ACCESS_KEY, APIHOST, AUTH_KEY, BUCKET, DB_HOST,
                    DB_PASSWORD, DB_PORT, DB_PROTOCOL, DB_USERNAME, ENDPOINT,
                    NAMESPACE, SECRET_KEY, USER_PASS, WSK)


def get_timestamp_ms():
    return int(round(datetime.now(timezone.utc).timestamp() * 1000))


def minio_get_mat(minio_client, bucket_name, mat_name, timestamps):
    minio_get_start_ms = get_timestamp_ms()
    recv = minio_client.get_object(
        bucket_name=bucket_name, object_name=mat_name)
    bytes_data = recv.read()
    minio_get_end_ms = get_timestamp_ms()
    timestamps['minio_get_ms'] += (minio_get_end_ms - minio_get_start_ms)
    mat = pickle.loads(bytes_data)
    return mat


def minio_put_mat(minio_client, bucket_name, mat_name, mat, timestamps):
    bytes_data = pickle.dumps(mat)
    minio_put_start_ms = get_timestamp_ms()
    minio_client.put_object(bucket_name=bucket_name,
                            object_name=mat_name,
                            data=io.BytesIO(bytes_data),
                            length=len(bytes_data))
    minio_put_end_ms = get_timestamp_ms()
    timestamps['minio_put_ms'] += (minio_put_end_ms - minio_put_start_ms)
    return


def minio_get_image(minio_client, bucket_name, image_name, timestamps):
    minio_get_start_ms = get_timestamp_ms()
    recv = minio_client.get_object(
        bucket_name=bucket_name, object_name=image_name)
    bytes_data = recv.read()
    minio_get_end_ms = get_timestamp_ms()
    timestamps['minio_get_ms'] += (minio_get_end_ms - minio_get_start_ms)
    image = Image.open(io.BytesIO(bytes_data))
    return image


def minio_put_image(minio_client, bucket_name, image_name, image, timestamps):
    bytes_buffer = io.BytesIO()
    if Path(image_name).suffix == '.jpg' or Path(image_name).suffix == '.jpeg':
        fmt = 'JPEG'
    elif Path(image_name).suffix == '.png':
        fmt = 'PNG'
    else:
        raise Exception(
            'Unsupported image format: {}.'.format(Path(image_name).suffix))
    image.save(fp=bytes_buffer, format=fmt)
    bytes_buffer.seek(0)
    minio_put_start_ms = get_timestamp_ms()
    minio_client.put_object(bucket_name=bucket_name,
                            object_name=image_name,
                            data=bytes_buffer,
                            length=bytes_buffer.getbuffer().nbytes)
    minio_put_end_ms = get_timestamp_ms()
    timestamps['minio_put_ms'] += (minio_put_end_ms - minio_put_start_ms)
    return


'''
Image.close():
This function is only required to close images that have not had their file read
and closed by the load() method.

Image.load():
Allocates storage for the image and loads the pixel data. In normal cases, 
you don’t need to call this method, since the Image class automatically loads 
an opened image when it is accessed for the first time. This method will close 
the file associated with the image.
'''

couchdb_client = None


def get_activation_by_id(activation_id):
    global couchdb_client
    if couchdb_client is None:
        couchdb_client = CouchDB(user='whisk_admin',
                                 auth_token=DB_PASSWORD,
                                 url=DB_PROTOCOL + '://' + DB_HOST + ':' + DB_PORT,
                                 connect=True)
    local_activations_db = couchdb_client['local_activations']

    _id = 'guest/' + activation_id
    if _id in local_activations_db:
        return local_activations_db[_id]
    else:
        return None


def _get_activation_by_id(activation_id):
    res = requests.post(url=DB_PROTOCOL + '://' + DB_HOST + ':' + DB_PORT + '/' + 'local_activations/_find',
                        json={
                            'selector': {
                                'activationId': {'$eq': activation_id}
                            },
                            'execution_stats': True
                        },
                        auth=(DB_USERNAME, DB_PASSWORD))
    activations = json.loads(res.text)['docs']
    if not activations:
        return None
    return activations[0]


def invoke_action(action_name, params, blocking=False, result=False, poll_interval=1):
    if not blocking and result:
        raise Exception('result cannot be true when blocking is false')
    url_params = dict()
    url_params['blocking'] = str(blocking).lower()
    url_params['result'] = str(result).lower()

    response = requests.post(url=APIHOST + '/api/v1/namespaces/' + NAMESPACE + '/actions/' + action_name,
                             json=params,
                             params=url_params,
                             auth=(USER_PASS[0], USER_PASS[1]), verify=False)
    if result:
        return json.loads(response.text)
    else:
        activation_id = json.loads(response.text)['activationId']
        if blocking and 'reponse' not in json.loads(response.text):
            while get_activation_by_id(activation_id=activation_id) is None:
                time.sleep(poll_interval)
        return activation_id
