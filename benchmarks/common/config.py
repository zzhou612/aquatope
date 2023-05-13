import configparser
from pathlib import Path

config = configparser.ConfigParser()
config_path = Path(__file__).parent.absolute() / 'config.ini'
config.read_file(open(config_path))

# CrouchDB
DB_PROVIDER = config['DB']['DB_PROVIDER']
DB_USERNAME = config['DB']['DB_USERNAME']
DB_PASSWORD = config['DB']['DB_PASSWORD']
DB_PROTOCOL = config['DB']['DB_PROTOCOL']
DB_HOST = config['DB']['DB_HOST']
DB_PORT = config['DB']['DB_PORT']

# MinIO
ENDPOINT = config['MinIO']['ENDPOINT']
BUCKET = config['MinIO']['BUCKET']
ACCESS_KEY = config['MinIO']['ACCESS_KEY']
SECRET_KEY = config['MinIO']['SECRET_KEY']

# WSK Props
WSK = config['OpenWhisk']['WSK']
APIHOST = config['OpenWhisk']['APIHOST']
AUTH_KEY = config['OpenWhisk']['AUTH_KEY']
NAMESPACE = config['OpenWhisk']['NAMESPACE']
USER_PASS = AUTH_KEY.split(':')
