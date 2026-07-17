#!/usr/bin/env bash
#
# Fetch the upstream Ghostty source at the pinned commit into the vendored
# source location and prefetch its zig build dependencies, so that the static
# libghostty-vt can subsequently be built with no network access.
#
# The pinned commit lives in exactly one place: ghostty-commit.txt.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/_lib.sh
source "${SCRIPT_DIR}/_lib.sh"

UPSTREAM_URL="${GHOSTTY_UPSTREAM_URL:-https://github.com/ghostty-org/ghostty}"
COMMIT="$(tr -d '[:space:]' < "${REPO_ROOT}/ghostty-commit.txt")"

if [[ -z "${COMMIT}" ]]; then
    echo "error: ghostty-commit.txt is empty" >&2
    exit 1
fi

echo ">> Fetching ${UPSTREAM_URL} at ${COMMIT}"
rm -rf "${GHOSTTY_DIR}"
mkdir -p "${GHOSTTY_DIR}"
git -C "${GHOSTTY_DIR}" init -q
git -C "${GHOSTTY_DIR}" remote add origin "${UPSTREAM_URL}"
git -C "${GHOSTTY_DIR}" fetch -q --depth 1 origin "${COMMIT}"
git -C "${GHOSTTY_DIR}" -c advice.detachedHead=false checkout -q FETCH_HEAD

# Retain upstream's license notice alongside the vendored source.
if [[ ! -f "${GHOSTTY_DIR}/LICENSE" ]]; then
    echo "error: upstream LICENSE missing from vendored source" >&2
    exit 1
fi
echo ">> Upstream license retained at vendor/ghostty/LICENSE"

echo ">> Prefetching zig build dependencies into vendor/zig-cache"
zig_build --fetch "${ZIG_BUILD_OPTS[@]}"

echo ">> Vendored source ready at vendor/ghostty (commit ${COMMIT})"
