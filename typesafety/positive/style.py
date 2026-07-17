# Positive typesafety pins for the style domain.
#
# Never executed: every line is a compile-time assertion. `assert_type` pins the
# type a checker infers for each public expression, so any drift in the style
# API's public types turns the suite red. This file must be diagnostic-free under
# every checker.
from __future__ import annotations

from typing import assert_type

from ghostty_vt import Rgb, Style, StyleColor, Underline

# A style is an immutable snapshot with colors and decoration flags.
style = Style(
    fg=Rgb(255, 0, 0),
    bg=1,
    underline_color=None,
    bold=True,
    italic=False,
    faint=False,
    blink=False,
    inverse=False,
    invisible=False,
    strikethrough=False,
    overline=False,
    underline=Underline.SINGLE,
)
assert_type(style, Style)

# A style color is the None | palette-index | Rgb union.
assert_type(style.fg, StyleColor)
assert_type(style.bg, StyleColor)
assert_type(style.underline_color, StyleColor)
assert_type(style.bold, bool)
assert_type(style.italic, bool)
assert_type(style.underline, Underline)

# The union alias accepts each of its members.
_none: StyleColor = None
_palette: StyleColor = 1
_rgb: StyleColor = Rgb(0, 0, 0)

# Every underline member is assignable to the enum type; dropping any one turns
# the suite red (a direct assert_type on a member infers the singleton literal).
_u_none: Underline = Underline.NONE
_u_single: Underline = Underline.SINGLE
_u_double: Underline = Underline.DOUBLE
_u_curly: Underline = Underline.CURLY
_u_dotted: Underline = Underline.DOTTED
_u_dashed: Underline = Underline.DASHED
