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

# Build the raw-layer cffi extension in place (builds the static lib if absent).
build:
    uv run python setup.py build_ext --inplace

# Lint with ruff.
lint:
    uv run ruff check

# Format with ruff.
fmt:
    uv run ruff format

# Check formatting without writing changes (CI).
fmt-check:
    uv run ruff format --check

# Run the test suite.
test:
    uv run pytest

# Remove vendored source and build outputs.
clean:
    rm -rf vendor build dist src/*.egg-info
    rm -f src/ghostty_vt/_raw*.so src/ghostty_vt/_raw*.pyd
