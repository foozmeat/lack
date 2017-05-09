import asyncio
import curses

from .lackmanager import LackManager
from .logsubwindow import LogSubWindow
from .window import PromptSubWindow, PanelWindow


class LackMainWindow(PanelWindow):
    def __init__(self, height: int, width: int, top: int, left: int, fg=curses.COLOR_WHITE) -> None:
        super(LackMainWindow, self).__init__(height, width, top, left, fg)

        logwin_height = self.height - 4
        logwin_width = self.width

        self.lack_manager = LackManager(logwin_width)

        self.logwin = LogSubWindow(self,
                                   height=logwin_height,
                                   datasource=self.lack_manager.loglines)

        self.promptwin = PromptSubWindow(self,
                                         height=4,
                                         top=logwin_height)

        self.promptwin.parent_key_handler = self.key_handler

        asyncio.ensure_future(self.draw())

    def key_handler(self, ch: int) -> int:

        ch = super(LackMainWindow, self).key_handler(ch)

        ch = self.logwin.key_handler(ch)

        return ch

    async def draw(self) -> None:

        await asyncio.sleep(0.05)

        if self.visible():
            self.logwin.draw()

            msg = self.promptwin.textbox_prompt("> ", curses.COLOR_RED)

            if msg:
                asyncio.ensure_future(self.lack_manager.send_message(msg))

        asyncio.ensure_future(self.draw())
