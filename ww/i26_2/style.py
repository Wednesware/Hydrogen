"""ANSI text styling: colors (16/256/truecolor), attributes, and themes.

The 256+ CSS colour table and the reset/attribute escape codes are not
reimplemented here: they're pulled straight from ``ww.mg26_11.color.Color``
so the two libraries never drift out of sync. ``Style`` adds on top of that
the 16-colour ANSI palette (``NAMED_COLORS``) and the SGR-combining/``Theme``
machinery ``ww`` doesn't have.
"""
from __future__ import annotations

from ww.mg26_11.color import Color  #COMPAT

NAMED_COLORS = {
    "black": 0, "red": 1, "green": 2, "yellow": 3,
    "blue": 4, "magenta": 5, "cyan": 6, "white": 7,
    "bright_black": 8, "gray": 8, "grey": 8,
    "bright_red": 9, "bright_green": 10, "bright_yellow": 11,
    "bright_blue": 12, "bright_magenta": 13, "bright_cyan": 14, "bright_white": 15,
}

# CSS colour names ("cornflower_blue", "rebecca_purple", ...) straight from
# ww's table, so `Style(fg="cornflower_blue")` works alongside the 16-colour
# names above without duplicating a single (r, g, b) triple.
CSS_COLORS = Color._CSS_COLORS

RESET = Color.reset


class Style:
    """An immutable-ish style descriptor. Colors may be a named string
    (see :data:`NAMED_COLORS`), an int 0-255 (256-color palette index), or
    an ``(r, g, b)`` tuple (truecolor).
    """

    def __init__(self, fg=None, bg=None, bold=False, dim=False, italic=False,
                 underline=False, reverse=False, strike=False):
        self.fg = fg
        self.bg = bg
        self.bold = bold
        self.dim = dim
        self.italic = italic
        self.underline = underline
        self.reverse = reverse
        self.strike = strike

    def _color_code(self, color, ground: str) -> str | None:
        base = 38 if ground == "fg" else 48
        if isinstance(color, tuple) and len(color) == 3:
            r, g, b = color
            return f"{base};2;{r};{g};{b}"
        if isinstance(color, str):
            idx = NAMED_COLORS.get(color)
            if idx is not None:
                return f"{base};5;{idx}"
            rgb = CSS_COLORS.get(color)
            if rgb is not None:
                r, g, b = rgb
                return f"{base};2;{r};{g};{b}"
            return None
        if isinstance(color, int):
            return f"{base};5;{color}"
        return None

    def ansi(self) -> str:
        parts = []
        if self.bold:
            parts.append("1")
        if self.dim:
            parts.append("2")
        if self.italic:
            parts.append("3")
        if self.underline:
            parts.append("4")
        if self.reverse:
            parts.append("7")
        if self.strike:
            parts.append("9")
        if self.fg is not None:
            c = self._color_code(self.fg, "fg")
            if c:
                parts.append(c)
        if self.bg is not None:
            c = self._color_code(self.bg, "bg")
            if c:
                parts.append(c)
        if not parts:
            return ""
        return "\x1b[" + ";".join(parts) + "m"

    def wrap(self, text: str) -> str:
        code = self.ansi()
        return f"{code}{text}{RESET}" if code else text

    def merge(self, other: "Style | None") -> "Style":
        """Return a new style with ``other``'s explicit attributes layered
        on top of this one (used to combine e.g. a cursor style with a
        syntax-highlight style)."""
        if other is None:
            return self
        return Style(
            fg=other.fg if other.fg is not None else self.fg,
            bg=other.bg if other.bg is not None else self.bg,
            bold=other.bold or self.bold,
            dim=other.dim or self.dim,
            italic=other.italic or self.italic,
            underline=other.underline or self.underline,
            reverse=other.reverse or self.reverse,
            strike=other.strike or self.strike,
        )


class Theme:
    """A named bundle of styles widgets pull from, so an app can restyle
    everything in one place."""

    def __init__(self, **styles: Style):
        self.styles = {
            "text": Style(),
            "prompt": Style(fg="cyan", bold=True),
            "placeholder": Style(dim=True),
            "cursor": Style(reverse=True),
            "error": Style(fg="red"),
            "hint": Style(dim=True, italic=True),
            "selected": Style(fg="black", bg="cyan", bold=True),
            "unselected": Style(),
            "pointer": Style(fg="cyan", bold=True),
            "checked": Style(fg="green", bold=True),
            "title": Style(bold=True, underline=True),
            "suggestion": Style(dim=True),
            "suggestion_selected": Style(fg="black", bg="yellow"),
            "line_number": Style(dim=True),
        }
        self.styles.update(styles)

    def __getitem__(self, key: str) -> Style:
        return self.styles[key]

    def get(self, key: str, default: Style | None = None) -> Style:
        return self.styles.get(key, default or Style())


DEFAULT_THEME = Theme()
