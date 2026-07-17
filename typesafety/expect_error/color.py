# Expect-error typesafety pins for the color domain.
#
# Never executed. Every statement below is a deliberate misuse of the public API.
# Each line tagged `# expect-error` MUST draw at least one diagnostic from every
# checker; the harness fails if any tagged line stops erroring or if an untagged
# line errors.
from __future__ import annotations

from ghostty_vt import Rgb
from ghostty_vt.color import X11Color, generate_palette, parse_palette_entry

Rgb()  # expect-error: missing r, g, and b
Rgb(0, 0, 0).does_not_exist  # expect-error: no such attribute
Rgb.parse(123)  # expect-error: value must be a str
Rgb.from_x11(123)  # expect-error: name must be a str
parse_palette_entry(123)  # expect-error: value must be a str
_wrong: int = Rgb(0, 0, 0)  # expect-error: Rgb is not an int
generate_palette(Rgb(0, 0, 0))  # expect-error: missing foreground
X11Color()  # expect-error: missing name and color
