# Positive typesafety pins for the paste domain.
#
# Never executed: every line is a compile-time assertion. `assert_type` pins the
# type a checker infers for each public expression, so any drift in the paste
# API's public types turns the suite red. This file must be diagnostic-free under
# every checker.
from __future__ import annotations

from typing import assert_type

from ghostty_vt.paste import encode, is_safe

# The safety check reports a bool; encoding produces pty bytes.
assert_type(is_safe("hello"), bool)
assert_type(encode("hello", bracketed=True), bytes)
assert_type(encode("hello", bracketed=False), bytes)
