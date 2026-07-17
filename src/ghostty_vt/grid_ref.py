"""Grid-ref domain: resolved references to terminal cell positions.

This is the idiomatic layer over the upstream ``grid_ref`` domain. A grid
reference names a specific cell position in the terminal and reads out that
cell's contents: its :class:`~ghostty_vt.style.Style`, grapheme text, hyperlink,
and layout attributes, all captured by the :class:`Cell` snapshot.

References come in two flavours, obtained from the terminal:

* :class:`GridRef` (from :meth:`~ghostty_vt.Terminal.grid_ref`) is an untracked
  snapshot of a position. It is only valid until the next terminal mutation, so
  read from it immediately.
* :class:`TrackedGridRef` (from :meth:`~ghostty_vt.Terminal.track_grid_ref`)
  follows its cell across scrolling, reflow, and other mutations. It owns a
  native handle, so it is a context manager with a finalizer fallback.
"""

from __future__ import annotations

import enum
import weakref
from dataclasses import dataclass
from types import TracebackType
from typing import TYPE_CHECKING, Any, Self

from ghostty_vt import _native, _raw, _result
from ghostty_vt.errors import UseAfterCloseError
from ghostty_vt.style import Style
from ghostty_vt.types import Point, PointTag

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["Cell", "CellWidth", "GridRef", "SemanticContent", "TrackedGridRef"]

_ffi = _raw.ffi
_lib = _raw.lib


class CellWidth(enum.Enum):
    """How wide a cell is and whether it is a spacer for a wide character."""

    NARROW = _lib.GHOSTTY_CELL_WIDE_NARROW
    """A normal single-width cell."""

    WIDE = _lib.GHOSTTY_CELL_WIDE_WIDE
    """A double-width character occupying two cells."""

    SPACER_TAIL = _lib.GHOSTTY_CELL_WIDE_SPACER_TAIL
    """The trailing spacer cell after a wide character; not rendered."""

    SPACER_HEAD = _lib.GHOSTTY_CELL_WIDE_SPACER_HEAD
    """A spacer at the end of a soft-wrapped line before a wide character."""


class SemanticContent(enum.Enum):
    """The semantic role of a cell, set by OSC 133 shell-integration sequences."""

    OUTPUT = _lib.GHOSTTY_CELL_SEMANTIC_OUTPUT
    """Regular command output."""

    INPUT = _lib.GHOSTTY_CELL_SEMANTIC_INPUT
    """Text that is part of user input."""

    PROMPT = _lib.GHOSTTY_CELL_SEMANTIC_PROMPT
    """Text that is part of a shell prompt."""


@dataclass(frozen=True, slots=True)
class Cell:
    """An immutable snapshot of a single terminal cell.

    Attributes:
        text: The cell's grapheme cluster, or ``""`` for an empty cell.
        style: The cell's visual style.
        width: The cell's width classification.
        protected: Whether the cell is protected from selective erase.
        semantic: The cell's semantic role from shell integration.
        hyperlink: The cell's hyperlink URI, or ``None`` if it has no hyperlink.
    """

    text: str
    style: Style
    width: CellWidth
    protected: bool
    semantic: SemanticContent
    hyperlink: str | None


def _point_cdata(point: Point) -> Any:
    cdata = _ffi.new("GhosttyPoint *")
    cdata.tag = point.tag.value
    cdata.value.coordinate.x = point.x
    cdata.value.coordinate.y = point.y
    return cdata


def _graphemes(ref: Any) -> str:
    # Probe with a NULL buffer: an empty cell reports success with length 0, a
    # non-empty cell reports the required length. A real error (a NULL-node ref)
    # resurfaces from the sized retry's own check below.
    out_len = _ffi.new("size_t *")
    probe = _lib.ghostty_grid_ref_graphemes(ref, _ffi.NULL, 0, out_len)
    if probe == _lib.GHOSTTY_SUCCESS:
        return ""
    count = out_len[0]
    buf = _ffi.new(f"uint32_t[{count}]")
    _result.check(
        _lib.ghostty_grid_ref_graphemes(ref, buf, count, out_len),
        "could not read cell graphemes",
    )
    return "".join(chr(buf[i]) for i in range(out_len[0]))


def _hyperlink(ref: Any) -> str | None:
    # Same NULL-buffer probe as _graphemes: no hyperlink reports success with
    # length 0, otherwise the required byte length is written for the retry.
    out_len = _ffi.new("size_t *")
    probe = _lib.ghostty_grid_ref_hyperlink_uri(ref, _ffi.NULL, 0, out_len)
    if probe == _lib.GHOSTTY_SUCCESS:
        return None
    count = out_len[0]
    buf = _ffi.new(f"uint8_t[{count}]")
    _result.check(
        _lib.ghostty_grid_ref_hyperlink_uri(ref, buf, count, out_len),
        "could not read cell hyperlink",
    )
    return bytes(_ffi.buffer(buf, out_len[0])).decode("utf-8")


def _cell_attr(ref: Any, key: int, ctype: str) -> Any:
    cell = _ffi.new("GhosttyCell *")
    _result.check(_lib.ghostty_grid_ref_cell(ref, cell), "could not read cell")
    out = _ffi.new(ctype)
    _result.check(_lib.ghostty_cell_get(cell[0], key, out), "could not read cell data")
    return out[0]


def _read_style(ref: Any) -> Style:
    style = _ffi.new("GhosttyStyle *")
    style.size = _ffi.sizeof("GhosttyStyle")
    _result.check(_lib.ghostty_grid_ref_style(ref, style), "could not read cell style")
    return _native.read_style(style)


def _read_cell(ref: Any) -> Cell:
    width = _cell_attr(ref, _lib.GHOSTTY_CELL_DATA_WIDE, "GhosttyCellWide *")
    protected = _cell_attr(ref, _lib.GHOSTTY_CELL_DATA_PROTECTED, "bool *")
    semantic = _cell_attr(ref, _lib.GHOSTTY_CELL_DATA_SEMANTIC_CONTENT, "int *")
    return Cell(
        text=_graphemes(ref),
        style=_read_style(ref),
        width=CellWidth(width),
        protected=bool(protected),
        semantic=SemanticContent(semantic),
        hyperlink=_hyperlink(ref),
    )


def _point_from_ref(handle: Any, ref: Any, tag: PointTag) -> Point | None:
    coord = _ffi.new("GhosttyPointCoordinate *")
    result = _lib.ghostty_terminal_point_from_grid_ref(handle, ref, tag.value, coord)
    if result == _lib.GHOSTTY_NO_VALUE:
        return None
    _result.check(result, "could not convert grid reference to point")
    return Point(tag, int(coord.x), int(coord.y))


class GridRef:
    """An untracked snapshot reference to a terminal cell position.

    Obtained from :meth:`~ghostty_vt.Terminal.grid_ref`. The reference is only
    valid until the next terminal mutation, so read from it immediately with
    :meth:`cell` or :meth:`point`.
    """

    def __init__(self, handle: Callable[[], Any], ref: Any) -> None:
        # `handle` is the owning terminal's liveness-checked handle getter; it
        # keeps the terminal alive and raises if it has been closed.
        self._handle = handle
        self._ref = ref

    def cell(self) -> Cell:
        """Read the cell at this position as an immutable :class:`Cell`."""
        return _read_cell(self._ref)

    def point(self, tag: PointTag) -> Point | None:
        """Convert this reference to a point in the ``tag`` coordinate space.

        Returns ``None`` if the position cannot be represented in the requested
        space, for example an active-area cell has no history coordinate.

        Raises:
            UseAfterCloseError: If the owning terminal has been closed.
        """
        return _point_from_ref(self._handle(), self._ref, tag)


class TrackedGridRef:
    """A tracked reference that follows its cell across terminal mutations.

    Obtained from :meth:`~ghostty_vt.Terminal.track_grid_ref`. Unlike a
    :class:`GridRef`, it survives scrolling, reflow, and scrollback pruning: the
    reference is updated automatically. It owns a native handle, so use it as a
    context manager or rely on the finalizer to release the handle.

    A tracked reference can still lose its cell (for example when its row is
    pruned from scrollback). In that state :attr:`has_value` is ``False`` and the
    lookups return ``None``; the reference can be repointed with :meth:`move_to`.
    """

    def __init__(self, handle: Callable[[], Any], tracked: Any) -> None:
        self._handle = handle
        self._tracked = tracked
        self._finalizer = weakref.finalize(
            self, _lib.ghostty_tracked_grid_ref_free, tracked
        )

    def _live(self) -> Any:
        if not self._finalizer.alive:
            raise UseAfterCloseError("operation on a closed TrackedGridRef")
        return self._tracked

    @property
    def has_value(self) -> bool:
        """Whether the reference currently points at a meaningful cell.

        Raises:
            UseAfterCloseError: If the reference has been closed.
        """
        return bool(_lib.ghostty_tracked_grid_ref_has_value(self._live()))

    def point(self, tag: PointTag) -> Point | None:
        """Convert this reference to a point in the ``tag`` coordinate space.

        Returns ``None`` if the reference has lost its cell or cannot be
        represented in the requested space.

        Raises:
            UseAfterCloseError: If the reference has been closed.
        """
        coord = _ffi.new("GhosttyPointCoordinate *")
        result = _lib.ghostty_tracked_grid_ref_point(self._live(), tag.value, coord)
        if result == _lib.GHOSTTY_NO_VALUE:
            return None
        _result.check(result, "could not convert tracked reference to point")
        return Point(tag, int(coord.x), int(coord.y))

    def snapshot(self) -> GridRef | None:
        """Snapshot into an untracked :class:`GridRef`, or ``None`` if lost.

        The returned reference has the same short lifetime as any
        :class:`GridRef`: read from it immediately.

        Raises:
            UseAfterCloseError: If the reference has been closed.
        """
        out = _ffi.new("GhosttyGridRef *")
        result = _lib.ghostty_tracked_grid_ref_snapshot(self._live(), out)
        if result == _lib.GHOSTTY_NO_VALUE:
            return None
        _result.check(result, "could not snapshot tracked reference")
        return GridRef(self._handle, out)

    def cell(self) -> Cell | None:
        """Read the referenced cell as a :class:`Cell`, or ``None`` if lost.

        Raises:
            UseAfterCloseError: If the reference has been closed.
        """
        snapshot = self.snapshot()
        if snapshot is None:
            return None
        return snapshot.cell()

    def move_to(self, point: Point) -> None:
        """Repoint the reference at ``point`` in the terminal's active screen.

        Clears any prior lost-cell state on success.

        Raises:
            UseAfterCloseError: If the reference or its terminal has been closed.
        """
        _result.check(
            _lib.ghostty_tracked_grid_ref_set(
                self._live(), self._handle(), _point_cdata(point)[0]
            ),
            "could not move tracked reference",
        )

    def close(self) -> None:
        """Release the native tracked-reference handle.

        Idempotent: closing an already-closed reference does nothing.
        """
        self._finalizer()

    def __enter__(self) -> Self:
        self._live()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()


def resolve(handle: Callable[[], Any], point: Point) -> GridRef:
    """Resolve ``point`` into an untracked :class:`GridRef` (internal)."""
    out = _ffi.new("GhosttyGridRef *")
    _result.check(
        _lib.ghostty_terminal_grid_ref(handle(), _point_cdata(point)[0], out),
        "could not resolve grid reference",
    )
    return GridRef(handle, out)


def track(handle: Callable[[], Any], point: Point) -> TrackedGridRef:
    """Resolve ``point`` into an owned :class:`TrackedGridRef` (internal)."""
    out = _ffi.new("GhosttyTrackedGridRef *")
    _result.check(
        _lib.ghostty_terminal_grid_ref_track(handle(), _point_cdata(point)[0], out),
        "could not track grid reference",
    )
    return TrackedGridRef(handle, out[0])
