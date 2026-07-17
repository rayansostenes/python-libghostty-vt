"""Render domain: a snapshot of a terminal's viewport for inspection.

This is the idiomatic layer over the upstream ``render`` domain. A
:class:`RenderState` is updated from a :class:`~ghostty_vt.Terminal` and then
read for the data needed to draw (or diff) a frame: the viewport dimensions and
dirty state, the resolved default and palette colors, and per-cell text, style,
and flattened foreground/background colors.

Unlike the grid-ref domain, the render state resolves palette indices to
concrete :class:`~ghostty_vt.Rgb` colors, so a cell's colors already reflect the
active palette. It owns a native handle, so it is a context manager with a
finalizer fallback.
"""

from __future__ import annotations

import enum
import weakref
from dataclasses import dataclass
from types import TracebackType
from typing import TYPE_CHECKING, Any, Self

from ghostty_vt import _native, _raw, _result
from ghostty_vt.color import Rgb
from ghostty_vt.errors import UseAfterCloseError
from ghostty_vt.style import Style

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = [
    "Dirty",
    "RenderCell",
    "RenderColors",
    "RenderRow",
    "RenderState",
]

_ffi = _raw.ffi
_lib = _raw.lib

_PALETTE_SIZE = 256


class Dirty(enum.Enum):
    """How much of the viewport changed since the render state was last clean."""

    FALSE = _lib.GHOSTTY_RENDER_STATE_DIRTY_FALSE
    """Nothing changed; rendering can be skipped."""

    PARTIAL = _lib.GHOSTTY_RENDER_STATE_DIRTY_PARTIAL
    """Some rows changed; a renderer can redraw them incrementally."""

    FULL = _lib.GHOSTTY_RENDER_STATE_DIRTY_FULL
    """Global state changed; a renderer should redraw everything."""


@dataclass(frozen=True, slots=True)
class RenderColors:
    """The resolved default colors of a render state.

    Attributes:
        background: The default background color.
        foreground: The default foreground color.
        cursor: The explicit cursor color, or ``None`` if unset.
        palette: The active 256-color palette, in palette-index order.
    """

    background: Rgb
    foreground: Rgb
    cursor: Rgb | None
    palette: tuple[Rgb, ...]


@dataclass(frozen=True, slots=True)
class RenderCell:
    """An immutable snapshot of a single cell in a render state.

    Attributes:
        text: The cell's grapheme cluster, or ``""`` for an empty cell.
        style: The cell's visual style.
        foreground: The resolved foreground color, or ``None`` if the cell has no
            explicit foreground (use the render state's default foreground).
        background: The resolved background color, or ``None`` if the cell has no
            explicit background (use the render state's default background).
        selected: Whether the cell is within the current selection.
        has_styling: Whether the cell has any non-default styling.
    """

    text: str
    style: Style
    foreground: Rgb | None
    background: Rgb | None
    selected: bool
    has_styling: bool


@dataclass(frozen=True, slots=True)
class RenderRow:
    """An immutable snapshot of one viewport row in a render state.

    Attributes:
        dirty: Whether the row changed since the render state was last clean.
        cells: The row's cells, in column order.
    """

    dirty: bool
    cells: tuple[RenderCell, ...]


def _rgb_from_cdata(color: Any) -> Rgb:
    return Rgb(color.r, color.g, color.b)


def _free_render(state: Any, iterator: Any, cells: Any) -> None:
    _lib.ghostty_render_state_row_cells_free(cells)
    _lib.ghostty_render_state_row_iterator_free(iterator)
    _lib.ghostty_render_state_free(state)


def _resolved_color(cells: Any, key: int) -> Rgb | None:
    out = _ffi.new("GhosttyColorRgb *")
    result = _lib.ghostty_render_state_row_cells_get(cells, key, out)
    if result == _lib.GHOSTTY_INVALID_VALUE:
        return None
    _result.check(result, "could not read cell color")
    return _rgb_from_cdata(out)


def _cell_text(cells: Any) -> str:
    # Probe with a NULL buffer: an empty cell reports success with length 0, a
    # non-empty cell reports the required byte length. A real error resurfaces
    # from the sized retry's own check below.
    key = _lib.GHOSTTY_RENDER_STATE_ROW_CELLS_DATA_GRAPHEMES_UTF8
    buffer = _ffi.new("GhosttyBuffer *")
    buffer.ptr = _ffi.NULL
    buffer.cap = 0
    buffer.len = 0
    probe = _lib.ghostty_render_state_row_cells_get(cells, key, buffer)
    if probe == _lib.GHOSTTY_SUCCESS:
        return ""
    size = buffer.len
    storage = _ffi.new(f"uint8_t[{size}]")
    buffer.ptr = storage
    buffer.cap = size
    buffer.len = 0
    _result.check(
        _lib.ghostty_render_state_row_cells_get(cells, key, buffer),
        "could not read cell text",
    )
    return bytes(_ffi.buffer(buffer.ptr, buffer.len)).decode("utf-8")


def _cell_bool(cells: Any, key: int) -> bool:
    out = _ffi.new("bool *")
    _result.check(
        _lib.ghostty_render_state_row_cells_get(cells, key, out),
        "could not read cell flag",
    )
    return bool(out[0])


def _cell_style(cells: Any) -> Style:
    style = _ffi.new("GhosttyStyle *")
    style.size = _ffi.sizeof("GhosttyStyle")
    _result.check(
        _lib.ghostty_render_state_row_cells_get(
            cells, _lib.GHOSTTY_RENDER_STATE_ROW_CELLS_DATA_STYLE, style
        ),
        "could not read cell style",
    )
    return _native.read_style(style)


def _read_render_cell(cells: Any) -> RenderCell:
    return RenderCell(
        text=_cell_text(cells),
        style=_cell_style(cells),
        foreground=_resolved_color(
            cells, _lib.GHOSTTY_RENDER_STATE_ROW_CELLS_DATA_FG_COLOR
        ),
        background=_resolved_color(
            cells, _lib.GHOSTTY_RENDER_STATE_ROW_CELLS_DATA_BG_COLOR
        ),
        selected=_cell_bool(cells, _lib.GHOSTTY_RENDER_STATE_ROW_CELLS_DATA_SELECTED),
        has_styling=_cell_bool(
            cells, _lib.GHOSTTY_RENDER_STATE_ROW_CELLS_DATA_HAS_STYLING
        ),
    )


class RenderState:
    """A reusable snapshot of a terminal's viewport.

    Obtain one from :meth:`~ghostty_vt.Terminal.render_state`; it stays bound to
    that terminal. Call :meth:`update` to refresh it, then read the viewport
    dimensions, :attr:`dirty` state, :attr:`colors`, and :meth:`grid`. Reading
    before the first update, or reading row data captured before a later update,
    is unsupported; call :meth:`update` first and read the fresh :meth:`grid`.

    The state owns native resources; use it as a context manager or rely on the
    finalizer to release them.
    """

    def __init__(self, terminal: Callable[[], Any]) -> None:
        # `terminal` is the bound terminal's liveness-checked handle getter; it
        # keeps the terminal alive and raises if it has been closed.
        self._terminal = terminal
        cleanup: list[Callable[[], object]] = []
        try:
            state = _ffi.new("GhosttyRenderState *")
            _result.check(
                _lib.ghostty_render_state_new(_ffi.NULL, state),
                "could not create render state",
            )
            cleanup.append(lambda: _lib.ghostty_render_state_free(state[0]))
            iterator = _ffi.new("GhosttyRenderStateRowIterator *")
            _result.check(
                _lib.ghostty_render_state_row_iterator_new(_ffi.NULL, iterator),
                "could not create render row iterator",
            )
            cleanup.append(
                lambda: _lib.ghostty_render_state_row_iterator_free(iterator[0])
            )
            cells = _ffi.new("GhosttyRenderStateRowCells *")
            _result.check(
                _lib.ghostty_render_state_row_cells_new(_ffi.NULL, cells),
                "could not create render row cells",
            )
        except BaseException:  # pragma: no cover - native allocation failure
            for free in reversed(cleanup):
                free()
            raise
        self._iterator_ptr = iterator
        self._cells_ptr = cells
        self._state: Any = state[0]
        self._iterator: Any = iterator[0]
        self._cells: Any = cells[0]
        self._finalizer = weakref.finalize(
            self, _free_render, self._state, self._iterator, self._cells
        )

    def _handle(self) -> Any:
        if not self._finalizer.alive:
            raise UseAfterCloseError("operation on a closed RenderState")
        return self._state

    def update(self) -> None:
        """Refresh this render state from its terminal's current viewport.

        Existing :class:`RenderRow` snapshots from a previous :meth:`grid` stay
        valid; they are immutable copies. Call :meth:`grid` again to read the
        refreshed viewport.

        Raises:
            UseAfterCloseError: If the render state or its terminal has been
                closed.
        """
        _result.check(
            _lib.ghostty_render_state_update(self._handle(), self._terminal()),
            "could not update render state",
        )

    def _get_u16(self, key: int) -> int:
        out = _ffi.new("uint16_t *")
        _result.check(
            _lib.ghostty_render_state_get(self._handle(), key, out),
            "could not read render state data",
        )
        return int(out[0])

    @property
    def cols(self) -> int:
        """The viewport width in cells."""
        return self._get_u16(_lib.GHOSTTY_RENDER_STATE_DATA_COLS)

    @property
    def rows(self) -> int:
        """The viewport height in cells."""
        return self._get_u16(_lib.GHOSTTY_RENDER_STATE_DATA_ROWS)

    @property
    def dirty(self) -> Dirty:
        """The viewport's dirty state as of the last :meth:`update`."""
        out = _ffi.new("GhosttyRenderStateDirty *")
        _result.check(
            _lib.ghostty_render_state_get(
                self._handle(), _lib.GHOSTTY_RENDER_STATE_DATA_DIRTY, out
            ),
            "could not read render dirty state",
        )
        return Dirty(out[0])

    @property
    def colors(self) -> RenderColors:
        """The render state's resolved default and palette colors."""
        out = _ffi.new("GhosttyRenderStateColors *")
        out.size = _ffi.sizeof("GhosttyRenderStateColors")
        _result.check(
            _lib.ghostty_render_state_colors_get(self._handle(), out),
            "could not read render colors",
        )
        cursor = _rgb_from_cdata(out.cursor) if out.cursor_has_value else None
        palette = tuple(_rgb_from_cdata(out.palette[i]) for i in range(_PALETTE_SIZE))
        return RenderColors(
            background=_rgb_from_cdata(out.background),
            foreground=_rgb_from_cdata(out.foreground),
            cursor=cursor,
            palette=palette,
        )

    def grid(self) -> tuple[RenderRow, ...]:
        """Return the viewport's rows and cells as immutable snapshots.

        Each call materializes the current render state fully, so the result
        stays valid across later :meth:`update` calls.

        Raises:
            UseAfterCloseError: If the render state has been closed.
        """
        _result.check(
            _lib.ghostty_render_state_get(
                self._handle(),
                _lib.GHOSTTY_RENDER_STATE_DATA_ROW_ITERATOR,
                self._iterator_ptr,
            ),
            "could not read render rows",
        )
        rows: list[RenderRow] = []
        while _lib.ghostty_render_state_row_iterator_next(self._iterator):
            dirty = _ffi.new("bool *")
            _result.check(
                _lib.ghostty_render_state_row_get(
                    self._iterator, _lib.GHOSTTY_RENDER_STATE_ROW_DATA_DIRTY, dirty
                ),
                "could not read row dirty state",
            )
            _result.check(
                _lib.ghostty_render_state_row_get(
                    self._iterator,
                    _lib.GHOSTTY_RENDER_STATE_ROW_DATA_CELLS,
                    self._cells_ptr,
                ),
                "could not read row cells",
            )
            cells: list[RenderCell] = []
            while _lib.ghostty_render_state_row_cells_next(self._cells):
                cells.append(_read_render_cell(self._cells))
            rows.append(RenderRow(dirty=bool(dirty[0]), cells=tuple(cells)))
        return tuple(rows)

    def close(self) -> None:
        """Release the native render-state resources.

        Idempotent: closing an already-closed render state does nothing.
        """
        self._finalizer()

    def __enter__(self) -> Self:
        self._handle()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
