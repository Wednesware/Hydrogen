"""Runs a widget's interaction loop against a real terminal."""
from __future__ import annotations

from typing import Optional

from ww.mg26_11.logging import error as ww_error  #COMPAT

from .keymap import Keymap
from .keys import read_key
from .terminal import Terminal
from .widgets.base import Widget


def run(
    widget: Widget,
    global_keymap: Optional[Keymap] = None,
    alt_screen: bool = False,
    term: Optional[Terminal] = None,
):
    """Drive ``widget`` interactively until it submits or is cancelled.

    ``global_keymap`` lets an application register hotkeys (e.g. F1 for
    help, Ctrl+S to save) that are checked before the widget's own key
    handling, regardless of which widget is currently focused.

    Returns the widget's result, or ``None`` if cancelled.
    """
    term = term or Terminal()
    caught: Exception | None = None
    with term.raw_mode():
        with term.hidden_cursor():
            stack = []
            if alt_screen:
                cm = term.alt_screen()
                cm.__enter__()
                stack.append(cm)
            try:
                widget.render(term)
                while not widget.done:
                    key = read_key(term.fd)
                    if key is None:
                        continue
                    if key.name == "CTRL_C" and not (global_keymap and "CTRL_C" in global_keymap._bindings):
                        widget.cancel()
                        break
                    handled = False
                    if global_keymap is not None:
                        handled = global_keymap.dispatch(key)
                    if not handled:
                        widget.handle_key(key)
                    widget.render(term)
            except Exception as exc:
                caught = exc
            finally:
                for cm in reversed(stack):
                    cm.__exit__(None, None, None)
                term.newline()
    if caught is not None:
        ww_error.from_exception(caught).print()
        raise caught
    return None if widget.cancelled else widget.result
