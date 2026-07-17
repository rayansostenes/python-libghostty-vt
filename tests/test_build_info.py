"""Behavioral tests for the build_info domain, through the public API.

Every assertion observes what a user of ``ghostty_vt`` would see: real data
returned by the native library across the full cffi path. The raw layer and the C
boundary are never touched directly.
"""

from __future__ import annotations

from pathlib import Path

import ghostty_vt
from ghostty_vt import BuildInfo, OptimizeMode

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_build_info_returns_a_populated_build_info() -> None:
    info = ghostty_vt.build_info()
    assert isinstance(info, BuildInfo)


def test_build_info_flags_are_booleans() -> None:
    info = ghostty_vt.build_info()
    assert isinstance(info.simd, bool)
    assert isinstance(info.kitty_graphics, bool)
    assert isinstance(info.tmux_control_mode, bool)


def test_build_info_optimize_is_an_optimize_mode() -> None:
    info = ghostty_vt.build_info()
    assert isinstance(info.optimize, OptimizeMode)


def test_optimize_mode_matches_the_release_build() -> None:
    # The wheels (and this dev build) are compiled ReleaseFast; see scripts/_lib.sh.
    assert ghostty_vt.build_info().optimize is OptimizeMode.RELEASE_FAST


def test_version_numbers_are_non_negative_ints() -> None:
    info = ghostty_vt.build_info()
    assert isinstance(info.version_major, int)
    assert isinstance(info.version_minor, int)
    assert isinstance(info.version_patch, int)
    assert info.version_major >= 0
    assert info.version_minor >= 0
    assert info.version_patch >= 0


def test_version_string_encodes_the_numeric_components() -> None:
    info = ghostty_vt.build_info()
    prefix = f"{info.version_major}.{info.version_minor}.{info.version_patch}"
    assert info.version.startswith(prefix)


def test_version_pre_is_populated_for_a_dev_build() -> None:
    # A non-empty pre-release field exercises the populated-string path.
    info = ghostty_vt.build_info()
    assert info.version_pre != ""
    assert info.version_pre in info.version


def test_version_build_metadata_is_empty() -> None:
    # This upstream build carries no build metadata, exercising the empty-string
    # path of the string query.
    assert ghostty_vt.build_info().version_build == ""


def test_ghostty_commit_equals_the_pinned_commit() -> None:
    pinned = (REPO_ROOT / "ghostty-commit.txt").read_text().strip()
    assert pinned == ghostty_vt.GHOSTTY_COMMIT
