# Expect-error typesafety pins for the kitty graphics domain.
#
# Never executed. Every statement below is a deliberate misuse of the public API.
# Each line tagged `# expect-error` MUST draw at least one diagnostic from every
# checker; the harness fails if any tagged line stops erroring or if an untagged
# line errors.
from __future__ import annotations

from ghostty_vt import Image, ImageFormat, Placement, Terminal

graphics = Terminal(80, 24).kitty_graphics()

graphics.image()  # expect-error: image_id is required
graphics.image("1")  # expect-error: image_id must be an int
graphics.does_not_exist  # expect-error: no such attribute
graphics.generation = 5  # expect-error: generation is read-only
_wrong: int = graphics.placements()  # expect-error: tuple is not an int

Placement()  # expect-error: missing required fields
Image(1, 0, 2, 2, ImageFormat.RGBA, 7, b"\x00").id = 2  # expect-error: frozen
ImageFormat.RGBA.does_not_exist  # expect-error: no such member
