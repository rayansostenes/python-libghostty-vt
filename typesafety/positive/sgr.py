# Positive typesafety pins for the SGR domain.
#
# Never executed: every line is a compile-time assertion. `assert_type` pins the
# type a checker infers for each public expression; enum members are pinned by
# annotated bindings (a member access infers the singleton literal, not the
# enum). This file must be diagnostic-free under every checker.
from __future__ import annotations

from typing import assert_type

from ghostty_vt import Rgb
from ghostty_vt.sgr import Attribute, AttributeKind, Underline, Unknown, parse

# Parsing yields an ordered tuple of attributes.
attributes = parse("1;31")
assert_type(attributes, tuple[Attribute, ...])

# An attribute carries its kind and a value whose type depends on the kind.
attribute = Attribute(AttributeKind.BOLD)
assert_type(attribute, Attribute)
assert_type(attribute.kind, AttributeKind)
assert_type(attribute.value, Rgb | int | Underline | Unknown | None)

# The unknown-attribute payload exposes both parameter lists.
unknown = Unknown((1, 99), (99,))
assert_type(unknown, Unknown)
assert_type(unknown.full, tuple[int, ...])
assert_type(unknown.partial, tuple[int, ...])

# Enum members are assignable to their enum type; dropping any turns the suite
# red. One representative member is pinned per value category.
_bold: AttributeKind = AttributeKind.BOLD
_unset: AttributeKind = AttributeKind.UNSET
_unknown_kind: AttributeKind = AttributeKind.UNKNOWN
_fg_rgb: AttributeKind = AttributeKind.DIRECT_COLOR_FG
_fg_256: AttributeKind = AttributeKind.FG_256
_underline_kind: AttributeKind = AttributeKind.UNDERLINE
_curly: Underline = Underline.CURLY
_no_underline: Underline = Underline.NONE
