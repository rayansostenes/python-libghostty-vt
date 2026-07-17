# Expect-error typesafety pins for the mouse domain.
#
# Never executed. Every statement below is a deliberate misuse of the public API.
# Each line tagged `# expect-error` MUST draw at least one diagnostic from every
# checker; the harness fails if any tagged line stops erroring or if an untagged
# line errors.
from __future__ import annotations

from ghostty_vt import (
    MouseAction,
    MouseButton,
    MouseEncoder,
    MouseEvent,
    MouseFormat,
    MouseTracking,
    SurfacePosition,
)
from ghostty_vt.mouse import Geometry

MouseEvent()  # expect-error: missing action and position
MouseEvent(MouseAction.PRESS)  # expect-error: missing position
MouseEvent(MouseAction.PRESS, SurfacePosition(0.0, 0.0)).nope  # expect-error: no attr
MouseButton.DOES_NOT_EXIST  # expect-error: no such enum member

geometry = Geometry(screen_width=800, screen_height=480, cell_width=10, cell_height=20)
Geometry()  # expect-error: missing required measurements

# The encoder's configuration is keyword-only and typed.
MouseEncoder(MouseTracking.NORMAL, MouseFormat.SGR, geometry)  # expect-error: kw-only
MouseEncoder(tracking=MouseTracking.NORMAL, format=42, geometry=geometry)  # expect-error: format must be a MouseFormat

encoder = MouseEncoder(
    tracking=MouseTracking.NORMAL, format=MouseFormat.SGR, geometry=geometry
)
press = MouseEvent(MouseAction.PRESS, SurfacePosition(0.0, 0.0))
encoder.encode("not an event")  # expect-error: encode wants a MouseEvent
_wrong: str = encoder.encode(press)  # expect-error: encode returns bytes, not str
