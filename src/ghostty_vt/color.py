"""Color domain: RGB values, color parsing, palettes, and contrast helpers.

This is the idiomatic layer over the upstream ``color`` domain. Colors are
represented by the immutable :class:`Rgb` value type; parsing accepts Ghostty's
flexible color syntax and X11 names; palette helpers expose the built-in
256-color palette and Ghostty's palette generation; and the WCAG luminance and
contrast metrics are available directly on :class:`Rgb`.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from ghostty_vt import _raw, _result

__all__ = [
    "Rgb",
    "X11Color",
    "default_palette",
    "generate_palette",
    "parse_palette_entry",
    "x11_names",
]

_ffi = _raw.ffi
_lib = _raw.lib

_CHANNEL_MAX = 255
_PALETTE_SIZE = 256


@dataclass(frozen=True, slots=True)
class Rgb:
    """An 8-bit-per-channel RGB color.

    Attributes:
        r: The red component (0-255).
        g: The green component (0-255).
        b: The blue component (0-255).
    """

    r: int
    g: int
    b: int

    def __post_init__(self) -> None:
        for value in (self.r, self.g, self.b):
            if not 0 <= value <= _CHANNEL_MAX:
                raise ValueError(f"RGB channel out of range (0-255): {value}")

    @classmethod
    def parse(cls, value: str) -> Rgb:
        """Parse a flexible Ghostty color value.

        Accepts Ghostty's terminal color syntax: X11 color names, hex colors in
        3-, 6-, 9-, or 12-digit form (the leading ``#`` is optional for the 3-
        and 6-digit forms), and ``rgb:<r>/<g>/<b>`` or ``rgbi:<r>/<g>/<b>``
        specifications. Leading and trailing spaces and tabs are trimmed.

        Raises:
            InvalidValueError: If the value cannot be parsed.
        """
        data = value.encode("utf-8")
        out = _ffi.new("GhosttyColorRgb *")
        result = _lib.ghostty_color_parse(data, len(data), out)
        _result.check(result, f"could not parse color: {value!r}")
        return cls(out.r, out.g, out.b)

    @classmethod
    def from_x11(cls, name: str) -> Rgb:
        """Resolve an X11 color name from Ghostty's embedded table.

        Matching trims leading and trailing spaces and tabs and is ASCII
        case-insensitive. Hex values are not accepted; use :meth:`parse` for
        those.

        Raises:
            InvalidValueError: If no color matches the name.
        """
        data = name.encode("utf-8")
        out = _ffi.new("GhosttyColorRgb *")
        result = _lib.ghostty_color_parse_x11(data, len(data), out)
        _result.check(result, f"unknown X11 color name: {name!r}")
        return cls(out.r, out.g, out.b)

    @property
    def hex(self) -> str:
        """The color as a ``#rrggbb`` lowercase hex string."""
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}"

    @property
    def luminance(self) -> float:
        """The W3C relative luminance, from 0.0 (black) to 1.0 (white).

        See https://www.w3.org/TR/WCAG20/#relativeluminancedef.
        """
        return float(_lib.ghostty_color_luminance(self._cdata()))

    @property
    def perceived_luminance(self) -> float:
        """The perceived luminance, from 0.0 (black) to 1.0 (white).

        Ghostty treats a background color as light when this exceeds 0.5.
        """
        return float(_lib.ghostty_color_perceived_luminance(self._cdata()))

    def contrast(self, other: Rgb) -> float:
        """The WCAG contrast ratio against ``other``.

        The ratio is symmetric, from 1.0 for identical colors to 21.0 for black
        against white.
        """
        return float(_lib.ghostty_color_contrast(self._cdata(), other._cdata()))

    def _cdata(self) -> Any:
        # A transient GhosttyColorRgb cdata for passing to the raw layer.
        return _ffi.new("GhosttyColorRgb *", [self.r, self.g, self.b])


@dataclass(frozen=True, slots=True)
class X11Color:
    """A named entry in Ghostty's X11 color table.

    Aliases are distinct entries, e.g. ``"medium spring green"`` and
    ``"MediumSpringGreen"`` share a color but appear as separate names.

    Attributes:
        name: The exact supported spelling from Ghostty's ``rgb.txt`` table.
        color: The RGB value of the color.
    """

    name: str
    color: Rgb


def _rgb_from_cdata(color: Any) -> Rgb:
    return Rgb(color.r, color.g, color.b)


def parse_palette_entry(value: str) -> tuple[int, Rgb]:
    """Parse a Ghostty palette entry of the form ``N=COLOR``.

    ``N`` is a palette index from 0 to 255 in decimal or in ``0x``, ``0o``, or
    ``0b``-prefixed form. Spaces and tabs around ``N`` and ``COLOR`` are ignored.
    ``COLOR`` accepts the same syntax as :meth:`Rgb.parse`.

    Returns:
        The parsed ``(index, color)`` pair.

    Raises:
        InvalidValueError: If the entry cannot be parsed, including index
            overflow.
    """
    data = value.encode("utf-8")
    out_index = _ffi.new("uint8_t *")
    out_rgb = _ffi.new("GhosttyColorRgb *")
    result = _lib.ghostty_color_parse_palette_entry(data, len(data), out_index, out_rgb)
    _result.check(result, f"could not parse palette entry: {value!r}")
    return int(out_index[0]), _rgb_from_cdata(out_rgb)


def default_palette() -> tuple[Rgb, ...]:
    """Return Ghostty's built-in default 256-color palette.

    The 256 entries are Ghostty's base16 defaults, the xterm 6x6x6 color cube,
    and the grayscale ramp, in palette-index order.
    """
    out = _ffi.new(f"GhosttyColorRgb[{_PALETTE_SIZE}]")
    _lib.ghostty_color_palette_default(out)
    return tuple(_rgb_from_cdata(color) for color in out)


def generate_palette(
    background: Rgb,
    foreground: Rgb,
    *,
    base: Sequence[Rgb] | None = None,
    skip: Iterable[int] | None = None,
    harmonious: bool = False,
) -> tuple[Rgb, ...]:
    """Generate a 256-color palette from base colors.

    Indices 0-15 come from ``base`` (or Ghostty's default palette when ``base``
    is ``None``) and are always preserved. The 216-color cube at indices 16-231
    is generated with CIELAB interpolation, and the grayscale ramp at indices
    232-255 is interpolated from ``background`` to ``foreground``.

    Args:
        background: The terminal background color.
        foreground: The terminal foreground color.
        base: A 256-color base palette, or ``None`` for Ghostty's default.
        skip: Palette indices (0-255) to preserve from ``base`` instead of
            regenerating, or ``None`` to preserve none.
        harmonious: For light themes, whether to keep the
            background-to-foreground orientation instead of swapping it.

    Returns:
        The generated 256-color palette in palette-index order.

    Raises:
        ValueError: If ``base`` does not hold exactly 256 colors, or if any
            ``skip`` index is outside 0-255.
    """
    base_ptr: Any = _ffi.NULL
    if base is not None:
        colors = list(base)
        if len(colors) != _PALETTE_SIZE:
            raise ValueError(
                f"base palette must have {_PALETTE_SIZE} colors, got {len(colors)}"
            )
        base_ptr = _ffi.new(
            f"GhosttyColorRgb[{_PALETTE_SIZE}]",
            [(color.r, color.g, color.b) for color in colors],
        )

    skip_ptr: Any = _ffi.NULL
    if skip is not None:
        mask = _ffi.new("GhosttyColorPaletteMask *")
        for index in skip:
            if not 0 <= index < _PALETTE_SIZE:
                raise ValueError(f"palette index out of range (0-255): {index}")
            mask.bits[index >> 6] |= 1 << (index & 63)
        skip_ptr = mask

    bg = _ffi.new("GhosttyColorRgb *", [background.r, background.g, background.b])
    fg = _ffi.new("GhosttyColorRgb *", [foreground.r, foreground.g, foreground.b])
    out = _ffi.new(f"GhosttyColorRgb[{_PALETTE_SIZE}]")
    _lib.ghostty_color_palette_generate(base_ptr, skip_ptr, bg, fg, harmonious, out)
    return tuple(_rgb_from_cdata(color) for color in out)


def x11_names() -> tuple[X11Color, ...]:
    """Return Ghostty's X11 color name table.

    Entries are in ``rgb.txt`` order and include aliases as separate entries. The
    names are the exact supported spellings; :meth:`Rgb.from_x11` also matches
    them case-insensitively.
    """
    count = _lib.ghostty_color_x11_name_count()
    entries = _lib.ghostty_color_x11_names()
    return tuple(
        X11Color(
            _ffi.string(entries[i].name).decode("utf-8"),
            _rgb_from_cdata(entries[i].color),
        )
        for i in range(count)
    )
