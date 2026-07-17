# Positive typesafety pins for the device domain.
#
# Never executed: every line is a compile-time assertion. `assert_type` pins the
# type a checker infers for each public expression, so any drift in the device
# API's public types turns the suite red. This file must be diagnostic-free under
# every checker.
from __future__ import annotations

from typing import assert_type

from ghostty_vt import DeviceAttributes, DeviceResponder
from ghostty_vt.device import (
    DeviceAttributesHandler,
    EnquiryHandler,
    PrimaryAttributes,
    SecondaryAttributes,
    TertiaryAttributes,
    XtversionHandler,
)

# The value types expose their fields with the declared types.
primary = PrimaryAttributes(62, (22, 52))
assert_type(primary, PrimaryAttributes)
assert_type(primary.conformance_level, int)
assert_type(primary.features, tuple[int, ...])

secondary = SecondaryAttributes(device_type=1, firmware_version=10)
assert_type(secondary, SecondaryAttributes)
assert_type(secondary.device_type, int)
assert_type(secondary.firmware_version, int)
assert_type(secondary.rom_cartridge, int)

tertiary = TertiaryAttributes(0xABCD)
assert_type(tertiary, TertiaryAttributes)
assert_type(tertiary.unit_id, int)

attrs = DeviceAttributes(primary, secondary, tertiary)
assert_type(attrs, DeviceAttributes)
assert_type(attrs.primary, PrimaryAttributes)
assert_type(attrs.secondary, SecondaryAttributes)
assert_type(attrs.tertiary, TertiaryAttributes)

# The responder is a context manager whose feed returns the pty response bytes.
responder = DeviceResponder(cols=80, rows=24)
assert_type(responder, DeviceResponder)
assert_type(responder.feed(b"\x1b[c"), bytes)
assert_type(responder.close(), None)

with DeviceResponder() as opened:
    assert_type(opened, DeviceResponder)

# Handlers match the exported callable aliases and register cleanly.
device_attributes_handler: DeviceAttributesHandler = lambda: attrs
enquiry_handler: EnquiryHandler = lambda: b"answerback"
xtversion_handler: XtversionHandler = lambda: "myterm 1.0"
assert_type(responder.on_device_attributes(device_attributes_handler), None)
assert_type(responder.on_enquiry(enquiry_handler), None)
assert_type(responder.on_xtversion(xtversion_handler), None)

# Handlers can be cleared with None.
responder.on_device_attributes(None)
responder.on_enquiry(None)
responder.on_xtversion(None)
