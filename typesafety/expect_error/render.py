# Expect-error typesafety pins for the render domain.
#
# Never executed. Every statement below is a deliberate misuse of the public API.
# Each line tagged `# expect-error` MUST draw at least one diagnostic from every
# checker; the harness fails if any tagged line stops erroring or if an untagged
# line errors.
from __future__ import annotations

from ghostty_vt import Terminal

state = Terminal(10, 2).render_state()

state.update(Terminal(5, 2))  # expect-error: update takes no arguments
state.does_not_exist  # expect-error: no such attribute
state.grid()[0].dirty = True  # expect-error: rows are frozen
state.colors.background = "black"  # expect-error: colors are frozen
_wrong: int = state.grid()  # expect-error: grid is a tuple, not an int
