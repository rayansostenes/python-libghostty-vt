# Positive typesafety pins for the render domain.
#
# Never executed: every line is a compile-time assertion. `assert_type` pins the
# type a checker infers for each public expression, so any drift in the render
# API's public types turns the suite red. This file must be diagnostic-free under
# every checker.
from __future__ import annotations

from typing import assert_type

from ghostty_vt import (
    Dirty,
    RenderCell,
    RenderColors,
    RenderRow,
    RenderState,
    Rgb,
    Style,
    Terminal,
)

term = Terminal(10, 2)

# A render state is created from a terminal and refreshed with update().
state = term.render_state()
assert_type(state, RenderState)
assert_type(state.update(), None)

# Frame-level reads.
assert_type(state.cols, int)
assert_type(state.rows, int)
assert_type(state.dirty, Dirty)
assert_type(state.close(), None)
with term.render_state() as managed:
    assert_type(managed, RenderState)

# Colors flatten to concrete Rgb, with an optional cursor color.
colors = state.colors
assert_type(colors, RenderColors)
assert_type(colors.background, Rgb)
assert_type(colors.foreground, Rgb)
assert_type(colors.cursor, Rgb | None)
assert_type(colors.palette, tuple[Rgb, ...])

# The grid materializes rows and cells.
grid = state.grid()
assert_type(grid, tuple[RenderRow, ...])
row = grid[0]
assert_type(row, RenderRow)
assert_type(row.dirty, bool)
assert_type(row.cells, tuple[RenderCell, ...])

cell = row.cells[0]
assert_type(cell, RenderCell)
assert_type(cell.text, str)
assert_type(cell.style, Style)
assert_type(cell.foreground, Rgb | None)
assert_type(cell.background, Rgb | None)
assert_type(cell.selected, bool)
assert_type(cell.has_styling, bool)

# Every Dirty member is assignable to the enum type; the annotated binding is the
# pin (a member access infers the singleton literal).
_clean: Dirty = Dirty.FALSE
_partial: Dirty = Dirty.PARTIAL
_full: Dirty = Dirty.FULL
