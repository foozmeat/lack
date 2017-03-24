#!/usr/bin/env python3
import asyncio
import locale
import signal
import sys
import curses

from lib import exit_handler
from lib.screen import SlackScreen
from lib.slackmanager import SlackManager

if sys.version_info < (3, 5):
    print("lack require Python 3.5+")
    sys.exit(1)

locale.setlocale(locale.LC_ALL, '')

signal.signal(signal.SIGINT, exit_handler)


def main(window):

    slack_manager = SlackManager()
    screen = SlackScreen(window, slack_manager)

    event_loop = asyncio.get_event_loop()
    # event_loop.set_debug(True)
    try:
        asyncio.async(screen.draw())
        asyncio.async(slack_manager.update_messages())
        event_loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        event_loop.close()

curses.wrapper(main)
