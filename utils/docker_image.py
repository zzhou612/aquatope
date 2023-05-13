from pathlib import Path

import docker


def docker_image_build(build_path, dockerfile, tag, result=True):
    # client = docker.DockerClient(base_url='unix://var/run/docker.sock')
    api_client = docker.APIClient(base_url='unix://var/run/docker.sock')

    # image, result_stream = client.images.build(path=str(build_path),
    #                                            dockerfile=dockerfile,
    #                                            tag=tag)

    result_stream = api_client.build(path=str(build_path),
                                     dockerfile=dockerfile,
                                     tag=tag,
                                     decode=True)
    if result:
        for chunk in result_stream:
            if 'stream' in chunk:
                print(chunk['stream'], end='')


def docker_image_push(tag, result=True):
    api_client = docker.APIClient(base_url='unix://var/run/docker.sock')

    result_stream = api_client.push(repository=tag, stream=True, decode=True)

    if result:
        for chunk in result_stream:
            print(chunk)
