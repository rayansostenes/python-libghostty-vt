"""White-box guard for the build_info query error path.

Unlike test_build_info.py, this drives the private ``_query`` helper directly to
exercise the non-success branch of the C boundary, which build_info() itself can
never reach (it only ever queries compile-time-valid variants).
"""

from __future__ import annotations

import pytest

from ghostty_vt.build_info import _lib, _query  # pyright: ignore[reportPrivateUsage]


def test_query_raises_on_invalid_tag() -> None:
    # GHOSTTY_BUILD_INFO_INVALID is a defined variant the C API rejects with a
    # non-success result without writing to the output buffer.
    with pytest.raises(RuntimeError):
        _query(_lib.GHOSTTY_BUILD_INFO_INVALID, "bool *")
