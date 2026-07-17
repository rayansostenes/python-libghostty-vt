"""Behavioral tests for the color scheme domain, through the public API.

Assertions pin the exact escape sequences the native library emits across the
full cffi path.
"""

from __future__ import annotations

from ghostty_vt import ColorScheme, color_scheme


def test_schemes_are_distinct() -> None:
    assert len({ColorScheme.LIGHT, ColorScheme.DARK}) == 2


def test_dark_scheme_reports_997_1() -> None:
    assert color_scheme.encode(ColorScheme.DARK) == b"\x1b[?997;1n"


def test_light_scheme_reports_997_2() -> None:
    assert color_scheme.encode(ColorScheme.LIGHT) == b"\x1b[?997;2n"
