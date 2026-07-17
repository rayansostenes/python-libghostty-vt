# Positive typesafety pins for the mouse domain.
#
# Never executed: every line is a compile-time assertion. `assert_type` pins the
# type a checker infers for each public expression, so any drift in the mouse
# API's public types turns the suite red. This file must be diagnostic-free under
# every checker.
from __future__ import annotations

from typing import assert_type

from ghostty_vt import (
    Mods,
    MouseAction,
    MouseButton,
    MouseEncoder,
    MouseEvent,
    MouseFormat,
    MouseTracking,
    SurfacePosition,
)
from ghostty_vt.mouse import Geometry

# The event is a value type carrying an action, position, optional button, and
# modifiers.
event = MouseEvent(MouseAction.PRESS, SurfacePosition(105.0, 45.0), MouseButton.LEFT)
assert_type(event, MouseEvent)
assert_type(event.action, MouseAction)
assert_type(event.position, SurfacePosition)
assert_type(event.button, MouseButton | None)
assert_type(event.mods, Mods)

# Geometry is a value type of integer pixel measurements.
geometry = Geometry(screen_width=800, screen_height=480, cell_width=10, cell_height=20)
assert_type(geometry, Geometry)
assert_type(geometry.cell_width, int)
assert_type(geometry.padding_left, int)

# The encoder is a context manager whose encode returns raw bytes.
encoder = MouseEncoder(
    tracking=MouseTracking.NORMAL, format=MouseFormat.SGR, geometry=geometry
)
assert_type(encoder, MouseEncoder)
assert_type(encoder.encode(event), bytes)
assert_type(encoder.reset(), None)
assert_type(encoder.close(), None)
assert_type(encoder.any_button_pressed, bool)
encoder.any_button_pressed = True
with encoder as entered:
    assert_type(entered, MouseEncoder)

# Every enum member is assignable to its enum type; dropping any one turns the
# suite red. Assignment (not assert_type) is deliberate: a checker narrows a bare
# member to its Literal type, so the enum-type annotation is what pins existence.
_actions: list[MouseAction] = [
    MouseAction.PRESS,
    MouseAction.RELEASE,
    MouseAction.MOTION,
]
_buttons: list[MouseButton] = [
    MouseButton.UNKNOWN,
    MouseButton.LEFT,
    MouseButton.RIGHT,
    MouseButton.MIDDLE,
    MouseButton.FOUR,
    MouseButton.FIVE,
    MouseButton.SIX,
    MouseButton.SEVEN,
    MouseButton.EIGHT,
    MouseButton.NINE,
    MouseButton.TEN,
    MouseButton.ELEVEN,
]
_trackings: list[MouseTracking] = [
    MouseTracking.NONE,
    MouseTracking.X10,
    MouseTracking.NORMAL,
    MouseTracking.BUTTON,
    MouseTracking.ANY,
]
_formats: list[MouseFormat] = [
    MouseFormat.X10,
    MouseFormat.UTF8,
    MouseFormat.SGR,
    MouseFormat.URXVT,
    MouseFormat.SGR_PIXELS,
]
_mods: Mods = Mods.CTRL | Mods.SHIFT
