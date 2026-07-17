# Expect-error typesafety pins for the terminal domain.
#
# Never executed. Every statement below is a deliberate misuse of the public API.
# Each line tagged `# expect-error` MUST draw at least one diagnostic from every
# checker; the harness fails if any tagged line stops erroring or if an untagged
# line errors.
from __future__ import annotations

from ghostty_vt import Terminal

Terminal()  # expect-error: missing cols and rows
Terminal("80", 24)  # expect-error: cols must be an int
Terminal(80, 24).feed("text")  # expect-error: feed takes bytes, not str
Terminal(80, 24).resize(100)  # expect-error: resize needs both dimensions
Terminal(80, 24).does_not_exist  # expect-error: no such attribute
_wrong: int = Terminal(80, 24).visible_text()  # expect-error: str is not an int
