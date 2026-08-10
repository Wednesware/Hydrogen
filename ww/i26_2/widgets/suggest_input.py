"""Text input with an autocomplete dropdown."""
from __future__ import annotations

from typing import Callable, Optional, Union

from ..keys import Key
from ..style import Theme, DEFAULT_THEME
from .text_input import TextInput

Suggestions = Union[list[str], Callable[[str], list[str]]]


class SuggestInput(TextInput):
    def __init__(
        self,
        suggestions: Suggestions,
        max_visible: int = 6,
        fuzzy: bool = False,
        accept_key: str = "TAB",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.suggestions = suggestions
        self.max_visible = max_visible
        self.fuzzy = fuzzy
        self.accept_key = accept_key
        self.selected = 0

    # -- filtering ------------------------------------------------------
    def _all_suggestions(self) -> list[str]:
        if callable(self.suggestions):
            return list(self.suggestions(self.text()))
        return list(self.suggestions)

    def _matches(self) -> list[str]:
        text = self.text()
        if not text:
            return []
        candidates = self._all_suggestions()
        if self.fuzzy:
            needle = text.lower()
            out = []
            for cand in candidates:
                hay = cand.lower()
                it = iter(hay)
                if all(c in it for c in needle):
                    out.append(cand)
            return out
        return [c for c in candidates if c.lower().startswith(text.lower()) and c != text]

    # -- rendering --------------------------------------------------
    def render_lines(self) -> list[str]:
        lines = super().render_lines()
        matches = self._matches()
        if not matches:
            self.selected = 0
            return lines
        self.selected = max(0, min(self.selected, len(matches) - 1))
        shown = matches[: self.max_visible]
        for i, cand in enumerate(shown):
            style = self.theme["suggestion_selected"] if i == self.selected else self.theme["suggestion"]
            lines.append("  " + style.wrap(cand))
        if len(matches) > self.max_visible:
            lines.append("  " + self.theme["hint"].wrap(f"... {len(matches) - self.max_visible} more"))
        return lines

    # -- keys ------------------------------------------------------
    def handle_key(self, key: Key) -> None:
        matches = self._matches()
        if matches:
            if key.name == "DOWN":
                self.selected = (self.selected + 1) % len(matches)
                return
            if key.name == "UP":
                self.selected = (self.selected - 1) % len(matches)
                return
            if key.token() == self.accept_key or (key.name == "RIGHT" and self.cursor == len(self.value)):
                chosen = matches[self.selected]
                self.value = list(chosen)
                self.cursor = len(self.value)
                self.selected = 0
                return
        super().handle_key(key)
