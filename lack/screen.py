import asyncio
import curses

from .lackmanager import LackManager
from .logwindow import LogWindow
from .window import Window, PromptWindow


class LackScreen(Window):

    def __init__(self, height: int, width: int, top: int, left: int, fg=curses.COLOR_WHITE):
        super(LackScreen, self).__init__(height, width, top, left, fg)

        curses.use_default_colors()
        for i in range(0, curses.COLORS):
            curses.init_pair(i, i, -1)

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
        self.promptwin.has_focus = True  # There's probably a better way to handle this

        self.promptwin.parent_key_handler = self.key_handler

        self.window.border(0)
        self.window.hline(self.logwin_height + 1,
                          1,
                          curses.ACS_HLINE,
                          self.cols - 2)
        self.window.noutrefresh()
        asyncio.ensure_future(self.draw())

    def key_handler(self, ch):

        ch = super(LackScreen, self).key_handler(ch)

        ch = self.logwin.key_handler(ch)

        return ch

    async def draw(self):

        await asyncio.sleep(0.05)

        if self.visible():
            self.window.noutrefresh()
            self.logwin.draw()

            msg = self.promptwin.textbox_prompt("> ", curses.COLOR_RED)

            if msg:
                asyncio.ensure_future(self.lack_manager.send_message(msg))

            curses.doupdate()

        asyncio.ensure_future(self.draw())
