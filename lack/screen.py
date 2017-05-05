import asyncio
import curses

from .lackmanager import LackManager
from .logwindow import LogWindow
from .window import Window, PromptWindow


class LackScreen(Window):
    def __init__(self, height: int, width: int, top: int, left: int, fg=curses.COLOR_WHITE) -> None:
        super(LackScreen, self).__init__(height, width, top, left, fg)

        logwin_top = self.window_y
        logwin_left = self.window_x
        logwin_height = self.height - 4
        logwin_width = self.width

        self.lack_manager = LackManager(logwin_width)

        self.logwin = LogWindow(logwin_height,
                                logwin_width,
                                logwin_top,
                                logwin_left,
                                self.lack_manager.loglines)

        self.promptwin = PromptWindow(4,
                                      logwin_width,
                                      logwin_top + logwin_height,
                                      logwin_left)
        self.promptwin.has_focus = True  # There's probably a better way to handle this

        self.promptwin.parent_key_handler = self.key_handler

        asyncio.ensure_future(self.draw())

    def key_handler(self, ch: int) -> int:

        ch = super(LackScreen, self).key_handler(ch)

        ch = self.logwin.key_handler(ch)

        return ch

    async def draw(self) -> None:

        await asyncio.sleep(0.05)

        if self.visible():
            self.logwin.draw()
            self.promptwin.draw()

            msg = self.promptwin.textbox_prompt("> ", curses.COLOR_RED)

            if msg:
                asyncio.ensure_future(self.lack_manager.send_message(msg))

        asyncio.ensure_future(self.draw())
