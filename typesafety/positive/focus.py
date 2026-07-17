# Positive typesafety pins for the focus domain.
#
# Never executed: every line is a compile-time assertion. `assert_type` pins the
# encoder's return type; the enum members are pinned by annotated bindings (a
# member access infers the singleton literal, not the enum). This file must be
# diagnostic-free under every checker.
from __future__ import annotations

from typing import assert_type

import ghostty_vt
from ghostty_vt import FocusEvent
from ghostty_vt.focus import encode

# Encoding a focus report yields pty bytes.
assert_type(encode(FocusEvent.GAINED), bytes)

# Every event member is assignable to the enum type; dropping either turns the
# suite red.
_gained: FocusEvent = FocusEvent.GAINED
_lost: FocusEvent = FocusEvent.LOST

# The top-level re-export is the same enum type.
_top: FocusEvent = ghostty_vt.FocusEvent.GAINED
