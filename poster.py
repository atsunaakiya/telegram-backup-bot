from utils import BotContext, PosterServer


def launch_poster():
    ctx = BotContext()
    PosterServer(ctx).run()



if __name__ == '__main__':
    launch_poster()
