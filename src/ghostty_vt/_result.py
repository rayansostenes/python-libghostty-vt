"""Private helper mapping ``GhosttyResult`` codes to the error hierarchy.

Domains call :func:`check` after every fallible raw call so a non-success result
becomes the matching :class:`~ghostty_vt.errors.GhosttyVtError` subclass instead
of a bare C result code. Keeping the mapping here means each domain wraps its
raw calls the same way without redefining the table.
"""

from __future__ import annotations

from ghostty_vt import _raw
from ghostty_vt.errors import (
    GhosttyVtError,
    InvalidValueError,
    NoValueError,
    OutOfMemoryError,
    OutOfSpaceError,
)

_lib = _raw.lib

_RESULT_ERRORS: dict[int, type[GhosttyVtError]] = {
    _lib.GHOSTTY_OUT_OF_MEMORY: OutOfMemoryError,
    _lib.GHOSTTY_INVALID_VALUE: InvalidValueError,
    _lib.GHOSTTY_OUT_OF_SPACE: OutOfSpaceError,
    _lib.GHOSTTY_NO_VALUE: NoValueError,
}


def check(result: int, message: str) -> None:
    """Raise the mapped :class:`GhosttyVtError` for a non-success result.

    A ``GHOSTTY_SUCCESS`` result returns without raising. Any other code raises
    its specific subclass, falling back to the :class:`GhosttyVtError` base for a
    code with no dedicated class.
    """
    if result == _lib.GHOSTTY_SUCCESS:
        return
    raise _RESULT_ERRORS.get(result, GhosttyVtError)(message)
