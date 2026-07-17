"""Behavioral tests for the size report domain, through the public API.

Assertions pin the exact escape sequences the native library emits across the
full cffi path, as a pty consumer would receive them.
"""

from __future__ import annotations

import pytest

from ghostty_vt import SizeReportStyle, size_report


def test_styles_are_distinct() -> None:
    styles = {
        SizeReportStyle.MODE_2048,
        SizeReportStyle.CSI_14_T,
        SizeReportStyle.CSI_16_T,
        SizeReportStyle.CSI_18_T,
    }
    assert len(styles) == 4


def test_mode_2048_reports_rows_columns_and_pixels() -> None:
    encoded = size_report.encode(
        SizeReportStyle.MODE_2048,
        rows=24,
        columns=80,
        cell_width=10,
        cell_height=20,
    )
    assert encoded == b"\x1b[48;24;80;480;800t"


def test_csi_18_t_reports_character_dimensions() -> None:
    encoded = size_report.encode(
        SizeReportStyle.CSI_18_T,
        rows=24,
        columns=80,
        cell_width=10,
        cell_height=20,
    )
    assert encoded == b"\x1b[8;24;80t"


def test_csi_14_t_reports_pixel_dimensions() -> None:
    encoded = size_report.encode(
        SizeReportStyle.CSI_14_T,
        rows=24,
        columns=80,
        cell_width=10,
        cell_height=20,
    )
    assert encoded == b"\x1b[4;480;800t"


def test_csi_16_t_reports_cell_pixel_size() -> None:
    encoded = size_report.encode(
        SizeReportStyle.CSI_16_T,
        rows=24,
        columns=80,
        cell_width=10,
        cell_height=20,
    )
    assert encoded == b"\x1b[6;20;10t"


def test_encode_rejects_out_of_range_rows() -> None:
    with pytest.raises(ValueError, match="rows out of range"):
        size_report.encode(
            SizeReportStyle.MODE_2048,
            rows=70000,
            columns=80,
            cell_width=10,
            cell_height=20,
        )


def test_encode_rejects_negative_columns() -> None:
    with pytest.raises(ValueError, match="columns out of range"):
        size_report.encode(
            SizeReportStyle.MODE_2048,
            rows=24,
            columns=-1,
            cell_width=10,
            cell_height=20,
        )


def test_encode_rejects_out_of_range_cell_width() -> None:
    with pytest.raises(ValueError, match="cell_width out of range"):
        size_report.encode(
            SizeReportStyle.MODE_2048,
            rows=24,
            columns=80,
            cell_width=0x1_0000_0000,
            cell_height=20,
        )


def test_encode_rejects_negative_cell_height() -> None:
    with pytest.raises(ValueError, match="cell_height out of range"):
        size_report.encode(
            SizeReportStyle.MODE_2048,
            rows=24,
            columns=80,
            cell_width=10,
            cell_height=-1,
        )
