"""Formatter domain: serialize a terminal's screen to text.

This is the idiomatic layer over the upstream ``formatter`` domain. It defines
the :class:`Format` output formats; the extraction itself is
:meth:`~ghostty_vt.Terminal.format`, which serializes a terminal's active screen
to a ``str`` in one of these formats with control over soft-wrap unwrapping and
trailing-whitespace trimming.
"""

from __future__ import annotations

import enum

from ghostty_vt import _raw

__all__ = ["Format"]

_lib = _raw.lib


class Format(enum.Enum):
    """The output format the formatter emits."""

    PLAIN = _lib.GHOSTTY_FORMATTER_FORMAT_PLAIN
    """Plain text: characters only, no styling."""

    VT = _lib.GHOSTTY_FORMATTER_FORMAT_VT
    """VT escape sequences that reproduce the screen when replayed."""

    HTML = _lib.GHOSTTY_FORMATTER_FORMAT_HTML
    """HTML markup with inline styling."""
