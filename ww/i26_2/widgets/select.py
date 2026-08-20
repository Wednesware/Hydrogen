"""Customizable selection screen: single-select or multi-select lists with
optional live search/filtering, custom item rendering, and scrolling for
long option lists."""
from __future__ import annotations

from typing import Any, Callable, Optional

from ..keys import Key
from ..style import Theme, DEFAULT_THEME
from .base import Widget


class Option:
    __slots__ = ("label", "value")

    def __init__(self, label: str, value: Any = None):
        self.label = label
        self.value = value if value is not None else label


class SelectMenu(Widget):
    def __init__(
        self,
        options: list,
        title: str = "",
        multi: bool = False,
        searchable: bool = True,
        max_visible: int = 10,
        render_item: Optional[Callable[[Option, bool, bool], str]] = None,
        pointer: str = "❯ ",
        theme: Theme = DEFAULT_THEME,
    ):
        super().__init__()
        self.options = [o if isinstance(o, Option) else Option(str(o)) for o in options]
        self.title = title
        self.multi = multi
        self.searchable = searchable
        self.max_visible = max_visible
        self.render_item = render_item
        self.pointer = pointer
        self.theme = theme

        self.cursor = 0
        self.query = ""
        self.checked: set[int] = set()

    # -- filtering ------------------------------------------------------
    def _filtered_indices(self) -> list[int]:
        if not self.query:
            return list(range(len(self.options)))
        q = self.query.lower()
        return [i for i, o in enumerate(self.options) if q in o.label.lower()]

    def _default_render_item(self, option: Option, is_cursor: bool, is_checked: bool) -> str:
        prefix = self.pointer if is_cursor else " " * len(self.pointer)
        box = ""
        if self.multi:
            box = self.theme["checked"].wrap("[x] ") if is_checked else "[ ] "
        style = self.theme["selected"] if is_cursor else self.theme["unselected"]
        return prefix + box + style.wrap(option.label)

    # -- rendering --------------------------------------------------
    def render_lines(self) -> list[str]:
        lines = []
        if self.title:
            lines.append(self.theme["title"].wrap(self.title))
        if self.searchable:
            lines.append(self.theme["prompt"].wrap("/ ") + self.query + self.theme["cursor"].wrap(" "))

        indices = self._filtered_indices()
        if not indices:
            lines.append(self.theme["hint"].wrap("  (no matches)"))
            return lines

        if self.cursor >= len(indices):
            self.cursor = len(indices) - 1
        if self.cursor < 0:
            self.cursor = 0

        offset = 0
        if len(indices) > self.max_visible:
            half = self.max_visible // 2
            offset = max(0, min(self.cursor - half, len(indices) - self.max_visible))
        visible = indices[offset: offset + self.max_visible]

        renderer = self.render_item or self._default_render_item
        for pos, idx in enumerate(visible):
            option = self.options[idx]
            is_cursor = (offset + pos) == self.cursor
            is_checked = idx in self.checked
            lines.append(renderer(option, is_cursor, is_checked))

        if len(indices) > self.max_visible:
            lines.append(self.theme["hint"].wrap(
                f"  {offset + 1}-{offset + len(visible)} of {len(indices)}"))

        hint = "↑/↓ move · enter select"
        if self.multi:
            hint += " · space toggle · enter confirm"
        if self.searchable:
            hint += " · type to filter"
        lines.append(self.theme["hint"].wrap("  " + hint))
        return lines

    # -- keys ------------------------------------------------------
    def handle_key(self, key: Key) -> None:
        indices = self._filtered_indices()
        name = key.name

        if name == "UP":
            self.cursor = (self.cursor - 1) % max(1, len(indices))
        elif name == "DOWN":
            self.cursor = (self.cursor + 1) % max(1, len(indices))
        elif name == "PAGE_UP":
            self.cursor = max(0, self.cursor - self.max_visible)
        elif name == "PAGE_DOWN":
            self.cursor = min(max(0, len(indices) - 1), self.cursor + self.max_visible)
        elif name == "HOME":
            self.cursor = 0
        elif name == "END":
            self.cursor = max(0, len(indices) - 1)
        elif name == "CHAR" and key.char == " " and self.multi:
            if indices:
                self.checked.symmetric_difference_update({indices[self.cursor]})
        elif name == "CHAR" and self.searchable:
            self.query += key.char
            self.cursor = 0
        elif name == "BACKSPACE" and self.searchable:
            self.query = self.query[:-1]
            self.cursor = 0
        elif name == "ENTER":
            if self.multi:
                chosen = [self.options[i] for i in sorted(self.checked)]
                self.submit([o.value for o in chosen])
            else:
                if indices:
                    self.submit(self.options[indices[self.cursor]].value)
                else:
                    self.cancel()
        elif name in ("ESC", "CTRL_C"):
            self.cancel()
