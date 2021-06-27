import unittest

from utils import BotContext


class MyTestCase(unittest.TestCase):
    def test_something(self):
        ctx = BotContext()
        print(ctx.dav.list())


if __name__ == '__main__':
    unittest.main()
