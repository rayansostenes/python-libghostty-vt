"""Turn the vendored libghostty-vt C headers into a cffi ``cdef``.

The raw layer is a generated 1:1 binding over the C API (per ADR 0001), so the
``cdef`` it is built from must be generated too. Hand-maintaining it against an
upstream that churns a ~250-function surface is exactly the cost the generator
removes.

Pipeline:

1. **Preprocess** the umbrella header (``ghostty/vt.h``) with the pinned zig
   ``cc``, using ``-nostdinc`` and the empty stub headers in ``stubs/`` so no
   compiler-internal typedefs or builtins leak in. ``GHOSTTY_STATIC`` collapses
   the ``GHOSTTY_API`` visibility macro to nothing, and the enum ``INT_MAX``
   sentinel is resolved by the ``limits.h`` stub. What survives is clean C:
   enums, structs, opaque-pointer typedefs, function-pointer typedefs, and
   function prototypes.
2. **Discover** every vt header the umbrella reaches. Preprocessing the umbrella
   pulls in the whole surface, so the ``# lineno "file"`` markers name exactly
   the headers that contribute declarations, in dependency order. This is what
   makes the raw layer complete *by construction*: a header upstream adds flows
   in automatically, and aggregator headers (``key.h``, ``mouse.h``) and the
   ``#ifdef __wasm__`` gated ``wasm.h`` drop out because they contribute nothing
   under native preprocessing.
3. **Split** the preprocessed stream back into per-header sections using those
   same line markers.
4. **Normalize** each section by turning ``static inline`` function definitions
   into bare prototypes: their bodies are valid C but not valid ``cdef`` input,
   yet declaring the prototype (with the header included in ``set_source``) keeps
   them callable through cffi's API-mode wrappers.
5. **Verify** by feeding the sections to ``cffi``'s own parser incrementally, so
   a rejected declaration is blamed on a specific header rather than dying
   opaquely.
6. **Render** a single deterministic ``cdef`` file, annotated with the pinned
   commit and per-header section comments.

The generator is build-time tooling: it lives outside the shipped package and is
never imported at runtime.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import cffi

_MODULE_DIR = Path(__file__).resolve().parent
STUBS_DIR = _MODULE_DIR / "stubs"

# The umbrella header that transitively includes the whole vt surface, in a
# dependency-correct order. Preprocessing it (rather than individual headers)
# lets upstream decide declaration ordering and handles headers that are not
# standalone (e.g. device.h relies on macros from types.h without including it).
UMBRELLA = "ghostty/vt.h"

# Only headers under this include-relative prefix are part of the raw surface.
# Discovery ignores anything else the umbrella might transitively reach (e.g. the
# empty stdint/stddef stubs), so the emitted cdef is exactly the vt API.
VT_HEADER_PREFIX = "ghostty/vt/"

# Matches a preprocessor line marker: `# <lineno> "<file>" [flags]`.
_LINE_MARKER = re.compile(r'^#\s+\d+\s+"(?P<file>(?:[^"\\]|\\.)*)"')

# cffi surfaces both syntax and semantic cdef failures as these two types.
_CDEF_ERRORS = (cffi.CDefError, cffi.FFIError)

# Raised while resolving a line-marker path (ValueError when not include-relative,
# OSError on a resolve failure). Named rather than an inline `except (A, B):`
# because ruff 0.15.x's formatter miscompiles that tuple under a py314 target.
_PATH_ERRORS = (ValueError, OSError)


class GeneratorError(Exception):
    """A cdef could not be generated, naming the offending stage or header."""


def repo_root() -> Path:
    """Locate the repo root by walking up to the pinned-commit file."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "ghostty-commit.txt").is_file():
            return parent
    raise GeneratorError("could not locate ghostty-commit.txt from gen_cdef")


@dataclass(frozen=True)
class Section:
    """The declarations contributed by a single upstream header."""

    header: str
    body: str


def _zig_cc() -> list[str]:
    """The pinned zig toolchain's C driver, invoked via the ziglang package."""
    return [sys.executable, "-m", "ziglang", "cc"]


def preprocess(include_dir: Path, umbrella: str = UMBRELLA) -> str:
    """Return the preprocessed text of ``umbrella`` under ``include_dir``.

    Raises ``GeneratorError`` naming the header when the preprocessor fails; its
    diagnostics (which carry the offending ``file:line:col``) are preserved.
    """
    header = include_dir / umbrella
    if not header.is_file():
        raise GeneratorError(f"umbrella header not found: {header}")
    cmd = [
        *_zig_cc(),
        "-E",  # preprocess only
        "-x",
        "c",  # treat as C, so `extern "C"` guards drop out
        "-nostdinc",  # no system headers; use the stubs instead
        "-DGHOSTTY_STATIC",  # collapse the GHOSTTY_API visibility macro
        "-I",
        str(STUBS_DIR),
        "-I",
        str(include_dir),
        str(header),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "no diagnostics"
        raise GeneratorError(f"preprocessing {umbrella} failed:\n{detail}")
    return proc.stdout


def _normalize(raw_path: str, include_dir: Path) -> str:
    """Reduce a line-marker path to its include-relative form, or its basename."""
    path = Path(raw_path)
    try:
        return path.resolve().relative_to(include_dir.resolve()).as_posix()
    except _PATH_ERRORS:
        return path.name


def split_sections(
    preprocessed: str, include_dir: Path, headers: tuple[str, ...]
) -> list[Section]:
    """Group the preprocessed lines into per-header sections in include order.

    Only lines attributed (via the preprocessor's line markers) to one of
    ``headers`` are kept. Consecutive runs from the same header are merged, so
    each requested header yields exactly one section, ordered as the preprocessor
    emitted it (i.e. dependency-first).
    """
    wanted = set(headers)
    current: str | None = None
    ordered: list[str] = []
    bodies: dict[str, list[str]] = {}
    for line in preprocessed.splitlines():
        marker = _LINE_MARKER.match(line)
        if marker:
            current = _normalize(marker.group("file"), include_dir)
            continue
        if current not in wanted or not line.strip():
            continue
        if current not in bodies:
            bodies[current] = []
            ordered.append(current)
        bodies[current].append(line.rstrip())

    missing = [h for h in headers if h not in bodies]
    if missing:
        raise GeneratorError(
            "no declarations found for header(s): "
            + ", ".join(missing)
            + " (not reachable from "
            + UMBRELLA
            + ", or misspelled)"
        )
    return [Section(header=h, body="\n".join(bodies[h])) for h in ordered]


def discover_headers(
    preprocessed: str, include_dir: Path, prefix: str = VT_HEADER_PREFIX
) -> tuple[str, ...]:
    """Return every ``prefix`` header that contributed declarations, in order.

    The umbrella preprocesses to the whole surface, so the line markers name each
    header exactly once it emits any declaration. Headers that contribute nothing
    under native preprocessing — aggregators that only ``#include`` others, and
    the ``#ifdef __wasm__`` gated ``wasm.h`` — never appear, which is what keeps
    the discovered set to the compilable surface.
    """
    ordered: list[str] = []
    seen: set[str] = set()
    current: str | None = None
    for line in preprocessed.splitlines():
        marker = _LINE_MARKER.match(line)
        if marker:
            current = _normalize(marker.group("file"), include_dir)
            continue
        if not line.strip() or current is None or not current.startswith(prefix):
            continue
        if current not in seen:
            seen.add(current)
            ordered.append(current)
    if not ordered:
        raise GeneratorError(f"no headers under {prefix!r} reachable from {UMBRELLA}")
    return tuple(ordered)


def _strip_inline_definitions(body: str) -> str:
    """Reduce ``static inline`` function definitions to bare cffi prototypes.

    A depth-0 ``{...}`` block immediately following a ``)`` is a function body;
    cffi's ``cdef`` rejects definitions but accepts prototypes. Dropping the body
    (and the ``static``/``inline`` qualifiers) yields a prototype cffi compiles
    into an API-mode wrapper, keeping the header-only helper callable from the raw
    layer. Type definitions (``struct``/``union``/``enum`` bodies, whose ``{``
    does not follow a ``)``) are left untouched.
    """
    out: list[str] = []
    depth = 0
    prev = ""
    i = 0
    n = len(body)
    while i < n:
        char = body[i]
        if char == "{" and depth == 0 and prev == ")":
            brace = 0
            j = i
            while j < n:
                if body[j] == "{":
                    brace += 1
                elif body[j] == "}":
                    brace -= 1
                    if brace == 0:
                        break
                j += 1
            out.append(";")
            i = j + 1
            prev = ";"
            continue
        out.append(char)
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        if not char.isspace():
            prev = char
        i += 1
    return _QUALIFIER.sub("", "".join(out))


# Storage/inline qualifiers a header-only helper carries but a cffi prototype
# must not. Matched as whole words so identifiers merely containing them are safe.
_QUALIFIER = re.compile(r"\b(?:static|inline)\b\s*")


def _split_declarations(body: str) -> list[str]:
    """Split a section body into top-level declarations on depth-0 semicolons."""
    decls: list[str] = []
    depth = 0
    start = 0
    for i, char in enumerate(body):
        if char in "{[(":
            depth += 1
        elif char in "}])":
            depth -= 1
        elif char == ";" and depth == 0:
            decl = body[start : i + 1].strip()
            if decl:
                decls.append(decl)
            start = i + 1
    tail = body[start:].strip()
    if tail:
        decls.append(tail)
    return decls


def _blame(prior: str, section: Section, error: Exception) -> GeneratorError:
    """Pinpoint the declaration in ``section`` that cffi rejected."""
    probe = cffi.FFI()
    if prior:
        probe.cdef(prior)
    # Feed the section's declarations cumulatively on one FFI so a decl that
    # legitimately depends on an earlier decl in this same section is not blamed
    # for the earlier type being "undefined"; only the genuinely bad decl fails.
    for decl in _split_declarations(section.body):
        try:
            probe.cdef(decl)
        except _CDEF_ERRORS:
            return GeneratorError(
                f"cffi rejected a declaration from {section.header}:\n"
                f"{decl}\n  ({error})"
            )
    return GeneratorError(
        f"cffi rejected the declarations from {section.header}:\n  ({error})"
    )


def verify(sections: list[Section]) -> None:
    """Feed the sections to cffi's parser, blaming the offending header on error.

    Sections are parsed cumulatively on one ``FFI`` in dependency order, mirroring
    how the raw-layer build consumes the emitted file. A failure is narrowed to
    the specific header and, where possible, the specific declaration.
    """
    ffi = cffi.FFI()
    accepted: list[str] = []
    for section in sections:
        try:
            ffi.cdef(section.body)
        except _CDEF_ERRORS as exc:
            raise _blame("\n".join(accepted), section, exc) from exc
        accepted.append(section.body)


def _render(sections: list[Section], commit: str | None) -> str:
    """Render the final deterministic cdef file from verified sections."""
    header_list = ", ".join(section.header for section in sections)
    lines = [
        "/*",
        " * Generated cdef for the libghostty-vt raw layer. DO NOT EDIT BY HAND.",
        " *",
        " * Produced from the vendored upstream headers by tools/gen_cdef.",
        " * Regenerate with `just gen-cdef` (after `just vendor`).",
        " *",
        f" * Pinned upstream commit: {commit or 'unknown'}",
        f" * Headers: {header_list}",
        " */",
    ]
    for section in sections:
        lines.append("")
        lines.append(f"/* ---- {section.header} ---- */")
        lines.append(section.body)
    return "\n".join(lines) + "\n"


def generate_cdef(
    include_dir: Path,
    headers: tuple[str, ...] | None = None,
    commit: str | None = None,
    umbrella: str = UMBRELLA,
) -> str:
    """Generate, verify, and return the cdef text for the vt surface.

    With ``headers=None`` (the default) the full surface reachable from the
    umbrella is discovered, so the raw layer is complete by construction. An
    explicit tuple restricts generation to those headers (used by the tooling
    tests and the ``--header`` CLI escape hatch).

    Deterministic for a given pinned commit: the output carries no timestamps or
    absolute paths, only the declarations, the commit, and the header list.
    """
    preprocessed = preprocess(include_dir, umbrella)
    if headers is None:
        headers = discover_headers(preprocessed, include_dir)
    sections = split_sections(preprocessed, include_dir, headers)
    sections = [
        Section(header=s.header, body=_strip_inline_definitions(s.body))
        for s in sections
    ]
    verify(sections)
    return _render(sections, commit)
