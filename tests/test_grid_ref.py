"""Behavioral tests for the grid-ref domain, through the public API.

Every assertion feeds bytes into a real terminal and inspects a resolved cell or
follows a tracked reference across mutations, exactly as a recorder or differ
would. The raw layer and the C boundary are never touched directly.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from ghostty_vt import (
    Cell,
    CellWidth,
    GhosttyVtError,
    InvalidValueError,
    Point,
    PointTag,
    Rgb,
    SemanticContent,
    Terminal,
    TrackedGridRef,
    Underline,
    UseAfterCloseError,
)


def _cell_at(term: Terminal, x: int, y: int, tag: PointTag = PointTag.ACTIVE) -> Cell:
    return term.grid_ref(Point(tag, x, y)).cell()


def test_cell_reports_plain_text() -> None:
    with Terminal(10, 2) as term:
        term.feed(b"Hi")
        assert _cell_at(term, 0, 0).text == "H"
        assert _cell_at(term, 1, 0).text == "i"


def test_empty_cell_has_no_text() -> None:
    with Terminal(10, 2) as term:
        term.feed(b"X")
        assert _cell_at(term, 5, 0).text == ""


def test_cell_style_reflects_sgr_foreground() -> None:
    with Terminal(10, 2) as term:
        term.feed(b"\x1b[31mR\x1b[0m")
        # SGR 31 is palette index 1.
        assert _cell_at(term, 0, 0).style.fg == 1


def test_cell_style_reflects_sgr_rgb_foreground() -> None:
    with Terminal(10, 2) as term:
        term.feed(b"\x1b[38;2;10;20;30mR\x1b[0m")
        assert _cell_at(term, 0, 0).style.fg == Rgb(10, 20, 30)


def test_cell_style_reflects_sgr_background() -> None:
    with Terminal(10, 2) as term:
        term.feed(b"\x1b[41mB\x1b[0m")
        assert _cell_at(term, 0, 0).style.bg == 1


def test_default_cell_style_has_no_colors() -> None:
    with Terminal(10, 2) as term:
        term.feed(b"x")
        style = _cell_at(term, 0, 0).style
        assert style.fg is None
        assert style.bg is None


def test_cell_style_reflects_bold_and_underline() -> None:
    with Terminal(10, 2) as term:
        term.feed(b"\x1b[1;4mX\x1b[0m")
        style = _cell_at(term, 0, 0).style
        assert style.bold is True
        assert style.underline is Underline.SINGLE


def test_cell_style_reflects_the_full_decoration_set() -> None:
    with Terminal(10, 2) as term:
        term.feed(b"\x1b[3;5;7;8;9;53mX\x1b[0m")
        style = _cell_at(term, 0, 0).style
        assert style.italic is True
        assert style.blink is True
        assert style.inverse is True
        assert style.invisible is True
        assert style.strikethrough is True
        assert style.overline is True


def test_wide_character_spans_two_cells() -> None:
    with Terminal(10, 2) as term:
        term.feed("世".encode())
        assert _cell_at(term, 0, 0).width is CellWidth.WIDE
        assert _cell_at(term, 1, 0).width is CellWidth.SPACER_TAIL


def test_narrow_cell_reports_narrow_width() -> None:
    with Terminal(10, 2) as term:
        term.feed(b"a")
        assert _cell_at(term, 0, 0).width is CellWidth.NARROW


def test_cell_without_hyperlink_has_none() -> None:
    with Terminal(10, 2) as term:
        term.feed(b"a")
        assert _cell_at(term, 0, 0).hyperlink is None


def test_cell_reports_its_hyperlink_uri() -> None:
    with Terminal(20, 2) as term:
        term.feed(b"\x1b]8;;https://example.com\x1b\\A\x1b]8;;\x1b\\")
        assert _cell_at(term, 0, 0).hyperlink == "https://example.com"


def test_cell_default_semantic_content_is_output() -> None:
    with Terminal(10, 2) as term:
        term.feed(b"a")
        assert _cell_at(term, 0, 0).semantic is SemanticContent.OUTPUT


def test_cell_is_not_protected_by_default() -> None:
    with Terminal(10, 2) as term:
        term.feed(b"a")
        assert _cell_at(term, 0, 0).protected is False


def test_grid_ref_converts_to_viewport_point() -> None:
    with Terminal(10, 2) as term:
        term.feed(b"hi")
        ref = term.grid_ref(Point(PointTag.ACTIVE, 1, 0))
        assert ref.point(PointTag.VIEWPORT) == Point(PointTag.VIEWPORT, 1, 0)


def test_grid_ref_out_of_range_coordinate_space_returns_none() -> None:
    with Terminal(5, 2, scrollback=1024) as term:
        term.feed(b"AAAAA\r\nBBBBB\r\nCCCCC\r\nDDDDD")
        # The top row has scrolled into history; it has no viewport coordinate.
        history_ref = term.grid_ref(Point(PointTag.HISTORY, 0, 0))
        assert history_ref.cell().text == "A"
        assert history_ref.point(PointTag.VIEWPORT) is None
        assert history_ref.point(PointTag.SCREEN) == Point(PointTag.SCREEN, 0, 0)


def test_grid_ref_out_of_bounds_raises() -> None:
    with Terminal(5, 2) as term, pytest.raises(InvalidValueError):
        term.grid_ref(Point(PointTag.ACTIVE, 0, 99))


def test_grid_ref_on_closed_terminal_raises() -> None:
    term = Terminal(5, 2)
    term.close()
    with pytest.raises(UseAfterCloseError):
        term.grid_ref(Point(PointTag.ACTIVE, 0, 0))


def test_grid_ref_cell_on_closed_terminal_raises() -> None:
    term = Terminal(5, 2)
    term.feed(b"A")
    ref = term.grid_ref(Point(PointTag.ACTIVE, 0, 0))
    term.close()
    with pytest.raises(UseAfterCloseError):
        ref.cell()


def test_tracked_ref_follows_a_scroll() -> None:
    with Terminal(10, 4) as term:
        term.feed(b"\x1b[3;1HROW")
        tracked = term.track_grid_ref(Point(PointTag.VIEWPORT, 0, 2))
        assert tracked.point(PointTag.VIEWPORT) == Point(PointTag.VIEWPORT, 0, 2)
        # Scroll the viewport up by one line; the tracked cell moves with it.
        term.feed(b"\x1b[4;1H\n")
        assert tracked.point(PointTag.VIEWPORT) == Point(PointTag.VIEWPORT, 0, 1)
        cell = tracked.cell()
        assert cell is not None
        assert cell.text == "R"
        tracked.close()


def test_tracked_ref_survives_scroll_into_scrollback() -> None:
    with Terminal(5, 2, scrollback=1024) as term:
        term.feed(b"TOP")
        tracked = term.track_grid_ref(Point(PointTag.VIEWPORT, 0, 0))
        term.feed(b"\r\nA\r\nB\r\nC")
        assert tracked.has_value is True
        cell = tracked.cell()
        assert cell is not None
        assert cell.text == "T"
        tracked.close()


def test_tracked_ref_can_be_repointed() -> None:
    with Terminal(10, 3) as term:
        term.feed(b"\x1b[1;1HAB\x1b[2;1HCD")
        tracked = term.track_grid_ref(Point(PointTag.VIEWPORT, 0, 0))
        before = tracked.cell()
        assert before is not None
        assert before.text == "A"
        tracked.move_to(Point(PointTag.VIEWPORT, 1, 1))
        assert tracked.point(PointTag.VIEWPORT) == Point(PointTag.VIEWPORT, 1, 1)
        after = tracked.cell()
        assert after is not None
        assert after.text == "D"
        tracked.close()


def test_tracked_ref_loses_value_when_grid_is_reset() -> None:
    with Terminal(5, 2, scrollback=64) as term:
        term.feed(b"TOP")
        tracked = term.track_grid_ref(Point(PointTag.VIEWPORT, 0, 0))
        assert tracked.has_value is True
        # RIS discards the whole grid; the tracked cell can no longer be mapped.
        term.feed(b"\x1bc")
        assert tracked.has_value is False
        assert tracked.point(PointTag.VIEWPORT) is None
        assert tracked.snapshot() is None
        assert tracked.cell() is None
        tracked.close()


def test_tracked_ref_snapshot_reads_the_current_cell() -> None:
    with Terminal(10, 2) as term:
        term.feed(b"Zz")
        tracked = term.track_grid_ref(Point(PointTag.VIEWPORT, 1, 0))
        snapshot = tracked.snapshot()
        assert snapshot is not None
        assert snapshot.cell().text == "z"
        tracked.close()


def test_tracked_ref_is_a_context_manager() -> None:
    with Terminal(10, 2) as term:
        term.feed(b"a")
        with term.track_grid_ref(Point(PointTag.VIEWPORT, 0, 0)) as tracked:
            assert isinstance(tracked, TrackedGridRef)


def test_tracked_ref_close_is_idempotent() -> None:
    with Terminal(10, 2) as term:
        term.feed(b"a")
        tracked = term.track_grid_ref(Point(PointTag.VIEWPORT, 0, 0))
        tracked.close()
        tracked.close()


_CLOSED_TRACKED_OPERATIONS: list[Callable[[TrackedGridRef], object]] = [
    lambda t: t.has_value,
    lambda t: t.point(PointTag.VIEWPORT),
    lambda t: t.snapshot(),
    lambda t: t.cell(),
    lambda t: t.move_to(Point(PointTag.VIEWPORT, 0, 0)),
]


@pytest.mark.parametrize("operation", _CLOSED_TRACKED_OPERATIONS)
def test_operations_on_closed_tracked_ref_raise(
    operation: Callable[[TrackedGridRef], object],
) -> None:
    term = Terminal(10, 2)
    term.feed(b"a")
    tracked = term.track_grid_ref(Point(PointTag.VIEWPORT, 0, 0))
    tracked.close()
    with pytest.raises(UseAfterCloseError):
        operation(tracked)


def test_enter_on_closed_tracked_ref_raises() -> None:
    term = Terminal(10, 2)
    term.feed(b"a")
    tracked = term.track_grid_ref(Point(PointTag.VIEWPORT, 0, 0))
    tracked.close()
    with pytest.raises(UseAfterCloseError), tracked:
        pass


def test_tracked_ref_error_is_a_ghostty_vt_error() -> None:
    assert issubclass(UseAfterCloseError, GhosttyVtError)
