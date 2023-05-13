import io
import tempfile

import cv2
import numpy as np
from minio import Minio
from PIL import Image

minio_client = None
cascade_classifier = None


def main(args):
    global minio_client, cascade_classifier

    # --------------------------------------------------------------------------
    # Parse args
    # --------------------------------------------------------------------------
    video_name = args.get('video', 'Amagami_720P_10s.mov')
    minio_config = args.get('minio_config', dict())
    endpoint = minio_config.get('api_endpoint',
                                'minio.faas.svc.cluster.local:9000')
    access_key = minio_config.get('access_key', 'faas_user')
    secret_key = minio_config.get('secret_key', 'faas_p@ssw0rd')
    bucket_name = minio_config.get('bucket_name', 'faas')

    # --------------------------------------------------------------------------
    # Function
    # --------------------------------------------------------------------------
    if cascade_classifier is None:
        cascade_classifier = cv2.CascadeClassifier(
            'haarcascade_frontalface_default.xml')
    if minio_client is None:
        minio_client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=False,
        )

    results = dict()
    with tempfile.NamedTemporaryFile() as fp:
        minio_client.fget_object(bucket_name=bucket_name,
                                 object_name=video_name, file_path=fp.name)
        cap = cv2.VideoCapture(fp.name)
        while True:
            # Read the frame
            success, img = cap.read()
            if not success:
                break
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # Detect the faces
            faces = cascade_classifier.detectMultiScale(gray, 1.1, 4)
            if len(faces) > 0:
                frame = int(cap.get(1))
                results[str(frame)] = faces.tolist()

    # --------------------------------------------------------------------------
    # Return result
    # --------------------------------------------------------------------------
    return results
