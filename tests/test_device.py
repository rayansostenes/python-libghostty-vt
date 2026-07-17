"""Behavioral tests for the device domain, through the public API.

Every assertion drives real VT bytes through a native terminal and observes the
bytes it writes back, exercising the full callback path across the C boundary.
The raw layer and the cffi callbacks are never invoked directly.
"""

from __future__ import annotations

import gc
import weakref

import pytest

from ghostty_vt import DeviceAttributes, DeviceResponder
from ghostty_vt.device import (
    PrimaryAttributes,
    SecondaryAttributes,
    TertiaryAttributes,
)

DA1_QUERY = b"\x1b[c"
DA2_QUERY = b"\x1b[>c"
DA3_QUERY = b"\x1b[=c"
ENQ_QUERY = b"\x05"
XTVERSION_QUERY = b"\x1b[>q"


# --- value types -----------------------------------------------------------


def test_primary_attributes_stores_fields() -> None:
    primary = PrimaryAttributes(62, (22, 52))
    assert primary.conformance_level == 62
    assert primary.features == (22, 52)


def test_primary_attributes_features_default_empty() -> None:
    assert PrimaryAttributes(62).features == ()


def test_primary_attributes_is_immutable() -> None:
    primary = PrimaryAttributes(62)
    with pytest.raises(AttributeError):
        primary.conformance_level = 63  # type: ignore[misc]


def test_primary_attributes_rejects_out_of_range_conformance() -> None:
    with pytest.raises(ValueError, match="conformance_level out of range"):
        PrimaryAttributes(70000)


def test_primary_attributes_rejects_too_many_features() -> None:
    with pytest.raises(ValueError, match="at most 64 feature codes"):
        PrimaryAttributes(62, tuple(range(65)))


def test_primary_attributes_rejects_out_of_range_feature() -> None:
    with pytest.raises(ValueError, match="feature code out of range"):
        PrimaryAttributes(62, (70000,))


def test_secondary_attributes_defaults_to_zero() -> None:
    secondary = SecondaryAttributes()
    assert secondary.device_type == 0
    assert secondary.firmware_version == 0
    assert secondary.rom_cartridge == 0


@pytest.mark.parametrize("field", ["device_type", "firmware_version", "rom_cartridge"])
def test_secondary_attributes_rejects_out_of_range(field: str) -> None:
    with pytest.raises(ValueError, match=f"{field} out of range"):
        SecondaryAttributes(**{field: 70000})


def test_tertiary_attributes_defaults_to_zero() -> None:
    assert TertiaryAttributes().unit_id == 0


def test_tertiary_attributes_accepts_full_uint32() -> None:
    assert TertiaryAttributes(0xFFFFFFFF).unit_id == 0xFFFFFFFF


def test_tertiary_attributes_rejects_out_of_range() -> None:
    with pytest.raises(ValueError, match="unit_id out of range"):
        TertiaryAttributes(0x1_0000_0000)


def test_device_attributes_defaults_secondary_and_tertiary() -> None:
    attrs = DeviceAttributes(PrimaryAttributes(62))
    assert attrs.secondary == SecondaryAttributes()
    assert attrs.tertiary == TertiaryAttributes()


# --- responder construction ------------------------------------------------


def test_responder_defaults_to_80x24() -> None:
    with DeviceResponder() as responder:
        assert responder.feed(b"hello") == b""


def test_responder_accepts_custom_size() -> None:
    with DeviceResponder(cols=132, rows=50) as responder:
        assert responder.feed(b"hello") == b""


@pytest.mark.parametrize("dimension", ["cols", "rows"])
def test_responder_rejects_out_of_range_size(dimension: str) -> None:
    with pytest.raises(ValueError, match=f"{dimension} out of range"):
        DeviceResponder(**{dimension: 70000})


@pytest.mark.parametrize("dimension", ["cols", "rows"])
def test_responder_rejects_zero_size(dimension: str) -> None:
    with pytest.raises(ValueError, match="must be positive"):
        DeviceResponder(**{dimension: 0})


# --- device attributes -----------------------------------------------------


def test_device_attributes_primary_response() -> None:
    with DeviceResponder() as responder:
        responder.on_device_attributes(
            lambda: DeviceAttributes(PrimaryAttributes(61, (1, 2, 4)))
        )
        assert responder.feed(DA1_QUERY) == b"\x1b[?61;1;2;4c"


def test_device_attributes_secondary_response() -> None:
    with DeviceResponder() as responder:
        responder.on_device_attributes(
            lambda: DeviceAttributes(
                PrimaryAttributes(62),
                secondary=SecondaryAttributes(device_type=1, firmware_version=10),
            )
        )
        assert responder.feed(DA2_QUERY) == b"\x1b[>1;10;0c"


def test_device_attributes_tertiary_response() -> None:
    with DeviceResponder() as responder:
        responder.on_device_attributes(
            lambda: DeviceAttributes(
                PrimaryAttributes(62), tertiary=TertiaryAttributes(0xABCD)
            )
        )
        assert responder.feed(DA3_QUERY) == b"\x1bP!|0000ABCD\x1b\\"


def test_device_attributes_without_handler_uses_default() -> None:
    with DeviceResponder() as responder:
        assert responder.feed(DA1_QUERY) == b"\x1b[?62;22c"


def test_device_attributes_handler_returning_none_uses_default() -> None:
    with DeviceResponder() as responder:
        responder.on_device_attributes(lambda: None)
        assert responder.feed(DA1_QUERY) == b"\x1b[?62;22c"


def test_device_attributes_handler_can_be_cleared() -> None:
    with DeviceResponder() as responder:
        responder.on_device_attributes(lambda: DeviceAttributes(PrimaryAttributes(61)))
        assert responder.feed(DA1_QUERY) == b"\x1b[?61c"
        responder.on_device_attributes(None)
        assert responder.feed(DA1_QUERY) == b"\x1b[?62;22c"


# --- enquiry ---------------------------------------------------------------


def test_enquiry_answerback() -> None:
    with DeviceResponder() as responder:
        responder.on_enquiry(lambda: b"hello")
        assert responder.feed(ENQ_QUERY) == b"hello"


def test_enquiry_without_handler_is_silent() -> None:
    with DeviceResponder() as responder:
        assert responder.feed(ENQ_QUERY) == b""


def test_enquiry_empty_answerback_is_silent() -> None:
    with DeviceResponder() as responder:
        responder.on_enquiry(lambda: b"")
        assert responder.feed(ENQ_QUERY) == b""


# --- xtversion -------------------------------------------------------------


def test_xtversion_report() -> None:
    with DeviceResponder() as responder:
        responder.on_xtversion(lambda: "myterm 1.0")
        assert responder.feed(XTVERSION_QUERY) == b"\x1bP>|myterm 1.0\x1b\\"


def test_xtversion_without_handler_uses_default() -> None:
    with DeviceResponder() as responder:
        assert responder.feed(XTVERSION_QUERY) == b"\x1bP>|libghostty\x1b\\"


def test_xtversion_empty_string_uses_default() -> None:
    with DeviceResponder() as responder:
        responder.on_xtversion(lambda: "")
        assert responder.feed(XTVERSION_QUERY) == b"\x1bP>|libghostty\x1b\\"


# --- exception containment -------------------------------------------------


def test_handler_exception_propagates_from_feed() -> None:
    def boom() -> bytes:
        raise RuntimeError("handler blew up")

    with DeviceResponder() as responder:
        responder.on_enquiry(boom)
        with pytest.raises(RuntimeError, match="handler blew up"):
            responder.feed(ENQ_QUERY)


def test_responder_recovers_after_handler_exception() -> None:
    with DeviceResponder() as responder:
        responder.on_enquiry(_raising(ValueError("nope")))
        with pytest.raises(ValueError, match="nope"):
            responder.feed(ENQ_QUERY)
        responder.on_enquiry(lambda: b"recovered")
        assert responder.feed(ENQ_QUERY) == b"recovered"


def test_only_first_handler_exception_is_raised() -> None:
    calls: list[str] = []

    def enquiry() -> bytes:
        calls.append("enquiry")
        raise ValueError("first")

    def device_attributes() -> DeviceAttributes:
        calls.append("device_attributes")
        raise RuntimeError("second")

    with DeviceResponder() as responder:
        responder.on_enquiry(enquiry)
        responder.on_device_attributes(device_attributes)
        with pytest.raises(ValueError, match="first"):
            responder.feed(ENQ_QUERY + DA1_QUERY)
        # Only the first exception surfaces, but the second handler still ran
        # and returned its default (ADR-0003: the contract is per-feed).
        assert calls == ["enquiry", "device_attributes"]


# --- lifetime --------------------------------------------------------------


def test_feed_after_close_raises() -> None:
    responder = DeviceResponder()
    responder.close()
    with pytest.raises(ValueError, match="closed"):
        responder.feed(ENQ_QUERY)


def test_close_is_idempotent() -> None:
    responder = DeviceResponder()
    responder.close()
    responder.close()


@pytest.mark.parametrize(
    "register",
    ["on_device_attributes", "on_enquiry", "on_xtversion"],
)
def test_register_after_close_raises(register: str) -> None:
    responder = DeviceResponder()
    responder.close()
    with pytest.raises(ValueError, match="closed"):
        getattr(responder, register)(lambda: None)


def test_dropped_responder_is_finalized() -> None:
    responder = DeviceResponder()
    responder.on_enquiry(lambda: b"x")
    assert responder.feed(ENQ_QUERY) == b"x"
    ref = weakref.ref(responder)
    del responder
    gc.collect()
    # The responder holds the only strong refs to its cffi callbacks, so once
    # it is collected nothing keeps the native terminal alive: no leak.
    assert ref() is None


def test_survives_gc_between_feeds() -> None:
    with DeviceResponder() as responder:
        responder.on_device_attributes(
            lambda: DeviceAttributes(PrimaryAttributes(62, (22,)))
        )
        for _ in range(3):
            gc.collect()
            assert responder.feed(DA1_QUERY) == b"\x1b[?62;22c"


# --- reentrancy ------------------------------------------------------------


def test_handler_feeding_reentrantly_raises() -> None:
    with DeviceResponder() as responder:

        def reenter() -> bytes:
            return responder.feed(ENQ_QUERY)

        responder.on_enquiry(reenter)
        with pytest.raises(RuntimeError, match="reentrantly"):
            responder.feed(ENQ_QUERY)
        # The responder stays usable after a blocked reentrant feed.
        responder.on_enquiry(lambda: b"ok")
        assert responder.feed(ENQ_QUERY) == b"ok"


def test_handler_closing_during_feed_raises() -> None:
    with DeviceResponder() as responder:

        def close_mid_feed() -> bytes:
            responder.close()
            return b""

        responder.on_enquiry(close_mid_feed)
        with pytest.raises(RuntimeError, match="from within feed"):
            responder.feed(ENQ_QUERY)
        # close() was blocked, so the native terminal was never freed.
        responder.on_enquiry(lambda: b"ok")
        assert responder.feed(ENQ_QUERY) == b"ok"


def _raising(error: Exception):  # type: ignore[no-untyped-def]
    def handler():  # type: ignore[no-untyped-def]
        raise error

    return handler
