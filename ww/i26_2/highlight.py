"""Lightweight regex-based syntax highlighting, no external dependencies.

A :class:`Highlighter` is just an ordered list of ``(regex, Style)`` rules.
The first matching rule wins for each character. Ships with a couple of
ready-made highlighters (``PYTHON``, ``JSON``) as examples/starting points.
"""
from __future__ import annotations

import re

from .style import Style


class Highlighter:
    def __init__(self, rules: list[tuple[str, Style]]):
        self.rules = [(re.compile(pattern), style) for pattern, style in rules]

    def styles_for(self, text: str) -> list[Style | None]:
        """Return a per-character list of the winning Style (or None)."""
        styled: list[Style | None] = [None] * len(text)
        for regex, style in self.rules:
            for m in regex.finditer(text):
                start, end = m.span()
                for i in range(start, end):
                    if styled[i] is None:
                        styled[i] = style
        return styled

    def highlight(self, text: str) -> str:
        """Return ``text`` wrapped in ANSI codes per matching rule."""
        styles = self.styles_for(text)
        out = []
        i, n = 0, len(text)
        while i < n:
            style = styles[i]
            j = i
            while j < n and styles[j] is style:
                j += 1
            chunk = text[i:j]
            out.append(style.wrap(chunk) if style else chunk)
            i = j
        return "".join(out)


PYTHON = Highlighter([
    (r"#.*$", Style(fg="bright_black", italic=True)),
    (r"(\"\"\".*?\"\"\"|'''.*?''')", Style(fg="green")),
    (r'(\".*?\"|\'.*?\')', Style(fg="green")),
    (r"\b\d+(\.\d+)?\b", Style(fg="magenta")),
    (r"\b(def|class|if|elif|else|for|while|return|import|from|as|with|"
     r"try|except|finally|raise|yield|lambda|in|not|and|or|is|None|True|"
     r"False|pass|break|continue|async|await|self)\b", Style(fg="cyan", bold=True)),
    (r"\b([A-Za-z_][A-Za-z0-9_]*)(?=\()", Style(fg="yellow")),
])

JSON = Highlighter([
    (r'"(\\.|[^"\\])*"\s*(?=:)', Style(fg="cyan")),
    (r'"(\\.|[^"\\])*"', Style(fg="green")),
    (r"\b(true|false|null)\b", Style(fg="magenta", bold=True)),
    (r"-?\b\d+(\.\d+)?([eE][+-]?\d+)?\b", Style(fg="yellow")),
    (r"[{}\[\],:]", Style(fg="bright_black")),
])
