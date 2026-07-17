# Expect-error typesafety pins for the OSC domain.
#
# Never executed. Every statement below is a deliberate misuse of the public API.
# Each line tagged `# expect-error` MUST draw at least one diagnostic from every
# checker; the harness fails if any tagged line stops erroring or if an untagged
# line errors.
from __future__ import annotations

from ghostty_vt.osc import Command, CommandType, parse

parse("0;title")  # expect-error: payload must be bytes, not str
parse(123)  # expect-error: payload must be bytes
Command()  # expect-error: missing type
Command(CommandType.INVALID).does_not_exist  # expect-error: no such attribute
CommandType.DOES_NOT_EXIST  # expect-error: no such enum member
Command(CommandType.CHANGE_WINDOW_TITLE, 123)  # expect-error: title must be str or None
_wrong: int = Command(CommandType.INVALID)  # expect-error: Command is not an int
