"""Unicode domain: terminal display widths for codepoints and strings.

This is the idiomatic layer over the upstream ``unicode`` domain. The widths
match the table the terminal itself uses when laying out printed text, so
callers can predict column layout — for example IME preedit overlays — that
matches what the terminal renders. Use :func:`codepoint_width` for a single
codepoint and :func:`string_width` for cluster-accurate whole-string widths.
"""

from __future__ import annotations

from ghostty_vt import _raw

__all__ = ["codepoint_width", "string_width"]

_ffi = _raw.ffi
_lib = _raw.lib

_MAX_CODEPOINT = 0x10FFFF


def codepoint_width(codepoint: int) -> int:
    """Return the terminal display width of ``codepoint`` in cells: 0, 1, or 2.

    Width 0 covers control characters and combining marks; width 2 covers East
    Asian wide and fullwidth codepoints, default-presentation emoji, and
    regional indicators; everything else is width 1.

    This measures a single codepoint and cannot account for cluster-level rules
    such as emoji variation selectors or ZWJ sequences; use :func:`string_width`
    for cluster-accurate measurement.

    Args:
        codepoint: The Unicode codepoint to measure.

    Returns:
        The display width in cells.

    Raises:
        ValueError: If ``codepoint`` is not in the range 0 to 0x10FFFF.
    """
    if not 0 <= codepoint <= _MAX_CODEPOINT:
        raise ValueError(f"codepoint out of range (0-0x10FFFF): {codepoint}")
    return int(_lib.ghostty_unicode_codepoint_width(codepoint))


def string_width(text: str) -> int:
    """Return the total display width of ``text`` in terminal cells.

    Width is summed over grapheme clusters using the same segmentation the
    terminal applies with grapheme clustering (mode 2027) enabled, so emoji
    variation selectors, ZWJ sequences, combining marks, and skin-tone modifiers
    are measured as the terminal would render them.

    Args:
        text: The string to measure.

    Returns:
        The total display width in cells.
    """
    codepoints = [ord(char) for char in text]
    count = len(codepoints)
    if count == 0:
        return 0
    buffer = _ffi.new("uint32_t[]", codepoints)
    width = _ffi.new("uint8_t *")
    total = 0
    index = 0
    while index < count:
        consumed = _lib.ghostty_unicode_grapheme_width(
            buffer + index, count - index, width
        )
        total += width[0]
        index += consumed
    return total
