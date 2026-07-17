"""Behavioral tests for the paste domain, through the public API.

Every assertion observes what a user of ``ghostty_vt`` would see: the native
library's real safety verdict and pty encoding across the full cffi path.
"""

from __future__ import annotations

from ghostty_vt import paste

BRACKET_START = b"\x1b[200~"
BRACKET_END = b"\x1b[201~"


def test_plain_text_is_safe() -> None:
    assert paste.is_safe("hello world") is True


def test_newline_is_unsafe() -> None:
    assert paste.is_safe("run\nrm -rf") is False


def test_bracketed_paste_end_sequence_is_unsafe() -> None:
    assert paste.is_safe("before\x1b[201~after") is False


def test_encode_plain_text_unbracketed_is_unchanged() -> None:
    assert paste.encode("hello", bracketed=False) == b"hello"


def test_encode_unbracketed_replaces_newlines_with_carriage_returns() -> None:
    assert paste.encode("a\nb", bracketed=False) == b"a\rb"


def test_encode_bracketed_wraps_the_content() -> None:
    encoded = paste.encode("hello", bracketed=True)
    assert encoded == BRACKET_START + b"hello" + BRACKET_END


def test_encode_bracketed_preserves_newlines() -> None:
    encoded = paste.encode("a\nb", bracketed=True)
    assert encoded == BRACKET_START + b"a\nb" + BRACKET_END


def test_encode_strips_unsafe_control_bytes_to_spaces() -> None:
    assert paste.encode("a\x1bb", bracketed=False) == b"a b"


def test_encode_empty_unbracketed_is_empty() -> None:
    assert paste.encode("", bracketed=False) == b""


def test_encode_empty_bracketed_is_just_the_wrapper() -> None:
    assert paste.encode("", bracketed=True) == BRACKET_START + BRACKET_END


def test_encode_handles_multibyte_utf8() -> None:
    encoded = paste.encode("café", bracketed=False)
    assert encoded == "café".encode()
