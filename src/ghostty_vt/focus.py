"""Focus domain: encode focus in/out events as escape sequences.

This is the idiomatic layer over the upstream ``focus`` domain. Use
:func:`encode` to build a focus report for focus reporting mode (mode 1004).
"""

from __future__ import annotations

import enum
from typing import Any

from ghostty_vt import _encode, _raw

__all__ = ["FocusEvent", "encode"]

_lib = _raw.lib


class FocusEvent(enum.Enum):
    """A focus change for focus reporting (mode 1004)."""

    GAINED = _lib.GHOSTTY_FOCUS_GAINED
    LOST = _lib.GHOSTTY_FOCUS_LOST


def encode(event: FocusEvent) -> bytes:
    """Encode a focus report for ``event``.

    Focus gained emits ``ESC [ I`` and focus lost emits ``ESC [ O``.

    Args:
        event: The focus change to report.

    Returns:
        The encoded escape sequence.
    """

    def call(buf: Any, buf_len: int, out: Any) -> int:
        return int(_lib.ghostty_focus_encode(event.value, buf, buf_len, out))

    return _encode.encode(call, "could not encode focus event")
