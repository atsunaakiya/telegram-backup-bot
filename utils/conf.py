import dataclasses
import json

from utils.data import BotData
from utils.path import config_path, data_path

TELEGRAM = 'telegram'
ADMIN = 'admin'
TOKEN = 'token'
TARGET = 'target'

def load_config():
    with config_path.open() as f:
        return json.load(f)


def load_data():
    data = json.load(data_path.open(encoding='utf-8'))
    return BotData(**data)


def save_data(data: BotData):
    json.dump(dict(dataclasses.asdict(data)), data_path.open('w', encoding='utf-8'), ensure_ascii=False)
