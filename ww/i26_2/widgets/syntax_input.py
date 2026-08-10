"""Multi-line input with live regex-based syntax highlighting."""
from __future__ import annotations

from typing import Optional

from ..highlight import Highlighter
from ..style import Style
from .multiline_input import MultilineInput


class SyntaxInput(MultilineInput):
    def __init__(self, highlighter: Highlighter, **kwargs):
        super().__init__(**kwargs)
        self.highlighter = highlighter
        self._cache_row = -1
        self._cache_text = None
        self._cache_styles: list[Optional[Style]] = []

    def _char_style(self, row: int, col: int) -> Optional[Style]:
        line_text = "".join(self.lines[row])
        if self._cache_row != row or self._cache_text != line_text:
            self._cache_row = row
            self._cache_text = line_text
            self._cache_styles = self.highlighter.styles_for(line_text)
        if col < len(self._cache_styles):
            return self._cache_styles[col]
        return None
