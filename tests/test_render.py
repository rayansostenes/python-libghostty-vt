"""Behavioral tests for the render domain, through the public API.

Every assertion feeds bytes into a real terminal, updates a render state, and
reads back the per-cell and per-frame data a renderer or differ would draw from.
The raw layer and the C boundary are never touched directly.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from ghostty_vt import Dirty, RenderState, Rgb, Terminal, UseAfterCloseError


def test_render_state_reports_viewport_dimensions() -> None:
    with Terminal(12, 4) as term, term.render_state() as state:
        state.update()
        assert state.cols == 12
        assert state.rows == 4


def test_render_state_is_dirty_after_an_update() -> None:
    with Terminal(6, 2) as term, term.render_state() as state:
        term.feed(b"hi")
        state.update()
        assert state.dirty is Dirty.FULL


def test_render_grid_has_a_row_per_viewport_line() -> None:
    with Terminal(6, 3) as term, term.render_state() as state:
        state.update()
        grid = state.grid()
        assert len(grid) == 3
        assert all(len(row.cells) == 6 for row in grid)


def test_render_cell_text_reflects_fed_input() -> None:
    with Terminal(6, 2) as term, term.render_state() as state:
        term.feed(b"Hi")
        state.update()
        cells = state.grid()[0].cells
        assert cells[0].text == "H"
        assert cells[1].text == "i"


def test_render_cell_empty_where_nothing_was_fed() -> None:
    with Terminal(6, 2) as term, term.render_state() as state:
        term.feed(b"X")
        state.update()
        assert state.grid()[0].cells[5].text == ""


def test_render_cell_foreground_resolves_sgr_palette() -> None:
    with Terminal(6, 2) as term, term.render_state() as state:
        term.feed(b"\x1b[31mR\x1b[0m")
        state.update()
        cell = state.grid()[0].cells[0]
        # Palette index 1 flattened to the active palette's red.
        assert cell.foreground == Rgb(204, 102, 102)
        assert cell.has_styling is True


def test_render_cell_background_resolves_sgr_rgb() -> None:
    with Terminal(6, 2) as term, term.render_state() as state:
        term.feed(b"\x1b[48;2;1;2;3mB\x1b[0m")
        state.update()
        assert state.grid()[0].cells[0].background == Rgb(1, 2, 3)


def test_render_cell_without_explicit_colors_is_none() -> None:
    with Terminal(6, 2) as term, term.render_state() as state:
        term.feed(b"a")
        state.update()
        cell = state.grid()[0].cells[0]
        assert cell.foreground is None
        assert cell.background is None
        assert cell.has_styling is False


def test_render_cell_style_reflects_decorations() -> None:
    with Terminal(6, 2) as term, term.render_state() as state:
        term.feed(b"\x1b[1mB\x1b[0m")
        state.update()
        assert state.grid()[0].cells[0].style.bold is True


def test_render_cell_is_unselected_without_a_selection() -> None:
    with Terminal(6, 2) as term, term.render_state() as state:
        term.feed(b"a")
        state.update()
        assert state.grid()[0].cells[0].selected is False


def test_render_default_colors_are_reported() -> None:
    with Terminal(6, 2) as term, term.render_state() as state:
        state.update()
        colors = state.colors
        assert colors.background == Rgb(0, 0, 0)
        assert colors.foreground == Rgb(255, 255, 255)
        assert len(colors.palette) == 256


def test_render_cursor_color_is_none_by_default() -> None:
    with Terminal(6, 2) as term, term.render_state() as state:
        state.update()
        assert state.colors.cursor is None


def test_render_cursor_color_reflects_osc_12() -> None:
    with Terminal(6, 2) as term, term.render_state() as state:
        term.feed(b"\x1b]12;rgb:00/ff/00\x07")
        state.update()
        assert state.colors.cursor == Rgb(0, 255, 0)


def test_render_state_can_be_updated_repeatedly() -> None:
    with Terminal(6, 2) as term, term.render_state() as state:
        term.feed(b"one")
        state.update()
        assert state.grid()[0].cells[0].text == "o"
        term.feed(b"\r\ntwo")
        state.update()
        assert state.grid()[1].cells[0].text == "t"


def test_render_state_close_is_idempotent() -> None:
    with Terminal(6, 2) as term:
        state = term.render_state()
        state.close()
        state.close()


_CLOSED_RENDER_OPERATIONS: list[Callable[[RenderState], object]] = [
    lambda s: s.update(),
    lambda s: s.cols,
    lambda s: s.rows,
    lambda s: s.dirty,
    lambda s: s.colors,
    lambda s: s.grid(),
]


@pytest.mark.parametrize("operation", _CLOSED_RENDER_OPERATIONS)
def test_operations_on_closed_render_state_raise(
    operation: Callable[[RenderState], object],
) -> None:
    term = Terminal(6, 2)
    state = term.render_state()
    state.close()
    with pytest.raises(UseAfterCloseError):
        operation(state)


def test_render_update_after_terminal_close_raises() -> None:
    term = Terminal(6, 2)
    state = term.render_state()
    term.close()
    with pytest.raises(UseAfterCloseError):
        state.update()
