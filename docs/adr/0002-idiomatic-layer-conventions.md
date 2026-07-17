# 2. Idiomatic-layer domain conventions

Date: 2026-07-17

## Status

Accepted

## Context

The idiomatic layer grows one domain at a time (terminal, key, mouse, osc, sgr,
selection, …), each a hand-written submodule over the generated raw layer. The
`build_info` tracer domain and the foundation domains (errors, shared types,
color) established a shape that every later domain should copy so contributors
and agents don't re-derive it per ticket. This ADR records that shape; the
foundation modules under `src/ghostty_vt/` are its canonical examples.

## Decision

Each domain is one public submodule of `ghostty_vt`:

- **Naming**: snake_case functions and attributes; `CapWords` types; enum members
  from the C API keep the upstream name minus its `GHOSTTY_<DOMAIN>_` prefix.
- **Layout**: the domain lives in `ghostty_vt/<domain>.py` with an explicit
  `__all__`; flagship names are re-exported from `ghostty_vt/__init__.py` and
  added to the top-level `__all__`, while domain-specific helpers stay reachable
  only via the submodule.
- **Value types**: immutable data is a `@dataclass(frozen=True, slots=True)`;
  C enums map to `enum.Enum` whose members are the raw `_lib` constants.
- **Errors**: no public API surfaces a raw C result code. Fallible raw calls go
  through `ghostty_vt._result.check`, which maps a non-success `GhosttyResult`
  onto the `GhosttyVtError` hierarchy in `ghostty_vt/errors.py`. Python-side
  argument validation raises the standard-library exception (`ValueError`, …).
- **Data flow**: `bytes` in for stream feeds, `str` out for text queries; raw
  cdata never crosses the public boundary.
- **Raw access**: a domain reaches the raw layer only through
  `from ghostty_vt import _raw` (and `_result`); the C boundary is confined to
  the submodule.

Every public symbol is covered on three seams:

- **Tests** (`tests/test_<domain>.py`) exercise only the public API and assert
  external behavior; the raw layer is never tested directly, and coverage stays
  at 100%.
- **Typesafety** (`typesafety/positive/<domain>.py` and
  `typesafety/expect_error/<domain>.py`) pins inferred types with `assert_type`
  and proves misuse is flagged; `pyright --verifytypes` stays at 100%.

## Consequences

- A new domain ticket is a mechanical copy of this shape, reducing review to
  "does it follow the pattern" rather than "is the pattern right".
- The error hierarchy and shared types are defined once and imported by every
  domain, so failure modes and coordinate types stay consistent across the API.
- The typesafety and coverage gates make convention drift (an untyped symbol, a
  leaked C error, an untested branch) fail CI rather than reach a release.
