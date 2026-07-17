# Positive typesafety pins for the terminal domain.
#
# Never executed: every line is a compile-time assertion. `assert_type` pins the
# type a checker infers for each public expression, so any drift in the terminal
# API's public types turns the suite red. This file must be diagnostic-free under
# every checker.
from __future__ import annotations

from typing import assert_type

from ghostty_vt import Terminal

# Construction takes cell dimensions and yields the terminal type.
term = Terminal(80, 24)
assert_type(term, Terminal)

# Dimensions read back as integers.
assert_type(term.cols, int)
assert_type(term.rows, int)

# Feeding takes bytes and returns nothing; reading text returns str.
assert_type(term.feed(b"hello"), None)
assert_type(term.visible_text(), str)

# Resizing takes dimensions and returns nothing.
assert_type(term.resize(100, 40), None)

# Lifecycle: explicit close, and use as a context manager binding the terminal.
assert_type(term.close(), None)
with Terminal(10, 3) as managed:
    assert_type(managed, Terminal)
