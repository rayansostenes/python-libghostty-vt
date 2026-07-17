"""Shared value types used across ``ghostty_vt`` domains.

These are the cross-cutting primitives — screen coordinates, surface positions,
and the common enums — that individual domains (selection, terminal, render,
mouse) build on. They live here so every domain refers to one definition instead
of redeclaring them.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

from ghostty_vt import _raw

__all__ = ["Mods", "Point", "PointTag", "SurfacePosition"]

_lib = _raw.lib


class Mods(enum.Flag):
    """Keyboard modifiers held during an input event.

    A bitmask combining the active modifier keys. Members compose with ``|`` and
    are tested with ``in``; the empty combination is :attr:`NONE`. The ``*_SIDE``
    members distinguish the right key from the left and are only meaningful when
    the matching base modifier is also set, on platforms that report it.
    """

    # Bit positions match Ghostty's GHOSTTY_MODS_* header constants; they are a
    # stable part of the C ABI but are #define macros the raw layer does not
    # expose, so they are pinned here directly.
    NONE = 0
    SHIFT = 1 << 0
    CTRL = 1 << 1
    ALT = 1 << 2
    SUPER = 1 << 3
    CAPS_LOCK = 1 << 4
    NUM_LOCK = 1 << 5
    SHIFT_SIDE = 1 << 6
    CTRL_SIDE = 1 << 7
    ALT_SIDE = 1 << 8
    SUPER_SIDE = 1 << 9


class PointTag(enum.Enum):
    """Which coordinate space a :class:`Point` is addressed in."""

    ACTIVE = _lib.GHOSTTY_POINT_TAG_ACTIVE
    """Active area where the cursor can move."""

    VIEWPORT = _lib.GHOSTTY_POINT_TAG_VIEWPORT
    """Visible viewport (changes when scrolled)."""

    SCREEN = _lib.GHOSTTY_POINT_TAG_SCREEN
    """Full screen including scrollback."""

    HISTORY = _lib.GHOSTTY_POINT_TAG_HISTORY
    """Scrollback history only (before the active area)."""


@dataclass(frozen=True, slots=True)
class Point:
    """A cell coordinate within one of the terminal's coordinate spaces.

    Attributes:
        tag: The coordinate space the point is relative to.
        x: The zero-based column.
        y: The zero-based row within the tagged space. May exceed the page size
            for the ``SCREEN`` and ``HISTORY`` tags.
    """

    tag: PointTag
    x: int
    y: int


@dataclass(frozen=True, slots=True)
class SurfacePosition:
    """A position in the rendered surface, in pixels.

    This is a surface-space coordinate, not a terminal grid coordinate: it is an
    x/y position in the rendered surface with ``(0, 0)`` at the top-left corner.

    Attributes:
        x: The x position in surface pixels.
        y: The y position in surface pixels.
    """

    x: float
    y: float
