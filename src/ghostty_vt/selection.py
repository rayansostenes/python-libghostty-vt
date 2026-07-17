"""Selection domain: text selections over a terminal's screen state.

This is the idiomatic layer over the upstream ``selection`` domain. A
:class:`Selection` marks a region of a :class:`~ghostty_vt.Terminal`'s screen —
built point-to-point, by word, by line, over the whole screen, or over a command's
output — and yields the plain text of that region with :meth:`Selection.text`.

Selections are created from a terminal through the classmethod constructors
(:meth:`Selection.point_to_point`, :meth:`Selection.word`, :meth:`Selection.line`,
:meth:`Selection.all`, and their siblings), each taking :class:`~ghostty_vt.Point`
coordinates in one of the terminal's coordinate spaces. Adjustments
(:meth:`Selection.adjust`) and reorderings (:meth:`Selection.ordered`) return a new
selection rather than mutating in place, so a selection value is stable once made.

A selection borrows its terminal: it holds no independent lifetime, and every
operation goes through the terminal's handle, so using a selection after its
terminal is closed raises :class:`~ghostty_vt.UseAfterCloseError`.
"""

from __future__ import annotations

import enum
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from ghostty_vt import _raw, _result
from ghostty_vt.types import Point, PointTag

if TYPE_CHECKING:
    from ghostty_vt.terminal import Terminal

__all__ = ["Selection", "SelectionAdjust", "SelectionOrder"]

_ffi = _raw.ffi
_lib = _raw.lib


class SelectionOrder(enum.Enum):
    """The relative order of a selection's start and end within the screen."""

    FORWARD = _lib.GHOSTTY_SELECTION_ORDER_FORWARD
    """Start precedes end in reading order (top-to-bottom, left-to-right)."""

    REVERSE = _lib.GHOSTTY_SELECTION_ORDER_REVERSE
    """End precedes start in reading order."""

    MIRRORED_FORWARD = _lib.GHOSTTY_SELECTION_ORDER_MIRRORED_FORWARD
    """Rectangular selection whose start is the top-right corner."""

    MIRRORED_REVERSE = _lib.GHOSTTY_SELECTION_ORDER_MIRRORED_REVERSE
    """Rectangular selection whose start is the bottom-left corner."""


class SelectionAdjust(enum.Enum):
    """A direction to grow or shrink a selection's active end by."""

    LEFT = _lib.GHOSTTY_SELECTION_ADJUST_LEFT
    """Move the end one cell left."""

    RIGHT = _lib.GHOSTTY_SELECTION_ADJUST_RIGHT
    """Move the end one cell right."""

    UP = _lib.GHOSTTY_SELECTION_ADJUST_UP
    """Move the end one row up."""

    DOWN = _lib.GHOSTTY_SELECTION_ADJUST_DOWN
    """Move the end one row down."""

    HOME = _lib.GHOSTTY_SELECTION_ADJUST_HOME
    """Move the end to the top-left of the screen."""

    END = _lib.GHOSTTY_SELECTION_ADJUST_END
    """Move the end to the bottom-right of the screen."""

    PAGE_UP = _lib.GHOSTTY_SELECTION_ADJUST_PAGE_UP
    """Move the end up by one screen height."""

    PAGE_DOWN = _lib.GHOSTTY_SELECTION_ADJUST_PAGE_DOWN
    """Move the end down by one screen height."""

    BEGINNING_OF_LINE = _lib.GHOSTTY_SELECTION_ADJUST_BEGINNING_OF_LINE
    """Move the end to the start of its row."""

    END_OF_LINE = _lib.GHOSTTY_SELECTION_ADJUST_END_OF_LINE
    """Move the end to the end of its row."""


def _terminal_handle(terminal: Terminal) -> Any:
    # Terminal._handle is the package-internal guarded accessor: it returns the
    # live native handle and raises UseAfterCloseError once the terminal is
    # closed. Reaching across the domain boundary is deliberate — the selection
    # domain operates on a terminal's screen — and routing every access through
    # this one helper keeps that intra-package contract in a single place.
    return terminal._handle()  # pyright: ignore[reportPrivateUsage]


def _point_cdata(point: Point) -> Any:
    p = _ffi.new("GhosttyPoint *")
    p.tag = point.tag.value
    p.value.coordinate.x = point.x
    p.value.coordinate.y = point.y
    return p[0]


def _grid_ref(handle: Any, point: Point) -> Any:
    out = _ffi.new("GhosttyGridRef *")
    result = _lib.ghostty_terminal_grid_ref(handle, _point_cdata(point), out)
    _result.check(result, f"could not resolve grid reference for {point}")
    return out


def _codepoints(chars: Iterable[str] | None) -> tuple[Any, int]:
    if chars is None:
        return _ffi.NULL, 0
    values = [ord(char) for char in chars]
    return _ffi.new("uint32_t[]", values), len(values)


class Selection:
    """A region of a terminal's screen and the text it covers.

    Create a selection with one of the classmethod constructors, then read its
    text with :meth:`text`. A selection borrows the terminal it was made from;
    every operation raises :class:`~ghostty_vt.UseAfterCloseError` once that
    terminal is closed.
    """

    def __init__(self, terminal: Terminal, cdata: Any) -> None:
        # Internal constructor. Use the classmethod factories; `cdata` is a raw
        # `GhosttySelection *` owned by this object and must outlive it.
        self._terminal = terminal
        self._cdata = cdata

    @classmethod
    def _wrap(cls, terminal: Terminal, cdata: Any) -> Selection:
        cdata.size = _ffi.sizeof("GhosttySelection")
        return cls(terminal, cdata)

    @classmethod
    def point_to_point(
        cls,
        terminal: Terminal,
        start: Point,
        end: Point,
        *,
        rectangle: bool = False,
    ) -> Selection:
        """Select the region spanning from ``start`` to ``end``.

        The two points may be given in any order; the selection covers the cells
        between them inclusively. With ``rectangle`` the selection is a column
        block bounded by the two corners instead of a linear text run.

        Args:
            terminal: The terminal whose screen is selected.
            start: One endpoint of the selection.
            end: The other endpoint of the selection.
            rectangle: Whether to select a rectangular block rather than a run.

        Raises:
            UseAfterCloseError: If the terminal has been closed.
            InvalidValueError: If a point lies outside the screen.
        """
        handle = _terminal_handle(terminal)
        start_ref = _grid_ref(handle, start)
        end_ref = _grid_ref(handle, end)
        cdata = _ffi.new("GhosttySelection *")
        cdata.start = start_ref[0]
        cdata.end = end_ref[0]
        cdata.rectangle = rectangle
        return cls._wrap(terminal, cdata)

    @classmethod
    def word(
        cls,
        terminal: Terminal,
        point: Point,
        *,
        boundaries: Iterable[str] | None = None,
    ) -> Selection:
        """Select the whole word under ``point``.

        Word bounds follow upstream's rules: a run of non-whitespace, or a run of
        whitespace when ``point`` is on whitespace. ``boundaries`` adds extra
        characters that split words, so ``"."`` selects ``foo`` in ``foo.bar``.

        Raises:
            UseAfterCloseError: If the terminal has been closed.
            InvalidValueError: If ``point`` lies outside the screen.
        """
        handle = _terminal_handle(terminal)
        boundary_ptr, boundary_len = _codepoints(boundaries)
        options = _ffi.new("GhosttyTerminalSelectWordOptions *")
        options.size = _ffi.sizeof("GhosttyTerminalSelectWordOptions")
        options.ref = _grid_ref(handle, point)[0]
        options.boundary_codepoints = boundary_ptr
        options.boundary_codepoints_len = boundary_len
        cdata = _ffi.new("GhosttySelection *")
        result = _lib.ghostty_terminal_select_word(handle, options, cdata)
        _result.check(result, "could not select word")
        return cls._wrap(terminal, cdata)

    @classmethod
    def word_between(
        cls,
        terminal: Terminal,
        start: Point,
        end: Point,
        *,
        boundaries: Iterable[str] | None = None,
    ) -> Selection:
        """Select the first whole word between ``start`` and ``end``.

        Cells are scanned from ``start`` toward ``end`` and the first word is
        selected whole — a run of whitespace counts as a word, so a scan over
        blanks yields an empty selection. This mirrors a word-granularity drag
        from ``start`` toward ``end``. ``boundaries`` adds extra word-splitting
        characters as in :meth:`word`.

        Raises:
            UseAfterCloseError: If the terminal has been closed.
            InvalidValueError: If a point lies outside the screen.
        """
        handle = _terminal_handle(terminal)
        boundary_ptr, boundary_len = _codepoints(boundaries)
        options = _ffi.new("GhosttyTerminalSelectWordBetweenOptions *")
        options.size = _ffi.sizeof("GhosttyTerminalSelectWordBetweenOptions")
        options.start = _grid_ref(handle, start)[0]
        options.end = _grid_ref(handle, end)[0]
        options.boundary_codepoints = boundary_ptr
        options.boundary_codepoints_len = boundary_len
        cdata = _ffi.new("GhosttySelection *")
        result = _lib.ghostty_terminal_select_word_between(handle, options, cdata)
        _result.check(result, "could not select words between points")
        return cls._wrap(terminal, cdata)

    @classmethod
    def line(
        cls,
        terminal: Terminal,
        point: Point,
        *,
        whitespace: Iterable[str] | None = None,
        semantic_prompt_boundary: bool = False,
    ) -> Selection:
        """Select the whole logical line under ``point``.

        Soft-wrapped rows are joined into one logical line. ``whitespace`` sets
        the characters trimmed from the line's ends; ``semantic_prompt_boundary``
        stops the line at shell prompt markers when the fed program emits them.

        Raises:
            UseAfterCloseError: If the terminal has been closed.
            InvalidValueError: If ``point`` lies outside the screen.
        """
        handle = _terminal_handle(terminal)
        whitespace_ptr, whitespace_len = _codepoints(whitespace)
        options = _ffi.new("GhosttyTerminalSelectLineOptions *")
        options.size = _ffi.sizeof("GhosttyTerminalSelectLineOptions")
        options.ref = _grid_ref(handle, point)[0]
        options.whitespace = whitespace_ptr
        options.whitespace_len = whitespace_len
        options.semantic_prompt_boundary = semantic_prompt_boundary
        cdata = _ffi.new("GhosttySelection *")
        result = _lib.ghostty_terminal_select_line(handle, options, cdata)
        _result.check(result, "could not select line")
        return cls._wrap(terminal, cdata)

    @classmethod
    def all(cls, terminal: Terminal) -> Selection:
        """Select every written cell, from scrollback through the active screen.

        Raises:
            UseAfterCloseError: If the terminal has been closed.
            NoValueError: If the screen holds no written content.
        """
        handle = _terminal_handle(terminal)
        cdata = _ffi.new("GhosttySelection *")
        result = _lib.ghostty_terminal_select_all(handle, cdata)
        _result.check(result, "could not select all content")
        return cls._wrap(terminal, cdata)

    @classmethod
    def output(cls, terminal: Terminal, point: Point) -> Selection:
        """Select the command output surrounding ``point``.

        This needs shell-integration prompt markers in the fed stream to bound
        the output region.

        Raises:
            UseAfterCloseError: If the terminal has been closed.
            InvalidValueError: If ``point`` lies outside the screen.
            NoValueError: If ``point`` is not within a marked output region.
        """
        handle = _terminal_handle(terminal)
        ref = _grid_ref(handle, point)
        cdata = _ffi.new("GhosttySelection *")
        result = _lib.ghostty_terminal_select_output(handle, ref[0], cdata)
        _result.check(result, "could not select output")
        return cls._wrap(terminal, cdata)

    @property
    def rectangle(self) -> bool:
        """Whether this is a rectangular (column-block) selection."""
        return bool(self._cdata.rectangle)

    @property
    def start(self) -> Point:
        """The selection's start cell, in full-screen coordinates."""
        return self._point_of(self._cdata.start)

    @property
    def end(self) -> Point:
        """The selection's end cell, in full-screen coordinates."""
        return self._point_of(self._cdata.end)

    def _point_of(self, grid_ref: Any) -> Point:
        handle = _terminal_handle(self._terminal)
        ref = _ffi.new("GhosttyGridRef *")
        ref[0] = grid_ref
        out = _ffi.new("GhosttyPointCoordinate *")
        result = _lib.ghostty_terminal_point_from_grid_ref(
            handle, ref, _lib.GHOSTTY_POINT_TAG_SCREEN, out
        )
        _result.check(result, "could not resolve selection point")
        return Point(PointTag.SCREEN, int(out.x), int(out.y))

    @property
    def order(self) -> SelectionOrder:
        """How the selection's start and end are ordered on screen."""
        handle = _terminal_handle(self._terminal)
        out = _ffi.new("GhosttySelectionOrder *")
        result = _lib.ghostty_terminal_selection_order(handle, self._cdata, out)
        _result.check(result, "could not query selection order")
        return SelectionOrder(out[0])

    def text(self, *, trim: bool = True, unwrap: bool = False) -> str:
        """Return the plain text the selection covers.

        Args:
            trim: Whether to strip trailing whitespace from each selected row.
            unwrap: Whether to join soft-wrapped rows into single lines instead
                of keeping the on-screen wrapping.

        Raises:
            UseAfterCloseError: If the terminal has been closed.
        """
        handle = _terminal_handle(self._terminal)
        options = _ffi.new("GhosttyTerminalSelectionFormatOptions *")
        options.size = _ffi.sizeof("GhosttyTerminalSelectionFormatOptions")
        options.emit = _lib.GHOSTTY_FORMATTER_FORMAT_PLAIN
        options.unwrap = unwrap
        options.trim = trim
        options.selection = self._cdata

        out_ptr = _ffi.new("uint8_t **")
        out_len = _ffi.new("size_t *")
        result = _lib.ghostty_terminal_selection_format_alloc(
            handle, _ffi.NULL, options[0], out_ptr, out_len
        )
        _result.check(result, "could not format selection text")
        try:
            return bytes(_ffi.buffer(out_ptr[0], out_len[0])).decode("utf-8")
        finally:
            _lib.ghostty_free(_ffi.NULL, out_ptr[0], out_len[0])

    def adjust(self, adjustment: SelectionAdjust) -> Selection:
        """Return a new selection with its end moved by ``adjustment``.

        The original selection is left unchanged.

        Raises:
            UseAfterCloseError: If the terminal has been closed.
        """
        handle = _terminal_handle(self._terminal)
        cdata = _ffi.new("GhosttySelection *")
        cdata[0] = self._cdata[0]
        result = _lib.ghostty_terminal_selection_adjust(handle, cdata, adjustment.value)
        _result.check(result, "could not adjust selection")
        return type(self)(self._terminal, cdata)

    def ordered(self, order: SelectionOrder) -> Selection:
        """Return an equivalent selection whose endpoints follow ``order``.

        The covered region is unchanged; only which endpoint is start and which
        is end may swap.

        Raises:
            UseAfterCloseError: If the terminal has been closed.
        """
        handle = _terminal_handle(self._terminal)
        cdata = _ffi.new("GhosttySelection *")
        result = _lib.ghostty_terminal_selection_ordered(
            handle, self._cdata, order.value, cdata
        )
        _result.check(result, "could not reorder selection")
        return type(self)(self._terminal, cdata)

    def contains(self, point: Point) -> bool:
        """Whether ``point`` falls within the selected region.

        Raises:
            UseAfterCloseError: If the terminal has been closed.
        """
        handle = _terminal_handle(self._terminal)
        out = _ffi.new("bool *")
        result = _lib.ghostty_terminal_selection_contains(
            handle, self._cdata, _point_cdata(point), out
        )
        _result.check(result, "could not test selection membership")
        return bool(out[0])

    def __contains__(self, point: Point) -> bool:
        return self.contains(point)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Selection):
            return NotImplemented
        if other._terminal is not self._terminal:
            return False
        handle = _terminal_handle(self._terminal)
        out = _ffi.new("bool *")
        result = _lib.ghostty_terminal_selection_equal(
            handle, self._cdata, other._cdata, out
        )
        _result.check(result, "could not compare selections")
        return bool(out[0])
