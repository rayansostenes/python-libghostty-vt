"""Idiomatic, fully typed Python bindings for libghostty-vt.

libghostty-vt is the C-ABI terminal (VT) library extracted from Ghostty. This
package exposes it through two layers: a private raw layer (a generated 1:1
binding over the C API) and this public idiomatic layer. The idiomatic layer is
the only surface with stability intent.

Domains are organized into submodules; flagship names are re-exported here at the
top level. This release covers the ``build_info`` tracer domain, the foundation
domains — errors, shared types, and color — the device domain's query callbacks,
the core of the ``terminal`` domain (create, feed, read visible text, resize),
the standalone sequence parsers ``osc`` and ``sgr``, and the small encode/measure
domains: paste, unicode, size report, color scheme, and focus. The remaining
domains land in later milestones.

The sequence parsers are reached through their submodules, ``ghostty_vt.osc`` and
``ghostty_vt.sgr``, so their generic names (``parse``, ``Command``, ``Attribute``)
stay domain-qualified rather than crowding the top level.
"""

from __future__ import annotations

from importlib.metadata import version as _version

from ghostty_vt.build_info import (
    GHOSTTY_COMMIT,
    BuildInfo,
    OptimizeMode,
    build_info,
)
from ghostty_vt.color import Rgb
from ghostty_vt.color_scheme import ColorScheme
from ghostty_vt.device import DeviceAttributes, DeviceResponder
from ghostty_vt.errors import (
    GhosttyVtError,
    InvalidValueError,
    NoValueError,
    OutOfMemoryError,
    OutOfSpaceError,
    UseAfterCloseError,
)
from ghostty_vt.focus import FocusEvent
from ghostty_vt.mouse import (
    MouseAction,
    MouseButton,
    MouseEncoder,
    MouseEvent,
    MouseFormat,
    MouseTracking,
)
from ghostty_vt.size_report import SizeReportStyle
from ghostty_vt.terminal import Terminal
from ghostty_vt.types import Mods, Point, PointTag, SurfacePosition

__all__ = [
    "GHOSTTY_COMMIT",
    "BuildInfo",
    "ColorScheme",
    "DeviceAttributes",
    "DeviceResponder",
    "FocusEvent",
    "GhosttyVtError",
    "InvalidValueError",
    "Mods",
    "MouseAction",
    "MouseButton",
    "MouseEncoder",
    "MouseEvent",
    "MouseFormat",
    "MouseTracking",
    "NoValueError",
    "OptimizeMode",
    "OutOfMemoryError",
    "OutOfSpaceError",
    "Point",
    "PointTag",
    "Rgb",
    "SizeReportStyle",
    "SurfacePosition",
    "Terminal",
    "UseAfterCloseError",
    "__version__",
    "build_info",
]

# Single source of truth: the version lives only in pyproject.toml and is read
# back from the installed distribution metadata. Keeping a second hand-edited
# literal here would let the runtime version drift from the published one — the
# release version guard only checks the sdist/pyproject version, not this.
__version__: str = _version("python-libghostty-vt")
