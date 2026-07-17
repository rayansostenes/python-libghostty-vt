"""Behavioral tests for the shared value types, through the public API."""

from __future__ import annotations

import pytest

from ghostty_vt import Mods, Point, PointTag, SurfacePosition


def test_mods_none_is_the_empty_combination() -> None:
    assert Mods.NONE.value == 0
    assert not (Mods.SHIFT & Mods.NONE)


def test_mods_compose_with_or() -> None:
    combined = Mods.CTRL | Mods.SHIFT
    assert Mods.CTRL in combined
    assert Mods.SHIFT in combined
    assert Mods.ALT not in combined


def test_mods_members_have_distinct_bits() -> None:
    members = [
        Mods.SHIFT,
        Mods.CTRL,
        Mods.ALT,
        Mods.SUPER,
        Mods.CAPS_LOCK,
        Mods.NUM_LOCK,
        Mods.SHIFT_SIDE,
        Mods.CTRL_SIDE,
        Mods.ALT_SIDE,
        Mods.SUPER_SIDE,
    ]
    values = {member.value for member in members}
    assert len(values) == len(members)


def test_point_tags_are_distinct() -> None:
    tags = {PointTag.ACTIVE, PointTag.VIEWPORT, PointTag.SCREEN, PointTag.HISTORY}
    assert len(tags) == 4


def test_point_stores_tag_and_coordinates() -> None:
    point = Point(PointTag.VIEWPORT, 3, 7)
    assert point.tag is PointTag.VIEWPORT
    assert point.x == 3
    assert point.y == 7


def test_point_is_immutable() -> None:
    point = Point(PointTag.ACTIVE, 0, 0)
    with pytest.raises(AttributeError):
        point.x = 5  # type: ignore[misc]


def test_point_equality_is_by_value() -> None:
    assert Point(PointTag.SCREEN, 1, 2) == Point(PointTag.SCREEN, 1, 2)
    assert Point(PointTag.SCREEN, 1, 2) != Point(PointTag.HISTORY, 1, 2)


def test_surface_position_stores_pixel_coordinates() -> None:
    position = SurfacePosition(12.5, 40.0)
    assert position.x == 12.5
    assert position.y == 40.0


def test_surface_position_is_immutable() -> None:
    position = SurfacePosition(0.0, 0.0)
    with pytest.raises(AttributeError):
        position.x = 1.0  # type: ignore[misc]
