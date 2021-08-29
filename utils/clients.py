from utils.conf import load_config, TOKEN, TELEGRAM


def create_bot():
    from telegram.ext import Updater
    config = load_config()
    return Updater(config[TELEGRAM][TOKEN])


