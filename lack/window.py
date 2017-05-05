import curses
import signal
import asyncio

from curses import panel
from curses.textpad import Textbox

"""
Some ideas taken from https://github.com/konsulko/tizen-distro/blob/master/bitbake/lib/bb/ui/ncurses.py
"""
class Window:
    def __init__(self, height: int, width: int, top: int, left: int, fg=curses.COLOR_WHITE) -> None:
        self.window = curses.newwin(height, width, top, left)

        self.height = height
        self.width = width
        self.top = top
        self.left = left
        self.panel = None
        self.parent_key_handler = None
        self.has_focus = False

        self.window_y, self.window_x = self.window.getbegyx()
        self.rows, self.cols = self.window.getmaxyx()

        if curses.has_colors():
            curses.use_default_colors()
            for i in range(0, curses.COLORS):
                curses.init_pair(i, i, -1)

            self.window.attron(curses.A_BOLD)
            self.window.bkgdset(ord(' '), curses.color_pair(fg))

        self.boxed = False
        self.erase()
        signal.signal(signal.SIGWINCH, self._resize_handler)

        self.window.noutrefresh()

    def erase(self):
        self.window.erase()

    def set_boxed(self):
        self.boxed = True
        self.window.box()
        self.window.noutrefresh()

    def set_text(self, y, x, text, color=None, clr=False, *args):

        if color:
            self.window.attron(curses.color_pair(color))

        self.window.addstr(y, x, text, *args)

        if clr:
            self.window.clrtoeol()

        if color:
            self.window.attroff(curses.color_pair(color))

        self.window.noutrefresh()

    def key_handler(self, ch):

        if self.parent_key_handler:
            ch = self.parent_key_handler(ch)

        return ch

    def draw(self):
        self.window.noutrefresh()

    def add_panel(self):
        self.panel = panel.new_panel(self.window)
        panel.update_panels()

        return self.panel

    def show(self):
        if self.panel:
            self.panel.show()
            # self.window.noutrefresh()
            panel.update_panels()
        self.has_focus = True

    def hide(self):
        if self.panel:
            self.panel.hide()
            # self.window.noutrefresh()
            panel.update_panels()
        self.has_focus = False

    def visible(self):
        if self.panel:
            return not self.panel.hidden()

        else:
            return True

    def _resize_handler(self, signum, frame):
        # if we don't trap the window resize we'll just crash
        pass


class PromptWindow(Window):
    def __init__(self, *args, **kwargs):
        super(PromptWindow, self).__init__(*args, **kwargs)

        self.window.keypad(1)
        self.window.nodelay(1)
        self.window.idlok(1)
        self.msgpad = None
        self.msgpad_window = None
        self.msgpad_contents = ""
        self.allow_newlines = False

    def textbox_prompt(self, prompt=None, color=None):
        """
        Don't use the standard curses textbox edit function since it won't play
        nicely with asyncio.
        """

        if not self.has_focus:
            return

        curses.curs_set(1)
        self.window.noutrefresh()

        if not self.msgpad:
            if prompt:
                self.set_text(0, 0, prompt, color=color)

            (y, x) = self.window.getyx()
            self.msgpad_window = curses.newwin(self.height,
                                               self.width - x,
                                               self.window_y,
                                               self.window_x + x)
            self.msgpad = _Textbox(self.msgpad_window, insert_mode=True)
            self.msgpad_window.keypad(1)
            self.msgpad_window.nodelay(1)
            self.msgpad_window.idlok(1)

        y, x = self.msgpad_window.getyx()
        self.msgpad_window.move(y, x)

        ch = self.msgpad_window.getch()

        if ch == -1:
            return

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

    def scan_for_keypress(self):

        ch = self.window.getch()
        self.key_handler(ch)

    def any_key_prompt(self, prompt=None, color=None):

        curses.curs_set(1)

        if prompt:
            self.set_text(0, 0, prompt, color=color)

        self.window.noutrefresh()
        y, x = self.window.getyx()
        self.window.move(y, x)

        ch = self.window.getch()
        if ch == -1:
            return

        ch = self.key_handler(ch)

        return ch

    # def char_prompt(self, prompt=None, color=None):
    #
    #     curses.curs_set(1)
    #     self.window.nodelay(0)
    #     self.erase()
    #
    #     if prompt:
    #         self.set_text(0, 0, prompt, color=color)
    #
    #     ch = -1
    #     while not ascii.isprint(ch):
    #         ch = self.window.getch()
    #         ch = self.key_handler(ch)
    #
    #     curses.curs_set(0)
    #     return chr(ch)

    # def _getch(self):
    #
    #     ch = -1
    #
    #     while ch <= 0 or ch >= 255:
    #         ch = self.window.getch()
    #         ch = self.key_handler(ch)
    #
    #         if 0 <= ch <= 255:
    #             break
    #
    #     return ch

    def key_handler(self, ch):

        if self.parent_key_handler:
            ch = self.parent_key_handler(ch)

        if ch == 127:
            return curses.KEY_BACKSPACE

        return ch

class _Textbox(Textbox):
    """
    Change the default textbox behavior of enter, up, and down.
    """

    def __init__(*args, **kwargs):
        Textbox.__init__(*args, **kwargs)

    def do_command(self, ch):

        if ch == curses.KEY_UP:
            return 1

        elif ch == curses.KEY_DOWN:
            return 1

        else:
            return Textbox.do_command(self, ch)

    def gather(self):
        "Collect and return the contents of the window."
        result = ""
        orig_y, orig_x = self.win.getyx()

        self._update_max_yx()
        for y in range(self.maxy+1):
            self.win.move(y, 0)
            stop = self._end_of_line(y)
            if stop == 0 and self.stripspaces:
                continue
            for x in range(self.maxx+1):
                if self.stripspaces and x > stop:
                    break
                result = result + chr(curses.ascii.ascii(self.win.inch(y, x)))
            if self.maxy > 0:
                result = result + "\n"

        self.win.move(orig_y, orig_x)
        return result
