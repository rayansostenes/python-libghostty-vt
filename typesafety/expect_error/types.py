# Expect-error typesafety pins for the shared types domain.
#
# Never executed. Every statement below is a deliberate misuse of the public API.
# Each line tagged `# expect-error` MUST draw at least one diagnostic from every
# checker; the harness fails if any tagged line stops erroring or if an untagged
# line errors.
from __future__ import annotations

from ghostty_vt import Mods, Point, PointTag, SurfacePosition

Point()  # expect-error: missing tag, x, and y
Point(PointTag.ACTIVE, 0, 0).does_not_exist  # expect-error: no such attribute
PointTag.DOES_NOT_EXIST  # expect-error: no such enum member
_wrong: int = Point(PointTag.ACTIVE, 0, 0)  # expect-error: Point is not an int
SurfacePosition(0.0)  # expect-error: missing y
Mods.DOES_NOT_EXIST  # expect-error: no such enum member
_bad_mods: int = Mods.SHIFT  # expect-error: Mods is not an int
