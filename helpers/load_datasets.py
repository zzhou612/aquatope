import io

from minio import Minio
from PIL import Image


def load_images(minio_client, bucket_name, images_dir):
    images = []
    mobilenet_images = []
    for image_path in images_dir.iterdir():
        image_name = image_path.name
        images.append(image_name)
        with Image.open(image_path) as image:
            bytes_buffer = io.BytesIO()
            if image_path.suffix == '.jpg' or image_path.suffix == '.jpeg':
                fmt = 'JPEG'
                mobilenet_images.append(image_name)
            elif image_path.suffix == '.png':
                fmt = 'PNG'
            else:
                raise Exception(
                    'Unsupported image format: {}.'.format(image_path.suffix))
            image.save(fp=bytes_buffer, format=fmt)
            bytes_buffer.seek(0)
            minio_client.put_object(bucket_name=bucket_name,
                                    object_name=image_name,
                                    data=bytes_buffer,
                                    length=bytes_buffer.getbuffer().nbytes)
    return images, mobilenet_images


def load_videos(minio_client, bucket_name, videos_dir):
    videos = []
    for video_path in videos_dir.iterdir():
        video_name = video_path.name
        videos.append(video_name)
        minio_client.fput_object(bucket_name=bucket_name,
                                 object_name=video_name,
                                 file_path=video_path)
    return videos
