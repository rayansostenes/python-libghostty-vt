# Expect-error typesafety pins for the size report domain.
#
# Never executed. Every statement below is a deliberate misuse of the public API.
# Each line tagged `# expect-error` MUST draw at least one diagnostic from every
# checker; the harness fails if any tagged line stops erroring or if an untagged
# line errors. Calls are kept on one line so the diagnostic anchors to the tag.
from __future__ import annotations

from ghostty_vt import SizeReportStyle
from ghostty_vt.size_report import encode

S = SizeReportStyle.MODE_2048

encode(S)  # expect-error: the size fields are required
encode(S, rows="24", columns=80, cell_width=1, cell_height=1)  # expect-error: rows int
encode(0, rows=1, columns=1, cell_width=1, cell_height=1)  # expect-error: style enum
_wrong: str = encode(S, rows=1, columns=1, cell_width=1, cell_height=1)  # expect-error
