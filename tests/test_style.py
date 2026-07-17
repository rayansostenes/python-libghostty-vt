"""Behavioral tests for the style value types, through the public API.

The style domain's :class:`Style` is read out of the screen by the grid-ref and
render domains; those suites assert that a style reflects fed SGR input. Here we
pin the value type's own surface: it is an immutable snapshot with the documented
fields, and the underline styles are a closed enum.
"""

from __future__ import annotations

import dataclasses

import pytest

from ghostty_vt import Rgb, Style, Underline


def _style(**overrides: object) -> Style:
    base: dict[str, object] = {
        "fg": None,
        "bg": None,
        "underline_color": None,
        "bold": False,
        "italic": False,
        "faint": False,
        "blink": False,
        "inverse": False,
        "invisible": False,
        "strikethrough": False,
        "overline": False,
        "underline": Underline.NONE,
    }
    base.update(overrides)
    return Style(**base)  # type: ignore[arg-type]


def test_style_is_immutable() -> None:
    style = _style(bold=True)
    with pytest.raises(dataclasses.FrozenInstanceError):
        style.bold = False  # type: ignore[misc]


def test_style_color_is_none_palette_index_or_rgb() -> None:
    assert _style(fg=None).fg is None
    assert _style(fg=1).fg == 1
    assert _style(fg=Rgb(255, 0, 0)).fg == Rgb(255, 0, 0)


def test_underline_members_are_distinct() -> None:
    styles = set(Underline)
    assert Underline.NONE in styles
    assert len(styles) == 6
