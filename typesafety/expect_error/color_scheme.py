# Expect-error typesafety pins for the color scheme domain.
#
# Never executed. Every statement below is a deliberate misuse of the public API.
# Each line tagged `# expect-error` MUST draw at least one diagnostic from every
# checker; the harness fails if any tagged line stops erroring or if an untagged
# line errors.
from __future__ import annotations

from ghostty_vt import ColorScheme
from ghostty_vt.color_scheme import encode

encode()  # expect-error: scheme is required
encode(0)  # expect-error: scheme must be a ColorScheme
_wrong: str = encode(ColorScheme.DARK)  # expect-error: encode returns bytes
