import curses
import signal
import asyncio
import typing
from typing import Callable, Optional, Any, Union

from curses import panel
from curses.textpad import Textbox

"""
Some ideas taken from https://github.com/konsulko/tizen-distro/blob/master/bitbake/lib/bb/ui/ncurses.py
"""


class Window(object):
    def __init__(self, height: int, width: int, top: int, left: int, fg: int = curses.COLOR_WHITE) -> None:
        self.window = curses.newwin(height, width, top, left)

        self.height = height
        self.width = width
        self.top = top
        self.left = left
        self.panel: panel = None
        self.parent_key_handler: Optional[Callable[[int], int]] = None
        self.has_focus: bool = False

        self.window_y, self.window_x = self.window.getbegyx()

        if curses.has_colors():
            curses.use_default_colors()
            for i in range(0, curses.COLORS):
                curses.init_pair(i, i, -1)

            self.window.attron(curses.A_BOLD)
            self.window.bkgdset(ord(' '), curses.color_pair(fg))

        signal.signal(signal.SIGWINCH, self._resize_handler)

    def erase(self) -> None:
        self.window.erase()

    def set_text(self,
                 y: int,
                 x: int,
                 text: str,
                 color: int = curses.COLOR_WHITE,
                 clr: bool = False,
                 *args: Any) -> None:

        self.window.attron(curses.color_pair(color))

        self.window.addstr(y,
                           x,
                           text,
                           *args)

        if clr:
            self.window.clrtoeol()

        self.window.attroff(curses.color_pair(color))
        self.window.refresh()

    def key_handler(self, ch: int) -> int:

        if self.parent_key_handler is not None:
            ch = self.parent_key_handler(ch)

        return ch

    def draw(self) -> None:
        pass
        # self.window.refresh()

    def add_panel(self) -> panel:
        self.panel = panel.new_panel(self.window)
        panel.update_panels()
        curses.doupdate()

        return self.panel

    def show(self) -> None:
        if self.panel:
            self.panel.show()
            panel.update_panels()
            curses.doupdate()
        self.has_focus = True

    def hide(self) -> None:
        if self.panel:
            self.panel.hide()
            panel.update_panels()
            curses.doupdate()
        self.has_focus = False

    def visible(self) -> bool:
        if self.panel is not None:
            return not self.panel.hidden()

        else:
            return True

    def _resize_handler(self, signum: Any, frame: Any) -> None:
        # if we don't trap the window resize we'll just crash
        pass


class BorderedWindow(Window):
    def __init__(self, height: int, width: int, top: int, left: int, fg: int = curses.COLOR_WHITE) -> None:
        # super(BorderedWindow, self).__init__(height - 2, width - 2, top + 1, left + 1, fg)
        super(BorderedWindow, self).__init__(height, width, top, left, fg)
        self.window.box()

        self.height -= 2
        self.width -= 2
        self.window_y += 1
        self.window_x += 1

    def set_text(self,
                 y: int,
                 x: int,
                 text: str,
                 color: int = curses.COLOR_WHITE,
                 clr: bool = False,
                 *args: Any) -> None:
        super(BorderedWindow, self).set_text(y + 1, x + 1, text, color=color, clr=clr, *args)


class PromptWindow(BorderedWindow):
    def __init__(self, height: int, width: int, top: int, left: int, fg: int = curses.COLOR_WHITE) -> None:
        super(PromptWindow, self).__init__(height, width, top, left, fg)

        self.window.keypad(1)
        self.window.nodelay(1)
        self.window.idlok(1)
        self.msgpad: Optional[_Textbox] = None
        self.msgpad_window: Any = None
        self.msgpad_contents: str = ""
        self.allow_newlines: bool = False

    def textbox_prompt(self, prompt: str = None, color: int = curses.COLOR_WHITE) -> Union[str, None]:

        if not self.has_focus:
            return None

        curses.curs_set(1)

        if not self.msgpad:
            if prompt is not None:
                self.set_text(0, 0, prompt, color=color)

            (y, x) = self.window.getyx()
            self.msgpad_window = self.window.subwin(self.height,
                                                    self.width - x,
                                                    self.window_y,
                                                    self.window_x + x)
            self.msgpad = _Textbox(self.msgpad_window, insert_mode=True)
            self.msgpad_window.keypad(1)
            self.msgpad_window.nodelay(1)
            self.msgpad_window.idlok(1)

            self.window.refresh()

        y, x = self.msgpad_window.getyx()
        self.msgpad_window.move(y, x)

        ch = self.msgpad_window.getch()

        if ch == -1:
            return None

        self.msgpad_window.refresh()

        ch = self.key_handler(ch)

        newline = True if ch == 10 else False

        dc_result = self.msgpad.do_command(ch)

        self.msgpad_contents = self.msgpad.gather().strip()

        if newline and not self.allow_newlines:
            msg = self.msgpad.gather().strip()

            self.msgpad = None
            self.msgpad_window = None
            self.msgpad_contents = ""

            if msg != '':
                return msg

        return None

    def scan_for_keypress(self) -> None:

        ch = self.window.getch()
        self.key_handler(ch)

    def any_key_prompt(self, prompt: str = "", color: int = curses.COLOR_WHITE) -> Union[str, None]:

        curses.curs_set(1)

        self.set_text(0, 0, prompt, color=color)

        y, x = self.window.getyx()
        self.window.move(y, x)

        ch = self.window.getch()
        if ch == -1:
            return None

        ch = self.key_handler(ch)

        return ch

    def key_handler(self, ch: int) -> int:

        ch = super(PromptWindow, self).key_handler(ch)

        if ch == 127:
            return curses.KEY_BACKSPACE

        return ch

    def draw(self):
        pass


class _Textbox(Textbox):
    def __init__(self, win, insert_mode=False) -> None:
        super(_Textbox, self).__init__(win, insert_mode)

    def do_command(self, ch: int) -> int:
        """
        Change the default textbox behavior of up, and down.
        """

        if ch == curses.KEY_UP:
            return 1

        elif ch == curses.KEY_DOWN:
            return 1

        else:
            return Textbox.do_command(self, ch)

    def gather(self) -> str:
        "Collect and return the contents of the window."
        result = ""
        orig_y, orig_x = self.win.getyx()

        self._update_max_yx()
        for y in range(self.maxy + 1):
            self.win.move(y, 0)
            stop = self._end_of_line(y)
            if stop == 0 and self.stripspaces:
                continue
            for x in range(self.maxx + 1):
                if self.stripspaces and x > stop:
                    break
                result = result + chr(curses.ascii.ascii(self.win.inch(y, x)))
            if self.maxy > 0:
                result = result + "\n"

        self.win.move(orig_y, orig_x)
        return result
