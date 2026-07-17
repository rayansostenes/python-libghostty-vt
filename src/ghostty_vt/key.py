"""Key domain: keyboard events and their encoding to terminal byte sequences.

This is the idiomatic layer over the upstream ``key`` domain. A :class:`KeyEvent`
describes a single keyboard event — the physical :class:`Key`, the active
:class:`Mods`, the :class:`KeyAction`, and any layout-dependent text — as an
immutable value. A :class:`KeyEncoder` turns an event into the bytes a terminal
expects, under either the classic (legacy) protocol or the Kitty keyboard
protocol; its options (:class:`KittyFlags`, DEC modes, macOS
:class:`OptionAsAlt`) are set at construction and select between the two.

Events are pure Python values and encoders are plain option holders: neither owns
a native resource, so the transient raw key event and encoder are built, used,
and freed within a single :meth:`KeyEncoder.encode` call.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any

from ghostty_vt import _raw, _result
from ghostty_vt.types import Mods

__all__ = [
    "Key",
    "KeyAction",
    "KeyEncoder",
    "KeyEvent",
    "KittyFlags",
    "OptionAsAlt",
]

_ffi = _raw.ffi
_lib = _raw.lib

_MAX_CODEPOINT = 0x10FFFF


class KeyAction(enum.Enum):
    """Whether a key was pressed, released, or is repeating."""

    RELEASE = _lib.GHOSTTY_KEY_ACTION_RELEASE
    PRESS = _lib.GHOSTTY_KEY_ACTION_PRESS
    REPEAT = _lib.GHOSTTY_KEY_ACTION_REPEAT


class KittyFlags(enum.Flag):
    """Kitty keyboard protocol progressive-enhancement flags.

    Combine these with ``|`` to select which Kitty protocol features an encoder
    reports; the empty flag (``KittyFlags(0)``, the encoder default) selects the
    legacy protocol instead. :attr:`ALL` enables every feature.

    Values mirror the ``GHOSTTY_KITTY_KEY_*`` constants from the upstream header,
    which are preprocessor macros the raw layer does not surface.
    """

    DISAMBIGUATE = 1 << 0
    """Disambiguate escape codes."""

    REPORT_EVENTS = 1 << 1
    """Report key press, repeat, and release events."""

    REPORT_ALTERNATES = 1 << 2
    """Report alternate (shifted and base-layout) key codes."""

    REPORT_ALL = 1 << 3
    """Report all keys as escape codes, including those normally handled."""

    REPORT_ASSOCIATED = 1 << 4
    """Report the text associated with a key event."""

    ALL = (
        DISAMBIGUATE
        | REPORT_EVENTS
        | REPORT_ALTERNATES
        | REPORT_ALL
        | REPORT_ASSOCIATED
    )
    """Every Kitty keyboard protocol feature enabled."""


class OptionAsAlt(enum.Enum):
    """How the macOS Option key maps to Alt during encoding.

    Mirrors Ghostty's ``macos-option-as-alt`` setting. This cannot be derived
    from terminal state and only affects encoding on macOS-style input.
    """

    FALSE = _lib.GHOSTTY_OPTION_AS_ALT_FALSE
    """Option is never treated as Alt."""

    TRUE = _lib.GHOSTTY_OPTION_AS_ALT_TRUE
    """Either Option key is treated as Alt."""

    LEFT = _lib.GHOSTTY_OPTION_AS_ALT_LEFT
    """Only the left Option key is treated as Alt."""

    RIGHT = _lib.GHOSTTY_OPTION_AS_ALT_RIGHT
    """Only the right Option key is treated as Alt."""


class Key(enum.Enum):
    """A physical, layout-independent key code.

    These identify the physical key regardless of keyboard layout — the key that
    is ``A`` on a US layout is the same :attr:`Key.A` on any layout, while the
    character it produces is carried separately as :attr:`KeyEvent.text`. Values
    follow the W3C UI Events ``code`` standard; see
    https://www.w3.org/TR/uievents-code.
    """

    UNIDENTIFIED = _lib.GHOSTTY_KEY_UNIDENTIFIED
    BACKQUOTE = _lib.GHOSTTY_KEY_BACKQUOTE
    BACKSLASH = _lib.GHOSTTY_KEY_BACKSLASH
    BRACKET_LEFT = _lib.GHOSTTY_KEY_BRACKET_LEFT
    BRACKET_RIGHT = _lib.GHOSTTY_KEY_BRACKET_RIGHT
    COMMA = _lib.GHOSTTY_KEY_COMMA
    DIGIT_0 = _lib.GHOSTTY_KEY_DIGIT_0
    DIGIT_1 = _lib.GHOSTTY_KEY_DIGIT_1
    DIGIT_2 = _lib.GHOSTTY_KEY_DIGIT_2
    DIGIT_3 = _lib.GHOSTTY_KEY_DIGIT_3
    DIGIT_4 = _lib.GHOSTTY_KEY_DIGIT_4
    DIGIT_5 = _lib.GHOSTTY_KEY_DIGIT_5
    DIGIT_6 = _lib.GHOSTTY_KEY_DIGIT_6
    DIGIT_7 = _lib.GHOSTTY_KEY_DIGIT_7
    DIGIT_8 = _lib.GHOSTTY_KEY_DIGIT_8
    DIGIT_9 = _lib.GHOSTTY_KEY_DIGIT_9
    EQUAL = _lib.GHOSTTY_KEY_EQUAL
    INTL_BACKSLASH = _lib.GHOSTTY_KEY_INTL_BACKSLASH
    INTL_RO = _lib.GHOSTTY_KEY_INTL_RO
    INTL_YEN = _lib.GHOSTTY_KEY_INTL_YEN
    A = _lib.GHOSTTY_KEY_A
    B = _lib.GHOSTTY_KEY_B
    C = _lib.GHOSTTY_KEY_C
    D = _lib.GHOSTTY_KEY_D
    E = _lib.GHOSTTY_KEY_E
    F = _lib.GHOSTTY_KEY_F
    G = _lib.GHOSTTY_KEY_G
    H = _lib.GHOSTTY_KEY_H
    I = _lib.GHOSTTY_KEY_I  # noqa: E741
    J = _lib.GHOSTTY_KEY_J
    K = _lib.GHOSTTY_KEY_K
    L = _lib.GHOSTTY_KEY_L
    M = _lib.GHOSTTY_KEY_M
    N = _lib.GHOSTTY_KEY_N
    O = _lib.GHOSTTY_KEY_O  # noqa: E741
    P = _lib.GHOSTTY_KEY_P
    Q = _lib.GHOSTTY_KEY_Q
    R = _lib.GHOSTTY_KEY_R
    S = _lib.GHOSTTY_KEY_S
    T = _lib.GHOSTTY_KEY_T
    U = _lib.GHOSTTY_KEY_U
    V = _lib.GHOSTTY_KEY_V
    W = _lib.GHOSTTY_KEY_W
    X = _lib.GHOSTTY_KEY_X
    Y = _lib.GHOSTTY_KEY_Y
    Z = _lib.GHOSTTY_KEY_Z
    MINUS = _lib.GHOSTTY_KEY_MINUS
    PERIOD = _lib.GHOSTTY_KEY_PERIOD
    QUOTE = _lib.GHOSTTY_KEY_QUOTE
    SEMICOLON = _lib.GHOSTTY_KEY_SEMICOLON
    SLASH = _lib.GHOSTTY_KEY_SLASH
    ALT_LEFT = _lib.GHOSTTY_KEY_ALT_LEFT
    ALT_RIGHT = _lib.GHOSTTY_KEY_ALT_RIGHT
    BACKSPACE = _lib.GHOSTTY_KEY_BACKSPACE
    CAPS_LOCK = _lib.GHOSTTY_KEY_CAPS_LOCK
    CONTEXT_MENU = _lib.GHOSTTY_KEY_CONTEXT_MENU
    CONTROL_LEFT = _lib.GHOSTTY_KEY_CONTROL_LEFT
    CONTROL_RIGHT = _lib.GHOSTTY_KEY_CONTROL_RIGHT
    ENTER = _lib.GHOSTTY_KEY_ENTER
    META_LEFT = _lib.GHOSTTY_KEY_META_LEFT
    META_RIGHT = _lib.GHOSTTY_KEY_META_RIGHT
    SHIFT_LEFT = _lib.GHOSTTY_KEY_SHIFT_LEFT
    SHIFT_RIGHT = _lib.GHOSTTY_KEY_SHIFT_RIGHT
    SPACE = _lib.GHOSTTY_KEY_SPACE
    TAB = _lib.GHOSTTY_KEY_TAB
    CONVERT = _lib.GHOSTTY_KEY_CONVERT
    KANA_MODE = _lib.GHOSTTY_KEY_KANA_MODE
    NON_CONVERT = _lib.GHOSTTY_KEY_NON_CONVERT
    DELETE = _lib.GHOSTTY_KEY_DELETE
    END = _lib.GHOSTTY_KEY_END
    HELP = _lib.GHOSTTY_KEY_HELP
    HOME = _lib.GHOSTTY_KEY_HOME
    INSERT = _lib.GHOSTTY_KEY_INSERT
    PAGE_DOWN = _lib.GHOSTTY_KEY_PAGE_DOWN
    PAGE_UP = _lib.GHOSTTY_KEY_PAGE_UP
    ARROW_DOWN = _lib.GHOSTTY_KEY_ARROW_DOWN
    ARROW_LEFT = _lib.GHOSTTY_KEY_ARROW_LEFT
    ARROW_RIGHT = _lib.GHOSTTY_KEY_ARROW_RIGHT
    ARROW_UP = _lib.GHOSTTY_KEY_ARROW_UP
    NUM_LOCK = _lib.GHOSTTY_KEY_NUM_LOCK
    NUMPAD_0 = _lib.GHOSTTY_KEY_NUMPAD_0
    NUMPAD_1 = _lib.GHOSTTY_KEY_NUMPAD_1
    NUMPAD_2 = _lib.GHOSTTY_KEY_NUMPAD_2
    NUMPAD_3 = _lib.GHOSTTY_KEY_NUMPAD_3
    NUMPAD_4 = _lib.GHOSTTY_KEY_NUMPAD_4
    NUMPAD_5 = _lib.GHOSTTY_KEY_NUMPAD_5
    NUMPAD_6 = _lib.GHOSTTY_KEY_NUMPAD_6
    NUMPAD_7 = _lib.GHOSTTY_KEY_NUMPAD_7
    NUMPAD_8 = _lib.GHOSTTY_KEY_NUMPAD_8
    NUMPAD_9 = _lib.GHOSTTY_KEY_NUMPAD_9
    NUMPAD_ADD = _lib.GHOSTTY_KEY_NUMPAD_ADD
    NUMPAD_BACKSPACE = _lib.GHOSTTY_KEY_NUMPAD_BACKSPACE
    NUMPAD_CLEAR = _lib.GHOSTTY_KEY_NUMPAD_CLEAR
    NUMPAD_CLEAR_ENTRY = _lib.GHOSTTY_KEY_NUMPAD_CLEAR_ENTRY
    NUMPAD_COMMA = _lib.GHOSTTY_KEY_NUMPAD_COMMA
    NUMPAD_DECIMAL = _lib.GHOSTTY_KEY_NUMPAD_DECIMAL
    NUMPAD_DIVIDE = _lib.GHOSTTY_KEY_NUMPAD_DIVIDE
    NUMPAD_ENTER = _lib.GHOSTTY_KEY_NUMPAD_ENTER
    NUMPAD_EQUAL = _lib.GHOSTTY_KEY_NUMPAD_EQUAL
    NUMPAD_MEMORY_ADD = _lib.GHOSTTY_KEY_NUMPAD_MEMORY_ADD
    NUMPAD_MEMORY_CLEAR = _lib.GHOSTTY_KEY_NUMPAD_MEMORY_CLEAR
    NUMPAD_MEMORY_RECALL = _lib.GHOSTTY_KEY_NUMPAD_MEMORY_RECALL
    NUMPAD_MEMORY_STORE = _lib.GHOSTTY_KEY_NUMPAD_MEMORY_STORE
    NUMPAD_MEMORY_SUBTRACT = _lib.GHOSTTY_KEY_NUMPAD_MEMORY_SUBTRACT
    NUMPAD_MULTIPLY = _lib.GHOSTTY_KEY_NUMPAD_MULTIPLY
    NUMPAD_PAREN_LEFT = _lib.GHOSTTY_KEY_NUMPAD_PAREN_LEFT
    NUMPAD_PAREN_RIGHT = _lib.GHOSTTY_KEY_NUMPAD_PAREN_RIGHT
    NUMPAD_SUBTRACT = _lib.GHOSTTY_KEY_NUMPAD_SUBTRACT
    NUMPAD_SEPARATOR = _lib.GHOSTTY_KEY_NUMPAD_SEPARATOR
    NUMPAD_UP = _lib.GHOSTTY_KEY_NUMPAD_UP
    NUMPAD_DOWN = _lib.GHOSTTY_KEY_NUMPAD_DOWN
    NUMPAD_RIGHT = _lib.GHOSTTY_KEY_NUMPAD_RIGHT
    NUMPAD_LEFT = _lib.GHOSTTY_KEY_NUMPAD_LEFT
    NUMPAD_BEGIN = _lib.GHOSTTY_KEY_NUMPAD_BEGIN
    NUMPAD_HOME = _lib.GHOSTTY_KEY_NUMPAD_HOME
    NUMPAD_END = _lib.GHOSTTY_KEY_NUMPAD_END
    NUMPAD_INSERT = _lib.GHOSTTY_KEY_NUMPAD_INSERT
    NUMPAD_DELETE = _lib.GHOSTTY_KEY_NUMPAD_DELETE
    NUMPAD_PAGE_UP = _lib.GHOSTTY_KEY_NUMPAD_PAGE_UP
    NUMPAD_PAGE_DOWN = _lib.GHOSTTY_KEY_NUMPAD_PAGE_DOWN
    ESCAPE = _lib.GHOSTTY_KEY_ESCAPE
    F1 = _lib.GHOSTTY_KEY_F1
    F2 = _lib.GHOSTTY_KEY_F2
    F3 = _lib.GHOSTTY_KEY_F3
    F4 = _lib.GHOSTTY_KEY_F4
    F5 = _lib.GHOSTTY_KEY_F5
    F6 = _lib.GHOSTTY_KEY_F6
    F7 = _lib.GHOSTTY_KEY_F7
    F8 = _lib.GHOSTTY_KEY_F8
    F9 = _lib.GHOSTTY_KEY_F9
    F10 = _lib.GHOSTTY_KEY_F10
    F11 = _lib.GHOSTTY_KEY_F11
    F12 = _lib.GHOSTTY_KEY_F12
    F13 = _lib.GHOSTTY_KEY_F13
    F14 = _lib.GHOSTTY_KEY_F14
    F15 = _lib.GHOSTTY_KEY_F15
    F16 = _lib.GHOSTTY_KEY_F16
    F17 = _lib.GHOSTTY_KEY_F17
    F18 = _lib.GHOSTTY_KEY_F18
    F19 = _lib.GHOSTTY_KEY_F19
    F20 = _lib.GHOSTTY_KEY_F20
    F21 = _lib.GHOSTTY_KEY_F21
    F22 = _lib.GHOSTTY_KEY_F22
    F23 = _lib.GHOSTTY_KEY_F23
    F24 = _lib.GHOSTTY_KEY_F24
    F25 = _lib.GHOSTTY_KEY_F25
    FN = _lib.GHOSTTY_KEY_FN
    FN_LOCK = _lib.GHOSTTY_KEY_FN_LOCK
    PRINT_SCREEN = _lib.GHOSTTY_KEY_PRINT_SCREEN
    SCROLL_LOCK = _lib.GHOSTTY_KEY_SCROLL_LOCK
    PAUSE = _lib.GHOSTTY_KEY_PAUSE
    BROWSER_BACK = _lib.GHOSTTY_KEY_BROWSER_BACK
    BROWSER_FAVORITES = _lib.GHOSTTY_KEY_BROWSER_FAVORITES
    BROWSER_FORWARD = _lib.GHOSTTY_KEY_BROWSER_FORWARD
    BROWSER_HOME = _lib.GHOSTTY_KEY_BROWSER_HOME
    BROWSER_REFRESH = _lib.GHOSTTY_KEY_BROWSER_REFRESH
    BROWSER_SEARCH = _lib.GHOSTTY_KEY_BROWSER_SEARCH
    BROWSER_STOP = _lib.GHOSTTY_KEY_BROWSER_STOP
    EJECT = _lib.GHOSTTY_KEY_EJECT
    LAUNCH_APP_1 = _lib.GHOSTTY_KEY_LAUNCH_APP_1
    LAUNCH_APP_2 = _lib.GHOSTTY_KEY_LAUNCH_APP_2
    LAUNCH_MAIL = _lib.GHOSTTY_KEY_LAUNCH_MAIL
    MEDIA_PLAY_PAUSE = _lib.GHOSTTY_KEY_MEDIA_PLAY_PAUSE
    MEDIA_SELECT = _lib.GHOSTTY_KEY_MEDIA_SELECT
    MEDIA_STOP = _lib.GHOSTTY_KEY_MEDIA_STOP
    MEDIA_TRACK_NEXT = _lib.GHOSTTY_KEY_MEDIA_TRACK_NEXT
    MEDIA_TRACK_PREVIOUS = _lib.GHOSTTY_KEY_MEDIA_TRACK_PREVIOUS
    POWER = _lib.GHOSTTY_KEY_POWER
    SLEEP = _lib.GHOSTTY_KEY_SLEEP
    AUDIO_VOLUME_DOWN = _lib.GHOSTTY_KEY_AUDIO_VOLUME_DOWN
    AUDIO_VOLUME_MUTE = _lib.GHOSTTY_KEY_AUDIO_VOLUME_MUTE
    AUDIO_VOLUME_UP = _lib.GHOSTTY_KEY_AUDIO_VOLUME_UP
    WAKE_UP = _lib.GHOSTTY_KEY_WAKE_UP
    COPY = _lib.GHOSTTY_KEY_COPY
    CUT = _lib.GHOSTTY_KEY_CUT
    PASTE = _lib.GHOSTTY_KEY_PASTE


def _validate_text(text: str) -> None:
    # The encoder derives modifier sequences from the logical key and mods, so
    # the associated text must be the unmodified character(s). Upstream rejects
    # C0 controls, DEL, and the macOS function-key private-use range; guard them
    # here so misuse is a Python error rather than undefined native behavior.
    if not isinstance(text, str):  # pyright: ignore[reportUnnecessaryIsInstance]
        raise TypeError(f"text must be a str, got {type(text).__name__}")
    for char in text:
        code = ord(char)
        if code <= 0x1F or code == 0x7F:
            raise ValueError(f"text must not contain C0 control characters: {char!r}")
        if 0xF700 <= code <= 0xF8FF:
            raise ValueError(
                f"text must not contain private-use function codes: {char!r}"
            )


@dataclass(frozen=True, slots=True)
class KeyEvent:
    """A single keyboard event, ready to be encoded.

    Attributes:
        key: The physical key.
        mods: The modifiers active for the event.
        action: Whether the key was pressed, released, or is repeating.
        text: The layout-dependent text the key produced (the unmodified
            character, e.g. ``"a"`` for the A key), or ``""`` when the key
            produces no text. Must not contain C0 controls, DEL, or private-use
            function codes.
        unshifted_codepoint: The Unicode codepoint the key produces without
            shift, used by the Kitty protocol's alternate-key reporting, or
            ``None`` to leave it unset.
        consumed_mods: The modifiers already consumed by text composition and so
            excluded from the encoded modifier sequence.
        composing: Whether the event is part of an active dead-key composition.

    Raises:
        TypeError: If ``key``, ``action``, ``mods``, ``consumed_mods``,
            ``text``, ``composing``, or ``unshifted_codepoint`` is not of its
            expected type.
        ValueError: If ``text`` contains a forbidden character or
            ``unshifted_codepoint`` is outside the Unicode range.
    """

    key: Key
    mods: Mods = field(default_factory=lambda: Mods(0))
    action: KeyAction = KeyAction.PRESS
    text: str = ""
    unshifted_codepoint: int | None = None
    consumed_mods: Mods = field(default_factory=lambda: Mods(0))
    composing: bool = False

    def __post_init__(self) -> None:
        # The static types below are advisory; a public constructor is also
        # called from untyped code, so guard the fields whose value reaches the C
        # boundary. This turns a wrong type into a clear Python error at
        # construction instead of a cryptic failure (or garbage) during encoding.
        if not isinstance(self.key, Key):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError(f"key must be a Key, got {type(self.key).__name__}")
        if not isinstance(self.action, KeyAction):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError(
                f"action must be a KeyAction, got {type(self.action).__name__}"
            )
        if not isinstance(self.mods, Mods):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError(f"mods must be a Mods, got {type(self.mods).__name__}")
        if not isinstance(self.consumed_mods, Mods):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError(
                f"consumed_mods must be a Mods, got {type(self.consumed_mods).__name__}"
            )
        if not isinstance(self.composing, bool):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError(
                f"composing must be a bool, got {type(self.composing).__name__}"
            )
        _validate_text(self.text)
        if self.unshifted_codepoint is not None:
            # bool is an int subclass, so exclude it explicitly: True/False are
            # never a meaningful codepoint and would otherwise pass as 1/0.
            if not isinstance(self.unshifted_codepoint, int) or isinstance(  # pyright: ignore[reportUnnecessaryIsInstance]
                self.unshifted_codepoint, bool
            ):
                raise TypeError(
                    "unshifted_codepoint must be an int or None, got "
                    f"{type(self.unshifted_codepoint).__name__}"
                )
            if not (0 <= self.unshifted_codepoint <= _MAX_CODEPOINT):
                raise ValueError(
                    "unshifted_codepoint out of range (0-0x10FFFF): "
                    f"{self.unshifted_codepoint}"
                )


@dataclass(frozen=True, slots=True)
class KeyEncoder:
    """Encodes key events into terminal byte sequences.

    An encoder holds the options that select and tune the output protocol. With
    the defaults it produces the classic (legacy) encoding of a traditional
    terminal; set :attr:`kitty_flags` to a non-empty :class:`KittyFlags` to emit
    the Kitty keyboard protocol instead. The DEC-mode options mirror the terminal
    modes a real terminal would apply.

    Attributes:
        kitty_flags: The Kitty keyboard protocol features to report; empty (the
            default) selects the legacy protocol.
        cursor_key_application: DEC mode 1 — emit application cursor-key
            sequences (``ESC O A``) instead of normal ones (``ESC [ A``).
        keypad_key_application: DEC mode 66 — emit application keypad sequences.
        ignore_keypad_with_numlock: DEC mode 1035 — ignore application keypad
            mode while Num Lock is on.
        alt_esc_prefix: DEC mode 1036 — prefix Alt-modified keys with ESC.
        modify_other_keys_state_2: Enable xterm ``modifyOtherKeys`` mode 2.
        macos_option_as_alt: How the macOS Option key maps to Alt.
        backarrow_key_mode: DEC mode DECBKM — when true, Backspace emits ``0x08``
            instead of the default ``0x7f``.

    Raises:
        TypeError: If ``kitty_flags`` is not a :class:`KittyFlags` or
            ``macos_option_as_alt`` is not an :class:`OptionAsAlt`.
    """

    kitty_flags: KittyFlags = field(default_factory=lambda: KittyFlags(0))
    cursor_key_application: bool = False
    keypad_key_application: bool = False
    ignore_keypad_with_numlock: bool = False
    alt_esc_prefix: bool = False
    modify_other_keys_state_2: bool = False
    macos_option_as_alt: OptionAsAlt = OptionAsAlt.FALSE
    backarrow_key_mode: bool = False

    def __post_init__(self) -> None:
        # Guard the option values that reach the C boundary; see KeyEvent above.
        if not isinstance(self.kitty_flags, KittyFlags):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError(
                "kitty_flags must be a KittyFlags, got "
                f"{type(self.kitty_flags).__name__}"
            )
        if not isinstance(self.macos_option_as_alt, OptionAsAlt):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError(
                "macos_option_as_alt must be an OptionAsAlt, got "
                f"{type(self.macos_option_as_alt).__name__}"
            )

    def encode(self, event: KeyEvent) -> bytes:
        """Encode ``event`` into the terminal byte sequence for this encoder.

        Returns the empty bytes object for events that produce no output, such
        as pressing a bare modifier key.
        """
        encoder_out = _ffi.new("GhosttyKeyEncoder *")
        _result.check(
            _lib.ghostty_key_encoder_new(_ffi.NULL, encoder_out),
            "could not create key encoder",
        )
        encoder = encoder_out[0]
        try:
            self._apply_options(encoder)
            return _encode_event(encoder, event)
        finally:
            _lib.ghostty_key_encoder_free(encoder)

    def _apply_options(self, encoder: Any) -> None:
        setopt = _lib.ghostty_key_encoder_setopt
        bool_options = (
            (
                _lib.GHOSTTY_KEY_ENCODER_OPT_CURSOR_KEY_APPLICATION,
                self.cursor_key_application,
            ),
            (
                _lib.GHOSTTY_KEY_ENCODER_OPT_KEYPAD_KEY_APPLICATION,
                self.keypad_key_application,
            ),
            (
                _lib.GHOSTTY_KEY_ENCODER_OPT_IGNORE_KEYPAD_WITH_NUMLOCK,
                self.ignore_keypad_with_numlock,
            ),
            (_lib.GHOSTTY_KEY_ENCODER_OPT_ALT_ESC_PREFIX, self.alt_esc_prefix),
            (
                _lib.GHOSTTY_KEY_ENCODER_OPT_MODIFY_OTHER_KEYS_STATE_2,
                self.modify_other_keys_state_2,
            ),
            (_lib.GHOSTTY_KEY_ENCODER_OPT_BACKARROW_KEY_MODE, self.backarrow_key_mode),
        )
        for option, value in bool_options:
            setopt(encoder, option, _ffi.new("bool *", value))
        setopt(
            encoder,
            _lib.GHOSTTY_KEY_ENCODER_OPT_KITTY_FLAGS,
            _ffi.new("uint8_t *", self.kitty_flags.value),
        )
        setopt(
            encoder,
            _lib.GHOSTTY_KEY_ENCODER_OPT_MACOS_OPTION_AS_ALT,
            _ffi.new("int *", self.macos_option_as_alt.value),
        )


def _encode_event(encoder: Any, event: KeyEvent) -> bytes:
    event_out = _ffi.new("GhosttyKeyEvent *")
    _result.check(
        _lib.ghostty_key_event_new(_ffi.NULL, event_out),
        "could not create key event",
    )
    raw_event = event_out[0]
    try:
        _lib.ghostty_key_event_set_key(raw_event, event.key.value)
        _lib.ghostty_key_event_set_action(raw_event, event.action.value)
        _lib.ghostty_key_event_set_mods(raw_event, event.mods.value)
        _lib.ghostty_key_event_set_consumed_mods(raw_event, event.consumed_mods.value)
        _lib.ghostty_key_event_set_composing(raw_event, event.composing)
        # The raw event borrows the UTF-8 buffer without copying, so text_buf
        # must outlive the encode call below; the local reference keeps it alive.
        text_buf = _ffi.NULL
        if event.text:
            data = event.text.encode("utf-8")
            text_buf = _ffi.new("char[]", data)
            _lib.ghostty_key_event_set_utf8(raw_event, text_buf, len(data))
        if event.unshifted_codepoint is not None:
            _lib.ghostty_key_event_set_unshifted_codepoint(
                raw_event, event.unshifted_codepoint
            )
        return _encode_raw(encoder, raw_event)
    finally:
        _lib.ghostty_key_event_free(raw_event)


def _encode_raw(encoder: Any, raw_event: Any) -> bytes:
    out_len = _ffi.new("size_t *")
    # A NULL buffer reports the required size: OUT_OF_SPACE with the length when
    # there is output, SUCCESS with length 0 when the event produces none. Any
    # other result is a genuine failure and must raise rather than be read as
    # "no output" (out_len stays zero-initialized on an error).
    sizing = _lib.ghostty_key_encoder_encode(encoder, raw_event, _ffi.NULL, 0, out_len)
    if sizing != _lib.GHOSTTY_OUT_OF_SPACE:
        _result.check(sizing, "could not encode key event")
    needed = out_len[0]
    if needed == 0:
        return b""
    buf = _ffi.new("char[]", needed)
    _result.check(
        _lib.ghostty_key_encoder_encode(encoder, raw_event, buf, needed, out_len),
        "could not encode key event",
    )
    return bytes(_ffi.buffer(buf, out_len[0]))
