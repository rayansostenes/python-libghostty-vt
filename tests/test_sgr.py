"""Behavioral tests for the SGR domain, through the public API.

Every assertion observes what a user of ``ghostty_vt`` would see: real SGR
parameter strings parsed by the native library across the full cffi path. The
raw layer and the C boundary are never touched directly.
"""

from __future__ import annotations

import pytest

from ghostty_vt import Rgb
from ghostty_vt.sgr import Attribute, AttributeKind, Underline, Unknown, parse


def kinds(params: str) -> list[AttributeKind]:
    return [attr.kind for attr in parse(params)]


def test_bold_then_foreground_parse_in_order() -> None:
    assert parse("1;31") == (
        Attribute(AttributeKind.BOLD),
        Attribute(AttributeKind.FG_8, 1),
    )


def test_empty_sequence_resets_all() -> None:
    assert parse("") == (Attribute(AttributeKind.UNSET),)


def test_zero_resets_all() -> None:
    assert parse("0") == (Attribute(AttributeKind.UNSET),)


def test_omitted_parameter_defaults_to_zero() -> None:
    # The empty middle parameter of `1;;31` is treated as a reset-all.
    assert kinds("1;;31") == [
        AttributeKind.BOLD,
        AttributeKind.UNSET,
        AttributeKind.FG_8,
    ]


def test_direct_foreground_color_yields_rgb() -> None:
    assert parse("38;2;10;20;30") == (
        Attribute(AttributeKind.DIRECT_COLOR_FG, Rgb(10, 20, 30)),
    )


def test_direct_background_color_yields_rgb() -> None:
    assert parse("48;2;1;2;3") == (
        Attribute(AttributeKind.DIRECT_COLOR_BG, Rgb(1, 2, 3)),
    )


def test_256_foreground_yields_palette_index() -> None:
    assert parse("38;5;200") == (Attribute(AttributeKind.FG_256, 200),)


def test_256_background_yields_palette_index() -> None:
    assert parse("48;5;12") == (Attribute(AttributeKind.BG_256, 12),)


def test_8_color_background_yields_palette_index() -> None:
    assert parse("41") == (Attribute(AttributeKind.BG_8, 1),)


def test_bright_foreground_and_background_yield_palette_indices() -> None:
    assert parse("92;102") == (
        Attribute(AttributeKind.BRIGHT_FG_8, 10),
        Attribute(AttributeKind.BRIGHT_BG_8, 10),
    )


def test_plain_underline_yields_single_style() -> None:
    assert parse("4") == (Attribute(AttributeKind.UNDERLINE, Underline.SINGLE),)


def test_colon_subparameters_select_curly_underline() -> None:
    assert parse("4:3") == (Attribute(AttributeKind.UNDERLINE, Underline.CURLY),)


def test_underline_color_yields_rgb() -> None:
    assert parse("58;2;255;97;136") == (
        Attribute(AttributeKind.UNDERLINE_COLOR, Rgb(255, 97, 136)),
    )


def test_256_underline_color_yields_palette_index() -> None:
    assert parse("58;5;42") == (Attribute(AttributeKind.UNDERLINE_COLOR_256, 42),)


def test_reset_underline_color_carries_no_value() -> None:
    assert parse("59") == (Attribute(AttributeKind.RESET_UNDERLINE_COLOR),)


def test_unrecognized_parameter_is_reported_as_unknown() -> None:
    (attribute,) = parse("99")
    assert attribute.kind is AttributeKind.UNKNOWN
    assert attribute.value == Unknown(full=(99,), partial=(99,))


def test_unknown_preserves_full_and_partial_parameter_lists() -> None:
    # `99` is unrecognized between a bold and a red foreground; the parser
    # recovers, so the partial slice spans from the unknown parameter onward.
    attributes = parse("1;99;31")
    unknown = attributes[1]
    assert unknown.kind is AttributeKind.UNKNOWN
    assert unknown.value == Unknown(full=(1, 99, 31), partial=(99, 31))


def test_mixed_separators_parse_a_full_kakoune_sequence() -> None:
    params = "4:3;38;2;51;51;51;48;2;170;170;170;58;2;255;97;136"
    assert parse(params) == (
        Attribute(AttributeKind.UNDERLINE, Underline.CURLY),
        Attribute(AttributeKind.DIRECT_COLOR_FG, Rgb(51, 51, 51)),
        Attribute(AttributeKind.DIRECT_COLOR_BG, Rgb(170, 170, 170)),
        Attribute(AttributeKind.UNDERLINE_COLOR, Rgb(255, 97, 136)),
    )


def test_reset_attributes_map_to_their_kinds() -> None:
    assert kinds("22;23;25;27;28;29;39;49;55") == [
        AttributeKind.RESET_BOLD,
        AttributeKind.RESET_ITALIC,
        AttributeKind.RESET_BLINK,
        AttributeKind.RESET_INVERSE,
        AttributeKind.RESET_INVISIBLE,
        AttributeKind.RESET_STRIKETHROUGH,
        AttributeKind.RESET_FG,
        AttributeKind.RESET_BG,
        AttributeKind.RESET_OVERLINE,
    ]


def test_disabling_underline_yields_the_none_style() -> None:
    assert parse("24") == (Attribute(AttributeKind.UNDERLINE, Underline.NONE),)


def test_non_numeric_parameter_is_rejected() -> None:
    with pytest.raises(ValueError, match="invalid SGR parameter"):
        parse("1;abc")


def test_out_of_range_parameter_is_rejected() -> None:
    with pytest.raises(ValueError, match="out of range"):
        parse("70000")


def test_attribute_is_immutable() -> None:
    attribute = Attribute(AttributeKind.BOLD)
    with pytest.raises(AttributeError):
        attribute.kind = AttributeKind.ITALIC  # type: ignore[misc]
