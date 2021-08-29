import os
from io import BytesIO
from pathlib import Path

from telegram import Bot, Update, PhotoSize
from telegram.ext import Dispatcher, MessageHandler, Filters, Updater, CallbackContext

from utils.clients import create_bot
from utils.conf import load_data, load_config
from utils.path import data_path


class BackupHelper:
    updater: Updater
    bot: Bot
    def __init__(self):
        self.updater = create_bot()
        self.bot = self.updater.bot
        self.data = load_data()
        self.config = load_config()
        self.root = self.config['target']


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
        print(chat_name, message_id)
        self.upload_file(chat_name, fn, msg.text.encode('utf-8'))
        self.notify(self.data.admin_chat, chat_id, message_id)


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
            self.upload_file(chat_name, fn, msg.text.encode('utf-8'))
        f = photo.get_file()
        ext = os.path.splitext(f.file_path)[1]
        fn = f"{from_msg_id}{ext}"
        buffer = BytesIO()
        f.download(out=buffer)
        print(chat_name, message_id)
        self.upload_file(chat_name, fn, buffer.getvalue())
        self.notify(self.data.admin_chat, chat_id, message_id)

    def upload_file(self, parent, filename, data: bytes):
        if parent is None:
            parent = 'DIRECT'
        fp = Path(f"{self.root}/{parent}/{filename}")
        fp.parent.mkdir(exist_ok=True, parents=True)
        with fp.open('wb') as f:
            f.write(data)

    def notify(self, admin_chat, chat_id, message_id):
        self.bot.forward_message(admin_chat, chat_id, message_id)


def main():
    BackupHelper().start()


if __name__ == '__main__':
    assert data_path.exists(), data_path
    main()
