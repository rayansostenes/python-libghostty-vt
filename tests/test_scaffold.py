"""Smoke tests for the package scaffold."""

from __future__ import annotations

import ghostty_vt


def test_version_is_exposed() -> None:
    assert ghostty_vt.__version__ == "0.1.0.dev0"
