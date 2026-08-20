"""Keybind trigger system: map key tokens (or chord sequences) to callbacks.

Used both for widget-local bindings and for global hotkeys that fire
regardless of which widget currently has focus (see :func:`iodine.runner.run`).
"""
from __future__ import annotations

from .keys import Key


class Keymap:
    """A flat map of key token -> callback, plus support for multi-key
    chord sequences (e.g. ``"g g"`` vim-style double-tap)."""

    def __init__(self):
        self._bindings: dict[str, callable] = {}
        self._chords: dict[tuple, callable] = {}
        self._chord_buffer: list[str] = []

    def bind(self, key: str, callback):
        """Bind a single key token, e.g. ``"F1"``, ``"CTRL_S"``, or a
        literal character like ``"q"``."""
        self._bindings[key] = callback
        return callback

    def bind_chord(self, *keys: str, callback):
        """Bind a sequence of key tokens pressed in order, e.g.
        ``bind_chord("g", "g", callback=go_to_top)``."""
        self._chords[tuple(keys)] = callback
        return callback

    def unbind(self, key: str):
        self._bindings.pop(key, None)

    def on(self, key: str):
        """Decorator form of :meth:`bind`."""
        def deco(fn):
            self.bind(key, fn)
            return fn
        return deco

    def dispatch(self, key: Key) -> bool:
        """Try to handle ``key``. Returns True if a callback fired."""
        token = key.token()

        if self._chords:
            self._chord_buffer.append(token)
            # trim buffer to longest chord length
            max_len = max((len(c) for c in self._chords), default=0)
            if len(self._chord_buffer) > max_len:
                self._chord_buffer = self._chord_buffer[-max_len:]
            for chord, cb in self._chords.items():
                n = len(chord)
                if tuple(self._chord_buffer[-n:]) == chord:
                    self._chord_buffer.clear()
                    cb(key)
                    return True

        cb = self._bindings.get(token)
        if cb is None and key.name != "CHAR":
            cb = self._bindings.get(key.name)
        if cb:
            cb(key)
            return True
        return False
