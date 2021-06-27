import logging
import os
import pickle
import time
from pathlib import Path
from tempfile import NamedTemporaryFile

from webdav3.exceptions import WebDavException, RemoteParentNotFound

from utils.clients import create_bot, create_dav
from utils.conf import load_config, WEBDAV, ROOT
from utils.data import CacheFile
from utils.path import cache_path


class PosterServer:
    def __init__(self):
        self.updater = create_bot()
        self.bot = self.updater.bot
        self.dav = create_dav()
        config = load_config()
        self.root = config[WEBDAV][ROOT]

    def load_file(self, fp: Path):
        with fp.open('rb') as f:
            return pickle.load(f)

    def upload(self, f: CacheFile):
        try:
            self.upload_file(f.parent, f.filename, f.payload)
        except WebDavException as err:
            logging.error(err)
            return False
        else:
            self.bot.forward_message(f.admin_chat, f.chat_id, f.message_id)
            return True

    def upload_file(self, parent, filename, data: bytes):
        dav = self.dav
        chat_name = parent
        fp = f"{self.root}/{chat_name}/{filename}"
        try:
            self._upload_data(data, fp)
        except RemoteParentNotFound:
            dav.mkdir(f"{self.root}/{chat_name}")
            self._upload_data(data, fp)

    def _upload_data(self, data: bytes, fp):
        with NamedTemporaryFile('wb') as f:
            f.write(data)
            f.flush()
            self.dav.upload(fp, f.name)

    def collect_files(self):
        return [
            cache_path / n
            for n in os.listdir(cache_path)
        ]

    def on_file(self, next_file):
        cache = self.load_file(next_file)
        success = self.upload(cache)
        return f"{cache.parent}/{cache.filename}", success

    def run(self):
        logging.info("Poster launched")
        while True:
            files = self.collect_files()
            files_n = len(files)
            for i, next_file in enumerate(files):
                path, success = self.on_file(next_file)
                if success:
                    os.remove(next_file)
                    logging.info(f"Send file {path}, rest: {files_n - i - 1}")
                    time.sleep(10)
                else:
                    logging.info("Failed to send file. Wait for 60s.")
                    time.sleep(60)
            time.sleep(5*60)


def launch_poster():
    logging.info("Poster started.")
    PosterServer().run()


if __name__ == '__main__':
    launch_poster()
