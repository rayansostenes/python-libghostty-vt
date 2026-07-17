# Expect-error typesafety pins for the style domain.
#
# Never executed. Every statement below is a deliberate misuse of the public API.
# Each line tagged `# expect-error` MUST draw at least one diagnostic from every
# checker; the harness fails if any tagged line stops erroring or if an untagged
# line errors.
from __future__ import annotations

from ghostty_vt import Style, StyleColor, Underline

Style()  # expect-error: missing every field
Style(fg=None).bold  # expect-error: missing most fields
Underline.NOT_A_MEMBER  # expect-error: no such underline member
_wrong: int = Underline.SINGLE  # expect-error: an Underline is not an int
_bad_color: StyleColor = "red"  # expect-error: str is not a style color
