# python-libghostty-vt

Python bindings for libghostty-vt, the C-ABI terminal (VT) library extracted
from Ghostty. Distribution name `python-libghostty-vt`, import name `ghostty_vt`.

## Language

- **Upstream**:
  The ghostty repository, the sole source of libghostty-vt.
  _Avoid_: vendor (that word is reserved for the vendored copy)

- **Pinned commit**:
  The single upstream commit hash this release of the bindings is built from.
  _Avoid_: version (upstream has no tagged versions yet)

- **Vendored source**:
  The copy of upstream sources at the pinned commit, bundled so builds need no network.

- **Raw layer**:
  The private, generated, unstable 1:1 binding over the C API; complete by construction.
  _Avoid_: low-level API, sys layer

- **Idiomatic layer**:
  The public, typed, hand-written Python API; the only surface with stability intent.
  _Avoid_: wrapper, high-level API

- **Domain**:
  A cohesive slice of the upstream API (terminal, key, mouse, osc, sgr, color,
  selection, kitty graphics, paste, formatter); each maps to one public submodule.
  _Avoid_: module (ambiguous), header group

- **Terminal**:
  The stateful emulated terminal: bytes are fed in, screen state is queried out.

- **Typesafety suite**:
  Never-executed Python files that must pass every supported type checker;
  guards the idiomatic layer's public types.
  _Avoid_: type tests (they don't run)

## Relationships

- The **Idiomatic layer** is built on the **Raw layer**; users never need the raw layer.
- Every **Domain** is covered by both layers before a release.
- The **Vendored source** is produced from **Upstream** at the **Pinned commit**.
- The **Typesafety suite** exercises only the **Idiomatic layer**.

## Example dialogue

> **Dev:** "Does bumping the **pinned commit** change the **idiomatic layer**?"
> **Maintainer:** "Only if **upstream** changed a **domain**'s semantics — the
> **raw layer** regenerates automatically; the idiomatic layer changes only by hand,
> and the **typesafety suite** catches any public type drift."

## Flagged ambiguities

- "full surface" was ambiguous between "raw layer covers everything" and
  "every domain is idiomatic" — resolved: every domain is idiomatic before v0.1.
