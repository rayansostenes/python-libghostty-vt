# Expect-error typesafety pins for the selection domain.
#
# Never executed. Every statement below is a deliberate misuse of the public API.
# Each line tagged `# expect-error` MUST draw at least one diagnostic from every
# checker; the harness fails if any tagged line stops erroring or if an untagged
# line errors.
from __future__ import annotations

from ghostty_vt import Point, PointTag, Selection, SelectionAdjust, SelectionOrder, Terminal

term = Terminal(10, 3)
where = Point(PointTag.ACTIVE, 0, 0)
selection = Selection.point_to_point(term, where, where)

Selection.point_to_point(term, where)  # expect-error: missing the end point
Selection.word(term, "here")  # expect-error: point must be a Point, not str
Selection.all()  # expect-error: missing the terminal
Selection.point_to_point(term, where, where, True)  # expect-error: rectangle is keyword-only
selection.adjust("left")  # expect-error: adjustment must be a SelectionAdjust
selection.contains("here")  # expect-error: point must be a Point, not str
selection.does_not_exist  # expect-error: no such attribute
SelectionOrder.DOES_NOT_EXIST  # expect-error: no such enum member
SelectionAdjust.DOES_NOT_EXIST  # expect-error: no such enum member
_wrong: int = selection.text()  # expect-error: str is not an int
