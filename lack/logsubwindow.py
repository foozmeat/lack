import asyncio
import curses
import math
from datetime import datetime
from typing import Any

from .window import BorderedSubWindow

from sortedcontainers import SortedDict

DOWN = 1
UP = -1


class LogSubWindow(BorderedSubWindow):
    def __init__(self,
                 window: Any,
                 height: int = 0,
                 width: int = 0,
                 top: int = 0,
                 left: int = 0,
                 datasource: SortedDict = SortedDict()) -> None:

        super(LogSubWindow, self).__init__(window, height, width, top, left)

        self.datasource = datasource
        self.topline = 0
        self.last_log_length = 0
        self.log_length = 0

        self.scrollbar_x = self.width
        self.line_length = self.width - 1

    def key_handler(self, ch):
        if ch == curses.KEY_UP:
            self.log_up_down(UP)

        elif ch == curses.KEY_DOWN:
            self.log_up_down(DOWN)

        return ch

    def log_up_down(self, increment):
        scroll_max = self.log_length - self.height

        if self.topline > 0 and increment == UP:
            self.topline -= 1

        elif self.topline < scroll_max and increment == DOWN:
            self.topline += 1

    def _draw_scrollbar(self):
        self.window.vline(1,
                          self.scrollbar_x - 1,
                          curses.ACS_VLINE,
                          self.height)

        self.window.vline(1,
                          self.scrollbar_x,
                          ' ',
                          self.height)

        self.window.vline(1,
                          self.scrollbar_x + 1,
                          curses.ACS_VLINE,
                          self.height)

        if self.log_length > self.height:
            overflow = self.log_length - self.height

            scrollbar_length = self.height * (float(self.height) / float(self.log_length))
            scrollbar_length = max(scrollbar_length, 3)
            scrollbar_length = int(math.floor(scrollbar_length))

            scrollbar_steps = overflow / float(self.height - scrollbar_length)
            scrollbar_y_float = (self.topline / scrollbar_steps)
            scrollbar_y = int(round(1 + scrollbar_y_float, 0))

            self.window.vline(scrollbar_y,
                              self.scrollbar_x,
                              curses.ACS_CKBOARD,
                              scrollbar_length)

    def _content(self) -> None:

        self.log_length = len(self.datasource)

        if self.log_length != self.last_log_length and self.log_length > self.height:
            self.topline = self.log_length - self.height

        bottom = self.topline + self.height

        if bottom > self.log_length:
            bottom = self.log_length

        log_keys = self.datasource.iloc[self.topline:bottom]

        for (index, ts) in enumerate(log_keys):

            color, msg = self.datasource[ts]

            if len(msg) > self.line_length:
                msg = msg[0:self.line_length]

            self.set_text(index, 0, msg, color, clr=True)

        self.last_log_length = self.log_length

        self._draw_scrollbar()
