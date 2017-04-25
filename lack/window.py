import curses
from curses.textpad import Textbox

X = 0
Y = 1
WIDTH = 2
HEIGHT = 3


class Window:
    def __init__(self, height: int, width: int, top: int, left: int, fg=curses.COLOR_WHITE, bg=curses.COLOR_BLACK):
        self.window = curses.newwin(height, width, top, left)

        self.height = height
        self.width = width
        self.top = top
        self.left = left

        self.window_y, self.window_x = self.window.getbegyx()
        self.rows, self.cols = self.window.getmaxyx()

        # if curses.has_colors():
        #     color = 99
        #     curses.init_pair(color, fg, bg)
        #     self.window.bkgdset(ord(' '), curses.color_pair(color))
        # else:
        #     self.window.bkgdset(ord(' '), curses.A_BOLD)

        self.boxed = False
        self.erase()

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

    def key_validation(self, ch):
        return ch

    def draw(self):
        self.window.noutrefresh()


class PromptWindow(Window):
    def __init__(self, *args, **kwargs):
        super(PromptWindow, self).__init__(*args, **kwargs)

        self.window.keypad(1)
        self.window.timeout(0)
        self.window.nodelay(1)
        self.window.idlok(1)
        # self.window.leaveok(1)  # don't reset cursor position on update
        self.msgpad = None

    def textbox_prompt(self, key_handler=None):
        """
        Don't use the standard curses textbox edit function since it won't play
        nicely with asyncio.
        """

        if not self.msgpad:
            self.msgpad = _Textbox(self.window, insert_mode=True)

        curses.curs_set(1)

        # Since we're using newwin we have to handle cursor position ourselves
        # self.set_text(0, 0, self.msgpad.gather().strip())
        # (y, x) = self.window.getyx()
        # self.window.move(y, x)

        ch = self.window.getch()

        if ch == -1:
            return

        ch = self.key_validation(ch)

        if key_handler:
            ch = key_handler(ch)

        dc_result = self.msgpad.do_command(ch)

        # self.window.noutrefresh()

        if dc_result == 0:
            msg = self.msgpad.gather().strip()

            self.msgpad = None
            self.window.clear()

            if msg != '':
                return msg

    def key_validation(self, ch):

        """
        This is our chance to modify incoming keystrokes before they're acted on
        in do_command
        """

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
