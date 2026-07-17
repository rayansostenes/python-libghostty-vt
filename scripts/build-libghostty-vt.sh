#!/usr/bin/env bash
#
# Build the static libghostty-vt from the vendored source using the pinned zig
# toolchain (provided by the `ziglang` dev dependency). Runs with no network
# access: all zig dependencies must already be present in vendor/zig-cache,
# populated by scripts/fetch-vendor.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

VENDOR_DIR="${REPO_ROOT}/vendor"
GHOSTTY_DIR="${VENDOR_DIR}/ghostty"
ZIG_CACHE_DIR="${VENDOR_DIR}/zig-cache"
OUT_DIR="${VENDOR_DIR}/dist"

OPTIMIZE="${ZIG_OPTIMIZE:-ReleaseFast}"

if [[ ! -d "${GHOSTTY_DIR}" ]]; then
    echo "error: vendored source missing; run 'just vendor' first" >&2
    exit 1
fi

echo ">> Building static libghostty-vt (optimize=${OPTIMIZE})"
rm -rf "${OUT_DIR}"
(
    cd "${GHOSTTY_DIR}"
    ZIG_GLOBAL_CACHE_DIR="${ZIG_CACHE_DIR}" \
        uv run --project "${REPO_ROOT}" python -m ziglang build \
        -Demit-lib-vt=true \
        -Demit-xcframework=false \
        "-Doptimize=${OPTIMIZE}" \
        --global-cache-dir "${ZIG_CACHE_DIR}" \
        --prefix "${OUT_DIR}"
)

LIB="${OUT_DIR}/lib/libghostty-vt.a"
if [[ ! -f "${LIB}" ]]; then
    echo "error: expected static lib not found at ${LIB}" >&2
    exit 1
fi
echo ">> Built ${LIB}"
