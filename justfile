set shell := ["bash", "-uc"]

# List available recipes.
default:
    @just --list

# Sync the dev environment (Python 3.14+, pinned zig via ziglang).
setup:
    uv sync

# Fetch upstream at the pinned commit and prefetch zig deps (needs network).
vendor:
    ./scripts/fetch-vendor.sh

# Build the static libghostty-vt from the vendored source (offline).
build-lib:
    ./scripts/build-libghostty-vt.sh

# Regenerate the raw-layer cdef from the vendored headers (needs `just vendor`).
gen-cdef:
    PYTHONPATH=tools uv run python -m gen_cdef

# Build the raw-layer cffi extension in place (builds the static lib if absent).
build:
    uv run python setup.py build_ext --inplace

# Check the built raw layer covers every exported vt header symbol (needs `just build`).
completeness:
    PYTHONPATH=tools uv run python -m gen_cdef.completeness

# Lint with ruff.
lint:
    uv run ruff check

# Format with ruff.
fmt:
    uv run ruff format

# Check formatting without writing changes (CI).
fmt-check:
    uv run ruff format --check

# Type-check the source and tests with mypy (strict).
mypy:
    uv run mypy

# Type-check the source and tests with pyright (strict).
pyright:
    uv run pyright

# Run both strict type checkers over source and tests.
typecheck: mypy pyright

# Run the test suite.
test:
    uv run pytest

# Remove vendored source and build outputs.
clean:
    rm -rf vendor build dist src/*.egg-info
    rm -f src/ghostty_vt/_raw*.so src/ghostty_vt/_raw*.pyd
