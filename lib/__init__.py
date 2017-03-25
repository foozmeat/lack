import asyncio
import curses

import sys

__version__ = "1.0"


def exit_handler(signal, frame):
    event_loop = asyncio.get_event_loop()
    event_loop.shutdown_asyncgens()
    event_loop.stop()
    # event_loop.close()
    curses.endwin()
    sys.exit(0)


def exit_wrapper():
    exit_handler(None, None)

