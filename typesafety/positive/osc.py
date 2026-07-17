# Positive typesafety pins for the OSC domain.
#
# Never executed: every line is a compile-time assertion. `assert_type` pins the
# type a checker infers for each public expression; enum members are pinned by
# annotated bindings (a member access infers the singleton literal, not the
# enum). This file must be diagnostic-free under every checker.
from __future__ import annotations

from typing import assert_type

from ghostty_vt.osc import Command, CommandType, parse

# Parsing a payload yields a single typed command.
command = parse(b"0;title")
assert_type(command, Command)
assert_type(command.type, CommandType)
assert_type(command.title, str | None)

# Enum members are assignable to their enum type; dropping any turns the suite
# red. A representative set is pinned.
_invalid: CommandType = CommandType.INVALID
_title: CommandType = CommandType.CHANGE_WINDOW_TITLE
_hyperlink: CommandType = CommandType.HYPERLINK_START
_clipboard: CommandType = CommandType.CLIPBOARD_CONTENTS
