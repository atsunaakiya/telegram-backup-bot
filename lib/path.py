from pathlib import Path

root_path = Path(__file__).parent.parent
config_path = root_path / 'config.json'
data_path = root_path / 'data.json'
cache_path = root_path / 'cache'

cache_path.mkdir(exist_ok=True)