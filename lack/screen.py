import asyncio
import curses
import signal
from curses import panel
from curses.textpad import Textbox

import os

from .lackmanager import LackManager
from .logwindow import UP, DOWN, LogWindow


class LackScreen:
    rows = 0
    cols = 0
    msgpad = None

    def __init__(self, window):
        self.lack_manager = LackManager()
        self.embedded = False

        if hasattr(window, 'window'):
            # we were passed a panel
            self.panel = window
            self.window = window.window()
            self.embedded = True
        else:
            self.window = window

        self.window.nodelay(1)
        self.window.attron(curses.A_BOLD)
        self.window.timeout(0)
        self.window_y, self.window_x = self.window.getbegyx()

        self.rows, self.cols = self.window.getmaxyx()

        curses.use_default_colors()
        for i in range(0, curses.COLORS):
            curses.init_pair(i, i, -1)

        self.logwin_top = self.window_y + 1
        self.logwin_left = self.window_x + 2
        self.logwin_height = self.rows - 5
        self.logwin_width = self.cols - 4

        self.logwin = LogWindow(
            self.window,
            self.logwin_height,
            self.logwin_width,
            self.logwin_top,
            self.logwin_left,
            self.lack_manager.loglines
        )

        self.promptwin = self.window.subwin(2,
                                            self.logwin_width,
                                            self.window_y + self.logwin_height + 2,
                                            self.logwin_left)
        self.promptwin.keypad(1)
        self.promptwin.timeout(0)
        self.promptwin.nodelay(1)
        self.promptwin.idlok(1)

        self._tz = os.getenv('SLACK_TZ', 'UTC')
        self.visible = True

        if not self.embedded:
            signal.signal(signal.SIGWINCH, self.resize_handler)

        self._draw_borders()
        self._draw_bottom()
        self.window.refresh()

        asyncio.ensure_future(self.draw())

    def resize_handler(self, signum, frame):
        # if we don't trap the window resize we'll just crash
        pass

    def _validator(self, ch):

        """
        This is our chance to modify incoming keystrokes before they're acted on
        in do_command
        """

        if ch == 127:
            return curses.KEY_BACKSPACE

        elif ch == curses.KEY_UP:
            self.log_up_down(UP)

        elif ch == curses.KEY_DOWN:
            self.log_up_down(DOWN)

        elif ch == curses.KEY_F1:
            self.toggle()

        return ch

    def log_up_down(self, direction):
        self.logwin.log_up_down(direction)

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
            curses.curs_set(0)

            return

        dc_result = self.msgpad.do_command(ch)
        # self.promptwin.noutrefresh()

        if dc_result == 0:
            msg = self.msgpad.gather().strip()

            self.msgpad = None
            if msg != '':
                asyncio.async(self.lack_manager.send_message(msg))
                # self.slack_manager.loglines.append((0, msg))

            self.promptwin.erase()
        curses.curs_set(0)

    def _draw_borders(self):
        self.window.box(curses.ACS_VLINE, curses.ACS_HLINE)
        self.window.hline(self.logwin_height + 1,
                          1,
                          curses.ACS_HLINE,
                          self.cols - 2)

    def _draw_bottom(self):

        if self.embedded:
            return

        self.window.attron(curses.color_pair(6))

        bottom_line = "Exit: Control-C"

        self.window.addstr(self.rows - 1,
                           2,
                           bottom_line)

        self.window.attroff(curses.color_pair(6))

    def hide(self):
        self.visible = False
        self.panel.hide()
        self._refresh()

    def show(self):
        self.visible = True

        self.panel.show()
        # self._draw_borders()
        self._refresh()

    def toggle(self):

        if self.visible:
            self.hide()
        else:
            self.show()

        self._refresh()

    def _refresh(self):
        panel.update_panels()
        self.window.refresh()

    @asyncio.coroutine
    def draw(self):

        yield from asyncio.sleep(0.025)  # 24 fps

        if self.visible:

            self.logwin.draw()
            self._prompt()

            self.window.refresh()
            if not self.embedded:
                curses.doupdate()
        asyncio.ensure_future(self.draw())


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
