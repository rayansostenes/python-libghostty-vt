# Expect-error typesafety pins for the device domain.
#
# Never executed. Every statement below is a deliberate misuse of the public API.
# Each line tagged `# expect-error` MUST draw at least one diagnostic from every
# checker; the harness fails if any tagged line stops erroring or if an untagged
# line errors.
from __future__ import annotations

from ghostty_vt import DeviceAttributes, DeviceResponder
from ghostty_vt.device import PrimaryAttributes, SecondaryAttributes, TertiaryAttributes

PrimaryAttributes()  # expect-error: missing conformance_level
PrimaryAttributes(62).does_not_exist  # expect-error: no such attribute
PrimaryAttributes("62")  # expect-error: conformance_level must be an int
SecondaryAttributes(device_type="1")  # expect-error: device_type must be an int
TertiaryAttributes("0")  # expect-error: unit_id must be an int
DeviceAttributes()  # expect-error: missing primary
_wrong: int = DeviceResponder()  # expect-error: DeviceResponder is not an int

responder = DeviceResponder()
responder.feed("not bytes")  # expect-error: feed takes bytes
responder.feed()  # expect-error: missing data
responder.on_enquiry(lambda: "not bytes")  # expect-error: enquiry returns bytes
responder.on_xtversion(lambda: b"not str")  # expect-error: xtversion returns str
responder.on_device_attributes(lambda: b"nope")  # expect-error: wrong return type
DeviceResponder(cols="80")  # expect-error: cols must be an int
