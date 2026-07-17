# Positive typesafety pins for the unicode domain.
#
# Never executed: every line is a compile-time assertion. `assert_type` pins the
# type a checker infers for each public expression, so any drift in the unicode
# API's public types turns the suite red. This file must be diagnostic-free under
# every checker.
from __future__ import annotations

from typing import assert_type

from ghostty_vt.unicode import codepoint_width, string_width

# Both width queries return plain integer cell counts.
assert_type(codepoint_width(0x41), int)
assert_type(string_width("hello"), int)
