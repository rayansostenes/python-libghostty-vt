"""Behavioral tests for the key domain, through the public API.

Every assertion observes what a user of ``ghostty_vt`` would see: a key event
constructed idiomatically and encoded to the exact bytes a terminal expects, over
the real cffi path. The raw layer and the C boundary are never touched directly.
The expected byte sequences are the protocol-defined output verified against the
native encoder (e.g. the Kitty ``ESC[57442;5:3u`` sequence upstream pins in its
own encoder test).
"""

from __future__ import annotations

import pytest

from ghostty_vt import (
    Key,
    KeyAction,
    KeyEncoder,
    KeyEvent,
    KittyFlags,
    Mods,
    OptionAsAlt,
)

LEGACY = KeyEncoder()
KITTY_ALL = KeyEncoder(kitty_flags=KittyFlags.ALL)


# --- Legacy encoding: matches a classic terminal ---------------------------


def test_ctrl_c_encodes_to_the_interrupt_byte() -> None:
    assert LEGACY.encode(KeyEvent(Key.C, Mods.CTRL)) == b"\x03"


def test_printable_key_encodes_its_text() -> None:
    assert LEGACY.encode(KeyEvent(Key.A, text="a")) == b"a"


def test_shifted_printable_key_encodes_the_shifted_text() -> None:
    assert LEGACY.encode(KeyEvent(Key.A, Mods.SHIFT, text="A")) == b"A"


def test_enter_encodes_to_carriage_return() -> None:
    assert LEGACY.encode(KeyEvent(Key.ENTER)) == b"\r"


def test_escape_encodes_to_the_escape_byte() -> None:
    assert LEGACY.encode(KeyEvent(Key.ESCAPE)) == b"\x1b"


def test_arrow_up_encodes_the_normal_cursor_sequence() -> None:
    assert LEGACY.encode(KeyEvent(Key.ARROW_UP)) == b"\x1b[A"


def test_home_encodes_its_sequence() -> None:
    assert LEGACY.encode(KeyEvent(Key.HOME)) == b"\x1b[H"


def test_function_key_encodes_its_sequence() -> None:
    assert LEGACY.encode(KeyEvent(Key.F1)) == b"\x1bOP"


def test_shift_tab_encodes_the_back_tab_sequence() -> None:
    assert LEGACY.encode(KeyEvent(Key.TAB, Mods.SHIFT)) == b"\x1b[Z"


def test_backspace_defaults_to_delete() -> None:
    assert LEGACY.encode(KeyEvent(Key.BACKSPACE)) == b"\x7f"


def test_bare_modifier_press_produces_no_output() -> None:
    assert LEGACY.encode(KeyEvent(Key.SHIFT_LEFT)) == b""


# --- Encoder options change the encoding observably ------------------------


def test_cursor_key_application_switches_to_application_sequences() -> None:
    normal = KeyEncoder().encode(KeyEvent(Key.ARROW_UP))
    application = KeyEncoder(cursor_key_application=True).encode(KeyEvent(Key.ARROW_UP))
    assert normal == b"\x1b[A"
    assert application == b"\x1bOA"
    assert normal != application


def test_keypad_application_switches_numpad_sequences() -> None:
    normal = KeyEncoder().encode(KeyEvent(Key.NUMPAD_1))
    application = KeyEncoder(keypad_key_application=True).encode(KeyEvent(Key.NUMPAD_1))
    assert application == b"\x1bOq"
    assert normal != application


def test_backarrow_key_mode_changes_the_backspace_byte() -> None:
    assert (
        KeyEncoder(backarrow_key_mode=True).encode(KeyEvent(Key.BACKSPACE)) == b"\x08"
    )


def test_alt_esc_prefix_with_option_as_alt_prepends_escape() -> None:
    encoder = KeyEncoder(alt_esc_prefix=True, macos_option_as_alt=OptionAsAlt.TRUE)
    event = KeyEvent(Key.A, Mods.ALT, text="a", unshifted_codepoint=ord("a"))
    assert encoder.encode(event) == b"\x1ba"


def test_ignore_keypad_with_numlock_is_accepted() -> None:
    encoder = KeyEncoder(ignore_keypad_with_numlock=True)
    assert encoder.encode(KeyEvent(Key.ENTER)) == b"\r"


def test_modify_other_keys_state_2_is_accepted() -> None:
    encoder = KeyEncoder(modify_other_keys_state_2=True)
    assert encoder.encode(KeyEvent(Key.C, Mods.CTRL)) == b"\x03"


# --- Kitty keyboard protocol ------------------------------------------------


def test_kitty_flags_change_the_encoding_from_legacy() -> None:
    legacy = KeyEncoder().encode(KeyEvent(Key.ESCAPE))
    kitty = KeyEncoder(kitty_flags=KittyFlags.DISAMBIGUATE).encode(KeyEvent(Key.ESCAPE))
    assert legacy == b"\x1b"
    assert kitty == b"\x1b[27u"
    assert legacy != kitty


def test_kitty_reports_ctrl_release_with_event_type() -> None:
    # Upstream pins this exact sequence in its own encoder test: the control
    # key code (57442) with the ctrl modifier (5) and the release event (:3).
    event = KeyEvent(Key.CONTROL_LEFT, Mods.CTRL, action=KeyAction.RELEASE)
    assert KITTY_ALL.encode(event) == b"\x1b[57442;5:3u"


def test_kitty_reports_associated_text() -> None:
    event = KeyEvent(Key.A, text="a", unshifted_codepoint=ord("a"))
    assert KITTY_ALL.encode(event) == b"\x1b[97;;97u"


def test_kitty_ctrl_c_press_uses_the_protocol_form() -> None:
    event = KeyEvent(Key.C, Mods.CTRL, text="c", unshifted_codepoint=ord("c"))
    assert KITTY_ALL.encode(event) == b"\x1b[99;5u"


def test_kitty_report_events_encodes_the_release_event_type() -> None:
    # REPORT_EVENTS makes releases reportable; the ``:3`` suffix is the release
    # event type. Without the flag a bare key release produces no output.
    encoder = KeyEncoder(kitty_flags=KittyFlags.REPORT_EVENTS)
    event = KeyEvent(
        Key.A, text="a", unshifted_codepoint=ord("a"), action=KeyAction.RELEASE
    )
    assert encoder.encode(event) == b"\x1b[97;1:3u"


def test_kitty_report_alternates_encodes_the_shifted_key_code() -> None:
    # REPORT_ALTERNATES appends the shifted layout code after the base code,
    # separated by ``:``, here base ``97`` (a) and shifted ``65`` (A).
    encoder = KeyEncoder(kitty_flags=KittyFlags.REPORT_ALTERNATES)
    event = KeyEvent(Key.A, Mods.SHIFT, text="A", unshifted_codepoint=ord("a"))
    assert encoder.encode(event) == b"\x1b[97:65;2u"


def test_kitty_report_all_encodes_a_plain_key_as_an_escape_sequence() -> None:
    # REPORT_ALL forces every key to the escape-code form; a plain ``a`` that
    # otherwise encodes to its literal byte becomes the ``97u`` sequence.
    encoder = KeyEncoder(kitty_flags=KittyFlags.REPORT_ALL)
    event = KeyEvent(Key.A, text="a", unshifted_codepoint=ord("a"))
    assert encoder.encode(event) == b"\x1b[97u"


def test_kitty_report_associated_encodes_the_text_codepoint() -> None:
    # REPORT_ASSOCIATED appends the associated text codepoint as a third field;
    # here shifted A carries modifier ``2`` and associated codepoint ``65``.
    encoder = KeyEncoder(kitty_flags=KittyFlags.REPORT_ASSOCIATED)
    event = KeyEvent(Key.A, Mods.SHIFT, text="A", unshifted_codepoint=ord("a"))
    assert encoder.encode(event) == b"\x1b[97;2;65u"


def test_kitty_all_enables_every_flag() -> None:
    assert KittyFlags.ALL == (
        KittyFlags.DISAMBIGUATE
        | KittyFlags.REPORT_EVENTS
        | KittyFlags.REPORT_ALTERNATES
        | KittyFlags.REPORT_ALL
        | KittyFlags.REPORT_ASSOCIATED
    )


# --- Key events are immutable, validated Python values ---------------------


def test_key_event_defaults_to_a_press_with_no_modifiers() -> None:
    event = KeyEvent(Key.A)
    assert event.action is KeyAction.PRESS
    assert event.mods is Mods(0)
    assert event.text == ""
    assert event.unshifted_codepoint is None
    assert event.composing is False


def test_key_event_is_immutable() -> None:
    event = KeyEvent(Key.A)
    with pytest.raises(AttributeError):
        event.text = "a"  # type: ignore[misc]


def test_modifiers_combine_as_flags() -> None:
    combined = Mods.CTRL | Mods.SHIFT
    assert Mods.CTRL in combined
    assert Mods.SHIFT in combined
    assert Mods.ALT not in combined


def test_key_event_rejects_a_non_key() -> None:
    with pytest.raises(TypeError, match="key must be a Key"):
        KeyEvent("A")  # type: ignore[arg-type]


def test_key_event_rejects_a_non_action() -> None:
    with pytest.raises(TypeError, match="action must be a KeyAction"):
        KeyEvent(Key.A, action="press")  # type: ignore[arg-type]


def test_key_event_rejects_non_mods() -> None:
    with pytest.raises(TypeError, match="mods must be a Mods"):
        KeyEvent(Key.A, mods=2)  # type: ignore[arg-type]


def test_key_event_rejects_non_mods_consumed() -> None:
    with pytest.raises(TypeError, match="consumed_mods must be a Mods"):
        KeyEvent(Key.A, consumed_mods=2)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad", ["\x00", "a\x1f", "\x7f"])
def test_key_event_rejects_control_characters_in_text(bad: str) -> None:
    with pytest.raises(ValueError, match="C0 control characters"):
        KeyEvent(Key.A, text=bad)


def test_key_event_rejects_private_use_function_codes_in_text() -> None:
    with pytest.raises(ValueError, match="private-use function codes"):
        KeyEvent(Key.A, text="\uf704")


@pytest.mark.parametrize("bad", [b"a", 123, ["a"]])
def test_key_event_rejects_non_str_text(bad: object) -> None:
    with pytest.raises(TypeError, match="text must be a str"):
        KeyEvent(Key.A, text=bad)  # type: ignore[arg-type]


def test_key_event_rejects_non_bool_composing() -> None:
    with pytest.raises(TypeError, match="composing must be a bool"):
        KeyEvent(Key.A, composing=1)  # type: ignore[arg-type]


def test_key_event_accepts_non_ascii_text() -> None:
    assert LEGACY.encode(KeyEvent(Key.UNIDENTIFIED, text="\u00e9")) == "\u00e9".encode()


def test_key_event_accepts_boundary_unshifted_codepoint() -> None:
    assert KeyEvent(Key.A, unshifted_codepoint=0x10FFFF).unshifted_codepoint == 0x10FFFF


@pytest.mark.parametrize("bad", [1.5, True, "97"])
def test_key_event_rejects_non_int_unshifted_codepoint(bad: object) -> None:
    with pytest.raises(TypeError, match="unshifted_codepoint must be an int"):
        KeyEvent(Key.A, unshifted_codepoint=bad)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad", [-1, 0x110000])
def test_key_event_rejects_out_of_range_unshifted_codepoint(bad: int) -> None:
    with pytest.raises(ValueError, match="unshifted_codepoint out of range"):
        KeyEvent(Key.A, unshifted_codepoint=bad)


# --- Encoders are immutable, validated option holders ----------------------


def test_encoder_rejects_non_kitty_flags() -> None:
    with pytest.raises(TypeError, match="kitty_flags must be a KittyFlags"):
        KeyEncoder(kitty_flags=1)  # type: ignore[arg-type]


def test_encoder_rejects_non_option_as_alt() -> None:
    with pytest.raises(TypeError, match="macos_option_as_alt must be an OptionAsAlt"):
        KeyEncoder(macos_option_as_alt=True)  # type: ignore[arg-type]


def test_encoder_is_immutable() -> None:
    encoder = KeyEncoder()
    with pytest.raises(AttributeError):
        encoder.alt_esc_prefix = True  # type: ignore[misc]
