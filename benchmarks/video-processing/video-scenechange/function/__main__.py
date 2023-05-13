import subprocess
from datetime import timedelta
from pathlib import Path

from minio import Minio

minio_client = None


def main(args):
    global minio_client

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
    if minio_client is None:
        minio_client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=False,
        )

    ffmpeg_path = subprocess.check_output(
        'which ffmpeg', shell=True).decode("utf-8").strip()
    video_url = minio_client.presigned_get_object(
        bucket_name=bucket_name, object_name=video_name,
        expires=timedelta(minutes=10))
    cmd = ffmpeg_path + ' -y -i "' + video_url + \
        '" -filter_complex "select=\'gt(scene,0.3)\',metadata=print:file=/tmp/timestamp.txt" -f null -'
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                   shell=True, check=True)

    result = Path('/tmp/timestamp.txt').read_text()
    # --------------------------------------------------------------------------
    # Return result
    # --------------------------------------------------------------------------
    return {'scenechange': result}
