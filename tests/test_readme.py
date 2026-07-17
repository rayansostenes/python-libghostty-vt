"""Run the README's quickstart examples as doctests.

The README shows interactive (``>>>``) sessions for the flagship flows —
terminal feed/read/resize, key encoding, and runtime introspection. Executing
them here against the real ``ghostty_vt`` extension keeps the front-door
examples honest: if the public API changes, these fail instead of silently
rotting.
"""

from __future__ import annotations

import doctest
from pathlib import Path

_README = Path(__file__).resolve().parent.parent / "README.md"


def test_readme_examples_run_as_written() -> None:
    failures, _ = doctest.testfile(
        str(_README),
        module_relative=False,
        optionflags=doctest.ELLIPSIS,
    )
    assert failures == 0
