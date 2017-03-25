#!/usr/bin/env python3
import asyncio
import curses
import locale
import signal
import sys

from .screen import LackScreen
from .lackmanager import LackManager

if sys.version_info < (3, 5):
    print("lack require Python 3.5+")
    sys.exit(1)

locale.setlocale(locale.LC_ALL, '')


def exit_handler(signal, frame):
    for task in asyncio.Task.all_tasks():
        task.cancel()

    event_loop = asyncio.get_event_loop()
    event_loop.stop()


def exit_wrapper():
    exit_handler(None, None)

signal.signal(signal.SIGINT, exit_handler)


def main(window):

    lack_manager = LackManager()
    screen = LackScreen(window, lack_manager)

    event_loop = asyncio.get_event_loop()
    # event_loop.set_debug(True)
    try:
        asyncio.async(screen.draw())
        asyncio.async(lack_manager.update_messages())
        event_loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        event_loop.close()

curses.wrapper(main)