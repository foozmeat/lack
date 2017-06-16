import curses
import signal
from curses import panel, ascii
from curses.textpad import Textbox
from typing import Callable, Optional, Any, Union

"""
Some ideas taken from https://github.com/konsulko/tizen-distro/blob/master/bitbake/lib/bb/ui/ncurses.py
"""

def flush():
    panel.update_panels()
    curses.doupdate()

class Window(object):
    def __init__(self, height: int, width: int, top: int, left: int, fg: int = curses.COLOR_WHITE) -> None:
        self.window = curses.newwin(height, width, top, left)
        self.height = height
        self.width = width
        self.top = top
        self.left = left
        self.window_y, self.window_x = self.window.getbegyx()
        self.parent_key_handler: Optional[Callable[[int], int]] = None

        if curses.has_colors():
            curses.use_default_colors()
            for i in range(0, curses.COLORS):
                curses.init_pair(i, i, -1)

            self.window.attron(curses.A_BOLD)
            self.window.bkgdset(ord(' '), curses.color_pair(fg))

        signal.signal(signal.SIGWINCH, self._resize_handler)

    def erase(self) -> None:
        self.window.erase()

    def _resize_handler(self, signum: Any, frame: Any) -> None:
        # if we don't trap the window resize we'll just crash
        pass

    def key_handler(self, ch: int) -> int:

        if self.parent_key_handler is not None:
            ch = self.parent_key_handler(ch)

        return ch

    def reset(self):
        self.window.erase()

class PanelWindow(Window):
    def __init__(self, *args, **kwargs) -> None:
        super(PanelWindow, self).__init__(*args, **kwargs)

        self.panel = panel.new_panel(self.window)
        self.panel.top()

        flush()

    def show(self) -> None:
        self.panel.show()
        flush()
        # self.has_focus = True

    def hide(self) -> None:
        self.panel.hide()
        flush()
        # self.has_focus = False

    def visible(self) -> bool:
        return not self.panel.hidden()


class SubWindow(object):

    """
    Subwindows are curses sub-windows - they share memory with their parent window. Top/Left are relative to the
    top/left of the parent window.
    """

    def __init__(self,
                 window: Window,
                 height: int = 0,
                 width: int = 0,
                 top: int = 0,
                 left: int = 0,
                 fg: int = curses.COLOR_WHITE) -> None:

        if height == 0:
            height = window.height

        if width == 0:
            width = window.width

        self.parent_window = window
        self.window = self.parent_window.window.derwin(height, width, top, left)

        self.height = height
        self.width = width
        self.top = top
        self.left = left
        self.window_y, self.window_x = self.window.getbegyx()
        self.parent_key_handler: Optional[Callable[[int], int]] = None
        self.window.bkgdset(ord(' '), curses.color_pair(fg))

    def hline(self, y:int, x:int, width:int) -> None:
        self.window.hline(y, x, curses.ACS_HLINE, width)

    def set_text(self,
                 y: int,
                 x: int,
                 text: str,
                 color: int = curses.COLOR_WHITE,
                 clr: bool = False,
                 *args: Any) -> None:

        self.window.attron(curses.color_pair(color))

        self.window.addstr(y, x, text, *args)

        if clr:
            self.window.clrtoeol()

        self.window.attroff(curses.color_pair(color))

    def draw(self) -> None:
        self._before_content()
        self._top_content()
        self._content()
        self._bottom_content()
        self._after_content()

    def _before_content(self) -> None:
        pass

    def _top_content(self) -> None:
        pass

    def _content(self) -> None:
        pass

    def _bottom_content(self) -> None:
        pass

    def _after_content(self) -> None:
        self.window.noutrefresh()
        # pass

    def key_handler(self, ch: int) -> int:

        if self.parent_key_handler is not None:
            ch = self.parent_key_handler(ch)

        return ch

    def reset(self):
        self.window.erase()

class BorderedSubWindow(SubWindow):
    def __init__(self, *args, **kwargs) -> None:
        super(BorderedSubWindow, self).__init__(*args, **kwargs)
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
        super(BorderedSubWindow, self).set_text(y + 1, x + 1, text, color=color, clr=clr, *args)

    def hline(self, y:int, x:int, width:int) -> None:
        self.window.hline(y + 1, x + 1, curses.ACS_HLINE, width)

    def reset(self):
        self.window.erase()
        self.window.box()

class PromptSubWindow(BorderedSubWindow):
    def __init__(self, *args, **kwargs) -> None:
        super(PromptSubWindow, self).__init__(*args, **kwargs)

        self.window.keypad(1)
        self.window.nodelay(1)
        self.window.idlok(1)
        self.msgpad: Optional[_Textbox] = None
        self.msgpad_window: Any = None
        self.msgpad_contents: str = ""
        self.allow_newlines: bool = False
        self.has_focus: bool = True

    def textbox_prompt(self, prompt: str = None, color: int = curses.COLOR_WHITE) -> Union[str, None]:

        if not self.has_focus:
            return None

        curses.curs_set(1)

        if not self.msgpad:
            self.reset()
            self.window.move(0, 0)

            if prompt is not None:
                self.set_text(0, 0, prompt, color=color)

            (y, x) = self.window.getyx()
            self.msgpad_window = self.window.subwin(self.height,
                                                    self.width - x,
                                                    self.window_y,
                                                    self.window_x + x)
            self.msgpad_window.erase()
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

        self.msgpad.do_command(ch)

        self.msgpad_contents = self.msgpad.gather().strip()

        if newline and not self.allow_newlines:
            msg = self.msgpad.gather().strip()

            self.msgpad_window.erase()

            self.msgpad = None
            self.msgpad_window = None
            self.msgpad_contents = ""

            self.window.refresh()
            if msg != '':
                return msg

        return None

    def scan_for_keypress(self) -> None:

        ch = self.window.getch()
        self.key_handler(ch)

    def any_key_prompt(self, prompt: str = "", color: int = curses.COLOR_WHITE) -> Union[int, None]:

        curses.curs_set(1)

        if prompt != "":
            self.set_text(0, 0, prompt, color=color)

            y, x = self.window.getyx()
            self.window.move(y, x)

        ch = self.window.getch()
        if ch == -1:
            return None

        ch = self.key_handler(ch)

        return chr(ch)

    def key_handler(self, ch: int) -> int:

        ch = super(PromptSubWindow, self).key_handler(ch)

        if ch == 127:
            return curses.KEY_BACKSPACE

        return ch

    def _after_content(self) -> None:
        pass
        # self.window.noutrefresh()

    def progressbar(self, msg: str, prog_val=0.0) -> None:

        text_len = len(msg)
        outer_bar_len = self.width - text_len - 7
        bar_len = outer_bar_len - 2

        if prog_val > 1.0:
            prog_val = 1.0

        percent_text = "{:.0f}%".format(prog_val * 100)
        bar_spaces = int(round(prog_val * bar_len, 0))
        blank_spaces = bar_len - bar_spaces
        prog_bar = "[" + ("#" * bar_spaces)
        prog_bar += " " * blank_spaces
        prog_bar += "] {}".format(percent_text)

        self.set_text(0, 0, f'{msg} {prog_bar}')


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
        """Collect and return the contents of the window."""
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
                result = result + chr(ascii.ascii(self.win.inch(y, x)))
            if self.maxy > 0:
                result = result + "\n"

        self.win.move(orig_y, orig_x)
        return result
