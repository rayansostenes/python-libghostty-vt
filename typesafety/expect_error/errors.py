# Expect-error typesafety pins for the errors domain.
#
# Never executed. Every statement below is a deliberate misuse of the public API.
# Each line tagged `# expect-error` MUST draw at least one diagnostic from every
# checker; the harness fails if any tagged line stops erroring or if an untagged
# line errors.
from __future__ import annotations

from ghostty_vt import GhosttyVtError, InvalidValueError

_not_an_int: int = GhosttyVtError()  # expect-error: an exception is not an int
_not_a_str: str = InvalidValueError("x")  # expect-error: an exception is not a str
