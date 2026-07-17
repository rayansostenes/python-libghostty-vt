"""Behavioral tests for the selection domain, through the public API.

Every assertion observes what a user of ``ghostty_vt`` would see: bytes fed into
a real terminal, a selection made over its screen, and the plain text (or the
membership, order, and equality) that selection reports. The raw layer and the C
boundary are never touched directly.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from ghostty_vt import (
    InvalidValueError,
    NoValueError,
    Point,
    PointTag,
    Selection,
    SelectionAdjust,
    SelectionOrder,
    Terminal,
    UseAfterCloseError,
)

ACTIVE = PointTag.ACTIVE
SCREEN = PointTag.SCREEN
HISTORY = PointTag.HISTORY


def _terminal(cols: int = 20, rows: int = 4, *, scrollback: int = 0) -> Terminal:
    return Terminal(cols, rows, scrollback=scrollback)


def _active(x: int, y: int) -> Point:
    return Point(ACTIVE, x, y)


# --- point-to-point ---------------------------------------------------------


def test_point_to_point_extracts_exactly_the_span() -> None:
    with _terminal() as term:
        term.feed(b"hello world")
        sel = Selection.point_to_point(term, _active(0, 0), _active(4, 0))
        assert sel.text() == "hello"


def test_point_to_point_endpoints_may_be_reversed() -> None:
    with _terminal() as term:
        term.feed(b"hello world")
        forward = Selection.point_to_point(term, _active(0, 0), _active(4, 0))
        backward = Selection.point_to_point(term, _active(4, 0), _active(0, 0))
        assert forward.text() == backward.text() == "hello"


def test_point_to_point_spans_multiple_rows() -> None:
    with _terminal() as term:
        term.feed(b"first line\r\nsecond line")
        sel = Selection.point_to_point(term, _active(0, 0), _active(5, 1))
        assert sel.text() == "first line\nsecond"


def test_point_to_point_is_not_rectangular_by_default() -> None:
    with _terminal() as term:
        term.feed(b"abc")
        sel = Selection.point_to_point(term, _active(0, 0), _active(2, 0))
        assert sel.rectangle is False


def test_point_outside_screen_raises_invalid_value() -> None:
    with _terminal(10, 3) as term:
        term.feed(b"abc")
        with pytest.raises(InvalidValueError, match="grid reference"):
            Selection.point_to_point(term, _active(100, 0), _active(0, 0))


# --- rectangular ------------------------------------------------------------


def test_rectangular_selects_a_column_block() -> None:
    with _terminal() as term:
        term.feed(b"hello\r\nworld\r\nabcde")
        sel = Selection.point_to_point(
            term, _active(0, 0), _active(2, 2), rectangle=True
        )
        assert sel.rectangle is True
        assert sel.text() == "hel\nwor\nabc"


# --- word -------------------------------------------------------------------


def test_word_selects_the_whole_word_under_the_point() -> None:
    with _terminal() as term:
        term.feed(b"hello world foo")
        sel = Selection.word(term, _active(7, 0))
        assert sel.text() == "world"


def test_word_boundaries_split_on_extra_characters() -> None:
    with _terminal() as term:
        term.feed(b"foo.bar baz")
        default = Selection.word(term, _active(1, 0))
        split = Selection.word(term, _active(1, 0), boundaries=".")
        assert default.text() == "foo.bar"
        assert split.text() == "foo"


def test_word_empty_boundaries_uses_default_word_bounds() -> None:
    # An empty boundary set is not an explicit "no boundaries" request: it falls
    # back to upstream's default word bounds, matching `boundaries=None`.
    with _terminal() as term:
        term.feed(b"foo bar baz")
        default = Selection.word(term, _active(5, 0))
        empty = Selection.word(term, _active(5, 0), boundaries="")
        assert default.text() == "bar"
        assert empty.text() == "bar"


# --- word_between -----------------------------------------------------------


def test_word_between_selects_the_first_word_from_start() -> None:
    with _terminal(30, 2) as term:
        term.feed(b"hello world foo bar")
        sel = Selection.word_between(term, _active(1, 0), _active(13, 0))
        assert sel.text() == "hello"


def test_word_between_honors_boundaries() -> None:
    with _terminal(30, 2) as term:
        term.feed(b"foo.bar baz")
        sel = Selection.word_between(term, _active(0, 0), _active(6, 0), boundaries=".")
        assert sel.text() == "foo"


# --- line -------------------------------------------------------------------


def test_line_selects_the_whole_logical_line() -> None:
    with _terminal() as term:
        term.feed(b"first row\r\nsecond row\r\nthird row")
        sel = Selection.line(term, _active(2, 1))
        assert sel.text() == "second row"


def test_line_covers_the_whole_soft_wrapped_line() -> None:
    with _terminal(5, 4) as term:
        term.feed(b"abcdefghij")
        sel = Selection.line(term, _active(0, 0))
        # The logical line spans both wrapped rows; unwrapping rejoins them.
        assert sel.text(unwrap=True) == "abcdefghij"


def test_line_whitespace_trims_the_selection() -> None:
    with _terminal() as term:
        term.feed(b"__padded__")
        sel = Selection.line(term, _active(0, 0), whitespace="_")
        assert sel.text() == "padded"


def test_line_can_stop_at_semantic_prompt_boundary() -> None:
    with _terminal() as term:
        term.feed(b"plain line here")
        sel = Selection.line(term, _active(0, 0), semantic_prompt_boundary=True)
        assert sel.text() == "plain line here"


# --- all --------------------------------------------------------------------


def test_all_selects_every_written_cell() -> None:
    with _terminal() as term:
        term.feed(b"one\r\ntwo\r\nthree")
        assert Selection.all(term).text() == "one\ntwo\nthree"


def test_all_on_blank_terminal_raises_no_value() -> None:
    with _terminal() as term, pytest.raises(NoValueError, match="select all"):
        Selection.all(term)


# --- output -----------------------------------------------------------------

_PROMPT = b"\x1b]133;A\x07$ \x1b]133;B\x07echo hi\x1b]133;C\x07\r\n"


def test_output_selects_command_output_between_markers() -> None:
    with _terminal(30, 6) as term:
        term.feed(_PROMPT)
        term.feed(b"hi there\r\nmore output\x1b]133;D\x07")
        sel = Selection.output(term, _active(0, 1))
        assert sel.text() == "hi there\nmore output"


def test_output_without_a_marked_region_raises_no_value() -> None:
    with _terminal(30, 6) as term:
        term.feed(b"no shell integration here")
        with pytest.raises(NoValueError, match="select output"):
            Selection.output(term, _active(0, 0))


# --- endpoints, order, membership -------------------------------------------


def test_start_and_end_report_screen_coordinates() -> None:
    with _terminal() as term:
        term.feed(b"hello world")
        sel = Selection.point_to_point(term, _active(1, 0), _active(4, 0))
        assert sel.start == Point(SCREEN, 1, 0)
        assert sel.end == Point(SCREEN, 4, 0)


def test_order_is_forward_when_start_precedes_end() -> None:
    with _terminal() as term:
        term.feed(b"hello")
        sel = Selection.point_to_point(term, _active(0, 0), _active(4, 0))
        assert sel.order is SelectionOrder.FORWARD


def test_order_is_reverse_when_end_precedes_start() -> None:
    with _terminal() as term:
        term.feed(b"hello")
        sel = Selection.point_to_point(term, _active(4, 0), _active(0, 0))
        assert sel.order is SelectionOrder.REVERSE


def test_ordered_normalizes_endpoints_without_changing_the_region() -> None:
    with _terminal() as term:
        term.feed(b"hello")
        reverse = Selection.point_to_point(term, _active(4, 0), _active(0, 0))
        forward = reverse.ordered(SelectionOrder.FORWARD)
        assert forward.order is SelectionOrder.FORWARD
        assert forward.text() == reverse.text() == "hello"


def test_contains_reports_membership() -> None:
    with _terminal() as term:
        term.feed(b"hello world")
        sel = Selection.point_to_point(term, _active(0, 0), _active(4, 0))
        assert sel.contains(_active(2, 0)) is True
        assert sel.contains(_active(9, 0)) is False


def test_in_operator_delegates_to_contains() -> None:
    with _terminal() as term:
        term.feed(b"hello world")
        sel = Selection.point_to_point(term, _active(0, 0), _active(4, 0))
        assert _active(3, 0) in sel
        assert _active(8, 0) not in sel


# --- text options -----------------------------------------------------------


def test_text_can_keep_trailing_whitespace() -> None:
    with _terminal() as term:
        term.feed(b"hi   end")
        sel = Selection.point_to_point(term, _active(0, 0), _active(4, 0))
        assert sel.text(trim=False) == "hi   "
        assert sel.text(trim=True) == "hi"


def test_text_can_unwrap_soft_wrapped_rows() -> None:
    with _terminal(5, 4) as term:
        term.feed(b"abcdefghij")
        sel = Selection.point_to_point(term, _active(0, 0), _active(4, 1))
        assert sel.text(unwrap=False) == "abcde\nfghij"
        assert sel.text(unwrap=True) == "abcdefghij"


# --- equality ---------------------------------------------------------------


def test_selections_over_the_same_region_are_equal() -> None:
    with _terminal() as term:
        term.feed(b"hello world")
        a = Selection.point_to_point(term, _active(0, 0), _active(4, 0))
        b = Selection.point_to_point(term, _active(0, 0), _active(4, 0))
        assert a == b


def test_selections_over_different_regions_are_unequal() -> None:
    with _terminal() as term:
        term.feed(b"hello world")
        a = Selection.point_to_point(term, _active(0, 0), _active(4, 0))
        b = Selection.point_to_point(term, _active(0, 0), _active(5, 0))
        assert a != b


def test_selections_from_different_terminals_are_unequal() -> None:
    with _terminal() as one, _terminal() as two:
        one.feed(b"hello")
        two.feed(b"hello")
        a = Selection.point_to_point(one, _active(0, 0), _active(4, 0))
        b = Selection.point_to_point(two, _active(0, 0), _active(4, 0))
        assert a != b


def test_selection_is_not_equal_to_other_types() -> None:
    with _terminal() as term:
        term.feed(b"hello")
        sel = Selection.point_to_point(term, _active(0, 0), _active(4, 0))
        assert sel != "hello"
        assert (sel == 5) is False


def test_selection_is_unhashable() -> None:
    with _terminal() as term:
        term.feed(b"hello")
        sel = Selection.point_to_point(term, _active(0, 0), _active(4, 0))
        with pytest.raises(TypeError):
            hash(sel)


# --- adjust -----------------------------------------------------------------


def test_adjust_extends_the_selection_and_leaves_the_original() -> None:
    with _terminal() as term:
        term.feed(b"hello world foo")
        sel = Selection.point_to_point(term, _active(0, 0), _active(4, 0))
        grown = sel.adjust(SelectionAdjust.END_OF_LINE)
        assert grown.text() == "hello world foo"
        assert sel.text() == "hello"


def test_adjust_beginning_of_line_moves_the_end() -> None:
    with _terminal() as term:
        term.feed(b"hello world")
        sel = Selection.point_to_point(term, _active(3, 0), _active(8, 0))
        shrunk = sel.adjust(SelectionAdjust.BEGINNING_OF_LINE)
        assert shrunk.text() == "hell"


# --- scrollback and resize --------------------------------------------------


def test_selection_reaches_into_scrollback_history() -> None:
    with _terminal(10, 2, scrollback=100) as term:
        for i in range(5):
            term.feed(f"row{i}\r\n".encode())
        # Rows 0-3 have scrolled into history; the screen space still addresses
        # them and the selection extracts them verbatim.
        sel = Selection.point_to_point(term, Point(SCREEN, 0, 0), Point(SCREEN, 9, 4))
        assert sel.text() == "row0\nrow1\nrow2\nrow3\nrow4"


def test_history_tag_addresses_scrolled_off_rows() -> None:
    with _terminal(10, 2, scrollback=100) as term:
        for i in range(5):
            term.feed(f"row{i}\r\n".encode())
        sel = Selection.point_to_point(term, Point(HISTORY, 0, 0), Point(HISTORY, 9, 0))
        assert sel.text() == "row0"


def test_all_spans_scrollback_and_active_screen() -> None:
    with _terminal(10, 2, scrollback=100) as term:
        for i in range(5):
            term.feed(f"row{i}\r\n".encode())
        assert Selection.all(term).text() == "row0\nrow1\nrow2\nrow3\nrow4"


def test_selection_after_resize_reflows_with_the_screen() -> None:
    with _terminal(20, 3) as term:
        term.feed(b"abcdefghij klmnop")
        term.resize(10, 3)
        # The reflowed content wraps; a fresh whole-screen selection sees it.
        assert Selection.all(term).text() == "abcdefghij\n klmnop"


def test_selection_follows_its_cells_into_scrollback() -> None:
    # A selection anchors to its cells: as content scrolls into history, the
    # same selection keeps reporting that content rather than the cells that
    # now occupy those screen positions.
    with _terminal(10, 3, scrollback=100) as term:
        term.feed(b"hello")
        sel = Selection.point_to_point(term, _active(0, 0), _active(4, 0))
        assert sel.text() == "hello"
        term.feed(b"\r\none\r\ntwo\r\nthree\r\nfour")
        assert sel.text() == "hello"
        assert sel.start == Point(SCREEN, 0, 0)


def test_selection_reused_after_resize_tracks_its_cells() -> None:
    with _terminal(20, 3) as term:
        term.feed(b"abcdefghij klmnop")
        sel = Selection.point_to_point(term, _active(0, 0), _active(9, 0))
        assert sel.text() == "abcdefghij"
        term.resize(10, 3)
        # The anchored endpoints reflow with the screen; the run still reads the
        # original cells rather than going stale.
        assert sel.text() == "abcdefghij"


# --- lifetime ---------------------------------------------------------------

_CLOSED_OPERATIONS: list[Callable[[Selection], object]] = [
    lambda s: s.text(),
    lambda s: s.start,
    lambda s: s.end,
    lambda s: s.order,
    lambda s: s.adjust(SelectionAdjust.RIGHT),
    lambda s: s.ordered(SelectionOrder.FORWARD),
    lambda s: s.contains(Point(PointTag.ACTIVE, 0, 0)),
    lambda s: Point(PointTag.ACTIVE, 0, 0) in s,
]


@pytest.mark.parametrize("operation", _CLOSED_OPERATIONS)
def test_operations_after_terminal_close_raise(
    operation: Callable[[Selection], object],
) -> None:
    term = _terminal()
    term.feed(b"hello")
    sel = Selection.point_to_point(term, _active(0, 0), _active(4, 0))
    term.close()
    with pytest.raises(UseAfterCloseError):
        operation(sel)


def test_rectangle_is_readable_after_close() -> None:
    # `rectangle` reflects the stored selection kind and touches no native state,
    # so it stays readable once the terminal is gone.
    term = _terminal()
    term.feed(b"hello")
    sel = Selection.point_to_point(term, _active(0, 0), _active(4, 0), rectangle=True)
    term.close()
    assert sel.rectangle is True


def test_creating_a_selection_after_close_raises() -> None:
    term = _terminal()
    term.feed(b"hello")
    term.close()
    with pytest.raises(UseAfterCloseError):
        Selection.all(term)


def test_equality_after_close_raises() -> None:
    term = _terminal()
    term.feed(b"hello")
    a = Selection.point_to_point(term, _active(0, 0), _active(4, 0))
    b = Selection.point_to_point(term, _active(0, 0), _active(4, 0))
    term.close()
    with pytest.raises(UseAfterCloseError):
        _ = a == b
