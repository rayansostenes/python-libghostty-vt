"""OSC domain: parse Operating System Command sequences into typed results.

This is the idiomatic layer over the upstream ``osc`` domain. :func:`parse`
takes the payload of an OSC sequence — the bytes between the introducer
(``ESC]``) and the terminator (``BEL`` or ``ST``) — and classifies it into a
typed :class:`Command`. For window-title commands the title string is extracted;
every other recognized command is reported by its :class:`CommandType` so
callers can dispatch on it. Malformed input yields
:attr:`CommandType.INVALID` rather than raising.

Parsing is independent of any :class:`~ghostty_vt.Terminal`.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Any

from ghostty_vt import _raw, _result

__all__ = [
    "Command",
    "CommandType",
    "parse",
]

_ffi = _raw.ffi
_lib = _raw.lib

# OSC parsing is terminator-insensitive for classification; BEL is the common
# terminator and only matters to commands that build a response.
_TERMINATOR = 0x07


class CommandType(enum.Enum):
    """The kind of an OSC :class:`Command`, mirroring the upstream commands."""

    INVALID = _lib.GHOSTTY_OSC_COMMAND_INVALID
    """Unrecognized or malformed input."""

    CHANGE_WINDOW_TITLE = _lib.GHOSTTY_OSC_COMMAND_CHANGE_WINDOW_TITLE
    """Set the window title; :attr:`Command.title` holds the new title."""

    CHANGE_WINDOW_ICON = _lib.GHOSTTY_OSC_COMMAND_CHANGE_WINDOW_ICON
    SEMANTIC_PROMPT = _lib.GHOSTTY_OSC_COMMAND_SEMANTIC_PROMPT
    CLIPBOARD_CONTENTS = _lib.GHOSTTY_OSC_COMMAND_CLIPBOARD_CONTENTS
    REPORT_PWD = _lib.GHOSTTY_OSC_COMMAND_REPORT_PWD
    MOUSE_SHAPE = _lib.GHOSTTY_OSC_COMMAND_MOUSE_SHAPE
    COLOR_OPERATION = _lib.GHOSTTY_OSC_COMMAND_COLOR_OPERATION
    KITTY_COLOR_PROTOCOL = _lib.GHOSTTY_OSC_COMMAND_KITTY_COLOR_PROTOCOL
    SHOW_DESKTOP_NOTIFICATION = _lib.GHOSTTY_OSC_COMMAND_SHOW_DESKTOP_NOTIFICATION
    HYPERLINK_START = _lib.GHOSTTY_OSC_COMMAND_HYPERLINK_START
    HYPERLINK_END = _lib.GHOSTTY_OSC_COMMAND_HYPERLINK_END
    CONEMU_SLEEP = _lib.GHOSTTY_OSC_COMMAND_CONEMU_SLEEP
    CONEMU_SHOW_MESSAGE_BOX = _lib.GHOSTTY_OSC_COMMAND_CONEMU_SHOW_MESSAGE_BOX
    CONEMU_CHANGE_TAB_TITLE = _lib.GHOSTTY_OSC_COMMAND_CONEMU_CHANGE_TAB_TITLE
    CONEMU_PROGRESS_REPORT = _lib.GHOSTTY_OSC_COMMAND_CONEMU_PROGRESS_REPORT
    CONEMU_WAIT_INPUT = _lib.GHOSTTY_OSC_COMMAND_CONEMU_WAIT_INPUT
    CONEMU_GUIMACRO = _lib.GHOSTTY_OSC_COMMAND_CONEMU_GUIMACRO
    CONEMU_RUN_PROCESS = _lib.GHOSTTY_OSC_COMMAND_CONEMU_RUN_PROCESS
    CONEMU_OUTPUT_ENVIRONMENT_VARIABLE = (
        _lib.GHOSTTY_OSC_COMMAND_CONEMU_OUTPUT_ENVIRONMENT_VARIABLE
    )
    CONEMU_XTERM_EMULATION = _lib.GHOSTTY_OSC_COMMAND_CONEMU_XTERM_EMULATION
    CONEMU_COMMENT = _lib.GHOSTTY_OSC_COMMAND_CONEMU_COMMENT
    KITTY_TEXT_SIZING = _lib.GHOSTTY_OSC_COMMAND_KITTY_TEXT_SIZING


@dataclass(frozen=True, slots=True)
class Command:
    """A parsed OSC command.

    Attributes:
        type: Which command was parsed. :attr:`CommandType.INVALID` denotes
            unrecognized or malformed input.
        title: The window title for :attr:`CommandType.CHANGE_WINDOW_TITLE`
            commands, otherwise ``None``.
    """

    type: CommandType
    title: str | None = None


def _title(command: Any) -> str:
    out = _ffi.new("const char **")
    # A change-title command always carries an extractable (possibly empty)
    # string, so the boolean result is not branched on.
    _lib.ghostty_osc_command_data(
        command, _lib.GHOSTTY_OSC_DATA_CHANGE_WINDOW_TITLE_STR, out
    )
    return str(_ffi.string(out[0]).decode("utf-8", errors="replace"))


def parse(payload: bytes) -> Command:
    """Parse an OSC payload into a typed :class:`Command`.

    Args:
        payload: The bytes of an OSC sequence between the introducer (``ESC]``)
            and the terminator (``BEL`` or ``ST``) — for example ``b"0;title"``
            for a window-title command.

    Returns:
        The parsed command. Unrecognized or malformed payloads yield a command
        of type :attr:`CommandType.INVALID`; parsing never raises for bad input.
    """
    handle = _ffi.new("GhosttyOscParser *")
    _result.check(
        _lib.ghostty_osc_new(_ffi.NULL, handle), "could not create OSC parser"
    )
    parser = handle[0]
    try:
        for byte in payload:
            _lib.ghostty_osc_next(parser, byte)
        command = _lib.ghostty_osc_end(parser, _TERMINATOR)
        if command == _ffi.NULL:
            return Command(CommandType.INVALID)
        command_type = CommandType(_lib.ghostty_osc_command_type(command))
        title = (
            _title(command) if command_type is CommandType.CHANGE_WINDOW_TITLE else None
        )
        return Command(command_type, title)
    finally:
        _lib.ghostty_osc_free(parser)
