# Positive typesafety pins for the color domain.
#
# Never executed: every line is a compile-time assertion. `assert_type` pins the
# type a checker infers for each public expression, so any drift in the color
# API's public types turns the suite red. This file must be diagnostic-free under
# every checker.
from __future__ import annotations

from typing import assert_type

from ghostty_vt import Rgb
from ghostty_vt.color import (
    X11Color,
    default_palette,
    generate_palette,
    parse_palette_entry,
    x11_names,
)

# The value type exposes integer channels and derived helpers.
color = Rgb(255, 136, 0)
assert_type(color, Rgb)
assert_type(color.r, int)
assert_type(color.g, int)
assert_type(color.b, int)
assert_type(color.hex, str)
assert_type(color.luminance, float)
assert_type(color.perceived_luminance, float)
assert_type(color.contrast(color), float)

# The parsing factories return the value type.
assert_type(Rgb.parse("#ff8800"), Rgb)
assert_type(Rgb.from_x11("red"), Rgb)

# Palette helpers return typed tuples; parse_palette_entry pairs an index with a
# color.
assert_type(parse_palette_entry("1=#ff0000"), tuple[int, Rgb])
assert_type(default_palette(), tuple[Rgb, ...])
assert_type(generate_palette(color, color), tuple[Rgb, ...])
assert_type(
    generate_palette(color, color, base=[color], skip=[1], harmonious=True),
    tuple[Rgb, ...],
)

# The X11 table yields named entries.
entry = x11_names()[0]
assert_type(entry, X11Color)
assert_type(entry.name, str)
assert_type(entry.color, Rgb)
