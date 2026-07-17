# Positive typesafety pins for the key domain.
#
# Never executed: every line is a compile-time assertion. `assert_type` pins the
# type a checker infers for each public expression, so any drift in the key API's
# public types turns the suite red. Enum members are pinned by annotated bindings
# instead (a member access infers the singleton literal, not the enum). This file
# must be diagnostic-free under every checker.
from __future__ import annotations

from typing import assert_type

from ghostty_vt import (
    Key,
    KeyAction,
    KeyEncoder,
    KeyEvent,
    KittyFlags,
    Mods,
    OptionAsAlt,
)

# A key event carries its typed fields.
event = KeyEvent(Key.A)
assert_type(event, KeyEvent)
assert_type(event.key, Key)
assert_type(event.mods, Mods)
assert_type(event.action, KeyAction)
assert_type(event.text, str)
assert_type(event.unshifted_codepoint, int | None)
assert_type(event.consumed_mods, Mods)
assert_type(event.composing, bool)

# Full construction keeps the value type.
assert_type(
    KeyEvent(
        Key.C,
        Mods.CTRL | Mods.SHIFT,
        action=KeyAction.RELEASE,
        text="c",
        unshifted_codepoint=99,
        consumed_mods=Mods.SHIFT,
        composing=False,
    ),
    KeyEvent,
)

# Modifiers and Kitty flags compose with ``|`` to a value of their own flag type
# (pinned by assignment: checkers disagree on whether to narrow the union of
# members, but all agree the result is assignable to the flag type).
_combined_mods: Mods = Mods.CTRL | Mods.SHIFT
_combined_flags: KittyFlags = KittyFlags.DISAMBIGUATE | KittyFlags.REPORT_EVENTS

# An encoder exposes its typed options and encodes to bytes.
encoder = KeyEncoder(kitty_flags=KittyFlags.ALL, macos_option_as_alt=OptionAsAlt.LEFT)
assert_type(encoder, KeyEncoder)
assert_type(encoder.kitty_flags, KittyFlags)
assert_type(encoder.macos_option_as_alt, OptionAsAlt)
assert_type(encoder.cursor_key_application, bool)
assert_type(encoder.encode(event), bytes)

# Every enum is a distinct closed set; dropping a member turns the suite red.
_key: Key = Key.ARROW_UP
_action: KeyAction = KeyAction.PRESS
_mods: Mods = Mods.SUPER
_flags: KittyFlags = KittyFlags.REPORT_ASSOCIATED
_opt: OptionAsAlt = OptionAsAlt.RIGHT
