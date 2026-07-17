"""Behavioral tests for the terminal domain, through the public API.

Every assertion observes what a user of ``ghostty_vt`` would see: bytes fed into
a real terminal and the visible text read back across the full cffi path. The
raw layer and the C boundary are never touched directly.
"""

from __future__ import annotations

import gc
from collections.abc import Callable

import pytest

from ghostty_vt import Cursor, Mode, Screen, Terminal, UseAfterCloseError


def test_new_terminal_reports_its_dimensions() -> None:
    with Terminal(80, 24) as term:
        assert term.cols == 80
        assert term.rows == 24


def test_new_terminal_is_blank() -> None:
    with Terminal(10, 3) as term:
        assert term.visible_text() == ""


def test_feed_prints_plain_text() -> None:
    with Terminal(20, 3) as term:
        term.feed(b"hello")
        assert term.visible_text() == "hello"


def test_feed_is_incremental() -> None:
    with Terminal(20, 3) as term:
        term.feed(b"hel")
        term.feed(b"lo")
        assert term.visible_text() == "hello"


def test_feed_resumes_an_escape_sequence_split_across_calls() -> None:
    with Terminal(20, 3) as term:
        # An SGR sequence and its styled text split mid-sequence: the stream
        # parser must hold state between feeds, not restart on each call.
        term.feed(b"\x1b[31")
        term.feed(b"mred\x1b[0m")
        assert term.visible_text() == "red"


def test_feed_resumes_a_utf8_codepoint_split_across_calls() -> None:
    with Terminal(20, 3) as term:
        encoded = "é".encode()
        term.feed(encoded[:1])
        term.feed(encoded[1:] + b"x")
        assert term.visible_text() == "éx"


def test_feed_empty_bytes_is_a_noop() -> None:
    with Terminal(20, 3) as term:
        term.feed(b"world")
        term.feed(b"")
        assert term.visible_text() == "world"


def test_carriage_return_newline_starts_a_row() -> None:
    with Terminal(20, 3) as term:
        term.feed(b"line one\r\nline two")
        assert term.visible_text() == "line one\nline two"


def test_sgr_styling_is_stripped_from_visible_text() -> None:
    with Terminal(20, 3) as term:
        # Red "warning", then reset. The visible text is the characters only.
        term.feed(b"\x1b[31mwarning\x1b[0m")
        assert term.visible_text() == "warning"


def test_cursor_movement_positions_text() -> None:
    with Terminal(20, 3) as term:
        # CUP to row 2, col 5 (1-based in the escape), then print.
        term.feed(b"\x1b[2;5Hhi")
        assert term.visible_text() == "\n    hi"


def test_erase_display_clears_the_screen() -> None:
    with Terminal(20, 3) as term:
        term.feed(b"garbage\x1b[2J\x1b[Hclean")
        assert term.visible_text() == "clean"


def test_wide_characters_are_preserved() -> None:
    with Terminal(20, 3) as term:
        text = "héllo☃"
        term.feed(text.encode("utf-8"))
        assert term.visible_text() == text


def test_content_wider_than_the_screen_wraps() -> None:
    with Terminal(5, 3) as term:
        term.feed(b"abcdefghij")
        assert term.visible_text() == "abcde\nfghij"


def test_trailing_whitespace_is_trimmed() -> None:
    with Terminal(20, 3) as term:
        term.feed(b"spaced out     ")
        assert term.visible_text() == "spaced out"


def test_resize_updates_dimensions() -> None:
    with Terminal(80, 24) as term:
        term.resize(100, 40)
        assert term.cols == 100
        assert term.rows == 40


def test_resize_reflows_content() -> None:
    with Terminal(20, 3) as term:
        term.feed(b"abcdefghij klmnop")
        assert term.visible_text() == "abcdefghij klmnop"
        term.resize(10, 3)
        assert term.visible_text() == "abcdefghij\n klmnop"


@pytest.mark.parametrize("cols", [0, -1, 0x10000])
def test_new_rejects_out_of_range_cols(cols: int) -> None:
    with pytest.raises(ValueError, match="cols must be between 1 and 65535"):
        Terminal(cols, 24)


@pytest.mark.parametrize("rows", [0, -1, 0x10000])
def test_new_rejects_out_of_range_rows(rows: int) -> None:
    with pytest.raises(ValueError, match="rows must be between 1 and 65535"):
        Terminal(80, rows)


def test_resize_rejects_out_of_range_dimensions() -> None:
    with (
        Terminal(80, 24) as term,
        pytest.raises(ValueError, match="cols must be between 1 and 65535"),
    ):
        term.resize(0, 24)


def test_extreme_dimensions_are_accepted() -> None:
    with Terminal(65535, 65535) as term:
        assert term.cols == 65535
        assert term.rows == 65535


def test_context_manager_returns_the_terminal() -> None:
    with Terminal(10, 3) as term:
        assert isinstance(term, Terminal)


def test_use_after_context_exit_raises() -> None:
    with Terminal(10, 3) as term:
        pass
    with pytest.raises(UseAfterCloseError):
        term.feed(b"x")


def test_close_is_idempotent() -> None:
    term = Terminal(10, 3)
    term.close()
    term.close()


_CLOSED_OPERATIONS: list[Callable[[Terminal], object]] = [
    lambda t: t.feed(b"x"),
    lambda t: t.visible_text(),
    lambda t: t.resize(20, 5),
    lambda t: t.cols,
    lambda t: t.rows,
    lambda t: t.cursor,
    lambda t: t.active_screen,
    lambda t: t.mouse_tracking,
    lambda t: t.total_rows,
    lambda t: t.scrollback_rows,
    lambda t: t.viewport_active,
    lambda t: t.get_mode(Mode.CURSOR_VISIBLE),
    lambda t: t.set_mode(Mode.CURSOR_VISIBLE, False),
    lambda t: t.scroll_to_top(),
    lambda t: t.scroll_to_bottom(),
    lambda t: t.scroll_by(-1),
    lambda t: t.scroll_to_row(0),
]


@pytest.mark.parametrize("operation", _CLOSED_OPERATIONS)
def test_operations_after_close_raise(
    operation: Callable[[Terminal], object],
) -> None:
    term = Terminal(10, 3)
    term.close()
    with pytest.raises(UseAfterCloseError, match="closed Terminal"):
        operation(term)


def test_resize_on_closed_terminal_checks_liveness_before_dimensions() -> None:
    # A closed terminal reports its closed state even when the dimensions are
    # also invalid: liveness is validated before the range check.
    term = Terminal(10, 3)
    term.close()
    with pytest.raises(UseAfterCloseError, match="closed Terminal"):
        term.resize(0, 24)


def test_enter_on_closed_terminal_raises() -> None:
    term = Terminal(10, 3)
    term.close()
    with pytest.raises(UseAfterCloseError, match="closed Terminal"), term:
        pass


def test_use_after_close_is_a_ghostty_vt_error() -> None:
    from ghostty_vt import GhosttyVtError

    assert issubclass(UseAfterCloseError, GhosttyVtError)


def test_unreferenced_terminal_is_finalized() -> None:
    # Observe the terminal's own native-freeing finalizer, not an unrelated one:
    # holding the finalize object does not keep the terminal alive, so watching
    # it go from alive to dead proves ghostty_terminal_free actually ran.
    term = Terminal(10, 3)
    finalizer = term._finalizer  # pyright: ignore[reportPrivateUsage]
    assert finalizer.alive
    del term
    gc.collect()
    assert not finalizer.alive


# --- Cursor and screen state -------------------------------------------------


def test_fresh_cursor_is_at_origin_and_visible() -> None:
    with Terminal(10, 3) as term:
        assert term.cursor == Cursor(x=0, y=0, visible=True, pending_wrap=False)


def test_cursor_tracks_printed_text() -> None:
    with Terminal(10, 3) as term:
        term.feed(b"abc")
        assert term.cursor.x == 3
        assert term.cursor.y == 0


def test_cursor_position_follows_cursor_movement() -> None:
    with Terminal(20, 5) as term:
        # CUP to row 3, col 7 (1-based in the escape) -> 0-based (6, 2).
        term.feed(b"\x1b[3;7H")
        assert term.cursor.x == 6
        assert term.cursor.y == 2


def test_cursor_pending_wrap_at_right_margin() -> None:
    with Terminal(5, 3) as term:
        term.feed(b"abcde")
        # Cursor stays on the last column with a wrap pending until the next
        # character actually wraps.
        assert term.cursor.pending_wrap is True
        assert term.cursor.x == 4


def test_hiding_the_cursor_updates_visibility() -> None:
    with Terminal(10, 3) as term:
        term.feed(b"\x1b[?25l")
        assert term.cursor.visible is False
        term.feed(b"\x1b[?25h")
        assert term.cursor.visible is True


def test_new_terminal_is_on_the_primary_screen() -> None:
    with Terminal(10, 3) as term:
        assert term.active_screen is Screen.PRIMARY


def test_alternate_screen_switch_is_observable() -> None:
    with Terminal(10, 3) as term:
        term.feed(b"\x1b[?1049h")
        on_alternate = term.active_screen
        term.feed(b"\x1b[?1049l")
        back_on_primary = term.active_screen
        assert on_alternate is Screen.ALTERNATE
        assert back_on_primary is Screen.PRIMARY


def test_mouse_tracking_reflects_mode() -> None:
    with Terminal(10, 3) as term:
        assert term.mouse_tracking is False
        term.feed(b"\x1b[?1000h")
        assert term.mouse_tracking is True


# --- Modes -------------------------------------------------------------------


def test_mode_set_by_escape_is_observable_through_query() -> None:
    with Terminal(10, 3) as term:
        assert term.get_mode(Mode.BRACKETED_PASTE) is False
        term.feed(b"\x1b[?2004h")
        assert term.get_mode(Mode.BRACKETED_PASTE) is True


def test_set_mode_reflects_in_query() -> None:
    with Terminal(10, 3) as term:
        term.set_mode(Mode.BRACKETED_PASTE, True)
        assert term.get_mode(Mode.BRACKETED_PASTE) is True
        term.set_mode(Mode.BRACKETED_PASTE, False)
        assert term.get_mode(Mode.BRACKETED_PASTE) is False


def test_set_mode_and_screen_state_agree() -> None:
    # DEC 25 is both a mode and a screen-state field; the two views agree.
    with Terminal(10, 3) as term:
        term.set_mode(Mode.CURSOR_VISIBLE, False)
        assert term.get_mode(Mode.CURSOR_VISIBLE) is False
        assert term.cursor.visible is False


def test_ansi_and_dec_modes_are_distinct() -> None:
    # ANSI 4 (INSERT) and DEC 4 (SLOW_SCROLL) share a number but are separate.
    with Terminal(10, 3) as term:
        term.set_mode(Mode.INSERT, True)
        assert term.get_mode(Mode.INSERT) is True
        assert term.get_mode(Mode.SLOW_SCROLL) is False


# --- Scrollback --------------------------------------------------------------


def test_no_scrollback_by_default() -> None:
    with Terminal(5, 2) as term:
        for i in range(6):
            term.feed(f"row{i}\r\n".encode())
        assert term.scrollback_rows == 0


def test_scrollback_retains_scrolled_off_lines() -> None:
    with Terminal(5, 2, scrollback=100) as term:
        for i in range(6):
            term.feed(f"row{i}\r\n".encode())
        assert term.scrollback_rows > 0
        assert term.total_rows > term.rows


def test_scrollback_content_is_reachable_beyond_the_visible_area() -> None:
    with Terminal(5, 2, scrollback=100) as term:
        for i in range(6):
            term.feed(f"row{i}\r\n".encode())
        text = term.visible_text()
        # row0 has scrolled off the two visible rows but remains reachable.
        assert "row0" in text
        assert "row5" in text


def test_new_rejects_negative_scrollback() -> None:
    with pytest.raises(ValueError, match="scrollback must be non-negative"):
        Terminal(10, 3, scrollback=-1)


def test_viewport_starts_pinned_to_the_active_area() -> None:
    with Terminal(5, 2, scrollback=100) as term:
        term.feed(b"a\r\nb\r\nc\r\nd")
        assert term.viewport_active is True


def test_scroll_to_top_moves_off_the_active_area() -> None:
    with Terminal(5, 2, scrollback=100) as term:
        for i in range(6):
            term.feed(f"row{i}\r\n".encode())
        term.scroll_to_top()
        assert term.viewport_active is False


def test_scroll_to_bottom_returns_to_the_active_area() -> None:
    with Terminal(5, 2, scrollback=100) as term:
        for i in range(6):
            term.feed(f"row{i}\r\n".encode())
        term.scroll_to_top()
        term.scroll_to_bottom()
        assert term.viewport_active is True


def test_scroll_by_negative_delta_scrolls_up() -> None:
    with Terminal(5, 2, scrollback=100) as term:
        for i in range(6):
            term.feed(f"row{i}\r\n".encode())
        term.scroll_by(-2)
        assert term.viewport_active is False


def test_scroll_to_row_positions_the_viewport() -> None:
    with Terminal(5, 2, scrollback=100) as term:
        for i in range(6):
            term.feed(f"row{i}\r\n".encode())
        term.scroll_to_row(0)
        assert term.viewport_active is False


def test_scroll_to_row_rejects_negative_rows() -> None:
    with (
        Terminal(5, 2, scrollback=100) as term,
        pytest.raises(ValueError, match="row must be non-negative"),
    ):
        term.scroll_to_row(-1)
