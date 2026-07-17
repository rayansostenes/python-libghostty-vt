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
    GeneratorError,
    Section,
    discover_headers,
    generate_cdef,
    preprocess,
    split_sections,
    verify,
)
from gen_cdef._generator import (
    _split_declarations,  # pyright: ignore[reportPrivateUsage]
    _strip_inline_definitions,  # pyright: ignore[reportPrivateUsage]
)
from gen_cdef.completeness import (
    compiled_symbols,
    missing_symbols,
    surface_symbols,
)

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
    regenerated = generate_cdef(include_dir=INCLUDE_DIR, commit=PINNED_COMMIT)
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
def test_discovery_spans_the_full_surface_and_drops_non_contributors() -> None:
    # Discovery is what makes the raw layer complete by construction: every vt
    # header that contributes declarations is picked up, in dependency order.
    headers = discover_headers(preprocess(INCLUDE_DIR), INCLUDE_DIR)
    # A spread of domains across the surface, not just the tracer subset.
    for header in (
        "ghostty/vt/types.h",
        "ghostty/vt/terminal.h",
        "ghostty/vt/key/event.h",
        "ghostty/vt/mouse/encoder.h",
        "ghostty/vt/selection.h",
        "ghostty/vt/modes.h",
    ):
        assert header in headers
    # Aggregator headers (only #include others) and the wasm-gated header
    # contribute no declarations, so they must not appear.
    assert "ghostty/vt/key.h" not in headers
    assert "ghostty/vt/mouse.h" not in headers
    assert "ghostty/vt/wasm.h" not in headers
    # Dependencies come before dependents (types.h underpins everything).
    assert headers.index("ghostty/vt/types.h") < headers.index("ghostty/vt/terminal.h")


@needs_vendor
def test_full_surface_inline_helpers_are_prototypes_not_definitions() -> None:
    # modes.h ships `static inline` helpers; the cdef keeps them callable as bare
    # prototypes (a definition would make cffi reject the whole file).
    cdef = generate_cdef(INCLUDE_DIR, commit=PINNED_COMMIT)
    assert "GhosttyMode ghostty_mode_new(uint16_t value, bool ansi) ;" in cdef
    assert "static" not in cdef
    assert "inline" not in cdef


def test_strip_inline_definitions_reduces_a_body_to_a_prototype() -> None:
    body = "static inline int add(int a, int b) {\n    return a + b;\n}"
    assert _strip_inline_definitions(body) == "int add(int a, int b) ;"


def test_strip_inline_definitions_leaves_type_bodies_untouched() -> None:
    # A struct body's `{` does not follow a `)`, so it must survive verbatim.
    body = "typedef struct { int x; int y; } Point;"
    assert _strip_inline_definitions(body) == body


def test_discover_headers_reports_an_empty_surface(tmp_path: Path) -> None:
    with pytest.raises(GeneratorError, match="no headers under"):
        discover_headers('# 1 "other/thing.h"\nint x;\n', tmp_path)


@needs_vendor
def test_raw_layer_covers_every_exported_symbol() -> None:
    # The completeness gate (issue #7): every exported vt header symbol must be
    # callable from the compiled raw layer. The compiled extension is imported
    # exactly as the idiomatic layer imports it.
    from ghostty_vt import _raw

    assert missing_symbols(INCLUDE_DIR, _raw.lib) == set()


@needs_vendor
def test_surface_symbols_are_a_subset_of_the_compiled_layer() -> None:
    from ghostty_vt import _raw

    surface = surface_symbols(INCLUDE_DIR)
    # A representative sample spanning several domains is present.
    assert {"ghostty_terminal_new", "ghostty_mode_new", "ghostty_build_info"} <= surface
    assert surface <= compiled_symbols(_raw.lib)


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
