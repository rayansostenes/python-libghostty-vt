# Positive typesafety pins for the formatter domain.
#
# Never executed: every line is a compile-time assertion. `assert_type` pins the
# type a checker infers for each public expression, so any drift in the formatter
# API's public types turns the suite red. This file must be diagnostic-free under
# every checker.
from __future__ import annotations

from typing import assert_type

from ghostty_vt import Format, Terminal

term = Terminal(10, 2)

# Extraction returns text, with keyword-only format and layout options.
assert_type(term.format(), str)
assert_type(term.format(emit=Format.VT), str)
assert_type(term.format(emit=Format.HTML, unwrap=True, trim=False), str)

# Every Format member is assignable to the enum type; the annotated binding is
# the pin (a member access infers the singleton literal).
_plain: Format = Format.PLAIN
_vt: Format = Format.VT
_html: Format = Format.HTML
