"""Tests for the error hierarchy and the result-code mapping.

The hierarchy relationships are the public contract callers write ``except``
clauses against. The mapping from native result codes to exceptions is driven
through the private ``_result.check`` helper directly: only some codes are
reachable through any single domain's public API, so this white-box guard pins
the whole table (mirroring ``test_query_errors.py``).
"""

from __future__ import annotations

import pytest

from ghostty_vt import (  # pyright: ignore[reportPrivateUsage]
    GhosttyVtError,
    InvalidValueError,
    NoValueError,
    OutOfMemoryError,
    OutOfSpaceError,
    _raw,
    _result,
)

_lib = _raw.lib

SPECIFIC_ERRORS = [
    InvalidValueError,
    OutOfMemoryError,
    OutOfSpaceError,
    NoValueError,
]


@pytest.mark.parametrize("error_type", SPECIFIC_ERRORS)
def test_specific_errors_derive_from_the_root(
    error_type: type[GhosttyVtError],
) -> None:
    assert issubclass(error_type, GhosttyVtError)


def test_invalid_value_error_is_also_a_value_error() -> None:
    assert issubclass(InvalidValueError, ValueError)


def test_out_of_memory_error_is_also_a_memory_error() -> None:
    assert issubclass(OutOfMemoryError, MemoryError)


def test_check_passes_on_success() -> None:
    _result.check(_lib.GHOSTTY_SUCCESS, "must not raise")


@pytest.mark.parametrize(
    ("code", "error_type"),
    [
        (_lib.GHOSTTY_OUT_OF_MEMORY, OutOfMemoryError),
        (_lib.GHOSTTY_INVALID_VALUE, InvalidValueError),
        (_lib.GHOSTTY_OUT_OF_SPACE, OutOfSpaceError),
        (_lib.GHOSTTY_NO_VALUE, NoValueError),
    ],
)
def test_check_maps_each_result_code(
    code: int, error_type: type[GhosttyVtError]
) -> None:
    with pytest.raises(error_type, match="boom"):
        _result.check(code, "boom")


def test_check_falls_back_to_the_root_error_for_an_unknown_code() -> None:
    # A code with no dedicated class still raises within the hierarchy rather
    # than leaking a bare result value.
    with pytest.raises(GhosttyVtError):
        _result.check(-999, "unknown result")
