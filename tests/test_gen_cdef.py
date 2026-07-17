"""Tests for the header-to-cdef generator (``tools/gen_cdef``).

These exercise build-time tooling, not the shipped ``ghostty_vt`` package, so
they are outside the package's coverage scope. Two concerns are covered: that the
generator produces a cffi-parseable cdef for the deliberately hard subset
(callback structs, nested structs, enums, opaque pointers) and stays in sync with
the committed output, and that failures name the offending header/declaration
rather than dying opaquely.
"""

from __future__ import annotations

import re
from pathlib import Path

import cffi
import gen_cdef
import pytest
from gen_cdef import (
    DEFAULT_HEADERS,
    GeneratorError,
    Section,
    generate_cdef,
    preprocess,
    split_sections,
    verify,
)
from gen_cdef._generator import _split_declarations

REPO_ROOT = Path(__file__).resolve().parent.parent
INCLUDE_DIR = REPO_ROOT / "vendor" / "ghostty" / "include"
COMMITTED_CDEF = REPO_ROOT / "src" / "ghostty_vt" / "_cdef.h"
PINNED_COMMIT = (REPO_ROOT / "ghostty-commit.txt").read_text().strip()

# The generator reads the vendored headers; when they are absent (a source tree
# before `just vendor`), the header-driven tests cannot run. The compiled
# extension the rest of the suite imports needs the same headers, so in practice
# these are only skipped in a bare checkout.
needs_vendor = pytest.mark.skipif(
    not INCLUDE_DIR.is_dir(), reason="vendored headers absent; run `just vendor`"
)


@needs_vendor
def test_generated_cdef_matches_committed() -> None:
    # The regeneration recipe is deterministic for the pinned commit: rerunning
    # it must reproduce the committed file byte for byte, or it is stale.
    regenerated = generate_cdef(
        include_dir=INCLUDE_DIR, headers=DEFAULT_HEADERS, commit=PINNED_COMMIT
    )
    assert regenerated == COMMITTED_CDEF.read_text()


@needs_vendor
def test_generation_is_deterministic() -> None:
    first = generate_cdef(INCLUDE_DIR, commit=PINNED_COMMIT)
    second = generate_cdef(INCLUDE_DIR, commit=PINNED_COMMIT)
    assert first == second


@needs_vendor
def test_generated_cdef_is_parseable_by_cffi() -> None:
    # The core acceptance: the hard subset produces a cdef cffi accepts.
    cdef = generate_cdef(INCLUDE_DIR, commit=PINNED_COMMIT)
    cffi.FFI().cdef(cdef)


@needs_vendor
def test_generated_cdef_covers_the_hard_constructs() -> None:
    cdef = generate_cdef(INCLUDE_DIR, commit=PINNED_COMMIT)
    # Opaque-pointer handle typedef.
    assert "typedef struct GhosttyTerminalImpl* GhosttyTerminal;" in cdef
    # Enum member carrying an explicit value.
    assert "GHOSTTY_BUILD_INFO_OPTIMIZE = 4," in cdef
    # Nested struct-of-structs (device attributes).
    assert "GhosttyDeviceAttributesPrimary primary;" in cdef
    # Struct-of-callbacks vtable (function-pointer member).
    assert "(*alloc)(void *ctx, size_t len, uint8_t alignment" in cdef
    # Standalone function-pointer callback typedef.
    assert "typedef bool (*GhosttySysDecodePngFn)(" in cdef
    # The visibility macro was stripped, not left verbatim.
    assert "GHOSTTY_API" not in cdef


@needs_vendor
def test_split_sections_reports_unreachable_header() -> None:
    preprocessed = preprocess(INCLUDE_DIR)
    with pytest.raises(GeneratorError, match=re.escape("ghostty/vt/nonexistent.h")):
        split_sections(preprocessed, INCLUDE_DIR, ("ghostty/vt/nonexistent.h",))


def test_preprocess_missing_umbrella_names_it(tmp_path: Path) -> None:
    with pytest.raises(GeneratorError, match="umbrella header not found"):
        preprocess(tmp_path, umbrella="ghostty/vt/absent.h")


def test_preprocess_failure_names_the_header(tmp_path: Path) -> None:
    # A header the preprocessor rejects: the error surfaces the header name and
    # the compiler diagnostic rather than a bare non-zero exit.
    bad = tmp_path / "broken.h"
    bad.write_text("#error deliberate failure\n")
    with pytest.raises(GeneratorError) as excinfo:
        preprocess(tmp_path, umbrella="broken.h")
    message = str(excinfo.value)
    assert "broken.h" in message
    assert "deliberate failure" in message


def test_verify_blames_the_offending_header_and_declaration() -> None:
    good = Section(header="ghostty/vt/types.h", body="typedef struct { int x; } A;")
    bad = Section(
        header="ghostty/vt/broken.h",
        body="typedef struct { int y; } B;\ntypedef struct { int z } C;",
    )
    with pytest.raises(GeneratorError) as excinfo:
        verify([good, bad])
    message = str(excinfo.value)
    assert "ghostty/vt/broken.h" in message
    # The specific unparseable declaration is quoted, not just the header.
    assert "int z" in message


def test_verify_blames_the_bad_decl_past_an_in_section_dependency() -> None:
    # A valid decl (B) depends on a type (A) defined earlier in the same section;
    # the genuinely malformed decl (C) comes after. Blame must land on C, not on
    # the innocent dependent B parsed in isolation.
    bad = Section(
        header="ghostty/vt/broken.h",
        body=(
            "typedef struct { int x; } A;\n"
            "typedef struct { A a; } B;\n"
            "typedef struct { int z } C;"
        ),
    )
    with pytest.raises(GeneratorError) as excinfo:
        verify([bad])
    message = str(excinfo.value)
    assert "int z" in message
    assert "} B;" not in message


def test_verify_accepts_a_valid_dependency_chain() -> None:
    sections = [
        Section("a.h", "typedef struct { int x; } A;"),
        Section("b.h", "typedef struct { A inner; } B;"),
    ]
    verify(sections)  # must not raise: b.h depends on a type from a.h


def test_split_declarations_ignores_semicolons_inside_braces() -> None:
    body = "typedef struct { int a; int b; } S;\nvoid f(void);"
    assert _split_declarations(body) == [
        "typedef struct { int a; int b; } S;",
        "void f(void);",
    ]


def test_public_api_is_exported() -> None:
    assert set(gen_cdef.__all__) <= set(dir(gen_cdef))
