set shell := ["bash", "-uc"]

# List available recipes.
default:
    @just --list

# Sync the dev environment (Python 3.14+, pinned zig via ziglang).
setup:
    uv sync

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
