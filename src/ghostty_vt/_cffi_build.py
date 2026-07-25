"""cffi out-of-line (API mode) build script for the raw layer.

This module builds ``ghostty_vt._raw``, the private, generated 1:1 binding over
the libghostty-vt C API (per ADR 0001). It is consumed by setuptools via the
``cffi_modules`` entry in ``setup.py`` and is never imported at runtime, so it is
excluded from the test-coverage scope.

The extension statically links the zig-built ``libghostty-vt`` and compiles
against the vendored upstream headers. When the static library is absent (e.g. a
clean wheel build from the sdist), it is built here with the pinned zig toolchain
from the vendored source — hermetically when the zig package cache is populated
(see ``_build_static_lib``). The pinned upstream commit is read from
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
# The cdef consumed here is generated from the vendored headers by
# tools/gen_cdef (regenerated with `just gen-cdef`); it sits next to this build
# script so it ships in the sdist and is available for offline wheel builds.
CDEF_FILE = Path(__file__).resolve().parent / "_cdef.h"
VENDOR_DIR = ROOT / "vendor"
GHOSTTY_DIR = VENDOR_DIR / "ghostty"
INCLUDE_DIR = GHOSTTY_DIR / "include"
DIST_LIB_DIR = VENDOR_DIR / "dist" / "lib"
ZIG_CACHE_DIR = VENDOR_DIR / "zig-cache"

# Kept in lockstep with scripts/_lib.sh: the offline build must use the same
# options as the cache-populating builds in fetch-vendor.sh, or a lazy zig
# dependency could be missing. Like _lib.sh, the optimize mode honors the
# ZIG_OPTIMIZE override and defaults to ReleaseFast.
# `-Dcpu=baseline` (as in _lib.sh) pins codegen to the portable baseline for
# the target arch instead of the build host's native CPU, so cached CI libs and
# release wheels run on any machine of that arch. Ghostty's SIMD hot paths are
# unaffected: they runtime-dispatch via Highway to the executing CPU.
_OPTIMIZE = os.environ.get("ZIG_OPTIMIZE", "ReleaseFast")
_ZIG_BUILD_OPTS = (
    "-Demit-lib-vt=true",
    "-Demit-xcframework=false",
    "-Dcpu=baseline",
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
    # With a populated package cache (a repo checkout after `just vendor`, or
    # CI where cibuildwheel copies vendor/ into the build environment),
    # --system disables zig's fetching entirely: the build is hermetic and a
    # missing dependency fails loudly instead of silently reaching for the
    # network. From a bare sdist there is no cache (bundling it would exceed
    # PyPI size limits), so zig fetches the build.zig.zon-pinned,
    # hash-verified dependencies over the network instead.
    package_cache = ZIG_CACHE_DIR / "p"
    system_mode = ["--system", str(package_cache)] if package_cache.is_dir() else []
    subprocess.run(
        [
            sys.executable,
            "-m",
            "ziglang",
            "build",
            *system_mode,
            *_ZIG_BUILD_OPTS,
            "--prefix",
            str(VENDOR_DIR / "dist"),
        ],
        cwd=GHOSTTY_DIR,
        env={
            **os.environ,
            "ZIG_GLOBAL_CACHE_DIR": str(ZIG_CACHE_DIR),
            # The vendored tree is a tarball export, not a git repo: upstream's
            # version detection would walk up into whatever repo contains the
            # build (this one, or a user's own) and misread its tags — a v*
            # tag trips build.zig's tagged-release check. An invalid GIT_DIR
            # makes that detection fail cleanly into its dev fallback.
            "GIT_DIR": str(GHOSTTY_DIR / ".git-none"),
        },
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
    # The upstream surface comes from the generated cdef; the pinned-commit
    # symbol below is our own injected constant (not an upstream declaration),
    # so it stays hand-written here.
    ffi.cdef(CDEF_FILE.read_text())
    ffi.cdef("extern const char *const ghostty_vt_pinned_commit;")
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
        # The static lib uses POSIX shared memory; on the manylinux glibc
        # baselines (< 2.34) shm_open/shm_unlink live in librt, not libc.
        # Harmless elsewhere on Linux: modern glibc ships librt as a shim and
        # musl as an empty stub. macOS has no librt (shm_* are in libc).
        libraries=["rt"] if sys.platform == "linux" else [],
        # No abi3: cffi API mode targets a specific CPython (cp314 only), per the
        # v0.1 spec. Left on, cffi's setuptools hook would build a limited-API
        # (.abi3) extension.
        py_limited_api=False,
    )
    return ffi


ffibuilder = _build()


if __name__ == "__main__":
    ffibuilder.compile(verbose=True)
