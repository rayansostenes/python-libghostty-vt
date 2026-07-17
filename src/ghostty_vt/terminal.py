"""Terminal domain: the stateful emulated terminal.

This is the idiomatic layer over the upstream ``terminal`` domain. A
:class:`Terminal` is created with cell dimensions, fed VT-encoded ``bytes`` with
:meth:`Terminal.feed`, and queried for the plain text a user would see with
:meth:`Terminal.visible_text`. Beyond that core, the terminal exposes its live
screen state — cursor position and visibility, which screen is active, mouse
tracking, and scrollback extent — plus the DEC/ANSI mode registers, which can be
read and written through :meth:`Terminal.get_mode` and :meth:`Terminal.set_mode`.

It owns a native handle, so it is a context manager with a finalizer fallback:
leaving the ``with`` block (or dropping the last reference) releases the handle,
and any use after that raises :class:`~ghostty_vt.UseAfterCloseError`.
"""

from __future__ import annotations

import enum
import weakref
from dataclasses import dataclass
from types import TracebackType
from typing import Any, Final, Self

from ghostty_vt import _raw, _result
from ghostty_vt.errors import UseAfterCloseError
from ghostty_vt.kitty_graphics import KittyGraphics

__all__ = ["Cursor", "Mode", "Screen", "Terminal"]

_ffi = _raw.ffi
_lib = _raw.lib

# Columns and rows are uint16_t in the C API; validate the range up front so a
# bad size raises a clear ValueError instead of a cffi OverflowError.
_MAX_DIMENSION: Final[int] = 0xFFFF

# max_scrollback is size_t in the C API; bound it up front for the same reason
# as the dimensions, so an out-of-range value raises a clear ValueError instead
# of a cffi OverflowError.
_MAX_SCROLLBACK: Final[int] = 2 ** (8 * _ffi.sizeof("size_t")) - 1


def _check_dimension(name: str, value: int) -> None:
    if not 1 <= value <= _MAX_DIMENSION:
        raise ValueError(f"{name} must be between 1 and {_MAX_DIMENSION}, got {value}")


class Screen(enum.Enum):
    """Which of the terminal's two screen buffers is active."""

    PRIMARY = _lib.GHOSTTY_TERMINAL_SCREEN_PRIMARY
    """The primary (normal) screen, which accrues scrollback."""

    ALTERNATE = _lib.GHOSTTY_TERMINAL_SCREEN_ALTERNATE
    """The alternate screen used by full-screen applications; no scrollback."""


class Mode(enum.Enum):
    """A DEC private or ANSI terminal mode that can be read and written.

    Modes are the on/off switches a terminal toggles via escape sequences (for
    example ``CSI ? 25 h`` to show the cursor). The members here are the modes
    libghostty-vt recognizes; pass one to :meth:`Terminal.get_mode` or
    :meth:`Terminal.set_mode`. ANSI modes and DEC private modes share numeric
    values but are distinct members.
    """

    KAM = _lib.ghostty_mode_new(2, True)
    """Keyboard action mode (ANSI 2): lock the keyboard."""

    INSERT = _lib.ghostty_mode_new(4, True)
    """Insert mode (ANSI 4): shift characters right on print."""

    SRM = _lib.ghostty_mode_new(12, True)
    """Send/receive mode (ANSI 12): local echo when reset."""

    LINEFEED = _lib.ghostty_mode_new(20, True)
    """Line feed / new line mode (ANSI 20)."""

    DECCKM = _lib.ghostty_mode_new(1, False)
    """Cursor keys mode (DEC 1): application vs. normal cursor keys."""

    COLUMN_132 = _lib.ghostty_mode_new(3, False)
    """132/80 column mode (DEC 3)."""

    SLOW_SCROLL = _lib.ghostty_mode_new(4, False)
    """Smooth (slow) scroll (DEC 4)."""

    REVERSE_COLORS = _lib.ghostty_mode_new(5, False)
    """Reverse video (DEC 5): swap foreground and background."""

    ORIGIN = _lib.ghostty_mode_new(6, False)
    """Origin mode (DEC 6): cursor addressing relative to the scroll region."""

    WRAPAROUND = _lib.ghostty_mode_new(7, False)
    """Auto-wrap mode (DEC 7): wrap to the next line at the right margin."""

    AUTOREPEAT = _lib.ghostty_mode_new(8, False)
    """Auto-repeat keys (DEC 8)."""

    X10_MOUSE = _lib.ghostty_mode_new(9, False)
    """X10 mouse reporting (DEC 9)."""

    CURSOR_BLINKING = _lib.ghostty_mode_new(12, False)
    """Cursor blink (DEC 12)."""

    CURSOR_VISIBLE = _lib.ghostty_mode_new(25, False)
    """Cursor visibility (DEC 25, DECTCEM)."""

    ENABLE_MODE_3 = _lib.ghostty_mode_new(40, False)
    """Allow 132 column mode (DEC 40)."""

    REVERSE_WRAP = _lib.ghostty_mode_new(45, False)
    """Reverse wraparound (DEC 45)."""

    ALT_SCREEN_LEGACY = _lib.ghostty_mode_new(47, False)
    """Alternate screen, legacy form (DEC 47)."""

    KEYPAD_KEYS = _lib.ghostty_mode_new(66, False)
    """Application keypad mode (DEC 66)."""

    BACKARROW_KEY = _lib.ghostty_mode_new(67, False)
    """Backarrow key mode (DEC 67, DECBKM)."""

    LEFT_RIGHT_MARGIN = _lib.ghostty_mode_new(69, False)
    """Left/right margin mode (DEC 69, DECLRMM)."""

    NORMAL_MOUSE = _lib.ghostty_mode_new(1000, False)
    """Normal mouse tracking (DEC 1000)."""

    BUTTON_MOUSE = _lib.ghostty_mode_new(1002, False)
    """Button-event mouse tracking (DEC 1002)."""

    ANY_MOUSE = _lib.ghostty_mode_new(1003, False)
    """Any-event mouse tracking (DEC 1003)."""

    FOCUS_EVENT = _lib.ghostty_mode_new(1004, False)
    """Focus in/out reporting (DEC 1004)."""

    UTF8_MOUSE = _lib.ghostty_mode_new(1005, False)
    """UTF-8 mouse coordinate format (DEC 1005)."""

    SGR_MOUSE = _lib.ghostty_mode_new(1006, False)
    """SGR mouse coordinate format (DEC 1006)."""

    ALT_SCROLL = _lib.ghostty_mode_new(1007, False)
    """Alternate scroll mode (DEC 1007)."""

    URXVT_MOUSE = _lib.ghostty_mode_new(1015, False)
    """URxvt mouse coordinate format (DEC 1015)."""

    SGR_PIXELS_MOUSE = _lib.ghostty_mode_new(1016, False)
    """SGR-Pixels mouse coordinate format (DEC 1016)."""

    NUMLOCK_KEYPAD = _lib.ghostty_mode_new(1035, False)
    """Ignore the keypad when NumLock is on (DEC 1035)."""

    ALT_ESC_PREFIX = _lib.ghostty_mode_new(1036, False)
    """Alt key sends an ESC prefix (DEC 1036)."""

    ALT_SENDS_ESC = _lib.ghostty_mode_new(1039, False)
    """Alt key sends ESC (DEC 1039)."""

    REVERSE_WRAP_EXT = _lib.ghostty_mode_new(1045, False)
    """Extended reverse wraparound (DEC 1045)."""

    ALT_SCREEN = _lib.ghostty_mode_new(1047, False)
    """Alternate screen (DEC 1047)."""

    SAVE_CURSOR = _lib.ghostty_mode_new(1048, False)
    """Save/restore cursor (DEC 1048, DECSC/DECRC)."""

    ALT_SCREEN_SAVE = _lib.ghostty_mode_new(1049, False)
    """Alternate screen with saved cursor and clear (DEC 1049)."""

    BRACKETED_PASTE = _lib.ghostty_mode_new(2004, False)
    """Bracketed paste mode (DEC 2004)."""

    SYNC_OUTPUT = _lib.ghostty_mode_new(2026, False)
    """Synchronized output (DEC 2026)."""

    GRAPHEME_CLUSTER = _lib.ghostty_mode_new(2027, False)
    """Grapheme cluster segmentation (DEC 2027)."""

    COLOR_SCHEME_REPORT = _lib.ghostty_mode_new(2031, False)
    """Report color-scheme changes (DEC 2031)."""

    IN_BAND_RESIZE = _lib.ghostty_mode_new(2048, False)
    """In-band size reports (DEC 2048)."""


@dataclass(frozen=True, slots=True)
class Cursor:
    """A snapshot of the active screen's cursor state.

    Attributes:
        x: The zero-based column of the cursor within the active area.
        y: The zero-based row of the cursor within the active area.
        visible: Whether the cursor is visible (DEC mode 25).
        pending_wrap: Whether the next printed character will soft-wrap to the
            following line because the cursor sits past the right margin.
    """

    x: int
    y: int
    visible: bool
    pending_wrap: bool


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
    with :meth:`visible_text`. Screen state — the :attr:`cursor`, the
    :attr:`active_screen`, :attr:`mouse_tracking`, and the scrollback extent
    (:attr:`total_rows`, :attr:`scrollback_rows`, :attr:`viewport_active`) — is
    read through properties, and DEC/ANSI modes through :meth:`get_mode` and
    :meth:`set_mode`. The terminal owns a native handle; use it as a context
    manager, or rely on the finalizer to release the handle when the last
    reference is dropped.
    """

    def __init__(self, cols: int, rows: int, *, scrollback: int = 0) -> None:
        """Create a terminal ``cols`` cells wide and ``rows`` cells tall.

        Args:
            cols: The terminal width in cells (1 to 65535).
            rows: The terminal height in cells (1 to 65535).
            scrollback: The maximum number of scrolled-off lines to retain in
                history. Defaults to ``0`` (no scrollback); pass a positive value
                to make lines that scroll past the top reachable through
                :meth:`visible_text` and the scrollback properties.

        Raises:
            ValueError: If ``cols`` or ``rows`` is outside 1 to 65535, or if
                ``scrollback`` is outside 0 to the platform ``size_t`` maximum.
            OutOfMemoryError: If the native terminal could not be allocated.
        """
        _check_dimension("cols", cols)
        _check_dimension("rows", rows)
        if not 0 <= scrollback <= _MAX_SCROLLBACK:
            raise ValueError(
                f"scrollback must be between 0 and {_MAX_SCROLLBACK}, got {scrollback}"
            )

        options = _ffi.new(
            "GhosttyTerminalOptions *",
            {"cols": cols, "rows": rows, "max_scrollback": scrollback},
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

    @property
    def cursor(self) -> Cursor:
        """The active screen's current cursor position and state."""
        return Cursor(
            x=self._get_u16(_lib.GHOSTTY_TERMINAL_DATA_CURSOR_X),
            y=self._get_u16(_lib.GHOSTTY_TERMINAL_DATA_CURSOR_Y),
            visible=self._get_bool(_lib.GHOSTTY_TERMINAL_DATA_CURSOR_VISIBLE),
            pending_wrap=self._get_bool(_lib.GHOSTTY_TERMINAL_DATA_CURSOR_PENDING_WRAP),
        )

    @property
    def active_screen(self) -> Screen:
        """Which screen buffer (primary or alternate) is currently active."""
        out = _ffi.new("GhosttyTerminalScreen *")
        result = _lib.ghostty_terminal_get(
            self._handle(), _lib.GHOSTTY_TERMINAL_DATA_ACTIVE_SCREEN, out
        )
        _result.check(result, "could not query active screen")
        return Screen(int(out[0]))

    @property
    def mouse_tracking(self) -> bool:
        """Whether any mouse tracking mode (X10, normal, button, any) is active."""
        return self._get_bool(_lib.GHOSTTY_TERMINAL_DATA_MOUSE_TRACKING)

    @property
    def total_rows(self) -> int:
        """The number of rows in the active screen, including scrollback."""
        return self._get_size(_lib.GHOSTTY_TERMINAL_DATA_TOTAL_ROWS)

    @property
    def scrollback_rows(self) -> int:
        """The number of scrollback rows above the visible active area."""
        return self._get_size(_lib.GHOSTTY_TERMINAL_DATA_SCROLLBACK_ROWS)

    @property
    def viewport_active(self) -> bool:
        """Whether the viewport is pinned to the active area.

        ``True`` when the viewport follows the active area (the default), and
        ``False`` once the viewport has been scrolled up into history with
        :meth:`scroll_to_top`, :meth:`scroll_by`, or :meth:`scroll_to_row`.
        """
        return self._get_bool(_lib.GHOSTTY_TERMINAL_DATA_VIEWPORT_ACTIVE)

    def _get_u16(self, key: Any) -> int:
        out = _ffi.new("uint16_t *")
        result = _lib.ghostty_terminal_get(self._handle(), key, out)
        _result.check(result, "could not query terminal data")
        return int(out[0])

    def _get_bool(self, key: Any) -> bool:
        out = _ffi.new("bool *")
        result = _lib.ghostty_terminal_get(self._handle(), key, out)
        _result.check(result, "could not query terminal data")
        return bool(out[0])

    def _get_size(self, key: Any) -> int:
        out = _ffi.new("size_t *")
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

        The full screen is formatted, including any scrollback above the visible
        area. Trailing whitespace is trimmed from each line and trailing blank
        lines are omitted, so the result is the text a user would see. Escape
        sequences and styling are resolved away, leaving only the characters.

        Raises:
            UseAfterCloseError: If the terminal has been closed.
        """
        return _visible_text(self._handle())

    def get_mode(self, mode: Mode) -> bool:
        """Return whether ``mode`` is currently set.

        The value reflects sequences already fed to the terminal, so a
        ``CSI ? 25 l`` in the input stream makes ``get_mode(Mode.CURSOR_VISIBLE)``
        return ``False``.

        Raises:
            UseAfterCloseError: If the terminal has been closed.
        """
        out = _ffi.new("bool *")
        result = _lib.ghostty_terminal_mode_get(self._handle(), mode.value, out)
        _result.check(result, "could not query terminal mode")
        return bool(out[0])

    def set_mode(self, mode: Mode, value: bool) -> None:
        """Set ``mode`` to ``value``.

        This writes the mode register directly, exactly as the C API does, and
        the change is observable through :meth:`get_mode`. It is *not* a replay
        of the mode's escape sequence, so the side effects a sequence would
        trigger do not happen: setting an alternate-screen mode records the mode
        but does not switch :attr:`active_screen`, for example. Feed the escape
        sequence with :meth:`feed` when you need those effects. Screen-state
        views that read the same register — such as :attr:`Cursor.visible` for
        :attr:`Mode.CURSOR_VISIBLE` — still agree with :meth:`get_mode`.

        Raises:
            UseAfterCloseError: If the terminal has been closed.
        """
        result = _lib.ghostty_terminal_mode_set(self._handle(), mode.value, value)
        _result.check(result, "could not set terminal mode")

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

    def scroll_to_top(self) -> None:
        """Scroll the viewport to the top of the scrollback.

        Raises:
            UseAfterCloseError: If the terminal has been closed.
        """
        self._scroll_viewport(_lib.GHOSTTY_SCROLL_VIEWPORT_TOP)

    def scroll_to_bottom(self) -> None:
        """Scroll the viewport back down to the active area.

        Raises:
            UseAfterCloseError: If the terminal has been closed.
        """
        self._scroll_viewport(_lib.GHOSTTY_SCROLL_VIEWPORT_BOTTOM)

    def scroll_by(self, rows: int) -> None:
        """Scroll the viewport by ``rows`` rows (negative scrolls up).

        The viewport is clamped to the scrollable area, so an over-large delta
        stops at the top or bottom.

        Raises:
            UseAfterCloseError: If the terminal has been closed.
        """
        self._scroll_viewport(_lib.GHOSTTY_SCROLL_VIEWPORT_DELTA, delta=rows)

    def scroll_to_row(self, row: int) -> None:
        """Scroll so ``row`` becomes the first visible row of the viewport.

        ``row`` is a zero-based offset from the top of the scrollable area, the
        same space as :attr:`scrollback_rows`. It is clamped so the viewport
        never scrolls past the active area.

        Args:
            row: The zero-based scrollable-area row to scroll to.

        Raises:
            UseAfterCloseError: If the terminal has been closed.
            ValueError: If ``row`` is negative.
        """
        if row < 0:
            raise ValueError(f"row must be non-negative, got {row}")
        self._scroll_viewport(_lib.GHOSTTY_SCROLL_VIEWPORT_ROW, row=row)

    def _scroll_viewport(
        self, tag: Any, *, delta: int | None = None, row: int | None = None
    ) -> None:
        handle = self._handle()
        behavior = _ffi.new("GhosttyTerminalScrollViewport *")
        behavior.tag = tag
        # delta and row alias the same union; set only the one the tag uses.
        if delta is not None:
            behavior.value.delta = delta
        elif row is not None:
            behavior.value.row = row
        _lib.ghostty_terminal_scroll_viewport(handle, behavior[0])

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
