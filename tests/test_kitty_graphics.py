"""Behavioral tests for the kitty graphics domain, through the public API.

Every assertion observes what a user of ``ghostty_vt`` would see: Kitty graphics
protocol sequences fed into a real terminal, and the resulting image and
placement state read back across the full cffi path. Images are transmitted in
the direct RGB/RGBA formats so the tests need no PNG decoder.
"""

from __future__ import annotations

import base64
from collections.abc import Callable

import pytest

from ghostty_vt import ImageFormat, KittyGraphics, Terminal, UseAfterCloseError

_RED = bytes([255, 0, 0])


def _transmit(
    *, action: str = "T", image_id: int = 1, extra: str = "", pixels: bytes = _RED
) -> bytes:
    """Build a Kitty graphics escape for a 1x1 RGB pixel.

    ``action`` is the ``a=`` verb (``T`` transmits and displays, ``t`` only
    transmits). ``q=2`` suppresses the protocol response so no write callback is
    needed. ``extra`` appends further comma-separated key/value pairs.
    """
    payload = base64.b64encode(pixels).decode("ascii")
    prefix = f"a={action},f=24,s=1,v=1,i={image_id},q=2"
    if extra:
        prefix = f"{prefix},{extra}"
    return f"\x1b_G{prefix};{payload}\x1b\\".encode()


def test_kitty_graphics_returns_a_view() -> None:
    with Terminal(80, 24) as term:
        assert isinstance(term.kitty_graphics(), KittyGraphics)


def test_empty_storage_reports_zero_generation() -> None:
    with Terminal(80, 24) as term:
        assert term.kitty_graphics().generation == 0


def test_empty_storage_has_no_placements() -> None:
    with Terminal(80, 24) as term:
        assert term.kitty_graphics().placements() == ()


def test_transmitting_and_displaying_creates_a_placement() -> None:
    with Terminal(80, 24) as term:
        graphics = term.kitty_graphics()
        term.feed(_transmit(image_id=1))
        placements = graphics.placements()
        assert len(placements) == 1
        assert placements[0].image_id == 1
        assert placements[0].is_virtual is False


def test_transmitting_advances_the_generation() -> None:
    with Terminal(80, 24) as term:
        graphics = term.kitty_graphics()
        term.feed(_transmit())
        assert graphics.generation > 0


def test_displayed_image_is_queryable() -> None:
    with Terminal(80, 24) as term:
        graphics = term.kitty_graphics()
        term.feed(_transmit(image_id=1))
        image = graphics.image(1)
        assert image is not None
        assert image.id == 1
        assert image.width == 1
        assert image.height == 1
        assert image.format is ImageFormat.RGB
        assert image.data == _RED
        assert image.generation > 0


def test_image_carries_rgba_pixels() -> None:
    rgba = bytes([10, 20, 30, 255] * 4)
    with Terminal(80, 24) as term:
        graphics = term.kitty_graphics()
        # A 2x2 RGBA image (f=32) transmitted and displayed.
        payload = base64.b64encode(rgba).decode("ascii")
        term.feed(f"\x1b_Ga=T,f=32,s=2,v=2,i=1,q=2;{payload}\x1b\\".encode())
        image = graphics.image(1)
        assert image is not None
        assert image.format is ImageFormat.RGBA
        assert (image.width, image.height) == (2, 2)
        assert image.data == rgba


def test_placement_keeps_explicit_id_and_z() -> None:
    with Terminal(80, 24) as term:
        graphics = term.kitty_graphics()
        term.feed(_transmit(image_id=3, extra="p=9,z=5"))
        (placement,) = graphics.placements()
        assert placement.placement_id == 9
        assert placement.z == 5


def test_placement_records_requested_columns_and_rows() -> None:
    with Terminal(80, 24) as term:
        graphics = term.kitty_graphics()
        term.feed(_transmit(extra="c=3,r=2"))
        (placement,) = graphics.placements()
        assert placement.columns == 3
        assert placement.rows == 2


def test_placement_records_the_source_rectangle() -> None:
    pixels = bytes([1, 2, 3] * 4)  # 2x2 RGB
    with Terminal(80, 24) as term:
        graphics = term.kitty_graphics()
        payload = base64.b64encode(pixels).decode("ascii")
        term.feed(
            f"\x1b_Ga=T,f=24,s=2,v=2,i=1,x=1,y=0,w=1,h=1,q=2;{payload}\x1b\\".encode()
        )
        (placement,) = graphics.placements()
        assert (placement.source_x, placement.source_y) == (1, 0)
        assert (placement.source_width, placement.source_height) == (1, 1)


def test_default_placement_source_rectangle_is_the_full_image() -> None:
    with Terminal(80, 24) as term:
        graphics = term.kitty_graphics()
        term.feed(_transmit())
        (placement,) = graphics.placements()
        assert placement.source_width == 0
        assert placement.source_height == 0


def test_unicode_placeholder_placement_is_virtual() -> None:
    with Terminal(80, 24) as term:
        graphics = term.kitty_graphics()
        term.feed(_transmit(image_id=2, extra="U=1"))
        (placement,) = graphics.placements()
        assert placement.is_virtual is True


def test_multiple_displays_produce_multiple_placements() -> None:
    with Terminal(80, 24) as term:
        graphics = term.kitty_graphics()
        term.feed(_transmit(image_id=1, extra="p=1"))
        term.feed(_transmit(image_id=1, extra="p=2"))
        placement_ids = {p.placement_id for p in graphics.placements()}
        assert placement_ids == {1, 2}


def test_transmit_only_image_has_no_placement() -> None:
    with Terminal(80, 24) as term:
        graphics = term.kitty_graphics()
        term.feed(_transmit(action="t", image_id=5))
        assert graphics.placements() == ()


def test_transmit_only_image_is_queryable_by_id() -> None:
    with Terminal(80, 24) as term:
        graphics = term.kitty_graphics()
        term.feed(_transmit(action="t", image_id=5))
        image = graphics.image(5)
        assert image is not None
        assert image.id == 5


def test_image_lookup_returns_none_for_unknown_id() -> None:
    with Terminal(80, 24) as term:
        assert term.kitty_graphics().image(999) is None


@pytest.mark.parametrize("image_id", [-1, 0x1_0000_0000])
def test_image_lookup_rejects_out_of_range_id(image_id: int) -> None:
    with Terminal(80, 24) as term:
        graphics = term.kitty_graphics()
        with pytest.raises(ValueError, match="image_id must be between 0 and"):
            graphics.image(image_id)


def test_retransmitting_an_image_changes_its_generation() -> None:
    with Terminal(80, 24) as term:
        graphics = term.kitty_graphics()
        term.feed(_transmit(image_id=1))
        first = graphics.image(1)
        assert first is not None
        term.feed(_transmit(image_id=1))
        second = graphics.image(1)
        assert second is not None
        assert second.generation != first.generation


def test_deleting_all_placements_clears_them() -> None:
    with Terminal(80, 24) as term:
        graphics = term.kitty_graphics()
        term.feed(_transmit())
        assert graphics.placements() != ()
        term.feed(b"\x1b_Ga=d\x1b\\")
        assert graphics.placements() == ()


def test_deleting_an_image_removes_it_from_storage() -> None:
    with Terminal(80, 24) as term:
        graphics = term.kitty_graphics()
        term.feed(_transmit(image_id=1))
        assert graphics.image(1) is not None
        # a=d,d=I,i=1 deletes image 1 and its placements entirely.
        term.feed(b"\x1b_Ga=d,d=I,i=1\x1b\\")
        assert graphics.image(1) is None


def test_deletion_advances_the_generation() -> None:
    with Terminal(80, 24) as term:
        graphics = term.kitty_graphics()
        term.feed(_transmit())
        before = graphics.generation
        term.feed(b"\x1b_Ga=d\x1b\\")
        assert graphics.generation > before


def test_view_reflects_feeds_after_it_was_obtained() -> None:
    with Terminal(80, 24) as term:
        graphics = term.kitty_graphics()
        assert graphics.placements() == ()
        term.feed(_transmit())
        assert len(graphics.placements()) == 1


_QUERIES: list[Callable[[KittyGraphics], object]] = [
    lambda g: g.generation,
    lambda g: g.placements(),
    lambda g: g.image(1),
]


@pytest.mark.parametrize("query", _QUERIES)
def test_queries_after_terminal_close_raise(
    query: Callable[[KittyGraphics], object],
) -> None:
    term = Terminal(80, 24)
    graphics = term.kitty_graphics()
    term.close()
    with pytest.raises(UseAfterCloseError):
        query(graphics)
