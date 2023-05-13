import tempfile

import numpy as np
from gluoncv import data, model_zoo, utils
from minio import Minio
from PIL import Image

minio_client = None
model = None


def is_box_valid(box: list) -> bool:
    for pos in box:
        if pos < 0:
            return False
    return True


def main(args):
    global minio_client, model

    # --------------------------------------------------------------------------
    # Parse args
    # --------------------------------------------------------------------------
    image = args.get('image', 'ILSVRC2012_val_00000001.jpeg')
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
        model = model_zoo.get_model('ssd_512_resnet50_v1_voc', pretrained=True)
    if minio_client is None:
        minio_client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=False,
        )

    with tempfile.NamedTemporaryFile() as fp:
        minio_client.fget_object(bucket_name=bucket_name,
                                 object_name=image, file_path=fp.name)
        x, img = data.transforms.presets.yolo.load_test(fp.name, short=512)

    class_IDs, scores, bounding_boxs = model(x)
    object_classes = []
    object_boxes = []

    for i in range(class_IDs.shape[1]):
        class_id = int(class_IDs[0][i][0].asscalar())
        score = float(scores[0][i][0].asscalar())
        box = bounding_boxs[0][i].asnumpy().tolist()
        if class_id != -1 and is_box_valid(box) and score > 0.5:
            object_classes.append(model.classes[class_id])
            object_boxes.append(box)

    # --------------------------------------------------------------------------
    # Return result
    # --------------------------------------------------------------------------
    res = {'object_classes': object_classes, 'object_boxes': object_boxes}
    return res
