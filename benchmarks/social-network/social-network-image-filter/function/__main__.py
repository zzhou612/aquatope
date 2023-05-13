import io
import tempfile

import numpy as np
from minio import Minio
from PIL import Image
from tensorflow.keras.applications import MobileNetV3Small
from tensorflow.keras.applications.mobilenet_v3 import (decode_predictions,
                                                        preprocess_input)
from tensorflow.keras.utils import img_to_array, load_img

minio_client = None
model = None


def main(args):
    global minio_client, model

    # --------------------------------------------------------------------------
    # Parse args
    # --------------------------------------------------------------------------
    images = args.get('images', ['ILSVRC2012_val_00000001.jpeg',
                                 'ILSVRC2012_val_00000002.jpeg'])
    minio_config = args.get('minio_config', dict())
    endpoint = minio_config.get('api_endpoint',
                                'minio.faas.svc.cluster.local:9000')
    access_key = minio_config.get('access_key', 'faas_user')
    secret_key = minio_config.get('secret_key', 'faas_p@ssw0rd')
    bucket_name = minio_config.get('bucket_name', 'faas')

    # --------------------------------------------------------------------------
    # Function
    # --------------------------------------------------------------------------
    if model is None:
        model = MobileNetV3Small(
            weights='weights_mobilenet_v3_small_224_1.0_float.h5')
    if minio_client is None:
        minio_client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=False,
        )

    x = []
    for img_name in images:
        # try:
        #     resp = minio_client.get_object(
        #         bucket_name=bucket_name, object_name=img_name)
        #     bytes_data = resp.read()
        #     img = Image.open(io.BytesIO(bytes_data))
        #     img = img.convert('RGB')
        # finally:
        #     resp.close()
        #     resp.release_conn()
        with tempfile.NamedTemporaryFile() as fp:
            minio_client.fget_object(bucket_name=bucket_name,
                                     object_name=img_name, file_path=fp.name)
            img = load_img(fp.name)

        img_arr = img_to_array(img)
        x.append(img_arr)

    x = np.array(x)
    x = preprocess_input(x)
    preds = model(x)
    results = decode_predictions(preds.numpy(), top=5)
    img_classes = list()
    for result in results:
        img_classes.append(result[0][1])

    # --------------------------------------------------------------------------
    # Return result
    # --------------------------------------------------------------------------
    res = {'predictions': img_classes}
    return res
