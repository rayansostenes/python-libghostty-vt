"""Private helpers that read native cffi cdata into idiomatic value types.

These live in a private module (like ``ghostty_vt._result``) so the domains that
share them — style, grid-ref, render, formatter — call one implementation
instead of each redeclaring the native-boundary reads. The functions are named
without a leading underscore so sibling domains can call them, while the module
name keeps them out of the public API.
"""

from __future__ import annotations

from typing import Any

from ghostty_vt import _raw, _result
from ghostty_vt.color import Rgb
from ghostty_vt.style import Style, StyleColor, Underline

_ffi = _raw.ffi
_lib = _raw.lib


def _style_color(color: Any) -> StyleColor:
    # Resolve a GhosttyStyleColor tagged union into a StyleColor.
    if color.tag == _lib.GHOSTTY_STYLE_COLOR_NONE:
        return None
    if color.tag == _lib.GHOSTTY_STYLE_COLOR_PALETTE:
        return int(color.value.palette)
    rgb = color.value.rgb
    return Rgb(rgb.r, rgb.g, rgb.b)


def read_style(style: Any) -> Style:
    """Build a :class:`Style` snapshot from a populated ``GhosttyStyle`` cdata."""
    return Style(
        fg=_style_color(style.fg_color),
        bg=_style_color(style.bg_color),
        underline_color=_style_color(style.underline_color),
        bold=bool(style.bold),
        italic=bool(style.italic),
        faint=bool(style.faint),
        blink=bool(style.blink),
        inverse=bool(style.inverse),
        invisible=bool(style.invisible),
        strikethrough=bool(style.strikethrough),
        overline=bool(style.overline),
        underline=Underline(style.underline),
    )


def format_screen(handle: Any, emit: int, *, unwrap: bool, trim: bool) -> str:
    """Format a terminal's active screen to text via a transient formatter.

    ``emit`` is a ``GhosttyFormatterFormat`` value; ``handle`` is a live terminal
    handle. The caller owns terminal liveness.
    """
    options = _ffi.new("GhosttyFormatterTerminalOptions *")
    options.size = _ffi.sizeof("GhosttyFormatterTerminalOptions")
    options.emit = emit
    options.unwrap = unwrap
    options.trim = trim
    options.extra.size = _ffi.sizeof("GhosttyFormatterTerminalExtra")
    options.extra.screen.size = _ffi.sizeof("GhosttyFormatterScreenExtra")
    options.selection = _ffi.NULL

    out_formatter = _ffi.new("GhosttyFormatter *")
    _result.check(
        _lib.ghostty_formatter_terminal_new(
            _ffi.NULL, out_formatter, handle, options[0]
        ),
        "could not create terminal formatter",
    )
    formatter = out_formatter[0]
    try:
        out_ptr = _ffi.new("uint8_t **")
        out_len = _ffi.new("size_t *")
        _result.check(
            _lib.ghostty_formatter_format_alloc(formatter, _ffi.NULL, out_ptr, out_len),
            "could not format terminal contents",
        )
        try:
            return bytes(_ffi.buffer(out_ptr[0], out_len[0])).decode("utf-8")
        finally:
            _lib.ghostty_free(_ffi.NULL, out_ptr[0], out_len[0])
    finally:
        _lib.ghostty_formatter_free(formatter)
