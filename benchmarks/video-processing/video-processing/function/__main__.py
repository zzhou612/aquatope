import json
import subprocess
import time
from datetime import timedelta
from pathlib import Path
from threading import Thread

import requests
from minio import Minio, ResponseError

from config import (ACCESS_KEY, BUCKET, DB_HOST, DB_PASSWORD, DB_PORT,
                    DB_PROTOCOL, DB_USERNAME, ENDPOINT, SECRET_KEY)
from utils import get_activation_by_id, get_timestamp_ms, invoke_action

minio_client = None


def main(args):
    global minio_client

    # -----------------------------------------------------------------------
    # Parse params
    # -----------------------------------------------------------------------
    timestamps = {
        'main_start_ms': 0,
        'main_end_ms': 0,
        'minio_get_ms': 0,
        'minio_put_ms': 0
    }
    timestamps['main_start_ms'] = get_timestamp_ms()
    if minio_client is None:
        minio_client = Minio(endpoint=ENDPOINT,
                             access_key=ACCESS_KEY,
                             secret_key=SECRET_KEY,
                             secure=False)
    params = args.get('video_processing', args)
    video_name = params['video_name']
    input_bucket = params['input_bucket']
    ouput_bucket = params['output_bucket']
    segment_time = params['segment_time']
    pipeline = params['pipeline']
    # params for pipeline actions
    fmt = params['fmt']

    # -----------------------------------------------------------------------
    # Action execution
    # -----------------------------------------------------------------------
    # split video into chunks, upload them to minio, remove local chunks
    ffmpeg_path = subprocess.check_output(
        'which ffmpeg', shell=True).decode("utf-8").strip()

    video_url = minio_client.presigned_get_object(
        bucket_name=input_bucket, object_name=video_name, expires=timedelta(minutes=3))
    seg_video_name = Path(video_name).stem + '_%03d' + Path(video_name).suffix
    seg_video_path = Path('/tmp') / seg_video_name
    split_cmd = [ffmpeg_path, '-y', '-i', video_url, '-c', 'copy',
                 '-f', 'segment', '-segment_time', str(segment_time),
                 '-reset_timestamps', '1',
                 str(seg_video_path)]
    subprocess.run(split_cmd, stdout=subprocess.PIPE,
                   stderr=subprocess.PIPE, check=True)

    seg_videos = []
    for seg_video_path in Path('/tmp').iterdir():
        if seg_video_path.stem.startswith(Path(video_name).stem + '_'):
            seg_videos.append(seg_video_path.name)
            minio_put_start_ms = get_timestamp_ms()
            minio_client.fput_object(
                bucket_name=ouput_bucket, object_name=seg_video_path.name, file_path=str(seg_video_path))
            minio_put_end_ms = get_timestamp_ms()
            timestamps['minio_put_ms'] += (minio_put_end_ms -
                                           minio_put_start_ms)
            seg_video_path.unlink()

    # process video chunks
    threads = []
    transcoded_seg_videos = []
    for seg_video in seg_videos:
        transcoded_seg_videos.append(Path(seg_video).stem + fmt)
        t = Thread(target=invoke_action, kwargs={
            'action_name': pipeline,
            'params': {
                'video_watermark': {
                    'video_name': seg_video,
                    'input_bucket': ouput_bucket,
                    'output_bucket': ouput_bucket,
                },
                'video_transcode': {
                    'video_name': seg_video,
                    'input_bucket': ouput_bucket,
                    'output_bucket': ouput_bucket,
                    'fmt': fmt
                },
                'video_scenechange': {
                    'video_name': seg_video,
                    'input_bucket': ouput_bucket
                }
            },
            'blocking': True,
            'poll_interval': 0.1
        })
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    # remove minio raw video chunks
    for seg_video in seg_videos:
        minio_client.remove_object(
            bucket_name=ouput_bucket, object_name=seg_video)

    segs_path = Path('/tmp') / 'segs_{}.txt'.format(Path(video_name).stem)
    if segs_path.exists():
        segs_path.unlink()

    # remove minio processed video chunks after downloading them locally
    with open(segs_path, 'a') as segs_f:
        for transcoded_seg_video in transcoded_seg_videos:
            transcoded_seg_video_path = Path('/tmp') / transcoded_seg_video
            segs_f.write('file {}\n'.format(
                str(transcoded_seg_video_path)))
            try:
                minio_client.fget_object(
                    bucket_name=ouput_bucket,
                    object_name=transcoded_seg_video,
                    file_path=str(transcoded_seg_video_path))
            except ResponseError as err:
                print(err)
            minio_client.remove_object(
                bucket_name=ouput_bucket, object_name=transcoded_seg_video)

    # merge processed video chunks, upload merged video to minio
    merged_name = 'merged_' + Path(video_name).stem + fmt
    merged_path = Path('/tmp') / merged_name
    merge_cmd = [ffmpeg_path, '-y', '-f', 'concat', '-safe', '0', '-i',
                 segs_path, '-c', 'copy', '-fflags', '+genpts', merged_path]
    subprocess.run(merge_cmd, stdout=subprocess.PIPE,
                   stderr=subprocess.PIPE, check=True)

    minio_client.fput_object(
        bucket_name=ouput_bucket, object_name=merged_name, file_path=str(merged_path))

    # remove local merged video
    for transcoded_seg_video in transcoded_seg_videos:
        transcoded_seg_video_path = Path('/tmp') / transcoded_seg_video
        transcoded_seg_video_path.unlink()

    # -----------------------------------------------------------------------
    # Return results
    # -----------------------------------------------------------------------
    timestamps['main_end_ms'] = get_timestamp_ms()
    args['timestamps'] = timestamps
    return args
