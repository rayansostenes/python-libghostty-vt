# Positive typesafety pins for the size report domain.
#
# Never executed: every line is a compile-time assertion. `assert_type` pins the
# encoder's return type; the enum members are pinned by annotated bindings (a
# member access infers the singleton literal, not the enum). This file must be
# diagnostic-free under every checker.
from __future__ import annotations

from typing import assert_type

import ghostty_vt
from ghostty_vt import SizeReportStyle
from ghostty_vt.size_report import encode

# Encoding a size report yields pty bytes.
assert_type(
    encode(SizeReportStyle.MODE_2048, rows=24, columns=80, cell_width=10, cell_height=20),
    bytes,
)

# Every style member is assignable to the enum type; dropping any one turns the
# suite red.
_mode_2048: SizeReportStyle = SizeReportStyle.MODE_2048
_csi_14_t: SizeReportStyle = SizeReportStyle.CSI_14_T
_csi_16_t: SizeReportStyle = SizeReportStyle.CSI_16_T
_csi_18_t: SizeReportStyle = SizeReportStyle.CSI_18_T

# The top-level re-export is the same enum type.
_top: SizeReportStyle = ghostty_vt.SizeReportStyle.MODE_2048
