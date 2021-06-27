import dataclasses
import json
import os
import pickle
import time
import uuid
from collections import deque
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
import multiprocessing
from typing import Optional, IO

from telegram import Update, Bot, Chat, PhotoSize
from telegram.ext import Updater, Dispatcher, CommandHandler, CallbackContext, MessageHandler, Filters
from webdav3.client import Client
from webdav3.exceptions import RemoteParentNotFound, WebDavException

root_path = Path(__file__).parent
config_path = root_path / 'config.json'
data_path = root_path / 'data.json'
cache_path = root_path / 'cache'
cache_path.mkdir(exist_ok=True)

pipe_path = root_path / 'queue.pipe'
if not pipe_path.exists():
    os.mkfifo(pipe_path)

TELEGRAM = 'telegram'
ADMIN = 'admin'
TOKEN = 'token'
WEBDAV = 'webdav'
HOST = 'host'
ROOT = 'root'
USERNAME = 'username'
PASSWORD = 'password'


@dataclasses.dataclass
class BotData:
    admin_chat: str = ''
    # chats: List[str] = dataclasses.field(default_factory=list)
    # chat_names: Dict[str, str] = dataclasses.field(default_factory=dict)
    # latest_messages: Dict[str, int] = dataclasses.field(default_factory=dict)
    # saved_messages: Dict[str, int] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class CacheFile:
    admin_chat: str
    chat_id: str
    message_id: str
    parent: str
    filename: str
    payload: bytes


class BotContext:
    def __init__(self):
        with config_path.open() as f:
            config = json.load(f)
        self._dav = None
        self._bot = None
        self.admin = config[TELEGRAM][ADMIN]
        self.config = config
        self.root = config[WEBDAV][ROOT]

    @property
    def bot(self) -> Updater:
        if self._bot is None:
            self._bot = Updater(self.config[TELEGRAM][TOKEN])
        return self._bot

    @property
    def dav(self) -> Client:
        if self._dav is None:
            self._dav = Client({
                'webdav_hostname': self.config[WEBDAV][HOST],
                'webdav_login': self.config[WEBDAV][USERNAME],
                'webdav_password': self.config[WEBDAV][PASSWORD]
            })
        return self._dav

    @staticmethod
    def load_data():
        data = json.load(data_path.open(encoding='utf-8'))
        return BotData(**data)

    @staticmethod
    def save_data(data: BotData):
        json.dump(dict(dataclasses.asdict(data)), data_path.open('w', encoding='utf-8'), ensure_ascii=False)



class InitHelper:
    dispatcher: Dispatcher

    def __init__(self, ctx: BotContext):
        self.ctx = ctx
        self.bot = ctx.bot
        self.dispatcher = self.bot.dispatcher
        if data_path.exists():
            self.data = ctx.load_data()
        else:
            self.data = BotData()

    def start(self):

        self.dispatcher.add_handler(CommandHandler('connect', self._init_connect_admin))
        # self.dispatcher.add_handler(MessageHandler(Filters.forwarded, self._init_connect_channel))

        print("1. Send /connect to the bot.")
        print("2. Set this bot as the admin of your channels.")
        self.bot.start_polling()
        self.bot.idle()

        self.ctx.save_data(self.data)
        print("Config saved.")

    def _init_connect_admin(self, update: Update, context: CallbackContext):
        if update.message.from_user.name != self.ctx.admin:
            update.message.reply_text("You are not my admin.")
            return
        update.message.reply_text('Ok, Admin. Now you can forward channels to me.')
        self.data.admin_chat = update.message.chat_id

    # def _init_connect_channel(self, update: Update, context: CallbackContext):
    #     if update.message.chat_id != self.data.admin_chat:
    #         update.message.reply_text(f'Expected chat {self.data.admin_chat}, got chat {update.message.chat_id}')
    #         return
    #     chat_id = str(update.message.chat_id)
    #     if chat_id not in self.data.chats:
    #         chat = update.message.forward_from_chat
    #         update.message.reply_text(f"Chat '{chat.title}' connected.")
    #         self.data.chats.append(chat.id)
    #         self.data.chat_names[chat.id] = chat.title


class BackupHelper:
    bot: Bot
    def __init__(self, ctx: BotContext):
        self.ctx = ctx
        self.bot = self.ctx.bot.bot
        self.data = ctx.load_data()

        self.poster = PosterClient()

    def start(self):
        dispatcher: Dispatcher = self.ctx.bot.dispatcher
        dispatcher.add_handler(MessageHandler(Filters.text, self._on_text_message))
        dispatcher.add_handler(MessageHandler(Filters.photo, self._on_photo_message))

        print("Waiting for poster...")
        with self.poster:
            self.ctx.bot.start_polling()
            print("Bot Started")
            self.ctx.bot.idle()

    def _on_text_message(self, update: Update, context: CallbackContext):
        msg = update.channel_post or update.edited_channel_post or update.message
        chat_id = str(msg.chat_id)
        message_id = msg.message_id
        if chat_id == str(self.data.admin_chat) and msg.forward_from_chat:
            chat_name = msg.forward_from_chat.title
            from_message_id = msg.forward_from_message_id
        else:
            chat_name = msg.chat.title
            from_message_id = message_id
        fn = f"{from_message_id}.txt"

        self.poster.put_file(self.data.admin_chat, chat_id, message_id, chat_name, fn, msg.text.encode('utf-8'))

    def _photo_size(self, photo: PhotoSize):
        return photo.width * photo.height

    def _on_photo_message(self, update: Update, context: CallbackContext):
        msg = update.channel_post or update.edited_channel_post or update.message
        caption = msg.caption
        photo = max(msg.photo, key=self._photo_size)
        chat_id = str(msg.chat_id)
        message_id = msg.message_id
        if chat_id == str(self.data.admin_chat) and msg.forward_from_chat:
            chat_name = msg.forward_from_chat.title
            from_msg_id = msg.forward_from_message_id
        else:
            chat_name = msg.chat.title
            from_msg_id = message_id

        if caption:
            fn = f"{from_msg_id}_caption.txt"
            self.poster.put_file(self.data.admin_chat, chat_id, message_id, chat_name, fn, caption.encode('utf-8'))
        f = photo.get_file()
        ext = os.path.splitext(f.file_path)[1]
        fn = f"{from_msg_id}{ext}"
        buffer = BytesIO()
        f.download(out=buffer)
        self.poster.put_file(self.data.admin_chat, chat_id, message_id, chat_name, fn, buffer.getvalue())


class PosterClient:
    pipe: Optional[IO]

    def __init__(self):
        self.pipe = None

    def init_queue(self):
        self.pipe = open(pipe_path, 'w')
        for n in os.listdir(cache_path):
            self.put_pipe(str(cache_path / n))

    def put_pipe(self, s: str):
        self.pipe.write(s)
        self.pipe.write('\n')
        self.pipe.flush()

    def put_file(self, admin_chat, chat_id, message_id, parent: str, fn: str, payload: bytes):
        cache = CacheFile(admin_chat, chat_id, message_id, parent, fn, payload)
        target = cache_path / f'{uuid.uuid4().hex}.pkl'
        with target.open('wb') as f:
            pickle.dump(cache, f)
        self.put_pipe(str(target))

    def send_stop(self):
        self.put_pipe('')

    def __enter__(self):
        self.init_queue()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.send_stop()
        self.pipe.close()


class PosterServer:
    def __init__(self, ctx: BotContext):
        self.ctx = ctx
        self.pipe = None
        self.retry_queue = deque()

    def fetch_pipe(self):
        line = self.pipe.readline()
        return line.strip()

    def load_file(self, fp: Path):
        with fp.open('rb') as f:
            return pickle.load(f)

    def upload(self, f: CacheFile):
        try:
            self.upload_file(f.parent, f.filename, f.payload)
        except WebDavException as err:
            print(err)
            return False
        else:
            self.ctx.bot.bot.forward_message(f.admin_chat, f.chat_id, f.message_id)
            return True

    def upload_file(self, parent, filename, data: bytes):
        dav = self.ctx.dav
        chat_name = parent
        fp = f"{self.ctx.root}/{chat_name}/{filename}"
        try:
            self._upload_data(data, fp)
        except RemoteParentNotFound:
            dav.mkdir(f"{self.ctx.root}/{chat_name}")
            self._upload_data(data, fp)

    def _upload_data(self, data: bytes, fp):
        with NamedTemporaryFile('wb') as f:
            f.write(data)
            f.flush()
            self.ctx.dav.upload(fp, f.name)

    def run(self):
        self.pipe = open(pipe_path, 'r')
        print("Poster started.")
        return
        while True:
            if self.retry_queue:
                next_file: str = self.retry_queue.popleft()
            else:
                next_file: str = self.fetch_pipe()
            if next_file == '':
                print("Stopping...")
                break
            next_file: Path = Path(next_file)
            if not next_file.exists():
                print("File not exist:", next_file)
                continue
            cache = self.load_file(next_file)
            success = self.upload(cache)
            if success:
                os.remove(next_file)
                print(f"Send file {cache.parent}/{cache.filename}, rest: {len(os.listdir(cache_path))}")
                time.sleep(10)
            else:
                print("Failed to send file. Wait for 60s.")
                self.retry_queue.append(next_file)
                time.sleep(60)

