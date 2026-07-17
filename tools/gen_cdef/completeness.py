"""Completeness check for the libghostty-vt raw layer.

The raw layer claims to be complete by construction: every exported ``ghostty_*``
symbol in the vendored vt headers must be callable from the compiled extension.
This module makes that claim checkable — it compares the exported header surface
against the symbols the built ``ghostty_vt._raw`` extension actually exposes and
reports any that are missing.

The header surface is derived from the *preprocessed* umbrella rather than by
scanning header files directly, so it honors exactly what the generator sees: the
``#ifdef __wasm__`` gate hides ``wasm.h``, the empty stubs contribute nothing, and
non-vt headers (e.g. the separate ``ghostty.h`` app API) never enter the picture.

Like the rest of ``gen_cdef`` this is build-time tooling: it is not shipped and is
outside the package's coverage scope. Run it with ``python -m gen_cdef.completeness``
(wired to ``just completeness``) after a build.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

from gen_cdef._generator import _LINE_MARKER, UMBRELLA, preprocess, repo_root

# A function declaration/definition site: a lowercase ``ghostty_*`` name directly
# before a ``(``. Exported functions and the header-only inline helpers match;
# CamelCase type names (``GhosttySysDecodePngFn``) and ``GHOSTTY_*`` enum
# constants do not, so this picks out exactly the callable surface.
_SYMBOL = re.compile(r"\b(ghostty_[a-z0-9_]+)\s*\(")


def surface_symbols(include_dir: Path, umbrella: str = UMBRELLA) -> set[str]:
    """Return the exported ``ghostty_*`` function names of the vt header surface."""
    preprocessed = preprocess(include_dir, umbrella)
    body = "\n".join(
        line for line in preprocessed.splitlines() if not _LINE_MARKER.match(line)
    )
    return {match.group(1) for match in _SYMBOL.finditer(body)}


def compiled_symbols(lib: Any) -> set[str]:
    """Return the ``ghostty_*`` symbols the compiled raw-layer ``lib`` exposes."""
    return {name for name in dir(lib) if name.startswith("ghostty_")}


def missing_symbols(include_dir: Path, lib: Any, umbrella: str = UMBRELLA) -> set[str]:
    """Return exported header symbols absent from the compiled raw layer."""
    return surface_symbols(include_dir, umbrella) - compiled_symbols(lib)


def main(argv: list[str] | None = None) -> int:
    root = repo_root()
    parser = argparse.ArgumentParser(
        prog="gen_cdef.completeness",
        description=(
            "Check that every exported vt header symbol is callable from the "
            "compiled ghostty_vt._raw extension."
        ),
    )
    parser.add_argument(
        "--include-dir",
        type=Path,
        default=root / "vendor" / "ghostty" / "include",
        help="Directory holding the vendored ghostty/vt headers.",
    )
    args = parser.parse_args(argv)

    try:
        from ghostty_vt import _raw
    except ImportError as exc:
        print(
            f"completeness: cannot import ghostty_vt._raw ({exc}); "
            "build the extension first with `just build`.",
            file=sys.stderr,
        )
        return 1

    surface = surface_symbols(args.include_dir)
    missing = surface - compiled_symbols(_raw.lib)
    if missing:
        print(
            f"completeness: raw layer is missing {len(missing)} exported symbol(s):",
            file=sys.stderr,
        )
        for name in sorted(missing):
            print(f"  - {name}", file=sys.stderr)
        return 1

    print(f"completeness: raw layer covers all {len(surface)} exported vt symbols")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
