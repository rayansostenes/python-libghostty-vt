"""Behavioral tests for the color domain, through the public API.

Every assertion observes what a user of ``ghostty_vt`` would see: real colors
parsed and computed by the native library across the full cffi path. The raw
layer and the C boundary are never touched directly.
"""

from __future__ import annotations

import pytest

from ghostty_vt import InvalidValueError, Rgb
from ghostty_vt.color import (
    X11Color,
    default_palette,
    generate_palette,
    parse_palette_entry,
    x11_names,
)

WHITE = Rgb(255, 255, 255)
BLACK = Rgb(0, 0, 0)


def test_rgb_stores_its_channels() -> None:
    color = Rgb(10, 20, 30)
    assert (color.r, color.g, color.b) == (10, 20, 30)


def test_rgb_is_immutable() -> None:
    color = Rgb(1, 2, 3)
    with pytest.raises(AttributeError):
        color.r = 9  # type: ignore[misc]


@pytest.mark.parametrize("channel", ["r", "g", "b"])
def test_rgb_rejects_out_of_range_channels(channel: str) -> None:
    kwargs = {"r": 0, "g": 0, "b": 0, channel: 256}
    with pytest.raises(ValueError, match="out of range"):
        Rgb(**kwargs)


def test_rgb_rejects_negative_channels() -> None:
    with pytest.raises(ValueError, match="out of range"):
        Rgb(-1, 0, 0)


def test_parse_hex_with_hash() -> None:
    assert Rgb.parse("#ff8800") == Rgb(255, 136, 0)


def test_parse_hex_without_hash() -> None:
    assert Rgb.parse("ff0000") == Rgb(255, 0, 0)


def test_parse_x11_name_via_parse() -> None:
    assert Rgb.parse("red") == Rgb(255, 0, 0)


def test_parse_rejects_garbage() -> None:
    with pytest.raises(InvalidValueError, match="could not parse color"):
        Rgb.parse("not a color")


def test_from_x11_resolves_a_named_color() -> None:
    assert Rgb.from_x11("MediumSpringGreen") == Rgb(0, 250, 154)


def test_from_x11_is_case_insensitive() -> None:
    assert Rgb.from_x11("medium spring green") == Rgb.from_x11("MediumSpringGreen")


def test_from_x11_rejects_unknown_name() -> None:
    with pytest.raises(InvalidValueError, match="unknown X11 color name"):
        Rgb.from_x11("definitely not a color")


def test_hex_round_trips_through_parse() -> None:
    color = Rgb(18, 52, 86)
    assert color.hex == "#123456"
    assert Rgb.parse(color.hex) == color


def test_luminance_spans_black_to_white() -> None:
    assert BLACK.luminance == pytest.approx(0.0)
    assert WHITE.luminance == pytest.approx(1.0)


def test_perceived_luminance_spans_black_to_white() -> None:
    assert BLACK.perceived_luminance == pytest.approx(0.0)
    assert WHITE.perceived_luminance == pytest.approx(1.0)


def test_contrast_is_maximal_for_black_and_white() -> None:
    assert WHITE.contrast(BLACK) == pytest.approx(21.0)


def test_contrast_is_minimal_for_identical_colors() -> None:
    assert WHITE.contrast(WHITE) == pytest.approx(1.0)


def test_parse_palette_entry_returns_index_and_color() -> None:
    index, color = parse_palette_entry("1=#ff0000")
    assert index == 1
    assert color == Rgb(255, 0, 0)


def test_parse_palette_entry_ignores_surrounding_whitespace() -> None:
    assert parse_palette_entry("  42 = red ") == (42, Rgb(255, 0, 0))


def test_parse_palette_entry_rejects_garbage() -> None:
    with pytest.raises(InvalidValueError, match="could not parse palette entry"):
        parse_palette_entry("not an entry")


def test_default_palette_has_256_colors() -> None:
    palette = default_palette()
    assert len(palette) == 256
    assert all(isinstance(color, Rgb) for color in palette)


def test_default_palette_cube_holds_pure_red() -> None:
    # Index 196 is the pure-red corner of the xterm 6x6x6 color cube.
    assert default_palette()[196] == Rgb(255, 0, 0)


def test_generate_palette_from_defaults() -> None:
    palette = generate_palette(BLACK, WHITE)
    assert len(palette) == 256
    # Indices 0-15 are preserved from the default base palette.
    assert palette[:16] == default_palette()[:16]


def test_generate_palette_from_explicit_base() -> None:
    base = default_palette()
    palette = generate_palette(BLACK, WHITE, base=list(base))
    assert len(palette) == 256
    assert palette[:16] == base[:16]


def test_generate_palette_preserves_skipped_indices() -> None:
    base = default_palette()
    palette = generate_palette(BLACK, WHITE, base=list(base), skip={100, 200})
    assert palette[100] == base[100]
    assert palette[200] == base[200]


def test_generate_palette_harmonious_flag_is_accepted() -> None:
    palette = generate_palette(WHITE, BLACK, harmonious=True)
    assert len(palette) == 256


def test_generate_palette_rejects_wrong_length_base() -> None:
    with pytest.raises(ValueError, match="must have 256 colors"):
        generate_palette(BLACK, WHITE, base=[BLACK])


def test_generate_palette_rejects_out_of_range_skip_index() -> None:
    with pytest.raises(ValueError, match="palette index out of range"):
        generate_palette(BLACK, WHITE, skip={256})


def test_x11_names_are_populated() -> None:
    names = x11_names()
    assert len(names) > 0
    assert all(isinstance(entry, X11Color) for entry in names)


def test_x11_names_entries_match_from_x11() -> None:
    entry = x11_names()[0]
    assert Rgb.from_x11(entry.name) == entry.color


def test_x11_names_include_aliases() -> None:
    names = {entry.name for entry in x11_names()}
    assert "medium spring green" in names
    assert "MediumSpringGreen" in names
