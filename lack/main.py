#!/usr/bin/env python3
import asyncio
import curses
import signal
import sys
from typing import Any

import locale

from .screen import LackScreen

if sys.version_info < (3, 5):
    print("lack require Python 3.5+")
    sys.exit(1)

locale.setlocale(locale.LC_ALL, '')


def exit_handler(*_: Any) -> None:
    for task in asyncio.Task.all_tasks():
        task.cancel()

    event_loop = asyncio.get_event_loop()
    event_loop.stop()


def exit_wrapper() -> None:
    exit_handler(None, None)

signal.signal(signal.SIGINT, exit_handler)


def main() -> None:
    def _main(window: Any) -> None:

        swin = curses.newwin(40, 80, 10, 10)

        screen = LackScreen(swin)

        event_loop = asyncio.get_event_loop()
        # event_loop.set_debug(True)
        try:
            asyncio.async(screen.draw())
            event_loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            event_loop.close()

    curses.wrapper(_main)
