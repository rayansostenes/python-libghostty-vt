"""Build info domain: query libghostty-vt's compile-time configuration.

This is the idiomatic layer over the upstream ``build_info`` domain: a typed,
Pythonic surface built on the private raw layer. The values reflect the options
the native library was compiled with and are constant for the process lifetime.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Any, Final

from ghostty_vt import _raw

__all__ = ["GHOSTTY_COMMIT", "BuildInfo", "OptimizeMode", "build_info"]

_ffi = _raw.ffi
_lib = _raw.lib


class OptimizeMode(enum.Enum):
    """The zig optimization mode the native library was built with."""

    DEBUG = _lib.GHOSTTY_OPTIMIZE_DEBUG
    RELEASE_SAFE = _lib.GHOSTTY_OPTIMIZE_RELEASE_SAFE
    RELEASE_SMALL = _lib.GHOSTTY_OPTIMIZE_RELEASE_SMALL
    RELEASE_FAST = _lib.GHOSTTY_OPTIMIZE_RELEASE_FAST


@dataclass(frozen=True, slots=True)
class BuildInfo:
    """Compile-time build configuration of the native libghostty-vt.

    Attributes:
        simd: Whether SIMD-accelerated code paths are enabled.
        kitty_graphics: Whether Kitty graphics protocol support is available.
        tmux_control_mode: Whether tmux control mode support is available.
        optimize: The optimization mode the library was built with.
        version: The full upstream version string (e.g. ``"1.2.3-dev"``).
        version_major: The major version number.
        version_minor: The minor version number.
        version_patch: The patch version number.
        version_pre: The pre-release metadata (e.g. ``"dev"``), or ``""``.
        version_build: The build metadata (e.g. a commit hash), or ``""``.
    """

    simd: bool
    kitty_graphics: bool
    tmux_control_mode: bool
    optimize: OptimizeMode
    version: str
    version_major: int
    version_minor: int
    version_patch: int
    version_pre: str
    version_build: str


def _query(tag: int, ctype: str) -> Any:
    # Returns the raw cffi cdata pointer; the C boundary is inherently dynamic.
    out = _ffi.new(ctype)
    result = _lib.ghostty_build_info(tag, out)
    if result != _lib.GHOSTTY_SUCCESS:  # pragma: no cover
        # Unreachable: every tag queried below is a compile-time-valid variant,
        # for which the C API always reports success.
        raise RuntimeError(f"ghostty_build_info failed for tag {tag}: {result}")
    return out


def _query_bool(tag: int) -> bool:
    out = _query(tag, "bool *")
    return bool(out[0])


def _query_size(tag: int) -> int:
    out = _query(tag, "size_t *")
    return int(out[0])


def _query_optimize(tag: int) -> OptimizeMode:
    # GhosttyOptimizeMode is backed by a C int; query into an int-sized buffer.
    out = _query(tag, "int *")
    return OptimizeMode(int(out[0]))


def _query_str(tag: int) -> str:
    out = _query(tag, "GhosttyString *")
    if out.len == 0:
        return ""
    return str(_ffi.string(_ffi.cast("char *", out.ptr), out.len).decode("utf-8"))


def build_info() -> BuildInfo:
    """Return the native library's compile-time build configuration."""
    return BuildInfo(
        simd=_query_bool(_lib.GHOSTTY_BUILD_INFO_SIMD),
        kitty_graphics=_query_bool(_lib.GHOSTTY_BUILD_INFO_KITTY_GRAPHICS),
        tmux_control_mode=_query_bool(_lib.GHOSTTY_BUILD_INFO_TMUX_CONTROL_MODE),
        optimize=_query_optimize(_lib.GHOSTTY_BUILD_INFO_OPTIMIZE),
        version=_query_str(_lib.GHOSTTY_BUILD_INFO_VERSION_STRING),
        version_major=_query_size(_lib.GHOSTTY_BUILD_INFO_VERSION_MAJOR),
        version_minor=_query_size(_lib.GHOSTTY_BUILD_INFO_VERSION_MINOR),
        version_patch=_query_size(_lib.GHOSTTY_BUILD_INFO_VERSION_PATCH),
        version_pre=_query_str(_lib.GHOSTTY_BUILD_INFO_VERSION_PRE),
        version_build=_query_str(_lib.GHOSTTY_BUILD_INFO_VERSION_BUILD),
    )


GHOSTTY_COMMIT: Final[str] = _ffi.string(_lib.ghostty_vt_pinned_commit).decode("ascii")
"""The pinned upstream commit the native library was built from."""
