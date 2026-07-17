"""Behavioral tests for the mouse domain, through the public API.

Every assertion observes what a user of ``ghostty_vt`` would see: real escape
sequences produced by the native encoder across the full cffi path. The raw layer
and the C boundary are never touched directly.
"""

from __future__ import annotations

import gc

import pytest

from ghostty_vt import (
    GhosttyVtError,
    Mods,
    MouseAction,
    MouseButton,
    MouseEncoder,
    MouseEvent,
    MouseFormat,
    MouseTracking,
    SurfacePosition,
)
from ghostty_vt.mouse import Geometry

# An 80x24 grid of 10x20 cells; the pixel (105, 45) lands in cell (11, 3) using
# xterm's 1-based coordinates.
GEOMETRY = Geometry(screen_width=800, screen_height=480, cell_width=10, cell_height=20)
AT_CELL_11_3 = SurfacePosition(105.0, 45.0)


def encoder(
    tracking: MouseTracking = MouseTracking.NORMAL,
    fmt: MouseFormat = MouseFormat.SGR,
    *,
    any_button_pressed: bool = False,
    track_last_cell: bool = False,
) -> MouseEncoder:
    return MouseEncoder(
        tracking=tracking,
        format=fmt,
        geometry=GEOMETRY,
        any_button_pressed=any_button_pressed,
        track_last_cell=track_last_cell,
    )


def test_mouse_event_stores_its_fields() -> None:
    event = MouseEvent(MouseAction.PRESS, AT_CELL_11_3, MouseButton.RIGHT, Mods.SHIFT)
    assert event.action is MouseAction.PRESS
    assert event.position == AT_CELL_11_3
    assert event.button is MouseButton.RIGHT
    assert event.mods is Mods.SHIFT


def test_mouse_event_defaults_to_no_button_and_no_mods() -> None:
    event = MouseEvent(MouseAction.MOTION, AT_CELL_11_3)
    assert event.button is None
    assert event.mods is Mods.NONE


def test_mouse_event_is_immutable() -> None:
    event = MouseEvent(MouseAction.PRESS, AT_CELL_11_3)
    with pytest.raises(AttributeError):
        event.action = MouseAction.RELEASE  # type: ignore[misc]


def test_geometry_requires_positive_cell_width() -> None:
    with pytest.raises(ValueError, match="cell_width must be positive"):
        Geometry(screen_width=800, screen_height=480, cell_width=0, cell_height=20)


def test_geometry_requires_positive_cell_height() -> None:
    with pytest.raises(ValueError, match="cell_height must be positive"):
        Geometry(screen_width=800, screen_height=480, cell_width=10, cell_height=-1)


def test_geometry_accepts_positive_cells_and_padding() -> None:
    geometry = Geometry(
        screen_width=800,
        screen_height=480,
        cell_width=10,
        cell_height=20,
        padding_top=1,
        padding_bottom=2,
        padding_left=3,
        padding_right=4,
    )
    assert geometry.cell_width == 10
    assert geometry.padding_left == 3


def test_press_encodes_to_sgr_button_report() -> None:
    with encoder() as enc:
        event = MouseEvent(MouseAction.PRESS, AT_CELL_11_3, MouseButton.LEFT)
        assert enc.encode(event) == b"\x1b[<0;11;3M"


def test_release_uses_the_lowercase_sgr_terminator() -> None:
    with encoder() as enc:
        event = MouseEvent(MouseAction.RELEASE, AT_CELL_11_3, MouseButton.LEFT)
        assert enc.encode(event) == b"\x1b[<0;11;3m"


def test_modifiers_change_the_encoded_button_code() -> None:
    with encoder() as enc:
        plain = enc.encode(
            MouseEvent(MouseAction.PRESS, AT_CELL_11_3, MouseButton.LEFT)
        )
        with_ctrl = enc.encode(
            MouseEvent(MouseAction.PRESS, AT_CELL_11_3, MouseButton.LEFT, Mods.CTRL)
        )
    assert plain == b"\x1b[<0;11;3M"
    assert with_ctrl == b"\x1b[<16;11;3M"
    assert plain != with_ctrl


def test_different_buttons_encode_differently() -> None:
    with encoder() as enc:
        left = enc.encode(MouseEvent(MouseAction.PRESS, AT_CELL_11_3, MouseButton.LEFT))
        right = enc.encode(
            MouseEvent(MouseAction.PRESS, AT_CELL_11_3, MouseButton.RIGHT)
        )
    assert left != right


@pytest.mark.parametrize(
    ("fmt", "expected"),
    [
        (MouseFormat.X10, b"\x1b[M +#"),
        (MouseFormat.UTF8, b"\x1b[M +#"),
        (MouseFormat.SGR, b"\x1b[<0;11;3M"),
        (MouseFormat.URXVT, b"\x1b[32;11;3M"),
        (MouseFormat.SGR_PIXELS, b"\x1b[<0;105;45M"),
    ],
)
def test_each_format_produces_its_own_encoding(
    fmt: MouseFormat, expected: bytes
) -> None:
    with encoder(fmt=fmt) as enc:
        event = MouseEvent(MouseAction.PRESS, AT_CELL_11_3, MouseButton.LEFT)
        assert enc.encode(event) == expected


def test_sgr_pixels_reports_pixels_where_sgr_reports_cells() -> None:
    event = MouseEvent(MouseAction.PRESS, AT_CELL_11_3, MouseButton.LEFT)
    with encoder(fmt=MouseFormat.SGR) as cells:
        cell_report = cells.encode(event)
    with encoder(fmt=MouseFormat.SGR_PIXELS) as pixels:
        pixel_report = pixels.encode(event)
    assert cell_report == b"\x1b[<0;11;3M"
    assert pixel_report == b"\x1b[<0;105;45M"


def test_unreported_event_encodes_to_empty_bytes() -> None:
    # X10 tracking reports presses only, so a release yields no output.
    with encoder(tracking=MouseTracking.X10) as enc:
        event = MouseEvent(MouseAction.RELEASE, AT_CELL_11_3, MouseButton.LEFT)
        assert enc.encode(event) == b""


def test_bare_motion_without_button_is_not_reported_in_normal_mode() -> None:
    with encoder(tracking=MouseTracking.NORMAL) as enc:
        event = MouseEvent(MouseAction.MOTION, AT_CELL_11_3)
        assert enc.encode(event) == b""


def test_track_last_cell_deduplicates_motion_within_a_cell() -> None:
    first = MouseEvent(
        MouseAction.MOTION, SurfacePosition(105.0, 45.0), MouseButton.LEFT
    )
    same_cell = MouseEvent(
        MouseAction.MOTION, SurfacePosition(106.0, 46.0), MouseButton.LEFT
    )
    with encoder(tracking=MouseTracking.BUTTON, track_last_cell=True) as enc:
        assert enc.encode(first) == b"\x1b[<32;11;3M"
        assert enc.encode(same_cell) == b""


def test_reset_clears_motion_deduplication_state() -> None:
    motion = MouseEvent(MouseAction.MOTION, AT_CELL_11_3, MouseButton.LEFT)
    with encoder(tracking=MouseTracking.BUTTON, track_last_cell=True) as enc:
        assert enc.encode(motion) == b"\x1b[<32;11;3M"
        assert enc.encode(motion) == b""
        enc.reset()
        assert enc.encode(motion) == b"\x1b[<32;11;3M"


def test_any_button_pressed_flag_is_accepted() -> None:
    with encoder(tracking=MouseTracking.ANY, any_button_pressed=True) as enc:
        event = MouseEvent(MouseAction.MOTION, AT_CELL_11_3)
        assert enc.encode(event).startswith(b"\x1b[<")


def test_encode_after_close_raises() -> None:
    enc = encoder()
    enc.close()
    with pytest.raises(GhosttyVtError, match="mouse encoder is closed"):
        enc.encode(MouseEvent(MouseAction.PRESS, AT_CELL_11_3, MouseButton.LEFT))


def test_reset_after_close_raises() -> None:
    enc = encoder()
    enc.close()
    with pytest.raises(GhosttyVtError, match="mouse encoder is closed"):
        enc.reset()


def test_close_is_idempotent() -> None:
    enc = encoder()
    enc.close()
    enc.close()


def test_context_manager_closes_on_exit() -> None:
    with encoder() as enc:
        pass
    with pytest.raises(GhosttyVtError, match="mouse encoder is closed"):
        enc.reset()


def test_forgotten_encoder_is_finalized_without_error() -> None:
    encoder()
    gc.collect()


def test_mouse_actions_are_distinct() -> None:
    actions = {MouseAction.PRESS, MouseAction.RELEASE, MouseAction.MOTION}
    assert len(actions) == 3


def test_mouse_buttons_cover_the_named_and_numbered_buttons() -> None:
    buttons = {MouseButton.LEFT, MouseButton.RIGHT, MouseButton.MIDDLE}
    assert len(buttons) == 3
    assert MouseButton.UNKNOWN not in buttons
    assert MouseButton.ELEVEN.value == 11
