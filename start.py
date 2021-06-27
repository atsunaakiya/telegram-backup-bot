from utils import BotContext, InitHelper


def start():
    ctx = BotContext()
    init = InitHelper(ctx)
    init.start()

if __name__ == '__main__':
    start()
