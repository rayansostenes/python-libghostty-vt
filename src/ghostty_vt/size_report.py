"""Size report domain: encode terminal size reports as escape sequences.

This is the idiomatic layer over the upstream ``size_report`` domain. Use
:func:`encode` to build an in-band size report (mode 2048) or an XTWINOPS
response (CSI 14 t, CSI 16 t, CSI 18 t) for writing to a terminal pty.
"""

from __future__ import annotations

import enum
from typing import Any

from ghostty_vt import _encode, _raw

__all__ = ["SizeReportStyle", "encode"]

_ffi = _raw.ffi
_lib = _raw.lib

_U16_MAX = 0xFFFF
_U32_MAX = 0xFFFFFFFF


class SizeReportStyle(enum.Enum):
    """The output format for a size report."""

    MODE_2048 = _lib.GHOSTTY_SIZE_REPORT_MODE_2048
    """In-band size report (mode 2048): rows, columns, and pixel size."""

    CSI_14_T = _lib.GHOSTTY_SIZE_REPORT_CSI_14_T
    """XTWINOPS text-area size in pixels."""

    CSI_16_T = _lib.GHOSTTY_SIZE_REPORT_CSI_16_T
    """XTWINOPS cell size in pixels."""

    CSI_18_T = _lib.GHOSTTY_SIZE_REPORT_CSI_18_T
    """XTWINOPS text-area size in characters."""


def _check_range(name: str, value: int, maximum: int) -> None:
    if not 0 <= value <= maximum:
        raise ValueError(f"{name} out of range (0-{maximum}): {value}")


def encode(
    style: SizeReportStyle,
    *,
    rows: int,
    columns: int,
    cell_width: int,
    cell_height: int,
) -> bytes:
    """Encode a terminal size report in the format given by ``style``.

    Args:
        style: The report format to emit.
        rows: Terminal row count in cells (0-65535).
        columns: Terminal column count in cells (0-65535).
        cell_width: Width of a single cell in pixels (0-4294967295).
        cell_height: Height of a single cell in pixels (0-4294967295).

    Returns:
        The encoded escape sequence.

    Raises:
        ValueError: If any field is outside its valid range.
    """
    _check_range("rows", rows, _U16_MAX)
    _check_range("columns", columns, _U16_MAX)
    _check_range("cell_width", cell_width, _U32_MAX)
    _check_range("cell_height", cell_height, _U32_MAX)
    size = _ffi.new(
        "GhosttySizeReportSize *",
        {
            "rows": rows,
            "columns": columns,
            "cell_width": cell_width,
            "cell_height": cell_height,
        },
    )

    def call(buf: Any, buf_len: int, out: Any) -> int:
        return int(
            _lib.ghostty_size_report_encode(style.value, size[0], buf, buf_len, out)
        )

    return _encode.encode(call, "could not encode size report")
