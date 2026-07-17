# 1. Bind libghostty-vt via cffi in API mode

Date: 2026-07-16

## Status

Accepted

## Context

libghostty-vt exposes ~250 C functions across ~30 headers, is explicitly
unstable upstream, and includes callback-struct-based APIs (`device.h`).
Wheels are built in CI for every platform, so end users never need a
compiler. Candidate mechanisms: ziggy-pydust, ctypes with a bundled shared
library, hand-written CPython extension, Cython, cffi.

ziggy-pydust is disqualified: maintenance mode, hard-coupled to poetry
(uv support issue #408 open, unanswered), Python 3.14 support unconfirmed.

## Decision

Use cffi in API (out-of-line, compiled) mode. The extension is generated
from the preprocessed upstream headers and statically links the zig-built
libghostty-vt. The package has two layers: a private raw binding layer and
a public, idiomatic, fully typed pure-Python layer (mirroring the Rust
`-sys` / safe-crate split).

## Consequences

- Fast native calls and first-class callback support, unlike ctypes.
- Binding generation is semi-automated from headers, which matters while
  upstream churns a 250-function surface.
- Requires per-platform wheel builds (cibuildwheel) with zig available in
  the build environment, instead of a single cross-compiling runner.
- A header-preprocessing step (C headers → cffi `cdef`) becomes part of
  the build and must track upstream header changes.
