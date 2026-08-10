"""Single-line text input: cursor movement, editing, history, validation,
password masking, placeholders."""
from __future__ import annotations

from typing import Callable, Optional

from ..keys import Key
from ..style import Style, Theme, DEFAULT_THEME
from .base import Widget


class TextInput(Widget):
    def __init__(
        self,
        prompt: str = "> ",
        value: str = "",
        placeholder: str = "",
        password: bool = False,
        mask_char: str = "*",
        validator: Optional[Callable[[str], Optional[str]]] = None,
        history: Optional[list[str]] = None,
        theme: Theme = DEFAULT_THEME,
    ):
        super().__init__()
        self.prompt = prompt
        self.value = list(value)
        self.cursor = len(self.value)
        self.placeholder = placeholder
        self.password = password
        self.mask_char = mask_char
        self.validator = validator
        self.history = list(history) if history else []
        self.history_index = len(self.history)
        self.theme = theme
        self.error: Optional[str] = None
        self._draft = ""

    # -- rendering --------------------------------------------------
    def _char_style(self, index: int) -> Optional[Style]:
        """Hook for subclasses (e.g. SyntaxInput) to style individual
        characters. Returning None uses the default text style."""
        return None

    def render_lines(self) -> list[str]:
        text = "".join(self.value)
        display = self.mask_char * len(text) if (self.password and text) else text
        cursor_style = self.theme["cursor"]

        if not text and self.placeholder:
            body = self.prompt + self.theme["placeholder"].wrap(self.placeholder)
        else:
            out = []
            for i, ch in enumerate(display):
                base = self._char_style(i)
                style = cursor_style if i == self.cursor else base
                out.append(style.wrap(ch) if style else ch)
            if self.cursor == len(display):
                out.append(cursor_style.wrap(" "))
            body = self.theme["prompt"].wrap(self.prompt) + "".join(out)

        lines = [body]
        if self.error:
            lines.append(self.theme["error"].wrap(self.error))
        return lines

    # -- editing helpers --------------------------------------------
    def insert(self, ch: str) -> None:
        self.value[self.cursor:self.cursor] = list(ch)
        self.cursor += len(ch)
        self.error = None

    def delete_before(self) -> None:
        if self.cursor > 0:
            del self.value[self.cursor - 1]
            self.cursor -= 1

    def delete_at(self) -> None:
        if self.cursor < len(self.value):
            del self.value[self.cursor]

    def delete_word_before(self) -> None:
        i = self.cursor
        while i > 0 and self.value[i - 1] == " ":
            i -= 1
        while i > 0 and self.value[i - 1] != " ":
            i -= 1
        del self.value[i:self.cursor]
        self.cursor = i

    def text(self) -> str:
        return "".join(self.value)

    # -- history ------------------------------------------------------
    def _history_up(self) -> None:
        if not self.history:
            return
        if self.history_index == len(self.history):
            self._draft = self.text()
        if self.history_index > 0:
            self.history_index -= 1
            self.value = list(self.history[self.history_index])
            self.cursor = len(self.value)

    def _history_down(self) -> None:
        if not self.history:
            return
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.value = list(self.history[self.history_index])
        elif self.history_index == len(self.history) - 1:
            self.history_index += 1
            self.value = list(self._draft)
        self.cursor = len(self.value)

    # -- key handling ------------------------------------------------
    def handle_key(self, key: Key) -> None:
        name = key.name
        if name == "CHAR":
            self.insert(key.char)
        elif name == "BACKSPACE":
            self.delete_before()
        elif name == "DELETE":
            self.delete_at()
        elif name == "LEFT":
            self.cursor = max(0, self.cursor - 1)
        elif name == "RIGHT":
            self.cursor = min(len(self.value), self.cursor + 1)
        elif name in ("HOME", "CTRL_A"):
            self.cursor = 0
        elif name in ("END", "CTRL_E"):
            self.cursor = len(self.value)
        elif name == "CTRL_W":
            self.delete_word_before()
        elif name == "CTRL_U":
            del self.value[:self.cursor]
            self.cursor = 0
        elif name == "UP":
            self._history_up()
        elif name == "DOWN":
            self._history_down()
        elif name in ("ENTER",):
            self._try_submit()
        elif name in ("ESC", "CTRL_C"):
            self.cancel()

    def _try_submit(self) -> None:
        text = self.text()
        if self.validator:
            err = self.validator(text)
            if err:
                self.error = err
                return
        self.history.append(text)
        self.submit(text)
