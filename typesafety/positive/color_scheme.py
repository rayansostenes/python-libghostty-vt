# Positive typesafety pins for the color scheme domain.
#
# Never executed: every line is a compile-time assertion. `assert_type` pins the
# encoder's return type; the enum members are pinned by annotated bindings (a
# member access infers the singleton literal, not the enum). This file must be
# diagnostic-free under every checker.
from __future__ import annotations

from typing import assert_type

import ghostty_vt
from ghostty_vt import ColorScheme
from ghostty_vt.color_scheme import encode

# Encoding a color scheme report yields pty bytes.
assert_type(encode(ColorScheme.DARK), bytes)

# Every scheme member is assignable to the enum type; dropping either turns the
# suite red.
_light: ColorScheme = ColorScheme.LIGHT
_dark: ColorScheme = ColorScheme.DARK

# The top-level re-export is the same enum type.
_top: ColorScheme = ghostty_vt.ColorScheme.DARK
