# Positive typesafety pins for the kitty graphics domain.
#
# Never executed: every line is a compile-time assertion. `assert_type` pins the
# type a checker infers for each public expression, so any drift in the kitty
# graphics API's public types turns the suite red. This file must be
# diagnostic-free under every checker.
from __future__ import annotations

from typing import assert_type

from ghostty_vt import Image, ImageFormat, KittyGraphics, Placement, Terminal

# A terminal hands out a live view of its Kitty graphics storage.
graphics = Terminal(80, 24).kitty_graphics()
assert_type(graphics, KittyGraphics)

# The storage generation reads back as an integer.
assert_type(graphics.generation, int)

# Placements come back as an immutable tuple of the value type.
placements = graphics.placements()
assert_type(placements, tuple[Placement, ...])

placement = placements[0]
assert_type(placement, Placement)
assert_type(placement.image_id, int)
assert_type(placement.placement_id, int)
assert_type(placement.is_virtual, bool)
assert_type(placement.x_offset, int)
assert_type(placement.y_offset, int)
assert_type(placement.source_x, int)
assert_type(placement.source_y, int)
assert_type(placement.source_width, int)
assert_type(placement.source_height, int)
assert_type(placement.columns, int)
assert_type(placement.rows, int)
assert_type(placement.z, int)

# Image lookup is optional: a missing ID yields None.
assert_type(graphics.image(1), Image | None)

# The image value type exposes its metadata and raw pixels.
image = Image(1, 0, 2, 2, ImageFormat.RGBA, 7, b"\x00")
assert_type(image, Image)
assert_type(image.id, int)
assert_type(image.number, int)
assert_type(image.width, int)
assert_type(image.height, int)
assert_type(image.format, ImageFormat)
assert_type(image.generation, int)
assert_type(image.data, bytes)
