# Expect-error typesafety pins for the paste domain.
#
# Never executed. Every statement below is a deliberate misuse of the public API.
# Each line tagged `# expect-error` MUST draw at least one diagnostic from every
# checker; the harness fails if any tagged line stops erroring or if an untagged
# line errors.
from __future__ import annotations

from ghostty_vt.paste import encode, is_safe

is_safe(123)  # expect-error: data must be a str
encode(123, bracketed=True)  # expect-error: data must be a str
encode("hello")  # expect-error: bracketed is a required keyword argument
encode("hello", bracketed="yes")  # expect-error: bracketed must be a bool
_wrong: str = encode("hello", bracketed=True)  # expect-error: encode returns bytes
