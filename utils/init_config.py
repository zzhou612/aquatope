import configparser
import socket
import subprocess
from pathlib import Path

from requests import get


def init_config(config_path):
    config = configparser.ConfigParser()
    config.optionxform = lambda option: option  # preserve case for letters

    config['DB'] = {
        'DB_PROVIDER': 'CouchDB',
        'DB_USERNAME': 'whisk_admin',
        'DB_PASSWORD': 'some_passw0rd',
        'DB_PROTOCOL': 'http',
        'DB_HOST': '172.17.0.1',
        'DB_PORT': '5984'
    }

    config['MinIO'] = {
        'ENDPOINT': socket.gethostname() + '.ece.cornell.edu:9001',
        'BUCKET': 'playground',
        'ACCESS_KEY': '5VCTEQOQ0GR0NV1T67GN',
        'SECRET_KEY': '8MBK5aJTR330V1sohz4n1i7W5Wv/jzahARNHUzi3'
    }

    WSK = 'wsk'
    APIHOST = subprocess.check_output(
        WSK + ' property get --apihost', shell=True).split()[3].decode("utf-8")
    AUTH_KEY = subprocess.check_output(
        WSK + ' property get --auth', shell=True).split()[2].decode("utf-8")
    NAMESPACE = subprocess.check_output(
        WSK + ' property get --namespace', shell=True).split()[2].decode("utf-8")

    config['OpenWhisk'] = {
        'WSK': WSK,
        'APIHOST': APIHOST,
        'AUTH_KEY': AUTH_KEY,
        'NAMESPACE': NAMESPACE,
    }

    with open(config_path, 'w') as configfile:
        config.write(configfile)


def init_wskprops(wskprops_path=Path.home() / '.wskprops'):
    config = configparser.ConfigParser()
    config.optionxform = lambda option: option  # preserve case for letters

    public_ip = get('https://api.ipify.org').text

    config['OpenWhisk'] = {
        'APIHOST': 'https://' + public_ip,
        'AUTH': '23bc46b1-71f6-4ed5-8c54-816aa4f8c502:123zO3xZCLrMN6v2BKK1dXYFpXlPkccOFqm12CdAsMgRU4VrNZ9lyGVCGuMDGIwP',
    }

    with open(wskprops_path, 'w') as configfile:
        config.write(configfile, space_around_delimiters=False)

    # remove section
    with open(wskprops_path, 'r') as fin:
        data = fin.read().splitlines(True)
    with open(wskprops_path, 'w') as fout:
        fout.writelines(data[1:])
