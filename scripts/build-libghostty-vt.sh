#!/usr/bin/env bash
#
# Build the static libghostty-vt from the vendored source using the pinned zig
# toolchain (provided by the `ziglang` dev dependency). Runs with no network
# access: all zig dependencies must already be present in vendor/zig-cache,
# populated by scripts/fetch-vendor.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/_lib.sh
source "${SCRIPT_DIR}/_lib.sh"

OUT_DIR="${VENDOR_DIR}/dist"

if [[ ! -d "${GHOSTTY_DIR}" ]]; then
    echo "error: vendored source missing; run 'just vendor' first" >&2
    exit 1
fi

echo ">> Building static libghostty-vt (optimize=${OPTIMIZE})"
rm -rf "${OUT_DIR}"
zig_build "${ZIG_BUILD_OPTS[@]}" --prefix "${OUT_DIR}"

# The static lib is named per platform: on Windows it is renamed to avoid
# colliding with the DLL import library (see upstream build.zig).
LIB=""
for candidate in libghostty-vt.a ghostty-vt-static.lib; do
    if [[ -f "${OUT_DIR}/lib/${candidate}" ]]; then
        LIB="${OUT_DIR}/lib/${candidate}"
        break
    fi
done
if [[ -z "${LIB}" ]]; then
    echo "error: expected static lib not found under ${OUT_DIR}/lib" >&2
    exit 1
fi
echo ">> Built ${LIB}"
