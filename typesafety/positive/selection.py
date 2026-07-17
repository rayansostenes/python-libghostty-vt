# Positive typesafety pins for the selection domain.
#
# Never executed: every line is a compile-time assertion. `assert_type` pins the
# type a checker infers for each public expression, so any drift in the selection
# API's public types turns the suite red. This file must be diagnostic-free under
# every checker.
from __future__ import annotations

from typing import assert_type

from ghostty_vt import (
    Point,
    PointTag,
    Selection,
    SelectionAdjust,
    SelectionOrder,
    Terminal,
)

term = Terminal(10, 3)
where = Point(PointTag.ACTIVE, 0, 0)

# Every constructor takes a terminal and yields the Selection type.
assert_type(Selection.point_to_point(term, where, where), Selection)
assert_type(Selection.point_to_point(term, where, where, rectangle=True), Selection)
assert_type(Selection.word(term, where), Selection)
assert_type(Selection.word(term, where, boundaries="."), Selection)
assert_type(Selection.word_between(term, where, where), Selection)
assert_type(Selection.word_between(term, where, where, boundaries="."), Selection)
assert_type(Selection.line(term, where), Selection)
assert_type(
    Selection.line(term, where, whitespace="_", semantic_prompt_boundary=True),
    Selection,
)
assert_type(Selection.all(term), Selection)
assert_type(Selection.output(term, where), Selection)

selection = Selection.point_to_point(term, where, where)

# Endpoints, kind, and order read back as their documented types.
assert_type(selection.rectangle, bool)
assert_type(selection.start, Point)
assert_type(selection.end, Point)
assert_type(selection.order, SelectionOrder)

# Text extraction returns str, with keyword-only formatting options.
assert_type(selection.text(), str)
assert_type(selection.text(trim=False, unwrap=True), str)

# Transformations return a new Selection; queries return bool.
assert_type(selection.adjust(SelectionAdjust.LEFT), Selection)
assert_type(selection.ordered(SelectionOrder.FORWARD), Selection)
assert_type(selection.contains(where), bool)
assert_type(where in selection, bool)
assert_type(selection == selection, bool)

# Every SelectionOrder member is assignable to the enum type; a member access
# infers the singleton literal, so the annotated binding is the pin. Dropping or
# renaming any member turns the suite red.
_order_forward: SelectionOrder = SelectionOrder.FORWARD
_order_reverse: SelectionOrder = SelectionOrder.REVERSE
_order_mirrored_forward: SelectionOrder = SelectionOrder.MIRRORED_FORWARD
_order_mirrored_reverse: SelectionOrder = SelectionOrder.MIRRORED_REVERSE

# Likewise for every SelectionAdjust member.
_adjust_left: SelectionAdjust = SelectionAdjust.LEFT
_adjust_right: SelectionAdjust = SelectionAdjust.RIGHT
_adjust_up: SelectionAdjust = SelectionAdjust.UP
_adjust_down: SelectionAdjust = SelectionAdjust.DOWN
_adjust_home: SelectionAdjust = SelectionAdjust.HOME
_adjust_end: SelectionAdjust = SelectionAdjust.END
_adjust_page_up: SelectionAdjust = SelectionAdjust.PAGE_UP
_adjust_page_down: SelectionAdjust = SelectionAdjust.PAGE_DOWN
_adjust_beginning_of_line: SelectionAdjust = SelectionAdjust.BEGINNING_OF_LINE
_adjust_end_of_line: SelectionAdjust = SelectionAdjust.END_OF_LINE
