# Expect-error typesafety pins for the grid-ref domain.
#
# Never executed. Every statement below is a deliberate misuse of the public API.
# Each line tagged `# expect-error` MUST draw at least one diagnostic from every
# checker; the harness fails if any tagged line stops erroring or if an untagged
# line errors.
from __future__ import annotations

from ghostty_vt import Point, PointTag, Terminal

term = Terminal(10, 2)
point = Point(PointTag.ACTIVE, 0, 0)

term.grid_ref()  # expect-error: missing point
term.grid_ref((0, 0))  # expect-error: point must be a Point
term.grid_ref(point).point("viewport")  # expect-error: tag must be a PointTag
term.grid_ref(point).does_not_exist  # expect-error: no such attribute
term.grid_ref(point).cell().text = "x"  # expect-error: cell is frozen
term.track_grid_ref(point).move_to((0, 0))  # expect-error: point must be a Point
_wrong: str = term.grid_ref(point).cell()  # expect-error: Cell is not a str
