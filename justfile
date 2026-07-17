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
build:
    ./scripts/build-libghostty-vt.sh

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
    rm -rf vendor
