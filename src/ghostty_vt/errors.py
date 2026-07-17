"""Error domain: the exception hierarchy for the idiomatic layer.

Every fallible operation in ``ghostty_vt`` reports failure by raising a
:class:`GhosttyVtError` subclass, never by letting a raw C result code or a cffi
error leak to the caller. The specific subclass mirrors the underlying
``GhosttyResult`` value so callers can distinguish failure modes while still
catching the common base.

The mapping from result codes to these classes lives in the private
``ghostty_vt._result`` helper; domains call it instead of inspecting result codes
by hand.
"""

from __future__ import annotations

__all__ = [
    "GhosttyVtError",
    "InvalidValueError",
    "NoValueError",
    "OutOfMemoryError",
    "OutOfSpaceError",
]


class GhosttyVtError(Exception):
    """Base class for every error raised by the ``ghostty_vt`` idiomatic layer."""


class OutOfMemoryError(GhosttyVtError, MemoryError):
    """libghostty-vt failed to allocate memory (``GHOSTTY_OUT_OF_MEMORY``)."""


class InvalidValueError(GhosttyVtError, ValueError):
    """An argument was rejected by libghostty-vt (``GHOSTTY_INVALID_VALUE``)."""


class OutOfSpaceError(GhosttyVtError):
    """A caller-provided buffer was too small (``GHOSTTY_OUT_OF_SPACE``)."""


class NoValueError(GhosttyVtError):
    """The requested value was not available (``GHOSTTY_NO_VALUE``)."""
