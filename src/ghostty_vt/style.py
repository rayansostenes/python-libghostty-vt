"""Style domain: the visual attributes of a terminal cell.

This is the idiomatic layer over the upstream ``style`` domain. A :class:`Style`
is the immutable snapshot of a cell's foreground, background, and underline
colors together with its text-decoration flags. Styles are read out of the
screen through the grid-ref and render domains; a :class:`Style` is never
constructed against the native library directly.

A style color is a :data:`StyleColor`: ``None`` when the attribute is unset (the
caller falls back to its own default), an ``int`` palette index (0-255), or an
:class:`~ghostty_vt.Rgb` for a direct color.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

from ghostty_vt import _raw
from ghostty_vt.color import Rgb

__all__ = ["Style", "StyleColor", "Underline"]

_lib = _raw.lib

type StyleColor = Rgb | int | None
"""A style color: ``None`` (unset), an ``int`` palette index, or an :class:`Rgb`."""


class Underline(enum.Enum):
    """The underline style of a cell, matching the SGR underline sub-parameters."""

    NONE = _lib.GHOSTTY_SGR_UNDERLINE_NONE
    """No underline."""

    SINGLE = _lib.GHOSTTY_SGR_UNDERLINE_SINGLE
    """A single underline (SGR 4)."""

    DOUBLE = _lib.GHOSTTY_SGR_UNDERLINE_DOUBLE
    """A double underline (SGR 4:2)."""

    CURLY = _lib.GHOSTTY_SGR_UNDERLINE_CURLY
    """A curly underline (SGR 4:3)."""

    DOTTED = _lib.GHOSTTY_SGR_UNDERLINE_DOTTED
    """A dotted underline (SGR 4:4)."""

    DASHED = _lib.GHOSTTY_SGR_UNDERLINE_DASHED
    """A dashed underline (SGR 4:5)."""


@dataclass(frozen=True, slots=True)
class Style:
    """The complete visual style of a terminal cell.

    Attributes:
        fg: The foreground (text) color.
        bg: The background color.
        underline_color: The underline color; falls back to ``fg`` when unset.
        bold: Whether the text is bold.
        italic: Whether the text is italic.
        faint: Whether the text is faint (dim).
        blink: Whether the text blinks.
        inverse: Whether foreground and background are swapped.
        invisible: Whether the text is hidden.
        strikethrough: Whether the text is struck through.
        overline: Whether the text is overlined.
        underline: The underline style.
    """

    fg: StyleColor
    bg: StyleColor
    underline_color: StyleColor
    bold: bool
    italic: bool
    faint: bool
    blink: bool
    inverse: bool
    invisible: bool
    strikethrough: bool
    overline: bool
    underline: Underline
