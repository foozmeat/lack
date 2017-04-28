import curses
import signal
from curses import panel, ascii
from curses.textpad import Textbox

X = 0
Y = 1
WIDTH = 2
HEIGHT = 3


class Window:
    def __init__(self, height: int, width: int, top: int, left: int, fg=curses.COLOR_WHITE):
        self.window = curses.newwin(height, width, top, left)

        self.height = height
        self.width = width
        self.top = top
        self.left = left
        self.panel = None
        self.parent_key_handler = None

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

    def hide(self):
        if self.panel:
            self.panel.hide()
            # self.window.noutrefresh()
            panel.update_panels()

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
        self.window.timeout(0)
        self.window.nodelay(1)
        self.window.idlok(1)
        # self.window.leaveok(1)  # don't reset cursor position on update
        self.msgpad = None
        self.msgpad_window = None

    def textbox_prompt(self, prompt=None, color=None):
        """
        Don't use the standard curses textbox edit function since it won't play
        nicely with asyncio.
        """

        if not self.msgpad:
            if prompt:
                self.set_text(0, 0, prompt, color=color)

            (y, x) = self.window.getyx()
            self.msgpad_window = curses.newwin(self.height,
                                               self.width - x,
                                               self.window_y,
                                               self.window_x + x)
            self.msgpad = _Textbox(self.msgpad_window, insert_mode=True)

        self.window.noutrefresh()
        curses.curs_set(1)

        # Since we're using newwin we have to handle cursor position ourselves
        # self.set_text(0, 0, self.msgpad.gather().strip())
        # (y, x) = self.window.getyx()
        # self.window.move(y, x)

        ch = self.msgpad_window.getch()

        if ch == -1:
            return

        ch = self.key_handler(ch)

        dc_result = self.msgpad.do_command(ch)

        # self.window.noutrefresh()

        if dc_result == 0:
            msg = self.msgpad.gather().strip()

            self.msgpad = None
            self.msgpad_window = None
            self.window.erase()

            if msg != '':
                return msg

    def scan_for_keypress(self):

        ch = self.window.getch()
        self.key_handler(ch)

    def any_prompt(self, prompt=None, color=None):

        self.erase()

        if prompt:
            self.set_text(0, 0, prompt, color=color)

        self.window.refresh()

        ch = self._getch()

        return chr(ch)

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

    def _getch(self):

        ch = -1

        while ch <= 0 or ch >= 255:
            ch = self.window.getch()
            ch = self.key_handler(ch)

            if 0 <= ch <= 255:
                break

        return ch

    def key_handler(self, ch):

        if self.parent_key_handler:
            ch = self.parent_key_handler(ch)

        if ch == 127:
            return curses.KEY_BACKSPACE

        return ch


# class DecoratedWindow(Window):
#     """Base class for windows with a box and a title bar"""
#
#     def __init__(self, title: str, height: int, width: int, top: int, left: int, fg=curses.COLOR_WHITE):
#         super(DecoratedWindow, self).__init__(height - 4, width - 2, top + 3, left + 1, fg)
#
#         self.decoration = Window(height, width, top, left, fg)
#         self.decoration.set_boxed()
#         self.decoration.win.hline(2, 1, curses.ACS_HLINE, width - 2)
#         self.set_title(title)
#
#     def set_title(self, title):
#         self.decoration.set_text(1, 1, title.center(self.width - 2), curses.A_BOLD)


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
