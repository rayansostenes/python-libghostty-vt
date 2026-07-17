"""Device domain: Python callbacks for terminal device queries.

This is the idiomatic layer over libghostty-vt's device-query effects — the
callbacks the terminal invokes when a program asks it to identify itself:
device attributes (DA1/DA2/DA3, ``CSI c`` / ``CSI > c`` / ``CSI = c``), the
enquiry answerback (``ENQ``, ``0x05``), and the XTVERSION report (``CSI > q``).

A :class:`DeviceResponder` owns a native terminal, lets you register Python
callables that answer those queries, feeds VT bytes through them, and returns the
bytes the terminal writes back. It exists to isolate the hard part of the
bindings — Python callables crossing the C boundary — with safe lifetimes and a
defined contract for exceptions raised inside a callback.

Handlers are plain zero-argument callables:

- device attributes: returns a :class:`DeviceAttributes` (or ``None`` to let the
  terminal answer with its built-in default);
- enquiry: returns the answerback ``bytes`` (empty for no response);
- XTVERSION: returns the version ``str`` (empty for the default ``libghostty``).

If a handler raises, the exception is contained on the C side (the terminal sees
the query's safe default) and re-raised from :meth:`DeviceResponder.feed` once
the native call returns, leaving the responder usable.
"""

from __future__ import annotations

import weakref
from collections.abc import Callable
from dataclasses import dataclass, field
from types import TracebackType
from typing import Any, Final

from ghostty_vt import _raw, _result

__all__ = [
    "DeviceAttributes",
    "DeviceAttributesHandler",
    "DeviceResponder",
    "EnquiryHandler",
    "PrimaryAttributes",
    "SecondaryAttributes",
    "TertiaryAttributes",
    "XtversionHandler",
]

_ffi = _raw.ffi
_lib = _raw.lib

_UINT16_MAX: Final = 0xFFFF
_UINT32_MAX: Final = 0xFFFFFFFF
_MAX_FEATURES: Final = 64

type DeviceAttributesHandler = Callable[[], DeviceAttributes | None]
"""A device-attributes handler: returns the response, or ``None`` to default."""

type EnquiryHandler = Callable[[], bytes]
"""An enquiry handler: returns the answerback bytes (empty for no response)."""

type XtversionHandler = Callable[[], str]
"""An XTVERSION handler: returns the version string (empty for the default)."""


def _check_uint(name: str, value: int, maximum: int) -> None:
    if not 0 <= value <= maximum:
        raise ValueError(f"{name} out of range (0-{maximum}): {value}")


@dataclass(frozen=True, slots=True)
class PrimaryAttributes:
    """A primary device attributes (DA1) response.

    Answers ``CSI c``: the conformance level (``Pp``, e.g. 62 for VT220) and the
    supported feature codes (``Ps``, e.g. 22 for ANSI color).

    Attributes:
        conformance_level: The DA1 conformance level (0-65535).
        features: The DA1 feature codes, at most 64 entries, each 0-65535.
    """

    conformance_level: int
    features: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        _check_uint("conformance_level", self.conformance_level, _UINT16_MAX)
        if len(self.features) > _MAX_FEATURES:
            raise ValueError(
                f"at most {_MAX_FEATURES} feature codes, got {len(self.features)}"
            )
        for feature in self.features:
            _check_uint("feature code", feature, _UINT16_MAX)


@dataclass(frozen=True, slots=True)
class SecondaryAttributes:
    """A secondary device attributes (DA2) response.

    Answers ``CSI > c``: the terminal type, firmware version, and ROM cartridge
    number. ``rom_cartridge`` is always 0 for emulators.

    Attributes:
        device_type: The terminal type identifier (``Pp``, 0-65535).
        firmware_version: The firmware/patch version (``Pv``, 0-65535).
        rom_cartridge: The ROM cartridge number (``Pc``, 0-65535).
    """

    device_type: int = 0
    firmware_version: int = 0
    rom_cartridge: int = 0

    def __post_init__(self) -> None:
        _check_uint("device_type", self.device_type, _UINT16_MAX)
        _check_uint("firmware_version", self.firmware_version, _UINT16_MAX)
        _check_uint("rom_cartridge", self.rom_cartridge, _UINT16_MAX)


@dataclass(frozen=True, slots=True)
class TertiaryAttributes:
    """A tertiary device attributes (DA3) response.

    Answers ``CSI = c``: the unit ID, reported as 8 uppercase hex digits.

    Attributes:
        unit_id: The unit ID (0-4294967295).
    """

    unit_id: int = 0

    def __post_init__(self) -> None:
        _check_uint("unit_id", self.unit_id, _UINT32_MAX)


@dataclass(frozen=True, slots=True)
class DeviceAttributes:
    """A device attributes response covering all three DA levels.

    The terminal reads whichever sub-response matches the query it received, so a
    handler answering only DA1 can leave ``secondary`` and ``tertiary`` at their
    zero defaults.

    Attributes:
        primary: The DA1 response.
        secondary: The DA2 response.
        tertiary: The DA3 response.
    """

    primary: PrimaryAttributes
    secondary: SecondaryAttributes = field(default_factory=SecondaryAttributes)
    tertiary: TertiaryAttributes = field(default_factory=TertiaryAttributes)


def _fill_device_attributes(out: Any, attrs: DeviceAttributes) -> None:
    primary = out.primary
    primary.conformance_level = attrs.primary.conformance_level
    primary.num_features = len(attrs.primary.features)
    for index, feature in enumerate(attrs.primary.features):
        primary.features[index] = feature

    secondary = out.secondary
    secondary.device_type = attrs.secondary.device_type
    secondary.firmware_version = attrs.secondary.firmware_version
    secondary.rom_cartridge = attrs.secondary.rom_cartridge

    out.tertiary.unit_id = attrs.tertiary.unit_id


class DeviceResponder:
    """A terminal that answers device queries with registered Python callbacks.

    Construct it, register handlers for the device queries you care about, then
    :meth:`feed` VT bytes and read back the bytes the terminal wrote in response.
    Use it as a context manager, or call :meth:`close`; a dropped responder is
    finalized automatically.

    Args:
        cols: The terminal width in columns (1-65535).
        rows: The terminal height in rows (1-65535).
    """

    def __init__(self, *, cols: int = 80, rows: int = 24) -> None:
        _check_uint("cols", cols, _UINT16_MAX)
        _check_uint("rows", rows, _UINT16_MAX)
        if cols == 0 or rows == 0:
            raise ValueError("cols and rows must be positive")

        self._device_attributes: DeviceAttributesHandler | None = None
        self._enquiry: EnquiryHandler | None = None
        self._xtversion: XtversionHandler | None = None

        self._output = bytearray()
        self._response_buffers: list[Any] = []
        self._pending_error: BaseException | None = None
        self._feeding = False

        terminal_out = _ffi.new("GhosttyTerminal *")
        options = _ffi.new(
            "GhosttyTerminalOptions *",
            {"cols": cols, "rows": rows, "max_scrollback": 0},
        )
        _result.check(
            _lib.ghostty_terminal_new(_ffi.NULL, terminal_out, options[0]),
            "could not create device responder terminal",
        )
        self._terminal = terminal_out[0]
        self._callbacks = self._register_callbacks()
        self._finalizer = weakref.finalize(
            self, _lib.ghostty_terminal_free, self._terminal
        )

    def _register_callbacks(self) -> dict[Any, Any]:
        def write_pty(terminal: Any, userdata: Any, data: Any, length: int) -> None:
            self._output.extend(_ffi.buffer(data, length))

        def device_attributes(terminal: Any, userdata: Any, out_attrs: Any) -> bool:
            handler = self._device_attributes
            if handler is None:
                return False
            attrs = handler()
            if attrs is None:
                return False
            _fill_device_attributes(out_attrs, attrs)
            return True

        def enquiry(terminal: Any, userdata: Any) -> Any:
            handler = self._enquiry
            if handler is None:
                return _EMPTY_STRING
            return self._make_string(handler())

        def xtversion(terminal: Any, userdata: Any) -> Any:
            handler = self._xtversion
            if handler is None:
                return _EMPTY_STRING
            return self._make_string(handler().encode("utf-8"))

        callbacks = {
            _lib.GHOSTTY_TERMINAL_OPT_WRITE_PTY: _ffi.callback(
                "GhosttyTerminalWritePtyFn", write_pty, onerror=self._capture_error
            ),
            _lib.GHOSTTY_TERMINAL_OPT_DEVICE_ATTRIBUTES: _ffi.callback(
                "GhosttyTerminalDeviceAttributesFn",
                device_attributes,
                onerror=self._capture_error,
            ),
            _lib.GHOSTTY_TERMINAL_OPT_ENQUIRY: _ffi.callback(
                "GhosttyTerminalEnquiryFn", enquiry, onerror=self._capture_error
            ),
            _lib.GHOSTTY_TERMINAL_OPT_XTVERSION: _ffi.callback(
                "GhosttyTerminalXtversionFn", xtversion, onerror=self._capture_error
            ),
        }
        for option, callback in callbacks.items():
            _result.check(
                _lib.ghostty_terminal_set(
                    self._terminal, option, _ffi.cast("void *", callback)
                ),
                "could not register device responder callback",
            )
        return callbacks

    def _capture_error(
        self,
        exc_type: type[BaseException],
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        # cffi's onerror hook: stash the first exception a handler raised so
        # feed() can re-raise it, and let the callback return its zeroed default
        # so the C stack is never unwound through.
        if self._pending_error is None:
            self._pending_error = exc_value

    def _make_string(self, data: bytes) -> Any:
        if not data:
            return _EMPTY_STRING
        # The GhosttyString borrows this buffer for the duration of the native
        # write; keep it alive past the callback return until the next feed.
        buffer = _ffi.new("uint8_t[]", data)
        self._response_buffers.append(buffer)
        return {"ptr": buffer, "len": len(data)}

    def on_device_attributes(self, handler: DeviceAttributesHandler | None) -> None:
        """Register (or clear, with ``None``) the device-attributes handler."""
        self._ensure_open()
        self._device_attributes = handler

    def on_enquiry(self, handler: EnquiryHandler | None) -> None:
        """Register (or clear, with ``None``) the enquiry answerback handler."""
        self._ensure_open()
        self._enquiry = handler

    def on_xtversion(self, handler: XtversionHandler | None) -> None:
        """Register (or clear, with ``None``) the XTVERSION handler."""
        self._ensure_open()
        self._xtversion = handler

    def feed(self, data: bytes) -> bytes:
        """Feed VT bytes and return the bytes written back to the pty.

        Any device query in ``data`` invokes the matching handler synchronously.

        Raises:
            ValueError: If the responder is closed.
            RuntimeError: If called reentrantly from within a handler; the
                native parser must not be re-entered while a feed is in flight.
            Exception: Whatever a handler raised while processing ``data``,
                re-raised here after the native call returns.
        """
        self._ensure_open()
        if self._feeding:
            raise RuntimeError("cannot feed device responder reentrantly")
        self._output.clear()
        self._response_buffers.clear()
        self._pending_error = None
        self._feeding = True
        try:
            _lib.ghostty_terminal_vt_write(self._terminal, data, len(data))
        finally:
            self._feeding = False
        if self._pending_error is not None:
            error = self._pending_error
            self._pending_error = None
            raise error
        return bytes(self._output)

    def close(self) -> None:
        """Free the native terminal. Idempotent; further :meth:`feed` raises.

        Raises:
            RuntimeError: If called from within a handler during :meth:`feed`;
                the native terminal must not be freed while it is parsing.
        """
        if self._feeding:
            raise RuntimeError("cannot close device responder from within feed")
        if self._finalizer.alive:
            self._finalizer()
        self._callbacks = {}
        self._response_buffers = []

    def _ensure_open(self) -> None:
        if not self._finalizer.alive:
            raise ValueError("device responder is closed")

    def __enter__(self) -> DeviceResponder:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()


# A zero-length GhosttyString: no bytes written back. Shared because it borrows
# nothing and never changes.
_EMPTY_STRING: Final = {"ptr": _ffi.NULL, "len": 0}
