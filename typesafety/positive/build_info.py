# Positive typesafety pins for the build_info domain.
#
# Never executed: every line is a compile-time assertion. `assert_type` pins the
# type a checker infers for each public expression, so any drift in the idiomatic
# layer's public types turns the suite red. This file must be diagnostic-free
# under every checker.
from __future__ import annotations

from typing import assert_type

import ghostty_vt
from ghostty_vt import BuildInfo, OptimizeMode, build_info

# The query returns the public BuildInfo dataclass.
info = build_info()
assert_type(info, BuildInfo)

# Each field carries its documented type.
assert_type(info.simd, bool)
assert_type(info.kitty_graphics, bool)
assert_type(info.tmux_control_mode, bool)
assert_type(info.optimize, OptimizeMode)
assert_type(info.version, str)
assert_type(info.version_major, int)
assert_type(info.version_minor, int)
assert_type(info.version_patch, int)
assert_type(info.version_pre, str)
assert_type(info.version_build, str)

# The constructor's keyword signature is part of the public surface.
constructed = BuildInfo(
    simd=True,
    kitty_graphics=False,
    tmux_control_mode=False,
    optimize=OptimizeMode.RELEASE_FAST,
    version="1.0.0",
    version_major=1,
    version_minor=0,
    version_patch=0,
    version_pre="",
    version_build="",
)
assert_type(constructed, BuildInfo)

# Every enum member is assignable to the enum type. The annotated binding is the
# pin: it fails to check if a member is not an OptimizeMode, and removing or
# renaming any member makes the access an error. (A direct
# `assert_type(OptimizeMode.RELEASE_FAST, OptimizeMode)` would wrongly fail —
# checkers infer the singleton literal type for a member access.) Pinning all
# four members means dropping any one turns the suite red.
_debug: OptimizeMode = OptimizeMode.DEBUG
_release_safe: OptimizeMode = OptimizeMode.RELEASE_SAFE
_release_small: OptimizeMode = OptimizeMode.RELEASE_SMALL
_release_fast: OptimizeMode = OptimizeMode.RELEASE_FAST

# Top-level re-exported constants.
assert_type(ghostty_vt.GHOSTTY_COMMIT, str)
assert_type(ghostty_vt.__version__, str)
