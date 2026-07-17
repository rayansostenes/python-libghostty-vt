"""SGR domain: parse Select Graphic Rendition sequences into typed attributes.

This is the idiomatic layer over the upstream ``sgr`` domain. :func:`parse`
takes the parameter portion of a CSI SGR sequence — the text between ``ESC[``
and the final ``m`` (e.g. ``"1;31"`` for bold red, or ``"4:3"`` for a curly
underline) — and returns the ordered :class:`Attribute` values the terminal
would apply. Colon and semicolon separators may be mixed, matching the syntax
terminals accept for sub-parameters such as colours and underline styles.

Colour values are surfaced with the shared :class:`~ghostty_vt.Rgb` type;
palette entries are returned as integer indices. Parsing is independent of any
:class:`~ghostty_vt.Terminal`.
"""

from __future__ import annotations

import enum
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ghostty_vt import _raw, _result
from ghostty_vt.color import Rgb
from ghostty_vt.errors import InvalidValueError

__all__ = [
    "Attribute",
    "AttributeKind",
    "Underline",
    "Unknown",
    "parse",
]

_ffi = _raw.ffi
_lib = _raw.lib

_SEPARATORS = ";:"
_MAX_PARAM = 0xFFFF


class AttributeKind(enum.Enum):
    """The kind of an SGR :class:`Attribute`, mirroring the upstream tags.

    The kind determines whether :attr:`Attribute.value` carries data and, if so,
    its type: the colour kinds carry an :class:`~ghostty_vt.Rgb`, the palette
    kinds an integer index, :attr:`UNDERLINE` an :class:`Underline`,
    :attr:`UNKNOWN` an :class:`Unknown`, and every other kind carries ``None``.
    """

    UNSET = _lib.GHOSTTY_SGR_ATTR_UNSET
    """Reset all attributes (SGR ``0`` or an empty sequence)."""

    UNKNOWN = _lib.GHOSTTY_SGR_ATTR_UNKNOWN
    """An unrecognized or incomplete parameter run; value is an :class:`Unknown`."""

    BOLD = _lib.GHOSTTY_SGR_ATTR_BOLD
    RESET_BOLD = _lib.GHOSTTY_SGR_ATTR_RESET_BOLD
    ITALIC = _lib.GHOSTTY_SGR_ATTR_ITALIC
    RESET_ITALIC = _lib.GHOSTTY_SGR_ATTR_RESET_ITALIC
    FAINT = _lib.GHOSTTY_SGR_ATTR_FAINT
    UNDERLINE = _lib.GHOSTTY_SGR_ATTR_UNDERLINE
    """A change of underline style; value is an :class:`Underline`."""

    UNDERLINE_COLOR = _lib.GHOSTTY_SGR_ATTR_UNDERLINE_COLOR
    """A direct-RGB underline colour; value is an :class:`~ghostty_vt.Rgb`."""

    UNDERLINE_COLOR_256 = _lib.GHOSTTY_SGR_ATTR_UNDERLINE_COLOR_256
    """A palette underline colour; value is an integer index (0-255)."""

    RESET_UNDERLINE_COLOR = _lib.GHOSTTY_SGR_ATTR_RESET_UNDERLINE_COLOR
    OVERLINE = _lib.GHOSTTY_SGR_ATTR_OVERLINE
    RESET_OVERLINE = _lib.GHOSTTY_SGR_ATTR_RESET_OVERLINE
    BLINK = _lib.GHOSTTY_SGR_ATTR_BLINK
    RESET_BLINK = _lib.GHOSTTY_SGR_ATTR_RESET_BLINK
    INVERSE = _lib.GHOSTTY_SGR_ATTR_INVERSE
    RESET_INVERSE = _lib.GHOSTTY_SGR_ATTR_RESET_INVERSE
    INVISIBLE = _lib.GHOSTTY_SGR_ATTR_INVISIBLE
    RESET_INVISIBLE = _lib.GHOSTTY_SGR_ATTR_RESET_INVISIBLE
    STRIKETHROUGH = _lib.GHOSTTY_SGR_ATTR_STRIKETHROUGH
    RESET_STRIKETHROUGH = _lib.GHOSTTY_SGR_ATTR_RESET_STRIKETHROUGH
    DIRECT_COLOR_FG = _lib.GHOSTTY_SGR_ATTR_DIRECT_COLOR_FG
    """A direct-RGB foreground colour; value is an :class:`~ghostty_vt.Rgb`."""

    DIRECT_COLOR_BG = _lib.GHOSTTY_SGR_ATTR_DIRECT_COLOR_BG
    """A direct-RGB background colour; value is an :class:`~ghostty_vt.Rgb`."""

    BG_8 = _lib.GHOSTTY_SGR_ATTR_BG_8
    """An 8-colour background; value is an integer palette index (0-7)."""

    FG_8 = _lib.GHOSTTY_SGR_ATTR_FG_8
    """An 8-colour foreground; value is an integer palette index (0-7)."""

    RESET_FG = _lib.GHOSTTY_SGR_ATTR_RESET_FG
    RESET_BG = _lib.GHOSTTY_SGR_ATTR_RESET_BG
    BRIGHT_BG_8 = _lib.GHOSTTY_SGR_ATTR_BRIGHT_BG_8
    """A bright 8-colour background; value is an integer palette index (8-15)."""

    BRIGHT_FG_8 = _lib.GHOSTTY_SGR_ATTR_BRIGHT_FG_8
    """A bright 8-colour foreground; value is an integer palette index (8-15)."""

    BG_256 = _lib.GHOSTTY_SGR_ATTR_BG_256
    """A 256-colour background; value is an integer palette index (0-255)."""

    FG_256 = _lib.GHOSTTY_SGR_ATTR_FG_256
    """A 256-colour foreground; value is an integer palette index (0-255)."""


class Underline(enum.Enum):
    """An underline style carried by an :attr:`AttributeKind.UNDERLINE`."""

    NONE = _lib.GHOSTTY_SGR_UNDERLINE_NONE
    SINGLE = _lib.GHOSTTY_SGR_UNDERLINE_SINGLE
    DOUBLE = _lib.GHOSTTY_SGR_UNDERLINE_DOUBLE
    CURLY = _lib.GHOSTTY_SGR_UNDERLINE_CURLY
    DOTTED = _lib.GHOSTTY_SGR_UNDERLINE_DOTTED
    DASHED = _lib.GHOSTTY_SGR_UNDERLINE_DASHED


@dataclass(frozen=True, slots=True)
class Unknown:
    """The parameters of an unrecognized or incomplete SGR attribute.

    Attributes:
        full: The complete parameter list the parser was given.
        partial: The trailing slice from where parsing could not continue; its
            first element is the parameter that was not recognized.
    """

    full: tuple[int, ...]
    partial: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class Attribute:
    """One styling attribute parsed from an SGR sequence.

    Attributes:
        kind: Which attribute this is; it determines the type of ``value``.
        value: The attribute's data, or ``None`` for kinds that carry none. See
            :class:`AttributeKind` for the type each kind carries.
    """

    kind: AttributeKind
    value: Rgb | int | Underline | Unknown | None = None


def _rgb(color: Any) -> Rgb:
    return Rgb(color.r, color.g, color.b)


def _unknown(unknown: Any) -> Unknown:
    full = tuple(int(unknown.full_ptr[i]) for i in range(unknown.full_len))
    partial = tuple(int(unknown.partial_ptr[i]) for i in range(unknown.partial_len))
    return Unknown(full, partial)


_ValueExtractor = Callable[[Any], "Rgb | int | Underline | Unknown"]

# Extracts the active union member for each value-carrying tag. Tags absent from
# the table (bold, resets, ...) carry no data and map to a ``None`` value.
_VALUE_EXTRACTORS: dict[int, _ValueExtractor] = {
    _lib.GHOSTTY_SGR_ATTR_UNDERLINE: lambda v: Underline(v.underline),
    _lib.GHOSTTY_SGR_ATTR_UNDERLINE_COLOR: lambda v: _rgb(v.underline_color),
    _lib.GHOSTTY_SGR_ATTR_UNDERLINE_COLOR_256: lambda v: int(v.underline_color_256),
    _lib.GHOSTTY_SGR_ATTR_DIRECT_COLOR_FG: lambda v: _rgb(v.direct_color_fg),
    _lib.GHOSTTY_SGR_ATTR_DIRECT_COLOR_BG: lambda v: _rgb(v.direct_color_bg),
    _lib.GHOSTTY_SGR_ATTR_BG_8: lambda v: int(v.bg_8),
    _lib.GHOSTTY_SGR_ATTR_FG_8: lambda v: int(v.fg_8),
    _lib.GHOSTTY_SGR_ATTR_BRIGHT_BG_8: lambda v: int(v.bright_bg_8),
    _lib.GHOSTTY_SGR_ATTR_BRIGHT_FG_8: lambda v: int(v.bright_fg_8),
    _lib.GHOSTTY_SGR_ATTR_BG_256: lambda v: int(v.bg_256),
    _lib.GHOSTTY_SGR_ATTR_FG_256: lambda v: int(v.fg_256),
    _lib.GHOSTTY_SGR_ATTR_UNKNOWN: lambda v: _unknown(v.unknown),
}


def _to_param(token: str) -> int:
    if token == "":
        # An omitted parameter defaults to zero, as terminals treat `ESC[;m`.
        return 0
    if not (token.isascii() and token.isdigit()):
        raise InvalidValueError(f"invalid SGR parameter: {token!r}")
    value = int(token)
    if value > _MAX_PARAM:
        raise InvalidValueError(f"SGR parameter out of range (0-{_MAX_PARAM}): {value}")
    return value


def _tokenize(params: str) -> tuple[list[int], str]:
    # Splits on both separators, recording for each parameter the separator that
    # follows it (the upstream convention); the trailing filler is ignored.
    values: list[int] = []
    separators: list[str] = []
    token = ""
    for char in params:
        if char in _SEPARATORS:
            values.append(_to_param(token))
            separators.append(char)
            token = ""
        else:
            token += char
    values.append(_to_param(token))
    separators.append(";")
    return values, "".join(separators)


def _attribute(attr: Any) -> Attribute:
    tag = attr.tag
    extractor = _VALUE_EXTRACTORS.get(tag)
    value = extractor(attr.value) if extractor is not None else None
    return Attribute(AttributeKind(tag), value)


def parse(params: str) -> tuple[Attribute, ...]:
    """Parse the parameter portion of a CSI SGR sequence into typed attributes.

    Args:
        params: The text between ``ESC[`` and the final ``m`` of an SGR
            sequence, such as ``"1;31"`` or ``"38;2;255;0;0"``. Colon and
            semicolon separators may be mixed. An empty string yields a single
            :attr:`AttributeKind.UNSET` (reset-all) attribute.

    Returns:
        The parsed attributes, in the order the terminal would apply them.

    Raises:
        InvalidValueError: If a parameter is not a non-negative decimal integer
            or exceeds the 16-bit range terminals allow.
    """
    values, separators = _tokenize(params)
    handle = _ffi.new("GhosttySgrParser *")
    _result.check(
        _lib.ghostty_sgr_new(_ffi.NULL, handle), "could not create SGR parser"
    )
    parser = handle[0]
    try:
        result = _lib.ghostty_sgr_set_params(
            parser,
            _ffi.new("uint16_t[]", values),
            _ffi.new("char[]", separators.encode("ascii")),
            len(values),
        )
        _result.check(result, "could not set SGR parameters")
        attr = _ffi.new("GhosttySgrAttribute *")
        attributes: list[Attribute] = []
        while _lib.ghostty_sgr_next(parser, attr):
            attributes.append(_attribute(attr))
        return tuple(attributes)
    finally:
        _lib.ghostty_sgr_free(parser)
