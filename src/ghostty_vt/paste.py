"""Paste domain: safety checks and pty encoding for clipboard content.

This is the idiomatic layer over the upstream ``paste`` domain. Use
:func:`is_safe` to decide whether pasting content verbatim is dangerous, and
:func:`encode` to prepare content for writing to a terminal pty, with or without
bracketed-paste wrapping.
"""

from __future__ import annotations

from typing import Any

from ghostty_vt import _encode, _raw

__all__ = ["encode", "is_safe"]

_ffi = _raw.ffi
_lib = _raw.lib


def is_safe(data: str) -> bool:
    """Report whether ``data`` is safe to paste into a terminal verbatim.

    Data is unsafe when it contains a newline (which could inject a command) or
    the bracketed-paste end sequence ``ESC [ 201 ~`` (which could break out of
    bracketed paste to inject commands). The check is conservative and
    independent of the terminal's current state.
    """
    raw = data.encode("utf-8")
    return bool(_lib.ghostty_paste_is_safe(raw, len(raw)))


def encode(data: str, *, bracketed: bool) -> bytes:
    """Encode ``data`` for writing to a terminal pty.

    Unsafe control bytes (NUL, ESC, DEL, and the like) are replaced with spaces.
    When ``bracketed`` is true the result is wrapped in the bracketed-paste
    start and end sequences; otherwise newlines are replaced with carriage
    returns.

    Args:
        data: The clipboard content to encode.
        bracketed: Whether bracketed paste mode is active.

    Returns:
        The bytes to write to the pty.
    """
    raw = data.encode("utf-8")

    def call(buf: Any, buf_len: int, out: Any) -> int:
        # A fresh copy per call: the raw encoder rewrites its input in place, so
        # the sizing and writing passes must each start from the original bytes.
        mutable = _ffi.new("char[]", raw)
        return int(
            _lib.ghostty_paste_encode(mutable, len(raw), bracketed, buf, buf_len, out)
        )

    return _encode.encode(call, "could not encode paste data")
