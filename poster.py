from utils import BotContext, PosterServer


def launch_poster():
    print("Started")
    ctx = BotContext()
    print("Context OK")
    PosterServer(ctx).run()



if __name__ == '__main__':
    launch_poster()
