"""Behavioral tests for the unicode domain, through the public API.

Widths are the native library's own, exercised across the full cffi path, so the
assertions pin the same table the terminal uses when laying out text.
"""

from __future__ import annotations

import pytest

from ghostty_vt import unicode


def test_ascii_is_one_cell() -> None:
    assert unicode.codepoint_width(ord("A")) == 1


def test_east_asian_wide_is_two_cells() -> None:
    assert unicode.codepoint_width(ord("中")) == 2


def test_combining_mark_is_zero_cells() -> None:
    assert unicode.codepoint_width(0x0301) == 0  # combining acute accent


def test_control_character_is_zero_cells() -> None:
    assert unicode.codepoint_width(0) == 0


def test_default_emoji_is_two_cells() -> None:
    assert unicode.codepoint_width(ord("👍")) == 2


def test_codepoint_width_rejects_negative() -> None:
    with pytest.raises(ValueError, match="codepoint out of range"):
        unicode.codepoint_width(-1)


def test_codepoint_width_rejects_beyond_unicode_max() -> None:
    with pytest.raises(ValueError, match="codepoint out of range"):
        unicode.codepoint_width(0x110000)


def test_codepoint_width_accepts_the_maximum_codepoint() -> None:
    assert unicode.codepoint_width(0x10FFFF) == 1


def test_string_width_of_empty_is_zero() -> None:
    assert unicode.string_width("") == 0


def test_string_width_sums_ascii() -> None:
    assert unicode.string_width("hello") == 5


def test_string_width_counts_wide_characters() -> None:
    assert unicode.string_width("中文") == 4


def test_string_width_folds_combining_sequence_into_one_cell() -> None:
    # "a" (U+0061) plus a combining acute accent (U+0301) is one cell.
    assert unicode.string_width("a\u0301") == 1


def test_string_width_measures_emoji_presentation_selectors() -> None:
    # U+2764 with VS16 (emoji) is wide; with VS15 (text) it is narrow.
    assert unicode.string_width("\u2764\ufe0f") == 2
    assert unicode.string_width("\u2764\ufe0e") == 1


def test_string_width_treats_zwj_sequence_as_one_cluster() -> None:
    family = "\U0001f468\u200d\U0001f469\u200d\U0001f467"
    assert unicode.string_width(family) == 2
