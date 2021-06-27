from utils import data_path, BotContext, BackupHelper


def main():
    ctx = BotContext()
    BackupHelper(ctx).start()


if __name__ == '__main__':
    assert data_path.exists(), data_path
    main()
