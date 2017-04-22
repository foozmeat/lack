import asyncio
import curses
import math
import signal
from curses.textpad import Textbox
from datetime import datetime

import os
import pytz

from .lackmanager import LackManager

DOWN = 1
UP = -1


class LackScreen:
    rows = 0
    cols = 0
    last_log_length = 0
    log_length = 0
    msgpad = None

    def __init__(self, window):
        self.lack_manager = LackManager()

        self.window = window
        self.window.nodelay(1)
        self.window.attron(curses.A_BOLD)
        self.window.timeout(0)
        self.window_y, self.window_x = self.window.getbegyx()

        self.rows, self.cols = self.window.getmaxyx()
        self.scrollbar_x = self.cols - 2

        curses.use_default_colors()
        for i in range(0, curses.COLORS):
            curses.init_pair(i, i, -1)

        self.logwin_top = self.window_y + 1
        self.logwin_left = self.window_x + 2

        self.logwin_height = self.rows - 5
        self.logwin_topline = 0
        self.logwin_width = self.cols - 5
        self.logwin = curses.newwin(self.logwin_height,
                                    self.logwin_width,
                                    self.logwin_top,
                                    self.logwin_left)
        self.logwin.scrollok(True)
        self.logwin.idlok(1)

        self.promptwin = curses.newwin(2,
                                       self.logwin_width,
                                       self.window_y + self.logwin_height + 2,
                                       self.logwin_left)
        self.promptwin.keypad(1)
        self.promptwin.timeout(0)
        self.promptwin.nodelay(1)
        self.promptwin.idlok(1)

        self.window.box(curses.ACS_VLINE, curses.ACS_HLINE)

        self.window.hline(self.logwin_height + 1,
                          1,
                          curses.ACS_HLINE,
                          self.cols - 2)

        self.log_length = len(self.lack_manager.loglines)

        self._tz = os.getenv('SLACK_TZ', 'UTC')

        signal.signal(signal.SIGWINCH, self.resize_handler)
        asyncio.async(self.lack_manager.update_messages())

    def resize_handler(self, signum, frame):
        # if we don't trap the window resize we'll just crash
        pass

    def _log_up_down(self, increment):
        scroll_max = self.log_length - self.logwin_height

        if self.logwin_topline > 0 and increment == UP:
            self.logwin_topline -= 1

        elif self.logwin_topline < scroll_max and increment == DOWN:
            self.logwin_topline += 1

        self.draw()

    def _draw_log(self):
        self.log_length = len(self.lack_manager.loglines)

        if self.log_length != self.last_log_length and self.log_length > self.logwin_height:
            self.logwin_topline = self.log_length - self.logwin_height
            self.bottom = self.log_length

        self.bottom = self.logwin_topline + self.logwin_height

        if self.bottom > self.log_length:
            self.bottom = self.log_length

        log_keys = self.lack_manager.loglines.iloc[self.logwin_topline:self.bottom]

        tz = pytz.timezone(self._tz)

        for (index, ts) in enumerate(log_keys):

            posix_timestamp, _ = ts.split('.')
            posix_timestamp = int(posix_timestamp)
            utc_dt = datetime.fromtimestamp(posix_timestamp)
            dt = utc_dt.astimezone(tz)
            date = dt.strftime('%A %I:%M%p')

            line = self.lack_manager.loglines[ts]
            color, name, msg = line
            self.logwin.attron(curses.color_pair(color))

            if len(msg) > self.logwin_width:
                msg = msg[0:self.logwin_width]

            self.logwin.addstr(index, 0, "{} {}: {}".format(date, name, msg))
            self.logwin.clrtoeol()
            self.logwin.attroff(curses.color_pair(color))

        self.logwin.refresh()

    def _draw_scrollbar(self):
        self.window.vline(1,
                          self.scrollbar_x,
                          ' ',
                          self.logwin_height)

        if self.log_length > self.logwin_height:
            overflow = self.log_length - self.logwin_height

            scrollbar_length = self.logwin_height * (float(self.logwin_height) / float(self.log_length))
            scrollbar_length = max(scrollbar_length, 3)
            scrollbar_length = int(math.floor(scrollbar_length))

            scrollbar_steps = overflow / float(self.logwin_height - scrollbar_length)
            scrollbar_y_float = (self.logwin_topline / scrollbar_steps)
            scrollbar_y = int(round(1 + scrollbar_y_float, 0))

            self.window.vline(scrollbar_y,
                              self.scrollbar_x,
                              curses.ACS_CKBOARD,
                              scrollbar_length)

            self.window.refresh()

    def _validator(self, ch):

        """
        This is our chance to modify incoming keystrokes before they're acted on
        in do_command
        """

        if ch == 127:
            return curses.KEY_BACKSPACE

        elif ch == curses.KEY_UP:
            self._log_up_down(UP)

        elif ch == curses.KEY_DOWN:
            self._log_up_down(DOWN)

        return ch

    def _prompt(self):
        """
        Don't use the standard curses textbox edit function since it won't play
        nicely with asyncio.
        """

        curses.curs_set(1)
        if not self.msgpad:
            self.msgpad = _Textbox(self.promptwin, insert_mode=True)
            self.msgpad.stripspaces = True

        (y, x) = self.promptwin.getyx()
        self.promptwin.move(y, x)

        ch = self.promptwin.getch()
        ch = self._validator(ch)

        if ch == -1:
            return

        dc_result = self.msgpad.do_command(ch)
        # self.state.loglines.append((0, str(dc)))

        # if not dc:
        #     return

        self.promptwin.refresh()

        if dc_result == 0:
            msg = self.msgpad.gather().strip()

            self.msgpad = None
            if msg != '':
                asyncio.async(self.lack_manager.send_message(msg))
                # self.slack_manager.loglines.append((0, msg))

            self.promptwin.erase()
        curses.curs_set(0)

    def _draw_bottom(self):

        self.window.attron(curses.color_pair(6))

        bottom_line = "Exit: Control-C"

        self.window.addstr(self.rows - 1,
                           2,
                           bottom_line)

        self.window.attroff(curses.color_pair(6))

    @asyncio.coroutine
    def draw(self):
        yield from asyncio.sleep(0.025)  # 24 fps
        self.window.refresh()
        self._draw_log()
        self._draw_scrollbar()
        self._prompt()
        self._draw_bottom()
        self.last_log_length = self.log_length
        asyncio.async(self.draw())


class _Textbox(Textbox):
    """
    Change the default textbox behavior of enter, up, and down.
    """

    def __init__(*args, **kwargs):
        Textbox.__init__(*args, **kwargs)

    def do_command(self, ch):
        if ch == 10:
            return 0

        elif ch == curses.KEY_UP:
            return 1

        elif ch == curses.KEY_DOWN:
            return 1

        else:
            return Textbox.do_command(self, ch)
