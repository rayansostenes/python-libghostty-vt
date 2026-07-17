"""Behavioral tests for the focus domain, through the public API.

Assertions pin the exact escape sequences the native library emits across the
full cffi path.
"""

from __future__ import annotations

from ghostty_vt import FocusEvent, focus


def test_events_are_distinct() -> None:
    assert len({FocusEvent.GAINED, FocusEvent.LOST}) == 2


def test_focus_gained_is_csi_i() -> None:
    assert focus.encode(FocusEvent.GAINED) == b"\x1b[I"


def test_focus_lost_is_csi_o() -> None:
    assert focus.encode(FocusEvent.LOST) == b"\x1b[O"
