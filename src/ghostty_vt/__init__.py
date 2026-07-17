"""Idiomatic, fully typed Python bindings for libghostty-vt.

libghostty-vt is the C-ABI terminal (VT) library extracted from Ghostty. This
package exposes it through two layers: a private raw layer (a generated 1:1
binding over the C API) and this public idiomatic layer. The idiomatic layer is
the only surface with stability intent.

The bindings and native extension are added in later milestones; this module
currently exposes only the package version.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0.dev0"
