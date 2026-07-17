"""Smoke tests for the package scaffold."""

from __future__ import annotations

import re
from pathlib import Path

import ghostty_vt

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_version_is_exposed() -> None:
    assert ghostty_vt.__version__ == "0.1.0.dev0"


def test_pinned_commit_is_a_single_full_sha() -> None:
    pin = REPO_ROOT / "ghostty-commit.txt"
    assert pin.is_file()
    assert re.fullmatch(r"[0-9a-f]{40}", pin.read_text().strip())
