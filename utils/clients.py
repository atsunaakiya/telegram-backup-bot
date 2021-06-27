from utils.conf import load_config, TOKEN, TELEGRAM, WEBDAV, HOST, USERNAME, PASSWORD


def create_bot():
    from telegram.ext import Updater
    config = load_config()
    return Updater(config[TELEGRAM][TOKEN])


def create_dav():
    from webdav3.client import Client
    config = load_config()
    return Client({
        'webdav_hostname': config[WEBDAV][HOST],
        'webdav_login': config[WEBDAV][USERNAME],
        'webdav_password': config[WEBDAV][PASSWORD]
    })


