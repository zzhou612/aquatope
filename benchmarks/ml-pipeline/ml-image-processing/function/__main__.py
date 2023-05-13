import io
import pickle
from datetime import datetime, timezone
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from config import ACCESS_KEY, BUCKET, ENDPOINT, SECRET_KEY
from minio import Minio
from PIL import Image, ImageFilter

from utils import get_timestamp_ms, minio_get_image, minio_put_image

minio_client = None


def main(args):
    global minio_client

    # -----------------------------------------------------------------------
    # Parse params
    # -----------------------------------------------------------------------
    timestamps = {
        "main_start_ms": 0,
        "main_end_ms": 0,
        "minio_get_ms": 0,
        "minio_put_ms": 0,
    }
    timestamps["main_start_ms"] = get_timestamp_ms()
    minio_config = args.get("minio_config", dict())
    endpoint = minio_config.get("api_endpoint", "minio.faas.svc.cluster.local:9000")
    access_key = minio_config.get("access_key", "faas_user")
    secret_key = minio_config.get("secret_key", "faas_p@ssw0rd")
    bucket_name = minio_config.get("bucket_name", "faas")
    if minio_client is None:
        minio_client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=False,
        )
    image_name = args.get("image", "ILSVRC2012_val_00000001.jpeg")

    # -----------------------------------------------------------------------
    # Action execution
    # -----------------------------------------------------------------------
    image = minio_get_image(
        minio_client=minio_client,
        bucket_name=BUCKET,
        image_name=image_name,
        timestamps=timestamps,
    )

    image = image.transpose(Image.FLIP_LEFT_RIGHT)
    image = image.transpose(Image.FLIP_TOP_BOTTOM)
    image = image.transpose(Image.ROTATE_90)
    image = image.transpose(Image.ROTATE_180)
    image = image.transpose(Image.ROTATE_270)
    image = image.filter(ImageFilter.BLUR)
    image = image.filter(ImageFilter.CONTOUR)
    image = image.filter(ImageFilter.SHARPEN)
    image = image.convert("L")

    new_image_name = Path(image_name).stem + "_processed" + Path(image_name).suffix
    minio_put_image(
        minio_client=minio_client,
        bucket_name=BUCKET,
        image_name=new_image_name,
        image=image,
        timestamps=timestamps,
    )

    # -----------------------------------------------------------------------
    # Return results
    # -----------------------------------------------------------------------
    timestamps["main_end_ms"] = get_timestamp_ms()
    args["timestamps"] = timestamps
    return args
