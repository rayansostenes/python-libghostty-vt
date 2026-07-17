# Positive typesafety pins for the terminal domain.
#
# Never executed: every line is a compile-time assertion. `assert_type` pins the
# type a checker infers for each public expression, so any drift in the terminal
# API's public types turns the suite red. This file must be diagnostic-free under
# every checker.
from __future__ import annotations

from typing import assert_type

from ghostty_vt import (
    Cursor,
    GridRef,
    Mode,
    Point,
    PointTag,
    RenderState,
    Screen,
    Terminal,
    TrackedGridRef,
)

# Construction takes cell dimensions and yields the terminal type; scrollback is
# an optional keyword-only integer.
term = Terminal(80, 24)
assert_type(term, Terminal)
assert_type(Terminal(80, 24, scrollback=1000), Terminal)

# Dimensions read back as integers.
assert_type(term.cols, int)
assert_type(term.rows, int)

# Feeding takes bytes and returns nothing; reading text returns str.
assert_type(term.feed(b"hello"), None)
assert_type(term.visible_text(), str)

# Resizing takes dimensions and returns nothing.
assert_type(term.resize(100, 40), None)

# Screen-state queries have precise types.
assert_type(term.cursor, Cursor)
assert_type(term.cursor.x, int)
assert_type(term.cursor.visible, bool)
assert_type(term.active_screen, Screen)
assert_type(term.mouse_tracking, bool)
assert_type(term.total_rows, int)
assert_type(term.scrollback_rows, int)
assert_type(term.viewport_active, bool)

# Modes are read and written through the Mode enum.
assert_type(term.get_mode(Mode.CURSOR_VISIBLE), bool)
assert_type(term.set_mode(Mode.CURSOR_VISIBLE, True), None)

# Viewport scrolling returns nothing.
assert_type(term.scroll_to_top(), None)
assert_type(term.scroll_to_bottom(), None)
assert_type(term.scroll_by(-1), None)
assert_type(term.scroll_to_row(0), None)

# The terminal is the factory for the screen-inspection domains.
_point = Point(PointTag.ACTIVE, 0, 0)
assert_type(term.grid_ref(_point), GridRef)
assert_type(term.track_grid_ref(_point), TrackedGridRef)
assert_type(term.render_state(), RenderState)
assert_type(term.format(), str)

# Lifecycle: explicit close, and use as a context manager binding the terminal.
assert_type(term.close(), None)
with Terminal(10, 3) as managed:
    assert_type(managed, Terminal)
