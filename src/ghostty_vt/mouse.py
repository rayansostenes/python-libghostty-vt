"""Mouse domain: mouse events and their encoding to escape sequences.

This is the idiomatic layer over the upstream ``mouse`` domain. A
:class:`MouseEvent` is an immutable description of a mouse action — a button
press, a release, or motion at a surface-space position, together with the
keyboard modifiers held at the time. A :class:`MouseEncoder` turns those events
into the byte sequences a terminal application expects, according to a mouse
:class:`MouseTracking` mode and a :class:`MouseFormat` output format.

The encoder is a resource-owning object: use it as a context manager, or rely on
the finalizer to release the native encoder if you forget. Operations on a closed
encoder raise :class:`~ghostty_vt.errors.GhosttyVtError`.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from types import TracebackType
from typing import Any

from ghostty_vt import _raw, _result
from ghostty_vt.errors import GhosttyVtError
from ghostty_vt.types import Mods, SurfacePosition

__all__ = [
    "Geometry",
    "MouseAction",
    "MouseButton",
    "MouseEncoder",
    "MouseEvent",
    "MouseFormat",
    "MouseTracking",
]

_ffi = _raw.ffi
_lib = _raw.lib


class MouseAction(enum.Enum):
    """What a mouse event represents."""

    PRESS = _lib.GHOSTTY_MOUSE_ACTION_PRESS
    """A mouse button was pressed."""

    RELEASE = _lib.GHOSTTY_MOUSE_ACTION_RELEASE
    """A mouse button was released."""

    MOTION = _lib.GHOSTTY_MOUSE_ACTION_MOTION
    """The mouse moved."""


class MouseButton(enum.Enum):
    """A mouse button identity.

    Represent "no button" — for a bare motion event — with ``None`` rather than a
    member of this enum. :attr:`UNKNOWN` is a distinct, present-but-unidentified
    button.
    """

    UNKNOWN = _lib.GHOSTTY_MOUSE_BUTTON_UNKNOWN
    LEFT = _lib.GHOSTTY_MOUSE_BUTTON_LEFT
    RIGHT = _lib.GHOSTTY_MOUSE_BUTTON_RIGHT
    MIDDLE = _lib.GHOSTTY_MOUSE_BUTTON_MIDDLE
    FOUR = _lib.GHOSTTY_MOUSE_BUTTON_FOUR
    FIVE = _lib.GHOSTTY_MOUSE_BUTTON_FIVE
    SIX = _lib.GHOSTTY_MOUSE_BUTTON_SIX
    SEVEN = _lib.GHOSTTY_MOUSE_BUTTON_SEVEN
    EIGHT = _lib.GHOSTTY_MOUSE_BUTTON_EIGHT
    NINE = _lib.GHOSTTY_MOUSE_BUTTON_NINE
    TEN = _lib.GHOSTTY_MOUSE_BUTTON_TEN
    ELEVEN = _lib.GHOSTTY_MOUSE_BUTTON_ELEVEN


class MouseTracking(enum.Enum):
    """The terminal's active mouse reporting mode.

    This selects *which* events are reported: :attr:`NONE` reports nothing,
    :attr:`X10` reports only presses, :attr:`NORMAL` reports presses and
    releases, :attr:`BUTTON` adds motion while a button is held, and :attr:`ANY`
    adds motion with no button held.
    """

    NONE = _lib.GHOSTTY_MOUSE_TRACKING_NONE
    X10 = _lib.GHOSTTY_MOUSE_TRACKING_X10
    NORMAL = _lib.GHOSTTY_MOUSE_TRACKING_NORMAL
    BUTTON = _lib.GHOSTTY_MOUSE_TRACKING_BUTTON
    ANY = _lib.GHOSTTY_MOUSE_TRACKING_ANY


class MouseFormat(enum.Enum):
    """The wire format used to encode a reported event.

    This selects *how* an event is encoded: the legacy :attr:`X10` byte triple,
    its :attr:`UTF8` extension, the :attr:`SGR` and :attr:`URXVT` numeric forms,
    or :attr:`SGR_PIXELS` which reports pixel positions instead of cells.
    """

    X10 = _lib.GHOSTTY_MOUSE_FORMAT_X10
    UTF8 = _lib.GHOSTTY_MOUSE_FORMAT_UTF8
    SGR = _lib.GHOSTTY_MOUSE_FORMAT_SGR
    URXVT = _lib.GHOSTTY_MOUSE_FORMAT_URXVT
    SGR_PIXELS = _lib.GHOSTTY_MOUSE_FORMAT_SGR_PIXELS


@dataclass(frozen=True, slots=True)
class MouseEvent:
    """An immutable mouse input event.

    Attributes:
        action: Whether this is a press, release, or motion.
        position: The mouse position in surface-space pixels.
        button: The button involved, or ``None`` for a bare motion event.
        mods: The keyboard modifiers held during the event.
    """

    action: MouseAction
    position: SurfacePosition
    button: MouseButton | None = None
    mods: Mods = Mods.NONE


@dataclass(frozen=True, slots=True)
class Geometry:
    """The rendered surface geometry a :class:`MouseEncoder` reports against.

    The encoder uses this to convert a :class:`MouseEvent`'s surface-space pixel
    position into the cell (or pixel) coordinates the wire format reports.

    Attributes:
        screen_width: Full screen width in pixels.
        screen_height: Full screen height in pixels.
        cell_width: Cell width in pixels; must be positive.
        cell_height: Cell height in pixels; must be positive.
        padding_top: Top padding in pixels.
        padding_bottom: Bottom padding in pixels.
        padding_left: Left padding in pixels.
        padding_right: Right padding in pixels.
    """

    screen_width: int
    screen_height: int
    cell_width: int
    cell_height: int
    padding_top: int = 0
    padding_bottom: int = 0
    padding_left: int = 0
    padding_right: int = 0

    def __post_init__(self) -> None:
        for name, value in (
            ("cell_width", self.cell_width),
            ("cell_height", self.cell_height),
        ):
            if value <= 0:
                raise ValueError(f"{name} must be positive, got {value}")


class MouseEncoder:
    """Encodes :class:`MouseEvent` values into terminal escape sequences.

    The encoder is configured once, at construction, with a tracking mode, an
    output format, and the surface :class:`Geometry`. It owns a native encoder
    handle; use it as a context manager for deterministic cleanup, or let the
    finalizer release it. It also carries motion-deduplication state when
    ``track_last_cell`` is set, which :meth:`reset` clears.
    """

    def __init__(
        self,
        *,
        tracking: MouseTracking,
        format: MouseFormat,
        geometry: Geometry,
        any_button_pressed: bool = False,
        track_last_cell: bool = False,
    ) -> None:
        """Create a configured mouse encoder.

        Args:
            tracking: The active mouse reporting mode.
            format: The wire format to encode events in.
            geometry: The rendered surface geometry for coordinate conversion.
            any_button_pressed: Whether any button is currently held, which some
                modes need to report motion.
            track_last_cell: Whether to suppress motion events that stay within
                the same cell as the previous report.

        Raises:
            OutOfMemoryError: If the native encoder could not be allocated.
        """
        out = _ffi.new("GhosttyMouseEncoder *")
        _result.check(
            _lib.ghostty_mouse_encoder_new(_ffi.NULL, out),
            "could not create mouse encoder",
        )
        self._handle: Any = _ffi.gc(out[0], _lib.ghostty_mouse_encoder_free)
        self._set_enum_opt(
            _lib.GHOSTTY_MOUSE_ENCODER_OPT_EVENT,
            "GhosttyMouseTrackingMode",
            tracking.value,
        )
        self._set_enum_opt(
            _lib.GHOSTTY_MOUSE_ENCODER_OPT_FORMAT,
            "GhosttyMouseFormat",
            format.value,
        )
        self._set_size(geometry)
        self._set_bool_opt(
            _lib.GHOSTTY_MOUSE_ENCODER_OPT_ANY_BUTTON_PRESSED, any_button_pressed
        )
        self._set_bool_opt(
            _lib.GHOSTTY_MOUSE_ENCODER_OPT_TRACK_LAST_CELL, track_last_cell
        )

    def encode(self, event: MouseEvent) -> bytes:
        """Encode ``event`` into its escape sequence for the configured mode.

        Not every event produces output: an event the tracking mode does not
        report (or a deduplicated in-cell motion) encodes to an empty ``bytes``.

        Raises:
            GhosttyVtError: If the encoder is closed, or if the native encode
                fails.
        """
        self._ensure_open()
        event_handle = self._build_event(event)
        try:
            return self._encode(event_handle)
        finally:
            _lib.ghostty_mouse_event_free(event_handle)

    def reset(self) -> None:
        """Clear motion-deduplication state (the last tracked cell).

        Raises:
            GhosttyVtError: If the encoder is closed.
        """
        self._ensure_open()
        _lib.ghostty_mouse_encoder_reset(self._handle)

    def close(self) -> None:
        """Release the native encoder. Idempotent; safe to call more than once."""
        if self._handle is not None:
            _ffi.release(self._handle)
            self._handle = None

    def __enter__(self) -> MouseEncoder:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def _encode(self, event_handle: Any) -> bytes:
        out_len = _ffi.new("size_t *")
        result = _lib.ghostty_mouse_encoder_encode(
            self._handle, event_handle, _ffi.NULL, 0, out_len
        )
        if result == _lib.GHOSTTY_SUCCESS:
            # A success on the zero-length sizing call means there is nothing to
            # encode for this event under the configured mode.
            return b""
        # Otherwise the output did not fit; out_len now holds the required size.
        # A genuine failure (not out-of-space) resurfaces from the sized call.
        required = out_len[0]
        buf = _ffi.new("char[]", required)
        _result.check(
            _lib.ghostty_mouse_encoder_encode(
                self._handle, event_handle, buf, required, out_len
            ),
            "could not encode mouse event",
        )
        return bytes(_ffi.buffer(buf, out_len[0]))

    def _ensure_open(self) -> None:
        if self._handle is None:
            raise GhosttyVtError("mouse encoder is closed")

    def _set_enum_opt(self, option: int, ctype: str, value: int) -> None:
        holder = _ffi.new(f"{ctype} *", value)
        _lib.ghostty_mouse_encoder_setopt(self._handle, option, holder)

    def _set_bool_opt(self, option: int, value: bool) -> None:
        holder = _ffi.new("bool *", value)
        _lib.ghostty_mouse_encoder_setopt(self._handle, option, holder)

    def _set_size(self, geometry: Geometry) -> None:
        size = _ffi.new("GhosttyMouseEncoderSize *")
        size.size = _ffi.sizeof("GhosttyMouseEncoderSize")
        size.screen_width = geometry.screen_width
        size.screen_height = geometry.screen_height
        size.cell_width = geometry.cell_width
        size.cell_height = geometry.cell_height
        size.padding_top = geometry.padding_top
        size.padding_bottom = geometry.padding_bottom
        size.padding_left = geometry.padding_left
        size.padding_right = geometry.padding_right
        _lib.ghostty_mouse_encoder_setopt(
            self._handle, _lib.GHOSTTY_MOUSE_ENCODER_OPT_SIZE, size
        )

    @staticmethod
    def _build_event(event: MouseEvent) -> Any:
        out = _ffi.new("GhosttyMouseEvent *")
        _result.check(
            _lib.ghostty_mouse_event_new(_ffi.NULL, out),
            "could not create mouse event",
        )
        handle = out[0]
        _lib.ghostty_mouse_event_set_action(handle, event.action.value)
        if event.button is None:
            _lib.ghostty_mouse_event_clear_button(handle)
        else:
            _lib.ghostty_mouse_event_set_button(handle, event.button.value)
        _lib.ghostty_mouse_event_set_mods(handle, event.mods.value)
        position = _ffi.new(
            "GhosttyMousePosition *", [event.position.x, event.position.y]
        )
        _lib.ghostty_mouse_event_set_position(handle, position[0])
        return handle
