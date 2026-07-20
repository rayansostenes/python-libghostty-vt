#!/usr/bin/env bash
#
# Vendor upstream libghostty-vt at the pinned commit and populate the zig
# package cache, so that the static libghostty-vt can subsequently be built
# with no network access.
#
# The vendored source is NOT the full Ghostty tree: the upstream checkout is
# only an intermediate. Upstream's own `zig build dist -Demit-lib-vt=true`
# produces a libghostty-vt-only source tarball (its GhosttyDist step maintains
# the canonical list of app-only paths to exclude), and that tarball is what
# lands in vendor/ghostty. This keeps the vendored tree and the sdist small
# without maintaining our own exclusion list.
#
# The zig package cache is populated by real per-target builds, not by
# `zig build --fetch`: ghostty's dependencies are lazy, and a fetch-only pass
# resolves just the eager ones, so only an actual build walks the full set a
# target needs. Each populating build doubles as proof that the vendored tree
# builds for that target. Targets are passed as arguments; with none, only the
# host is built (its static lib is kept, so a later `just build` skips the zig
# compile). Wheel CI passes extra targets whose builds run hermetically from
# this cache (e.g. the musllinux containers). Windows is best-effort (its C++
# deps do not cross-compile), so a failing windows build still contributes its
# fetched dependencies but never fails the vendoring.
#
# The pinned commit lives in exactly one place: ghostty-commit.txt.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/_lib.sh
source "${SCRIPT_DIR}/_lib.sh"

UPSTREAM_URL="${GHOSTTY_UPSTREAM_URL:-https://github.com/ghostty-org/ghostty}"
COMMIT="$(tr -d '[:space:]' < "${REPO_ROOT}/ghostty-commit.txt")"
CHECKOUT_DIR="${VENDOR_DIR}/checkout"

if [[ -z "${COMMIT}" ]]; then
    echo "error: ghostty-commit.txt is empty" >&2
    exit 1
fi

echo ">> Fetching ${UPSTREAM_URL} at ${COMMIT}"
# Invalidate any previously built static lib: it was linked against the old
# vendored source, and the cffi build shim reuses a cached lib without
# rebuilding, so a stale one would be linked against the freshly fetched commit.
rm -rf "${CHECKOUT_DIR}" "${VENDOR_DIR}/dist"
mkdir -p "${CHECKOUT_DIR}"
git -C "${CHECKOUT_DIR}" init -q
git -C "${CHECKOUT_DIR}" remote add origin "${UPSTREAM_URL}"
git -C "${CHECKOUT_DIR}" fetch -q --depth 1 origin "${COMMIT}"
git -C "${CHECKOUT_DIR}" -c advice.detachedHead=false checkout -q FETCH_HEAD

echo ">> Packaging the libghostty-vt-only source (upstream dist tarball)"
zig_build "${CHECKOUT_DIR}" dist "${ZIG_BUILD_OPTS[@]}" \
    --prefix "${CHECKOUT_DIR}/zig-out"
TARBALLS=("${CHECKOUT_DIR}"/zig-out/dist/libghostty-vt-*.tar.gz)
if [[ ${#TARBALLS[@]} -ne 1 || ! -f "${TARBALLS[0]}" ]]; then
    echo "error: expected exactly one libghostty-vt dist tarball" >&2
    exit 1
fi

rm -rf "${GHOSTTY_DIR}"
mkdir -p "${GHOSTTY_DIR}"
tar -xzf "${TARBALLS[0]}" -C "${GHOSTTY_DIR}" --strip-components 1
rm -rf "${CHECKOUT_DIR}"

# Retain upstream's license notice alongside the vendored source.
if [[ ! -f "${GHOSTTY_DIR}/LICENSE" ]]; then
    echo "error: upstream LICENSE missing from vendored source" >&2
    exit 1
fi
echo ">> Upstream license retained at vendor/ghostty/LICENSE"

# Populate the zig package cache and validate the vendored tree, one real
# build per requested target. The host build installs into vendor/dist so its
# static lib is immediately usable; cross builds install into a scratch prefix
# that is discarded.
echo ">> Building libghostty-vt for the host (populates the zig cache)"
zig_build "${GHOSTTY_DIR}" "${ZIG_BUILD_OPTS[@]}" --prefix "${VENDOR_DIR}/dist"

for target in "$@"; do
    scratch="${VENDOR_DIR}/cross-out"
    rm -rf "${scratch}"
    if [[ "${target}" == *windows* ]]; then
        echo ">> Building libghostty-vt for ${target} (best-effort)"
        zig_build "${GHOSTTY_DIR}" "${ZIG_BUILD_OPTS[@]}" \
            "-Dtarget=${target}" --prefix "${scratch}" \
            || echo ">> warning: ${target} build failed (best-effort target)"
    else
        echo ">> Building libghostty-vt for ${target}"
        zig_build "${GHOSTTY_DIR}" "${ZIG_BUILD_OPTS[@]}" \
            "-Dtarget=${target}" --prefix "${scratch}"
    fi
    rm -rf "${scratch}"
done

echo ">> Vendored source ready at vendor/ghostty (commit ${COMMIT})"
