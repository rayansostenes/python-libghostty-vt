"""cffi out-of-line (API mode) build script for the raw layer.

This module builds ``ghostty_vt._raw``, the private, generated 1:1 binding over
the libghostty-vt C API (per ADR 0001). It is consumed by setuptools via the
``cffi_modules`` entry in ``setup.py`` and is never imported at runtime, so it is
excluded from the test-coverage scope.

The extension statically links the zig-built ``libghostty-vt`` and compiles
against the vendored upstream headers. When the static library is absent (e.g. a
clean wheel build from the sdist), it is built here with the pinned zig toolchain
from the vendored source, offline. The pinned upstream commit is read from
``ghostty-commit.txt`` and baked into the extension so the runtime value can
never drift from the artifact it was compiled against.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from cffi import FFI


def _repo_root() -> Path:
    """Locate the project root by walking up to the pinned-commit file.

    Works both in the source tree and in an unpacked sdist, where the vendored
    source and ``ghostty-commit.txt`` sit at the archive root.
    """
    for parent in Path(__file__).resolve().parents:
        if (parent / "ghostty-commit.txt").is_file():
            return parent
    raise FileNotFoundError("could not locate ghostty-commit.txt from _cffi_build.py")


ROOT = _repo_root()
VENDOR_DIR = ROOT / "vendor"
GHOSTTY_DIR = VENDOR_DIR / "ghostty"
INCLUDE_DIR = GHOSTTY_DIR / "include"
DIST_LIB_DIR = VENDOR_DIR / "dist" / "lib"
ZIG_CACHE_DIR = VENDOR_DIR / "zig-cache"

# Kept in lockstep with scripts/_lib.sh: the offline build must use the same
# options the vendoring prefetch walked, or a lazy zig dependency could be
# missing. Like _lib.sh, the optimize mode honors the ZIG_OPTIMIZE override and
# defaults to ReleaseFast.
_OPTIMIZE = os.environ.get("ZIG_OPTIMIZE", "ReleaseFast")
_ZIG_BUILD_OPTS = (
    "-Demit-lib-vt=true",
    "-Demit-xcframework=false",
    f"-Doptimize={_OPTIMIZE}",
)

# Platform-specific names of the static library emitted by upstream's build.zig.
_STATIC_LIB_NAMES = ("libghostty-vt.a", "ghostty-vt-static.lib")


def _find_static_lib() -> Path | None:
    for name in _STATIC_LIB_NAMES:
        candidate = DIST_LIB_DIR / name
        if candidate.is_file():
            return candidate
    return None


def _build_static_lib() -> Path:
    """Build the static libghostty-vt from the vendored source, offline."""
    if not GHOSTTY_DIR.is_dir():
        raise FileNotFoundError(
            f"vendored source missing at {GHOSTTY_DIR}; run 'just vendor' first"
        )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "ziglang",
            "build",
            *_ZIG_BUILD_OPTS,
            "--prefix",
            str(VENDOR_DIR / "dist"),
        ],
        cwd=GHOSTTY_DIR,
        env={**os.environ, "ZIG_GLOBAL_CACHE_DIR": str(ZIG_CACHE_DIR)},
        check=True,
    )
    lib = _find_static_lib()
    if lib is None:
        raise FileNotFoundError(
            f"static lib not found under {DIST_LIB_DIR} after zig build"
        )
    return lib


def _static_lib() -> Path:
    return _find_static_lib() or _build_static_lib()


def _pinned_commit() -> str:
    return (ROOT / "ghostty-commit.txt").read_text().strip()


def _build() -> FFI:
    ffi = FFI()
    ffi.cdef(
        """
        typedef enum {
            GHOSTTY_SUCCESS,
            GHOSTTY_OUT_OF_MEMORY,
            GHOSTTY_INVALID_VALUE,
            GHOSTTY_OUT_OF_SPACE,
            GHOSTTY_NO_VALUE,
            ...
        } GhosttyResult;

        typedef enum {
            GHOSTTY_OPTIMIZE_DEBUG,
            GHOSTTY_OPTIMIZE_RELEASE_SAFE,
            GHOSTTY_OPTIMIZE_RELEASE_SMALL,
            GHOSTTY_OPTIMIZE_RELEASE_FAST,
            ...
        } GhosttyOptimizeMode;

        typedef enum {
            GHOSTTY_BUILD_INFO_INVALID,
            GHOSTTY_BUILD_INFO_SIMD,
            GHOSTTY_BUILD_INFO_KITTY_GRAPHICS,
            GHOSTTY_BUILD_INFO_TMUX_CONTROL_MODE,
            GHOSTTY_BUILD_INFO_OPTIMIZE,
            GHOSTTY_BUILD_INFO_VERSION_STRING,
            GHOSTTY_BUILD_INFO_VERSION_MAJOR,
            GHOSTTY_BUILD_INFO_VERSION_MINOR,
            GHOSTTY_BUILD_INFO_VERSION_PATCH,
            GHOSTTY_BUILD_INFO_VERSION_PRE,
            GHOSTTY_BUILD_INFO_VERSION_BUILD,
            ...
        } GhosttyBuildInfo;

        typedef struct {
            const uint8_t* ptr;
            size_t len;
        } GhosttyString;

        GhosttyResult ghostty_build_info(GhosttyBuildInfo data, void *out);

        extern const char *const ghostty_vt_pinned_commit;
        """
    )
    commit = _pinned_commit()
    ffi.set_source(
        "ghostty_vt._raw",
        f"""
        #define GHOSTTY_STATIC
        #include <ghostty/vt.h>

        static const char *const ghostty_vt_pinned_commit = "{commit}";
        """,
        include_dirs=[str(INCLUDE_DIR)],
        extra_objects=[str(_static_lib())],
        # No abi3: cffi API mode targets a specific CPython (cp314 only), per the
        # v0.1 spec. Left on, cffi's setuptools hook would build a limited-API
        # (.abi3) extension.
        py_limited_api=False,
    )
    return ffi


ffibuilder = _build()


if __name__ == "__main__":
    ffibuilder.compile(verbose=True)
