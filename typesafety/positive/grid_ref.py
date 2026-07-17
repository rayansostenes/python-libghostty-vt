# Positive typesafety pins for the grid-ref domain.
#
# Never executed: every line is a compile-time assertion. `assert_type` pins the
# type a checker infers for each public expression, so any drift in the grid-ref
# API's public types turns the suite red. This file must be diagnostic-free under
# every checker.
from __future__ import annotations

from typing import assert_type

from ghostty_vt import (
    Cell,
    CellWidth,
    GridRef,
    Point,
    PointTag,
    SemanticContent,
    Style,
    Terminal,
    TrackedGridRef,
)

term = Terminal(10, 2)
point = Point(PointTag.ACTIVE, 0, 0)

# The terminal resolves points to references.
ref = term.grid_ref(point)
assert_type(ref, GridRef)
assert_type(term.track_grid_ref(point), TrackedGridRef)

# A grid reference reads a cell snapshot and converts back to a point.
cell = ref.cell()
assert_type(cell, Cell)
assert_type(ref.point(PointTag.VIEWPORT), Point | None)

# The cell snapshot carries text, style, layout, and hyperlink data.
assert_type(cell.text, str)
assert_type(cell.style, Style)
assert_type(cell.width, CellWidth)
assert_type(cell.protected, bool)
assert_type(cell.semantic, SemanticContent)
assert_type(cell.hyperlink, str | None)

# A tracked reference is queried, snapshotted, and repointed.
tracked = term.track_grid_ref(point)
assert_type(tracked.has_value, bool)
assert_type(tracked.point(PointTag.SCREEN), Point | None)
assert_type(tracked.snapshot(), GridRef | None)
assert_type(tracked.cell(), Cell | None)
assert_type(tracked.move_to(point), None)
assert_type(tracked.close(), None)
with term.track_grid_ref(point) as managed:
    assert_type(managed, TrackedGridRef)

# Every CellWidth and SemanticContent member is assignable to its enum type; the
# annotated binding is the pin (a member access infers the singleton literal).
_narrow: CellWidth = CellWidth.NARROW
_wide: CellWidth = CellWidth.WIDE
_spacer_tail: CellWidth = CellWidth.SPACER_TAIL
_spacer_head: CellWidth = CellWidth.SPACER_HEAD
_output: SemanticContent = SemanticContent.OUTPUT
_input: SemanticContent = SemanticContent.INPUT
_prompt: SemanticContent = SemanticContent.PROMPT
