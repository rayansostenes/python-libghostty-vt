"""Behavioral tests for the formatter domain, through the public API.

The formatter extracts a terminal's visible screen to text. These assertions feed
bytes into a real terminal and check the serialized output for each format and
option; the raw layer and the C boundary are never touched directly.
"""

from __future__ import annotations

import pytest

from ghostty_vt import Format, Terminal, UseAfterCloseError


def test_format_defaults_to_trimmed_plain_text() -> None:
    with Terminal(20, 3) as term:
        term.feed(b"hello     ")
        assert term.format() == "hello"


def test_format_plain_matches_visible_text() -> None:
    with Terminal(20, 3) as term:
        term.feed(b"\x1b[31mwarning\x1b[0m")
        assert term.format(emit=Format.PLAIN) == term.visible_text()


def test_format_vt_emits_escape_sequences() -> None:
    with Terminal(10, 2) as term:
        term.feed(b"\x1b[1mA\x1b[0m")
        output = term.format(emit=Format.VT)
        assert "A" in output
        assert "\x1b[" in output


def test_format_html_emits_markup() -> None:
    with Terminal(10, 2) as term:
        term.feed(b"hi")
        output = term.format(emit=Format.HTML)
        assert "<" in output and ">" in output


def test_format_unwrap_joins_soft_wrapped_lines() -> None:
    with Terminal(5, 3) as term:
        term.feed(b"abcdefghij")
        assert term.format() == "abcde\nfghij"
        assert term.format(unwrap=True) == "abcdefghij"


def test_without_trim_trailing_whitespace_is_kept() -> None:
    with Terminal(8, 2) as term:
        term.feed(b"hi    ")
        assert term.format(trim=True) == "hi"
        assert term.format(trim=False) == "hi    "


def test_format_on_closed_terminal_raises() -> None:
    term = Terminal(10, 2)
    term.close()
    with pytest.raises(UseAfterCloseError):
        term.format()
