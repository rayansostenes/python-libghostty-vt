# shellcheck shell=bash
#
# Shared bootstrap and zig invocation for the vendoring/build scripts.
# Sourced (not executed): derives all paths from this file's location and
# exposes a single `zig_build` entry point plus the common build options, so
# the vendoring prefetch and the offline build stay in lockstep.

_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${_LIB_DIR}/.." && pwd)"

VENDOR_DIR="${REPO_ROOT}/vendor"
# shellcheck disable=SC2034  # consumed by the scripts that source this file
GHOSTTY_DIR="${VENDOR_DIR}/ghostty"
ZIG_CACHE_DIR="${VENDOR_DIR}/zig-cache"

OPTIMIZE="${ZIG_OPTIMIZE:-ReleaseFast}"

# The build option set. The cache-populating builds in fetch-vendor.sh and the
# offline build must use the same options: zig only fetches the lazy
# dependencies reachable under the options a build is given, so a mismatch
# could leave a dep unfetched and break the no-network build.
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

# Run `zig build` via the pinned `ziglang` dev dependency, from the source
# tree given as the first argument, using the shared zig global cache. The
# remaining args are passed through. The tree is a parameter because vendoring
# runs zig from two different trees: `dist` from the full upstream checkout,
# then the cache-populating builds from the trimmed vendored source.
#
# The toolchain is provisioned with `uv sync --no-install-project`: it installs
# the dev dependencies (ziglang included) but skips building/installing the
# project itself. The subsequent `uv run --no-sync` then executes against that
# environment without re-syncing. Without this split, `uv run` would build the
# cffi extension as a side effect of syncing the editable install, dragging a
# full static-lib compile into the vendoring prefetch (before its deps are even
# fetched). Vendoring only needs the zig toolchain, never the extension.
zig_build() {
    local src_dir="$1"
    shift
    uv sync --project "${REPO_ROOT}" --no-install-project --quiet
    (
        cd "${src_dir}" || exit
        ZIG_GLOBAL_CACHE_DIR="${ZIG_CACHE_DIR}" \
            uv run --project "${REPO_ROOT}" --no-sync \
            python -m ziglang build "$@"
    )
}
