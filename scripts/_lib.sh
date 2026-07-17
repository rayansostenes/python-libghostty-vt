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
# shellcheck disable=SC2034  # consumed by the scripts that source this file
ZIG_BUILD_OPTS=(
    -Demit-lib-vt=true
    -Demit-xcframework=false
    "-Doptimize=${OPTIMIZE}"
)

# Run `zig build` via the pinned `ziglang` dev dependency, from the vendored
# source, using the shared zig global cache. Extra args are passed through.
zig_build() {
    (
        cd "${GHOSTTY_DIR}" || exit
        ZIG_GLOBAL_CACHE_DIR="${ZIG_CACHE_DIR}" \
            uv run --project "${REPO_ROOT}" python -m ziglang build "$@"
    )
}
