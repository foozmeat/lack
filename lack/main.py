import asyncio
import curses
import signal
import sys
from typing import Any

import locale

from .screen import LackScreen

if sys.version_info < (3, 6):
    print("lack require Python 3.6+")
    sys.exit(1)

locale.setlocale(locale.LC_ALL, '')


def exit_handler(*_: Any) -> None:
    curses.endwin()
    sys.exit(0)


def exit_wrapper() -> None:
    exit_handler(None, None)


signal.signal(signal.SIGINT, exit_handler)


def main() -> None:
    def _main(window: Any) -> None:

        event_loop = asyncio.get_event_loop()

        rows, cols = window.getmaxyx()

        LackScreen(rows, cols, 0, 0)

        event_loop.run_forever()

        event_loop.close()
        curses.endwin()

    curses.wrapper(_main)
