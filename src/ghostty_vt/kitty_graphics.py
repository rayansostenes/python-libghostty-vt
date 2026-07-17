"""Kitty graphics domain: inline-image state tracking.

This is the idiomatic layer over the upstream ``kitty_graphics`` domain. Feeding
`Kitty graphics protocol
<https://sw.kovidgoyal.net/kitty/graphics-protocol/>`_ sequences into a
:class:`~ghostty_vt.Terminal` stores images and places them on the screen; this
domain reads that state back out.

A :class:`KittyGraphics` view is obtained from a terminal with
:meth:`~ghostty_vt.Terminal.kitty_graphics`. It is a live view, not a snapshot:
each query reads the terminal's current storage, so a single view reflects images
transmitted, replaced, or deleted by later feeds. Every query returns immutable
value types (:class:`Placement`, :class:`Image`) copied out of the native
storage, so the results stay valid even after the terminal is fed again or
closed.

The storage is per active screen: switching to the alternate screen exposes a
different storage. Coordinates and sizes here are storage state (grid columns and
rows, pixel offsets, and the source rectangle); rendered pixel geometry, which
depends on cell pixel dimensions, is out of scope for this domain.
"""

from __future__ import annotations

import enum
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final

from ghostty_vt import _raw, _result

__all__ = ["Image", "ImageFormat", "KittyGraphics", "Placement"]

_ffi = _raw.ffi
_lib = _raw.lib

# Image IDs are uint32_t in the C API; validate the range up front so a bad ID
# raises a clear ValueError instead of a cffi OverflowError.
_MAX_IMAGE_ID: Final[int] = 0xFFFFFFFF


class ImageFormat(enum.Enum):
    """The pixel format of a stored Kitty graphics image.

    Stored images are always fully decoded, so :attr:`PNG` is never reported by
    :attr:`Image.format`; a transmitted PNG is decoded to :attr:`RGBA` before
    storage. The value exists only for protocol-level completeness.
    """

    RGB = _lib.GHOSTTY_KITTY_IMAGE_FORMAT_RGB
    """24-bit RGB, 3 bytes per pixel."""

    RGBA = _lib.GHOSTTY_KITTY_IMAGE_FORMAT_RGBA
    """32-bit RGBA, 4 bytes per pixel."""

    PNG = _lib.GHOSTTY_KITTY_IMAGE_FORMAT_PNG
    """PNG; never stored (decoded to :attr:`RGBA` on transmission)."""

    GRAY_ALPHA = _lib.GHOSTTY_KITTY_IMAGE_FORMAT_GRAY_ALPHA
    """Grayscale with alpha, 2 bytes per pixel."""

    GRAY = _lib.GHOSTTY_KITTY_IMAGE_FORMAT_GRAY
    """Grayscale, 1 byte per pixel."""


@dataclass(frozen=True, slots=True)
class Image:
    """A decoded image held in a terminal's Kitty graphics storage.

    Attributes:
        id: The image ID assigned by the protocol.
        number: The client-assigned image number, or 0 if none was given.
        width: The image width in pixels.
        height: The image height in pixels.
        format: The pixel format of :attr:`data`; never :attr:`ImageFormat.PNG`.
        generation: A process-wide-unique stamp bumped whenever this image ID is
            added or replaced, so a changed value signals new pixel contents even
            when the dimensions are unchanged.
        data: The raw, fully decoded and decompressed pixels, exactly
            ``width * height * bytes-per-pixel`` bytes for :attr:`format`.
    """

    id: int
    number: int
    width: int
    height: int
    format: ImageFormat
    generation: int
    data: bytes


@dataclass(frozen=True, slots=True)
class Placement:
    """A single placement of an image on the terminal's screen.

    A placement is one occurrence of an image on the screen; the same image ID
    can back several placements. Displaying an image (``a=p`` or ``a=T``) adds a
    placement; ``a=d`` sequences delete them.

    Attributes:
        image_id: The ID of the :class:`Image` this placement displays.
        placement_id: The client-assigned placement ID, or 0 if none was given.
        is_virtual: Whether this is a virtual placement, positioned by unicode
            placeholder cells rather than at a fixed screen location.
        x_offset: Horizontal pixel offset from the left edge of the anchor cell.
        y_offset: Vertical pixel offset from the top edge of the anchor cell.
        source_x: X origin, in image pixels, of the displayed source rectangle.
        source_y: Y origin, in image pixels, of the displayed source rectangle.
        source_width: Width of the source rectangle in pixels; 0 means the full
            image width.
        source_height: Height of the source rectangle in pixels; 0 means the full
            image height.
        columns: Requested width in grid cells, or 0 to size from the image.
        rows: Requested height in grid cells, or 0 to size from the image.
        z: The z-index; higher values draw on top, negatives draw below text.
    """

    image_id: int
    placement_id: int
    is_virtual: bool
    x_offset: int
    y_offset: int
    source_x: int
    source_y: int
    source_width: int
    source_height: int
    columns: int
    rows: int
    z: int


def _placement_get(iterator: Any, key: int, ctype: str) -> Any:
    out = _ffi.new(ctype)
    result = _lib.ghostty_kitty_graphics_placement_get(iterator, key, out)
    _result.check(result, "could not read kitty graphics placement data")
    return out[0]


def _read_placement(iterator: Any) -> Placement:
    def u32(key: int) -> int:
        return int(_placement_get(iterator, key, "uint32_t *"))

    return Placement(
        image_id=u32(_lib.GHOSTTY_KITTY_GRAPHICS_PLACEMENT_DATA_IMAGE_ID),
        placement_id=u32(_lib.GHOSTTY_KITTY_GRAPHICS_PLACEMENT_DATA_PLACEMENT_ID),
        is_virtual=bool(
            _placement_get(
                iterator,
                _lib.GHOSTTY_KITTY_GRAPHICS_PLACEMENT_DATA_IS_VIRTUAL,
                "bool *",
            )
        ),
        x_offset=u32(_lib.GHOSTTY_KITTY_GRAPHICS_PLACEMENT_DATA_X_OFFSET),
        y_offset=u32(_lib.GHOSTTY_KITTY_GRAPHICS_PLACEMENT_DATA_Y_OFFSET),
        source_x=u32(_lib.GHOSTTY_KITTY_GRAPHICS_PLACEMENT_DATA_SOURCE_X),
        source_y=u32(_lib.GHOSTTY_KITTY_GRAPHICS_PLACEMENT_DATA_SOURCE_Y),
        source_width=u32(_lib.GHOSTTY_KITTY_GRAPHICS_PLACEMENT_DATA_SOURCE_WIDTH),
        source_height=u32(_lib.GHOSTTY_KITTY_GRAPHICS_PLACEMENT_DATA_SOURCE_HEIGHT),
        columns=u32(_lib.GHOSTTY_KITTY_GRAPHICS_PLACEMENT_DATA_COLUMNS),
        rows=u32(_lib.GHOSTTY_KITTY_GRAPHICS_PLACEMENT_DATA_ROWS),
        z=int(
            _placement_get(
                iterator, _lib.GHOSTTY_KITTY_GRAPHICS_PLACEMENT_DATA_Z, "int32_t *"
            )
        ),
    )


def _image_get(image: Any, key: int, ctype: str) -> Any:
    out = _ffi.new(ctype)
    result = _lib.ghostty_kitty_graphics_image_get(image, key, out)
    _result.check(result, "could not read kitty graphics image data")
    return out[0]


def _read_image(image: Any) -> Image:
    length = int(_image_get(image, _lib.GHOSTTY_KITTY_IMAGE_DATA_DATA_LEN, "size_t *"))
    data_ptr = _ffi.new("uint8_t **")
    result = _lib.ghostty_kitty_graphics_image_get(
        image, _lib.GHOSTTY_KITTY_IMAGE_DATA_DATA_PTR, data_ptr
    )
    _result.check(result, "could not read kitty graphics image data")

    def u32(key: int) -> int:
        return int(_image_get(image, key, "uint32_t *"))

    return Image(
        id=u32(_lib.GHOSTTY_KITTY_IMAGE_DATA_ID),
        number=u32(_lib.GHOSTTY_KITTY_IMAGE_DATA_NUMBER),
        width=u32(_lib.GHOSTTY_KITTY_IMAGE_DATA_WIDTH),
        height=u32(_lib.GHOSTTY_KITTY_IMAGE_DATA_HEIGHT),
        format=ImageFormat(
            int(_image_get(image, _lib.GHOSTTY_KITTY_IMAGE_DATA_FORMAT, "int *"))
        ),
        generation=int(
            _image_get(image, _lib.GHOSTTY_KITTY_IMAGE_DATA_GENERATION, "uint64_t *")
        ),
        data=bytes(_ffi.buffer(data_ptr[0], length)),
    )


class KittyGraphics:
    """A live view of a terminal's Kitty graphics storage.

    Obtain one with :meth:`~ghostty_vt.Terminal.kitty_graphics`; it is not
    constructed directly. Each query reads the terminal's storage at call time,
    so one view stays current as the terminal is fed, and every query raises
    :class:`~ghostty_vt.UseAfterCloseError` once the terminal is closed.
    """

    def __init__(self, terminal_handle: Callable[[], Any]) -> None:
        # A zero-arg callable returning the live native terminal handle (and
        # raising UseAfterCloseError if the terminal is closed). The borrowed
        # graphics handle is invalidated by any terminal mutation, so it is
        # re-fetched on every query rather than cached.
        self._terminal_handle = terminal_handle

    def _graphics(self) -> Any:
        out = _ffi.new("GhosttyKittyGraphics *")
        result = _lib.ghostty_terminal_get(
            self._terminal_handle(),
            _lib.GHOSTTY_TERMINAL_DATA_KITTY_GRAPHICS,
            out,
        )
        _result.check(result, "could not access kitty graphics storage")
        return out[0]

    @property
    def generation(self) -> int:
        """The storage's content-generation stamp.

        Bumped on every image transmit, replace, placement, or delete, and unique
        and monotonically increasing process-wide. Zero means the storage has
        never been mutated and is therefore empty; an unchanged value since a
        previous read means the images and placements are identical.

        Raises:
            UseAfterCloseError: If the terminal has been closed.
        """
        out = _ffi.new("uint64_t *")
        result = _lib.ghostty_kitty_graphics_get(
            self._graphics(), _lib.GHOSTTY_KITTY_GRAPHICS_DATA_GENERATION, out
        )
        _result.check(result, "could not read kitty graphics generation")
        return int(out[0])

    def placements(self) -> tuple[Placement, ...]:
        """Return every placement currently on the active screen.

        The placements are returned in the storage's own order. The result is a
        snapshot of immutable values, safe to keep across later feeds.

        Raises:
            UseAfterCloseError: If the terminal has been closed.
        """
        graphics = self._graphics()
        out_iterator = _ffi.new("GhosttyKittyGraphicsPlacementIterator *")
        result = _lib.ghostty_kitty_graphics_placement_iterator_new(
            _ffi.NULL, out_iterator
        )
        _result.check(result, "could not create kitty graphics placement iterator")
        iterator = out_iterator[0]
        try:
            result = _lib.ghostty_kitty_graphics_get(
                graphics,
                _lib.GHOSTTY_KITTY_GRAPHICS_DATA_PLACEMENT_ITERATOR,
                out_iterator,
            )
            _result.check(result, "could not read kitty graphics placements")
            iterator = out_iterator[0]
            placements: list[Placement] = []
            while _lib.ghostty_kitty_graphics_placement_next(iterator):
                placements.append(_read_placement(iterator))
            return tuple(placements)
        finally:
            _lib.ghostty_kitty_graphics_placement_iterator_free(iterator)

    def image(self, image_id: int) -> Image | None:
        """Return the stored image with ``image_id``, or ``None`` if there is none.

        Looks up an image by ID directly, so it resolves images that have no
        placement (transmitted with ``a=t``) as well as displayed ones.

        Args:
            image_id: The image ID to look up (0 to 4294967295).

        Raises:
            ValueError: If ``image_id`` is outside 0 to 4294967295.
            UseAfterCloseError: If the terminal has been closed.
        """
        if not 0 <= image_id <= _MAX_IMAGE_ID:
            raise ValueError(
                f"image_id must be between 0 and {_MAX_IMAGE_ID}, got {image_id}"
            )
        image = _lib.ghostty_kitty_graphics_image(self._graphics(), image_id)
        if image == _ffi.NULL:
            return None
        return _read_image(image)
