# shellcheck shell=bash
#
# Shared bootstrap and zig invocation for the vendoring/build scripts.
# Sourced (not executed): derives all paths from this file's location and
# exposes a single `zig_build` entry point plus the common build options, so
# the vendoring prefetch and the offline build stay in lockstep.

_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${_LIB_DIR}/.." && pwd)"

VENDOR_DIR="${REPO_ROOT}/vendor"
GHOSTTY_DIR="${VENDOR_DIR}/ghostty"
ZIG_CACHE_DIR="${VENDOR_DIR}/zig-cache"

OPTIMIZE="${ZIG_OPTIMIZE:-ReleaseFast}"

# The build option set. The prefetch (`--fetch`) and the offline build must use
# the same options: `zig build --fetch` only walks lazy dependencies reachable
# under the options it is given, so a mismatch could leave a dep unfetched and
# break the no-network build.
# `-Dcpu=baseline` pins codegen to the portable baseline for the target arch:
# zig otherwise targets the *native* host CPU, so a lib built on one machine
# (e.g. a CI runner with AVX-512) can SIGILL on another. Portability matters
# twice: CI restores cached libs across a heterogeneous runner fleet, and
# release wheels must run on any user machine. Ghostty's SIMD hot paths keep
# their speed regardless: they use Highway's runtime dispatch, which selects
# the best instruction set on the executing CPU.
# shellcheck disable=SC2034  # consumed by the scripts that source this file
ZIG_BUILD_OPTS=(
    -Demit-lib-vt=true
    -Demit-xcframework=false
    -Dcpu=baseline
    "-Doptimize=${OPTIMIZE}"
)

# Run `zig build` via the pinned `ziglang` dev dependency, from the vendored
# source, using the shared zig global cache. Extra args are passed through.
#
# The toolchain is provisioned with `uv sync --no-install-project`: it installs
# the dev dependencies (ziglang included) but skips building/installing the
# project itself. The subsequent `uv run --no-sync` then executes against that
# environment without re-syncing. Without this split, `uv run` would build the
# cffi extension as a side effect of syncing the editable install, dragging a
# full static-lib compile into the vendoring prefetch (before its deps are even
# fetched). Vendoring only needs the zig toolchain, never the extension.
zig_build() {
    uv sync --project "${REPO_ROOT}" --no-install-project --quiet
    (
        cd "${GHOSTTY_DIR}" || exit
        ZIG_GLOBAL_CACHE_DIR="${ZIG_CACHE_DIR}" \
            uv run --project "${REPO_ROOT}" --no-sync \
            python -m ziglang build "$@"
    )
}
