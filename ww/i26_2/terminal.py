"""Low level terminal control: raw mode, ANSI cursor/screen control, sizing.

Stdlib only (termios/tty are POSIX-only; this library targets Linux/macOS
terminals). No third-party dependencies.
"""
from __future__ import annotations

import contextlib
import os
import shutil
import sys
import termios
import tty


class Terminal:
    """Wraps a POSIX tty with raw-mode + ANSI helpers.

    Widgets never emit real cursor moves for editing (they render a "virtual"
    cursor as a highlighted character instead), which means redrawing a block
    of N lines only ever needs: move up (N-1), carriage return, clear to end
    of screen, write new block. See :meth:`redraw`.
    """

    def __init__(self, out=None, in_fd: int | None = None):
        self.out = out or sys.stdout
        self.fd = in_fd if in_fd is not None else sys.stdin.fileno()
        self._saved_attrs = None

    # -- raw mode -----------------------------------------------------
    @contextlib.contextmanager
    def raw_mode(self):
        self._saved_attrs = termios.tcgetattr(self.fd)
        tty.setraw(self.fd)
        try:
            yield self
        finally:
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self._saved_attrs)

    @contextlib.contextmanager
    def hidden_cursor(self):
        self.write("\x1b[?25l")
        self.flush()
        try:
            yield self
        finally:
            self.write("\x1b[?25h")
            self.flush()

    @contextlib.contextmanager
    def alt_screen(self):
        self.write("\x1b[?1049h")
        self.flush()
        try:
            yield self
        finally:
            self.write("\x1b[?1049l")
            self.flush()

    # -- low level ------------------------------------------------------
    def write(self, s: str) -> None:
        self.out.write(s)

    def flush(self) -> None:
        self.out.flush()

    @property
    def size(self) -> tuple[int, int]:
        cols, rows = shutil.get_terminal_size()
        return cols, rows

    # -- block redraw ---------------------------------------------------
    def redraw(self, prev_line_count: int, lines: list[str]) -> int:
        """Erase the previously drawn block (``prev_line_count`` lines,
        cursor assumed at the end of the last line with no trailing
        newline) and write ``lines`` in its place. Returns new line count.
        """
        if prev_line_count:
            if prev_line_count > 1:
                self.write(f"\x1b[{prev_line_count - 1}A")
            self.write("\r\x1b[J")
        self.write("\r\n".join(lines))
        self.flush()
        return len(lines)

    def clear_block(self, prev_line_count: int) -> None:
        if prev_line_count:
            if prev_line_count > 1:
                self.write(f"\x1b[{prev_line_count - 1}A")
            self.write("\r\x1b[J")
        self.flush()

    def newline(self) -> None:
        self.write("\r\n")
        self.flush()
