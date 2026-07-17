# Positive typesafety pins for the errors domain.
#
# Never executed: every line is a compile-time assertion. The exception hierarchy
# is the public contract callers write `except` clauses against, so each
# relationship is pinned by an annotated binding — assignable to the root, and to
# the standard-library base the specific error mixes in. This file must be
# diagnostic-free under every checker.
from __future__ import annotations

from typing import assert_type

from ghostty_vt import (
    GhosttyVtError,
    InvalidValueError,
    NoValueError,
    OutOfMemoryError,
    OutOfSpaceError,
    UseAfterCloseError,
)

# Constructing the root error yields the root type.
assert_type(GhosttyVtError("boom"), GhosttyVtError)

# Every specific error is a GhosttyVtError.
_invalid: GhosttyVtError = InvalidValueError()
_out_of_memory: GhosttyVtError = OutOfMemoryError()
_out_of_space: GhosttyVtError = OutOfSpaceError()
_no_value: GhosttyVtError = NoValueError()
_use_after_close: GhosttyVtError = UseAfterCloseError()

# The mixed-in standard-library bases are part of the public contract.
_as_value_error: ValueError = InvalidValueError()
_as_memory_error: MemoryError = OutOfMemoryError()
