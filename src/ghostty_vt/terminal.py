"""Terminal domain: the stateful emulated terminal.

This is the idiomatic layer over the upstream ``terminal`` domain. A
:class:`Terminal` is created with cell dimensions, fed VT-encoded ``bytes`` with
:meth:`Terminal.feed`, and queried for the plain text a user would see with
:meth:`Terminal.visible_text`. It owns a native handle, so it is a context
manager with a finalizer fallback: leaving the ``with`` block (or dropping the
last reference) releases the handle, and any use after that raises
:class:`~ghostty_vt.UseAfterCloseError`.
"""

from __future__ import annotations

import weakref
from types import TracebackType
from typing import Any, Final, Self

from ghostty_vt import _raw, _result
from ghostty_vt.errors import UseAfterCloseError
from ghostty_vt.kitty_graphics import KittyGraphics

__all__ = ["Terminal"]

_ffi = _raw.ffi
_lib = _raw.lib

# Columns and rows are uint16_t in the C API; validate the range up front so a
# bad size raises a clear ValueError instead of a cffi OverflowError.
_MAX_DIMENSION: Final[int] = 0xFFFF


def _check_dimension(name: str, value: int) -> None:
    if not 1 <= value <= _MAX_DIMENSION:
        raise ValueError(f"{name} must be between 1 and {_MAX_DIMENSION}, got {value}")


def _visible_text(handle: Any) -> str:
    # Format the active screen as plain text via a transient formatter. Trailing
    # whitespace on non-blank lines is trimmed so the result reads as the text a
    # user would see; soft-wrapped lines are left wrapped as displayed.
    options = _ffi.new("GhosttyFormatterTerminalOptions *")
    options.size = _ffi.sizeof("GhosttyFormatterTerminalOptions")
    options.emit = _lib.GHOSTTY_FORMATTER_FORMAT_PLAIN
    options.unwrap = False
    options.trim = True
    options.extra.size = _ffi.sizeof("GhosttyFormatterTerminalExtra")
    options.extra.screen.size = _ffi.sizeof("GhosttyFormatterScreenExtra")
    options.selection = _ffi.NULL

    out_formatter = _ffi.new("GhosttyFormatter *")
    result = _lib.ghostty_formatter_terminal_new(
        _ffi.NULL, out_formatter, handle, options[0]
    )
    _result.check(result, "could not create terminal formatter")
    formatter = out_formatter[0]
    try:
        out_ptr = _ffi.new("uint8_t **")
        out_len = _ffi.new("size_t *")
        result = _lib.ghostty_formatter_format_alloc(
            formatter, _ffi.NULL, out_ptr, out_len
        )
        _result.check(result, "could not format terminal contents")
        try:
            return bytes(_ffi.buffer(out_ptr[0], out_len[0])).decode("utf-8")
        finally:
            _lib.ghostty_free(_ffi.NULL, out_ptr[0], out_len[0])
    finally:
        _lib.ghostty_formatter_free(formatter)


class Terminal:
    """A stateful emulated terminal: bytes are fed in, screen state is read out.

    Feed VT-encoded ``bytes`` with :meth:`feed` and read the visible plain text
    with :meth:`visible_text`. The terminal owns a native handle; use it as a
    context manager, or rely on the finalizer to release the handle when the
    last reference is dropped.
    """

    def __init__(self, cols: int, rows: int) -> None:
        """Create a terminal ``cols`` cells wide and ``rows`` cells tall.

        Args:
            cols: The terminal width in cells (1 to 65535).
            rows: The terminal height in cells (1 to 65535).

        Raises:
            ValueError: If ``cols`` or ``rows`` is outside 1 to 65535.
            OutOfMemoryError: If the native terminal could not be allocated.
        """
        _check_dimension("cols", cols)
        _check_dimension("rows", rows)

        options = _ffi.new(
            "GhosttyTerminalOptions *",
            {"cols": cols, "rows": rows, "max_scrollback": 0},
        )
        out = _ffi.new("GhosttyTerminal *")
        result = _lib.ghostty_terminal_new(_ffi.NULL, out, options[0])
        _result.check(result, "could not create terminal")
        self._terminal: Any = out[0]
        self._finalizer = weakref.finalize(
            self, _lib.ghostty_terminal_free, self._terminal
        )

    def _handle(self) -> Any:
        if not self._finalizer.alive:
            raise UseAfterCloseError("operation on a closed Terminal")
        return self._terminal

    @property
    def cols(self) -> int:
        """The terminal width in cells."""
        return self._get_u16(_lib.GHOSTTY_TERMINAL_DATA_COLS)

    @property
    def rows(self) -> int:
        """The terminal height in cells."""
        return self._get_u16(_lib.GHOSTTY_TERMINAL_DATA_ROWS)

    def _get_u16(self, key: int) -> int:
        out = _ffi.new("uint16_t *")
        result = _lib.ghostty_terminal_get(self._handle(), key, out)
        _result.check(result, "could not query terminal data")
        return int(out[0])

    def feed(self, data: bytes) -> None:
        """Feed VT-encoded bytes through the terminal's stream parser.

        Malformed input never raises: the parser keeps the terminal state
        consistent and logs any errors internally, matching how a real terminal
        treats untrusted output.

        Raises:
            UseAfterCloseError: If the terminal has been closed.
        """
        _lib.ghostty_terminal_vt_write(self._handle(), data, len(data))

    def visible_text(self) -> str:
        """Return the plain text of the terminal's active screen.

        Trailing whitespace is trimmed from each line and trailing blank lines
        are omitted, so the result is the text a user would see. Escape
        sequences and styling are resolved away, leaving only the characters.

        Raises:
            UseAfterCloseError: If the terminal has been closed.
        """
        return _visible_text(self._handle())

    def resize(self, cols: int, rows: int) -> None:
        """Resize the terminal to ``cols`` by ``rows`` cells.

        The primary screen reflows its content to the new width. If the
        dimensions are unchanged this is a no-op.

        Args:
            cols: The new width in cells (1 to 65535).
            rows: The new height in cells (1 to 65535).

        Raises:
            UseAfterCloseError: If the terminal has been closed.
            ValueError: If ``cols`` or ``rows`` is outside 1 to 65535.
        """
        handle = self._handle()
        _check_dimension("cols", cols)
        _check_dimension("rows", rows)
        result = _lib.ghostty_terminal_resize(handle, cols, rows, 0, 0)
        _result.check(result, "could not resize terminal")

    def kitty_graphics(self) -> KittyGraphics:
        """Return a live view of this terminal's Kitty graphics image storage.

        The view reads the terminal's storage on each query, so a single view
        reflects images and placements transmitted, replaced, or deleted by later
        feeds. Its queries raise :class:`~ghostty_vt.UseAfterCloseError` once the
        terminal is closed. The storage is per active screen.
        """
        return KittyGraphics(self._handle)

    def close(self) -> None:
        """Release the native terminal handle.

        Idempotent: closing an already-closed terminal does nothing. After this,
        any other operation raises :class:`~ghostty_vt.UseAfterCloseError`.
        """
        self._finalizer()

    def __enter__(self) -> Self:
        self._handle()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
