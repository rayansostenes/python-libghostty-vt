# Expect-error typesafety pins for the formatter domain.
#
# Never executed. Every statement below is a deliberate misuse of the public API.
# Each line tagged `# expect-error` MUST draw at least one diagnostic from every
# checker; the harness fails if any tagged line stops erroring or if an untagged
# line errors.
from __future__ import annotations

from ghostty_vt import Format, Terminal

term = Terminal(10, 2)

term.format(Format.PLAIN)  # expect-error: emit is keyword-only
term.format(emit="plain")  # expect-error: emit must be a Format
term.format(trim="no")  # expect-error: trim must be a bool
Format.NOT_A_MEMBER  # expect-error: no such format member
_wrong: int = term.format()  # expect-error: format returns str, not int
