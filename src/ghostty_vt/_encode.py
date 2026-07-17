"""Private helper for the two-pass buffer-encoding protocol.

The encode-only domains (paste, size report, color scheme, focus) all share the
upstream contract: call once with an empty buffer to learn the required size,
then again with a buffer of that size, treating ``GHOSTTY_OUT_OF_SPACE`` from the
sizing pass as expected rather than an error. This wraps that dance so each
domain issues its raw call the same way instead of re-deriving the retry.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ghostty_vt import _raw, _result

_ffi = _raw.ffi
_lib = _raw.lib

Encoder = Callable[[Any, int, Any], int]


def encode(call: Encoder, message: str) -> bytes:
    """Run ``call`` under the size-probe/retry protocol and return the result.

    ``call`` receives ``(buf, buf_len, out_written)`` and returns a raw
    ``GhosttyResult``. It is invoked first with an empty buffer so the library
    reports the required size, then again with a buffer of exactly that size.

    Args:
        call: The raw encode invocation to drive.
        message: The error message for a non-success result.

    Returns:
        The encoded bytes (empty when the encoding is empty).

    Raises:
        GhosttyVtError: If the raw call reports a failure other than the
            expected out-of-space during sizing.
    """
    out_written = _ffi.new("size_t *")
    result = call(_ffi.NULL, 0, out_written)
    if result == _lib.GHOSTTY_OUT_OF_SPACE:
        size = out_written[0]
        buf = _ffi.new(f"char[{size}]")
        result = call(buf, size, out_written)
        _result.check(result, message)
        return bytes(_ffi.buffer(buf, out_written[0]))
    _result.check(result, message)
    return b""
