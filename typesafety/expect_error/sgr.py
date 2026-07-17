# Expect-error typesafety pins for the SGR domain.
#
# Never executed. Every statement below is a deliberate misuse of the public API.
# Each line tagged `# expect-error` MUST draw at least one diagnostic from every
# checker; the harness fails if any tagged line stops erroring or if an untagged
# line errors.
from __future__ import annotations

from ghostty_vt.sgr import Attribute, AttributeKind, Underline, Unknown, parse

parse(123)  # expect-error: params must be a str
parse(b"1;31")  # expect-error: params must be a str, not bytes
Attribute()  # expect-error: missing kind
Attribute(AttributeKind.BOLD).does_not_exist  # expect-error: no such attribute
Attribute(AttributeKind.BOLD, "red")  # expect-error: str is not a valid value
AttributeKind.DOES_NOT_EXIST  # expect-error: no such enum member
Underline.DOES_NOT_EXIST  # expect-error: no such enum member
Unknown((1,))  # expect-error: missing partial
_wrong: int = Attribute(AttributeKind.BOLD)  # expect-error: Attribute is not an int
