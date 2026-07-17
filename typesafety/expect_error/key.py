# Expect-error typesafety pins for the key domain.
#
# Never executed. Every statement below is a deliberate misuse of the public API.
# Each line tagged `# expect-error` MUST draw at least one diagnostic from every
# checker; the harness fails if any tagged line stops erroring or if an untagged
# line errors.
from __future__ import annotations

from ghostty_vt import Key, KeyEncoder, KeyEvent, KittyFlags, Mods, OptionAsAlt

KeyEvent()  # expect-error: missing key
KeyEvent(Key.A).does_not_exist  # expect-error: no such attribute
KeyEvent(Key.A, mods=1)  # expect-error: mods must be a Mods, not an int
KeyEvent(Key.A, text=b"a")  # expect-error: text must be a str
Key.DOES_NOT_EXIST  # expect-error: no such enum member
KittyFlags.DOES_NOT_EXIST  # expect-error: no such enum member
KeyEncoder().encode("a")  # expect-error: encode requires a KeyEvent
KeyEncoder(kitty_flags=1)  # expect-error: kitty_flags must be a KittyFlags
KeyEncoder(macos_option_as_alt=True)  # expect-error: not an OptionAsAlt
_mods: OptionAsAlt = Mods.CTRL  # expect-error: Mods is not an OptionAsAlt
_wrong: int = KeyEncoder()  # expect-error: KeyEncoder is not an int
