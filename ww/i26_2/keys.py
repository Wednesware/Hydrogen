"""Keyboard input decoding.

Reads raw bytes from a tty file descriptor (already in raw mode) and turns
them into :class:`Key` tokens, resolving multi-byte ANSI escape sequences
(arrow keys, Home/End/Delete, function keys, etc.) and Ctrl+letter chords.
"""
from __future__ import annotations

import os
import select

# Multi-byte escape sequences -> canonical key name.
ESCAPE_SEQUENCES = {
    "\x1b[A": "UP", "\x1b[B": "DOWN", "\x1b[C": "RIGHT", "\x1b[D": "LEFT",
    "\x1bOA": "UP", "\x1bOB": "DOWN", "\x1bOC": "RIGHT", "\x1bOD": "LEFT",
    "\x1b[H": "HOME", "\x1b[F": "END",
    "\x1b[1~": "HOME", "\x1b[4~": "END", "\x1b[7~": "HOME", "\x1b[8~": "END",
    "\x1b[3~": "DELETE",
    "\x1b[5~": "PAGE_UP", "\x1b[6~": "PAGE_DOWN",
    "\x1bOP": "F1", "\x1bOQ": "F2", "\x1bOR": "F3", "\x1bOS": "F4",
    "\x1b[15~": "F5", "\x1b[17~": "F6", "\x1b[18~": "F7", "\x1b[19~": "F8",
    "\x1b[20~": "F9", "\x1b[21~": "F10", "\x1b[23~": "F11", "\x1b[24~": "F12",
    "\x1b[Z": "SHIFT_TAB",
    "\x1b[1;5C": "CTRL_RIGHT", "\x1b[1;5D": "CTRL_LEFT",
}


class Key:
    """A single decoded key event.

    ``name`` is a canonical token (e.g. ``"UP"``, ``"ENTER"``, ``"CTRL_A"``,
    or ``"CHAR"`` for printable input). ``char`` holds the literal printable
    character when ``name == "CHAR"``.
    """

    __slots__ = ("name", "char")

    def __init__(self, name: str, char: str | None = None):
        self.name = name
        self.char = char

    def __eq__(self, other):
        if isinstance(other, str):
            return self.name == other or self.char == other
        if isinstance(other, Key):
            return self.name == other.name and self.char == other.char
        return NotImplemented

    def __hash__(self):
        return hash((self.name, self.char))

    def __repr__(self):
        return f"Key({self.name!r}, {self.char!r})"

    def token(self) -> str:
        """The value most useful for keymap lookups: the char if printable,
        otherwise the canonical name."""
        return self.char if self.name == "CHAR" and self.char else self.name


def read_key(fd: int, timeout: float | None = None) -> Key | None:
    """Read and decode a single key event from ``fd``.

    Blocks until a key is available unless ``timeout`` is given, in which
    case ``None`` is returned if nothing arrives in time.
    """
    if timeout is not None:
        ready, _, _ = select.select([fd], [], [], timeout)
        if not ready:
            return None

    first = os.read(fd, 1)
    if not first:
        return None
    ch = first.decode(errors="ignore")

    if ch == "\x1b":
        seq = ch
        while True:
            ready, _, _ = select.select([fd], [], [], 0.01)
            if not ready:
                break
            seq += os.read(fd, 1).decode(errors="ignore")
            if seq in ESCAPE_SEQUENCES:
                break
            if len(seq) > 8:
                break
        if seq == "\x1b":
            return Key("ESC")
        name = ESCAPE_SEQUENCES.get(seq)
        return Key(name) if name else Key("UNKNOWN", char=seq)

    if ch in ("\r", "\n"):
        return Key("ENTER")
    if ch == "\t":
        return Key("TAB")
    if ch in ("\x7f", "\x08"):
        return Key("BACKSPACE")
    if ch == "\x03":
        return Key("CTRL_C")
    if ch == "\x04":
        return Key("CTRL_D")

    code = ord(ch)
    if 1 <= code <= 26:
        # Ctrl+A..Ctrl+Z (Ctrl+I == Tab, Ctrl+M == Enter handled above)
        letter = chr(code + 96).upper()
        return Key(f"CTRL_{letter}")

    return Key("CHAR", char=ch)
