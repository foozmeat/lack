import asyncio
import curses
from curses import panel

import os

from .lackmanager import LackManager
from .logwindow import LogWindow
from .window import Window, PromptWindow


class LackScreen(Window):
    rows = 0
    cols = 0
    msgpad = None

    def __init__(self, height: int, width: int, top: int, left: int, fg=curses.COLOR_WHITE):
        super(LackScreen, self).__init__(height, width, top, left, fg)

        self.embedded = False
        self.visible = True

        curses.use_default_colors()
        for i in range(0, curses.COLORS):
            curses.init_pair(i, i, -1)

        # if hasattr(window, 'window'):
        #     # we were passed a panel
        #     self.panel = window
        #     self.window = window.window()
        #     self.parent = parent
        #     self.embedded = True
        #     self.hide()
        #
        # else:
        #     self.window = window

        self.logwin_top = self.window_y + 1
        self.logwin_left = self.window_x + 2
        self.logwin_height = self.rows - 5
        self.logwin_width = self.cols - 4

        self.lack_manager = LackManager(self.logwin_width)

        self.logwin = LogWindow(self.logwin_height,
                                self.logwin_width,
                                self.logwin_top,
                                self.logwin_left,
                                self.lack_manager.loglines)

        self.promptwin = PromptWindow(2,
                                      self.logwin_width,
                                      self.window_y + self.logwin_height + 2,
                                      self.logwin_left)

        self.promptwin.parent_key_handler = self.key_handler
        
        self._tz = os.getenv('SLACK_TZ', 'UTC')

        if not self.embedded:
            asyncio.ensure_future(self.async_draw())

        self.window.border(0)
        self.window.hline(self.logwin_height + 1,
                          1,
                          curses.ACS_HLINE,
                          self.cols - 2)
        self.window.noutrefresh()

    def key_handler(self, ch):

        ch = self.logwin.key_handler(ch)

        return ch

    def _draw_bottom(self):

        if self.embedded:
            return

        self.window.attron(curses.color_pair(6))

        bottom_line = "Exit: Control-C"

        self.window.addstr(self.rows - 1,
                           2,
                           bottom_line)

        self.window.attroff(curses.color_pair(6))
        self.window.noutrefresh()

    def hide(self):
        if self.embedded:
            self.visible = False
            self.panel.bottom()
            panel.update_panels()
            # self.parent.lack_did_hide()

    def show(self):
        if self.embedded:
            self.visible = True
            self.window.clear()
            self.panel.top()
            self.window.noutrefresh()
            panel.update_panels()
            # self.parent.lack_did_show()

    # def toggle(self):
    #     if self.visible:
    #         self.hide()
    #
    #     else:
    #         self.show()
    #
    #     panel.update_panels()
    #     # curses.doupdate()

    @asyncio.coroutine
    def async_draw(self):
        yield from asyncio.sleep(0.025)  # 24 fps
        self.draw()
        asyncio.ensure_future(self.async_draw())

    def draw(self):
        if self.visible:
            self.logwin.draw()

            if not self.embedded:
                self._draw_bottom()

            msg = self.promptwin.textbox_prompt()
            self.promptwin.draw()
            if msg:
                asyncio.async(self.lack_manager.send_message(msg))

        if not self.embedded:
            curses.doupdate()

