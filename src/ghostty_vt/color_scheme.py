"""Color scheme domain: encode color scheme reports as escape sequences.

This is the idiomatic layer over the upstream ``color_scheme`` domain. Use
:func:`encode` to build a color scheme report for color-scheme reporting mode
(mode 2031).
"""

from __future__ import annotations

import enum
from typing import Any

from ghostty_vt import _encode, _raw

__all__ = ["ColorScheme", "encode"]

_lib = _raw.lib


class ColorScheme(enum.Enum):
    """A terminal color scheme for reporting (mode 2031)."""

    LIGHT = _lib.GHOSTTY_COLOR_SCHEME_LIGHT
    DARK = _lib.GHOSTTY_COLOR_SCHEME_DARK


def encode(scheme: ColorScheme) -> bytes:
    """Encode a color scheme report for ``scheme``.

    Dark schemes emit ``ESC [ ? 997 ; 1 n`` and light schemes emit
    ``ESC [ ? 997 ; 2 n``, matching the terminal's own CSI ? 996 n query
    response.

    Args:
        scheme: The color scheme to report.

    Returns:
        The encoded escape sequence.
    """

    def call(buf: Any, buf_len: int, out: Any) -> int:
        return int(
            _lib.ghostty_color_scheme_report_encode(scheme.value, buf, buf_len, out)
        )

    return _encode.encode(call, "could not encode color scheme report")
