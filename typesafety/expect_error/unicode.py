# Expect-error typesafety pins for the unicode domain.
#
# Never executed. Every statement below is a deliberate misuse of the public API.
# Each line tagged `# expect-error` MUST draw at least one diagnostic from every
# checker; the harness fails if any tagged line stops erroring or if an untagged
# line errors.
from __future__ import annotations

from ghostty_vt.unicode import codepoint_width, string_width

codepoint_width("A")  # expect-error: codepoint must be an int
string_width(0x41)  # expect-error: text must be a str
_wrong: str = codepoint_width(0x41)  # expect-error: codepoint_width returns int
