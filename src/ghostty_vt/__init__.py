"""Idiomatic, fully typed Python bindings for libghostty-vt.

libghostty-vt is the C-ABI terminal (VT) library extracted from Ghostty. This
package exposes it through two layers: a private raw layer (a generated 1:1
binding over the C API) and this public idiomatic layer. The idiomatic layer is
the only surface with stability intent.

Domains are organized into submodules; flagship names are re-exported here at the
top level. This release covers the ``build_info`` domain as the tracer path
through every layer; the remaining domains land in later milestones.
"""

from __future__ import annotations

from importlib.metadata import version as _version

from ghostty_vt.build_info import (
    GHOSTTY_COMMIT,
    BuildInfo,
    OptimizeMode,
    build_info,
)

__all__ = [
    "GHOSTTY_COMMIT",
    "BuildInfo",
    "OptimizeMode",
    "__version__",
    "build_info",
]

# Single source of truth: the version lives only in pyproject.toml and is read
# back from the installed distribution metadata. Keeping a second hand-edited
# literal here would let the runtime version drift from the published one — the
# release version guard only checks the sdist/pyproject version, not this.
__version__: str = _version("python-libghostty-vt")
