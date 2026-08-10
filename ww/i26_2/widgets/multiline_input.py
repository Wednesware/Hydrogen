"""Multi-line text editor widget (a minimal textarea).

Plain Enter inserts a newline; submit with Ctrl+D (like EOF), cancel with
Esc or Ctrl+C. Supports optional line numbers.
"""
from __future__ import annotations

from typing import Optional

from ..keys import Key
from ..style import Style, Theme, DEFAULT_THEME
from .base import Widget


class MultilineInput(Widget):
    def __init__(
        self,
        prompt: str = "",
        value: str = "",
        placeholder: str = "Enter text... (Ctrl+D to submit, Esc to cancel)",
        line_numbers: bool = False,
        theme: Theme = DEFAULT_THEME,
        max_visible_lines: Optional[int] = None,
    ):
        super().__init__()
        self.prompt = prompt
        self.lines: list[list[str]] = [list(line) for line in (value.split("\n") if value else [""])]
        self.row = len(self.lines) - 1
        self.col = len(self.lines[self.row])
        self.placeholder = placeholder
        self.line_numbers = line_numbers
        self.theme = theme
        self.max_visible_lines = max_visible_lines

    # -- rendering --------------------------------------------------
    def _char_style(self, row: int, col: int) -> Optional[Style]:
        """Hook for subclasses (e.g. SyntaxInput) to style characters."""
        return None

    def render_lines(self) -> list[str]:
        cursor_style = self.theme["cursor"]
        is_empty = len(self.lines) == 1 and not self.lines[0]

        out_lines: list[str] = []
        if self.prompt:
            out_lines.append(self.theme["prompt"].wrap(self.prompt))

        if is_empty and self.placeholder:
            out_lines.append(self.theme["placeholder"].wrap(self.placeholder))
            return out_lines

        visible = self.lines
        offset = 0
        if self.max_visible_lines and len(self.lines) > self.max_visible_lines:
            half = self.max_visible_lines // 2
            offset = max(0, min(self.row - half, len(self.lines) - self.max_visible_lines))
            visible = self.lines[offset:offset + self.max_visible_lines]

        width = len(str(len(self.lines)))
        for i, line in enumerate(visible):
            real_row = i + offset
            rendered = []
            for j, ch in enumerate(line):
                base = self._char_style(real_row, j)
                style = cursor_style if (real_row == self.row and j == self.col) else base
                rendered.append(style.wrap(ch) if style else ch)
            if real_row == self.row and self.col == len(line):
                rendered.append(cursor_style.wrap(" "))
            text = "".join(rendered)
            if self.line_numbers:
                num = self.theme["line_number"].wrap(str(real_row + 1).rjust(width) + " │ ")
                text = num + text
            out_lines.append(text)
        return out_lines

    # -- helpers ------------------------------------------------------
    def text(self) -> str:
        return "\n".join("".join(line) for line in self.lines)

    # -- key handling ------------------------------------------------
    def handle_key(self, key: Key) -> None:
        name = key.name
        line = self.lines[self.row]

        if name == "CHAR":
            line[self.col:self.col] = list(key.char)
            self.col += len(key.char)
        elif name == "ENTER":
            rest = line[self.col:]
            del line[self.col:]
            self.lines.insert(self.row + 1, rest)
            self.row += 1
            self.col = 0
        elif name == "BACKSPACE":
            if self.col > 0:
                del line[self.col - 1]
                self.col -= 1
            elif self.row > 0:
                prev = self.lines[self.row - 1]
                self.col = len(prev)
                prev.extend(line)
                del self.lines[self.row]
                self.row -= 1
        elif name == "DELETE":
            if self.col < len(line):
                del line[self.col]
            elif self.row < len(self.lines) - 1:
                nxt = self.lines.pop(self.row + 1)
                line.extend(nxt)
        elif name == "LEFT":
            if self.col > 0:
                self.col -= 1
            elif self.row > 0:
                self.row -= 1
                self.col = len(self.lines[self.row])
        elif name == "RIGHT":
            if self.col < len(line):
                self.col += 1
            elif self.row < len(self.lines) - 1:
                self.row += 1
                self.col = 0
        elif name == "UP":
            if self.row > 0:
                self.row -= 1
                self.col = min(self.col, len(self.lines[self.row]))
        elif name == "DOWN":
            if self.row < len(self.lines) - 1:
                self.row += 1
                self.col = min(self.col, len(self.lines[self.row]))
        elif name in ("HOME", "CTRL_A"):
            self.col = 0
        elif name in ("END", "CTRL_E"):
            self.col = len(line)
        elif name == "TAB":
            line[self.col:self.col] = list("    ")
            self.col += 4
        elif name == "CTRL_D":
            self.submit(self.text())
        elif name in ("ESC", "CTRL_C"):
            self.cancel()
