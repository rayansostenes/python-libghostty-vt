# Positive typesafety pins for the shared types domain.
#
# Never executed: every line is a compile-time assertion. `assert_type` pins the
# type a checker infers for each public expression; the enum members are pinned by
# annotated bindings (a member access infers the singleton literal, not the enum).
# This file must be diagnostic-free under every checker.
from __future__ import annotations

from typing import assert_type

from ghostty_vt import Mods, Point, PointTag, SurfacePosition

# Modifiers are a flag enum: members and their combinations share the enum type.
_none: Mods = Mods.NONE
_shift: Mods = Mods.SHIFT
_ctrl: Mods = Mods.CTRL
_alt: Mods = Mods.ALT
_super: Mods = Mods.SUPER
_caps: Mods = Mods.CAPS_LOCK
_num: Mods = Mods.NUM_LOCK
_shift_side: Mods = Mods.SHIFT_SIDE
_ctrl_side: Mods = Mods.CTRL_SIDE
_alt_side: Mods = Mods.ALT_SIDE
_super_side: Mods = Mods.SUPER_SIDE
_combined: Mods = Mods.CTRL | Mods.SHIFT

# A point carries its tag and integer coordinates.
point = Point(PointTag.ACTIVE, 3, 7)
assert_type(point, Point)
assert_type(point.tag, PointTag)
assert_type(point.x, int)
assert_type(point.y, int)

# Every PointTag member is assignable to the enum type; dropping any one turns
# the suite red.
_active: PointTag = PointTag.ACTIVE
_viewport: PointTag = PointTag.VIEWPORT
_screen: PointTag = PointTag.SCREEN
_history: PointTag = PointTag.HISTORY

# A surface position carries float pixel coordinates.
position = SurfacePosition(12.5, 40.0)
assert_type(position, SurfacePosition)
assert_type(position.x, float)
assert_type(position.y, float)
