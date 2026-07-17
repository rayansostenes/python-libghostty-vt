# Expect-error typesafety pins for the focus domain.
#
# Never executed. Every statement below is a deliberate misuse of the public API.
# Each line tagged `# expect-error` MUST draw at least one diagnostic from every
# checker; the harness fails if any tagged line stops erroring or if an untagged
# line errors.
from __future__ import annotations

from ghostty_vt import FocusEvent
from ghostty_vt.focus import encode

encode()  # expect-error: event is required
encode(0)  # expect-error: event must be a FocusEvent
_wrong: str = encode(FocusEvent.GAINED)  # expect-error: encode returns bytes
