"""Behavioral tests for the OSC domain, through the public API.

Every assertion observes what a user of ``ghostty_vt`` would see: real OSC
payloads parsed by the native library across the full cffi path. The raw layer
and the C boundary are never touched directly.
"""

from __future__ import annotations

import pytest

from ghostty_vt.osc import Command, CommandType, parse


def test_change_window_title_extracts_the_title() -> None:
    assert parse(b"0;hello") == Command(CommandType.CHANGE_WINDOW_TITLE, "hello")


def test_change_window_title_may_be_empty() -> None:
    assert parse(b"0;") == Command(CommandType.CHANGE_WINDOW_TITLE, "")


def test_non_utf8_title_is_decoded_without_crashing() -> None:
    command = parse(b"0;caf\xe9")
    assert command.type is CommandType.CHANGE_WINDOW_TITLE
    assert command.title is not None


def test_hyperlink_is_classified_without_a_title() -> None:
    command = parse(b"8;;https://example.com")
    assert command.type is CommandType.HYPERLINK_START
    assert command.title is None


def test_clipboard_contents_is_classified() -> None:
    assert parse(b"52;c;aGVsbG8=").type is CommandType.CLIPBOARD_CONTENTS


def test_report_pwd_is_classified() -> None:
    assert parse(b"7;file:///home/user").type is CommandType.REPORT_PWD


def test_malformed_payload_is_invalid() -> None:
    assert parse(b"notacommand") == Command(CommandType.INVALID)


def test_empty_payload_is_invalid() -> None:
    assert parse(b"") == Command(CommandType.INVALID)


def test_command_is_immutable() -> None:
    command = parse(b"0;hello")
    with pytest.raises(AttributeError):
        command.title = "other"  # type: ignore[misc]
