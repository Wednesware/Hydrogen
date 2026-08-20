"""Base class shared by all interactive widgets."""
from __future__ import annotations

from ..keys import Key
from ..terminal import Terminal


class Widget:
    """A single interactive prompt. Subclasses implement ``render_lines``
    (returning the current block of text lines to draw) and ``handle_key``
    (mutating state in response to input). The base class takes care of
    tracking how many lines were previously drawn so redraws only touch
    the widget's own block of the screen.
    """

    def __init__(self):
        self.done = False
        self.cancelled = False
        self.result = None
        self._last_lines = 0

    # -- to override ------------------------------------------------
    def render_lines(self) -> list[str]:
        raise NotImplementedError

    def handle_key(self, key: Key) -> None:
        raise NotImplementedError

    # -- shared helpers ------------------------------------------------
    def render(self, term: Terminal) -> None:
        lines = self.render_lines() or [""]
        self._last_lines = term.redraw(self._last_lines, lines)

    def submit(self, result=None) -> None:
        self.result = result
        self.done = True

    def cancel(self) -> None:
        self.cancelled = True
        self.done = True
