# Expect-error typesafety pins for the terminal domain.
#
# Never executed. Every statement below is a deliberate misuse of the public API.
# Each line tagged `# expect-error` MUST draw at least one diagnostic from every
# checker; the harness fails if any tagged line stops erroring or if an untagged
# line errors.
from __future__ import annotations

from ghostty_vt import Mode, Terminal

Terminal()  # expect-error: missing cols and rows
Terminal("80", 24)  # expect-error: cols must be an int
Terminal(80, 24, scrollback="lots")  # expect-error: scrollback must be an int
Terminal(80, 24, 100)  # expect-error: scrollback is keyword-only
Terminal(80, 24).feed("text")  # expect-error: feed takes bytes, not str
Terminal(80, 24).resize(100)  # expect-error: resize needs both dimensions
Terminal(80, 24).does_not_exist  # expect-error: no such attribute
Terminal(80, 24, scrollback="big")  # expect-error: scrollback must be an int
_wrong: int = Terminal(80, 24).visible_text()  # expect-error: str is not an int
Terminal(80, 24).get_mode(25)  # expect-error: get_mode takes a Mode, not an int
Terminal(80, 24).set_mode(Mode.CURSOR_VISIBLE)  # expect-error: missing value
Terminal(80, 24).cursor.x = 5  # expect-error: Cursor is frozen
Terminal(80, 24).scroll_by("1")  # expect-error: rows must be an int
