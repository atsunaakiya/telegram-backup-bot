from telegram import Update
from telegram.ext import Dispatcher, CommandHandler, CallbackContext

from utils.clients import create_bot
from utils.conf import load_data, load_config, TELEGRAM, ADMIN, save_data
from utils.data import BotData
from utils.path import data_path


class InitHelper:
    dispatcher: Dispatcher

    def __init__(self):
        config = load_config()
        self.admin = config[TELEGRAM][ADMIN]
        self.bot = create_bot()
        self.dispatcher = self.bot.dispatcher
        if data_path.exists():
            self.data = load_data()
        else:
            self.data = BotData()

    def start(self):

        self.dispatcher.add_handler(CommandHandler('connect', self._init_connect_admin))
        # self.dispatcher.add_handler(MessageHandler(Filters.forwarded, self._init_connect_channel))

        print("1. Send /connect to the bot.")
        print("2. Set this bot as the admin of your channels.")
        self.bot.start_polling()
        self.bot.idle()

        save_data(self.data)
        print("Config saved.")

    def _init_connect_admin(self, update: Update, context: CallbackContext):
        if update.message.from_user.name != self.admin:
            update.message.reply_text("You are not my admin.")
            return
        update.message.reply_text('Ok, Admin. Now you can forward channels to me.')
        self.data.admin_chat = update.message.chat_id


def start():
    init = InitHelper()
    init.start()


if __name__ == '__main__':
    start()
