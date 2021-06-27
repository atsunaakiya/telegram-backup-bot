import os
import pickle
import uuid
from io import BytesIO

from telegram import Bot, Update, PhotoSize
from telegram.ext import Dispatcher, MessageHandler, Filters, Updater, CallbackContext

from lib.clients import create_bot
from lib.conf import load_data
from lib.data import CacheFile
from lib.path import cache_path, data_path


class BackupHelper:
    updater: Updater
    bot: Bot
    def __init__(self):
        self.updater = create_bot()
        self.bot = self.updater.bot
        self.data = load_data()

        self.poster = PosterClient()

    def start(self):
        dispatcher: Dispatcher = self.updater.dispatcher
        dispatcher.add_handler(MessageHandler(Filters.text, self._on_text_message))
        dispatcher.add_handler(MessageHandler(Filters.photo, self._on_photo_message))

        self.updater.start_polling()
        print("Bot Started")
        self.updater.idle()

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

    def put_file(self, admin_chat, chat_id, message_id, parent: str, fn: str, payload: bytes):
        cache = CacheFile(admin_chat, chat_id, message_id, parent, fn, payload)
        target = cache_path / f'{uuid.uuid4().hex}.pkl'
        with target.open('wb') as f:
            pickle.dump(cache, f)

def main():
    BackupHelper().start()


if __name__ == '__main__':
    assert data_path.exists(), data_path
    main()
