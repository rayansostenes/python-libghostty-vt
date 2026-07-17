# python-libghostty-vt

Idiomatic, fully typed Python bindings for
[libghostty-vt](https://github.com/ghostty-org/ghostty) — the C-ABI terminal
(VT) library extracted from [Ghostty](https://ghostty.org).

- **Distribution name:** `python-libghostty-vt`
- **Import name:** `ghostty_vt`

Feed a terminal the bytes a program would print and read back the plain text a
human would see; encode keyboard input to the exact bytes a PTY expects; parse
OSC/SGR escape sequences into typed results. Useful for testing TUIs,
recording and replaying sessions, cleaning subprocess output for an AI agent,
and building terminal frontends — no running terminal or subprocess required.

> [!WARNING]
> Early development. libghostty-vt's C API is explicitly unstable ("public
> alpha"), and these bindings are not yet published to PyPI. Expect breaking
> changes on every upstream bump. Each release pins one upstream commit (see
> [Versioning](#versioning)).

## Two-layer design

The package is built in two layers:

- The **raw layer** is a private, generated 1:1 cffi binding over the C API,
  complete by construction and regenerated whenever the pinned upstream commit
  moves. It is unstable and not part of the public API.
- The **idiomatic layer** — everything you import from `ghostty_vt` — is a
  hand-written, fully typed, Pythonic API organized into domain submodules
  (terminal, key, mouse, osc, sgr, color, …). It is the only surface with
  stability intent. You never need to touch the raw layer.

See [ADR 0001](docs/adr/0001-cffi-api-mode-bindings.md) for the binding
mechanism and [ADR 0002](docs/adr/0002-idiomatic-layer-conventions.md) for the
idiomatic conventions (snake_case, `GhosttyVtError` hierarchy, context managers,
`bytes` in / `str` out).

## Installation

```sh
pip install python-libghostty-vt   # or: uv add python-libghostty-vt
```

Prebuilt wheels ship for the platforms below — no zig, no C compiler. Requires
**Python 3.14 or newer**; the API targets modern typing and idioms with no
legacy shims.

### Supported platforms

| Platform          | Architectures      | Wheel                    |
| ----------------- | ------------------ | ------------------------ |
| Linux (glibc)     | x86_64, aarch64    | manylinux                |
| Linux (musl)      | x86_64, aarch64    | musllinux (e.g. Alpine)  |
| macOS             | arm64, x86_64      | native                   |
| Windows           | x86_64             | best-effort, unsupported |

Wheels are CPython 3.14 GIL builds (`cp314`) only: cffi's API mode targets a
specific interpreter, so there is no `abi3` wheel and no free-threaded
(`cp314t`) wheel yet. On any other platform, the source distribution builds
offline from the bundled vendored source — that path needs only zig and a C
compiler, never the network.

## Quickstart

Create a `Terminal`, feed it VT-encoded bytes, and read back the visible text.
It is a context manager, so the native handle is released when the block exits:

```python
>>> from ghostty_vt import Terminal
>>> with Terminal(80, 24) as term:
...     term.feed(b"hello, \x1b[1mworld\x1b[0m\r\n")
...     term.feed(b"goodbye")
...     print(term.visible_text())
hello, world
goodbye

```

Styling is resolved away, escape sequences are interpreted, and trailing
whitespace is trimmed — the result is what a user would see, not the raw stream.
Terminals resize and reflow, and their dimensions are queryable:

```python
>>> term = Terminal(80, 24)
>>> term.cols, term.rows
(80, 24)
>>> term.resize(100, 40)
>>> term.cols, term.rows
(100, 40)
>>> term.close()

```

Encode keyboard input to the bytes a terminal expects. A `KeyEncoder` produces
the classic (legacy) encoding by default; pass `kitty_flags` to switch to the
Kitty keyboard protocol:

```python
>>> from ghostty_vt import Key, KeyEncoder, KeyEvent, KittyFlags, Mods
>>> legacy = KeyEncoder()
>>> legacy.encode(KeyEvent(Key.C, Mods.CTRL))
b'\x03'
>>> legacy.encode(KeyEvent(Key.ARROW_UP))
b'\x1b[A'
>>> kitty = KeyEncoder(kitty_flags=KittyFlags.DISAMBIGUATE)
>>> kitty.encode(KeyEvent(Key.ESCAPE))
b'\x1b[27u'

```

Build metadata and the pinned upstream commit are available at runtime, so you
can report upstream-specific bugs precisely:

```python
>>> import ghostty_vt
>>> info = ghostty_vt.build_info()
>>> info.optimize.name
'RELEASE_FAST'
>>> len(ghostty_vt.GHOSTTY_COMMIT)   # the 40-char upstream commit hash
40
>>> isinstance(ghostty_vt.__version__, str)
True

```

## Local development

Requires [uv](https://docs.astral.sh/uv/) and
[just](https://github.com/casey/just). The zig toolchain is pinned and provided
automatically through the `ziglang` dev dependency — no separate zig install is
needed.

A fresh clone reaches green tests with three documented commands:

```sh
just vendor    # fetch upstream at the pinned commit + prefetch zig deps (network)
just build     # build the raw-layer cffi extension in place (offline)
just test      # run the test suite with 100% branch coverage enforced
```

`just setup` (run by `just vendor`'s environment implicitly, or on its own)
syncs the dev environment. The full recipe set:

```sh
just setup     # sync the dev environment (Python 3.14+, pinned zig)
just vendor    # fetch upstream at the pinned commit + prefetch zig deps (network)
just build     # build the raw-layer cffi extension in place (offline)
just build-lib # build only the static libghostty-vt from vendored source (offline)
just gen-cdef  # regenerate the raw-layer cdef from the vendored headers
just lint      # ruff lint
just fmt       # ruff format
just test      # run the test suite with 100% branch coverage enforced
just typecheck # mypy + pyright (strict) over source and tests
just typesafety # run the typesafety suite (five checkers + verifytypes)
```

Run `just` with no arguments to list every recipe. After `just vendor`,
`just build` compiles the extension (building the static library first if
needed) so `just test` can import `ghostty_vt`.

The README's quickstart examples are executed as doctests by the test suite, so
they cannot silently rot.

### Vendoring

The single pinned upstream commit lives in
[`ghostty-commit.txt`](ghostty-commit.txt) — exactly one place. `just vendor`
fetches the Ghostty source at that commit into `vendor/ghostty/` (gitignored)
and prefetches its zig build dependencies into `vendor/zig-cache/`, so
`just build` runs with no network access. Upstream's MIT license notice is
retained alongside the vendored source.

Bumping upstream is a one-hash edit to `ghostty-commit.txt` followed by
`just vendor`. The pinned zig version tracks upstream's minimum and is bumped
via the `ziglang` pin in [`pyproject.toml`](pyproject.toml).

## Versioning

The package uses **0.x semver**: a minor bump signals an API or upstream change,
a patch bump a fix. Each release is built from exactly one upstream commit,
recorded in [`ghostty-commit.txt`](ghostty-commit.txt) and exposed at runtime as
`ghostty_vt.GHOSTTY_COMMIT`. Release notes state the pinned commit per release,
so a downstream maintainer can map any behavior to a precise upstream revision.
Because upstream's API is unstable, expect the raw layer to regenerate and the
idiomatic layer to need hand-updates whenever the pinned commit moves.

The package version is single-sourced from `pyproject.toml` and read back from
the installed metadata as `ghostty_vt.__version__`.

## Releasing

Releases are token-free: publishing a GitHub release runs the whole pipeline.
The [Wheels workflow](.github/workflows/wheels.yml) builds the sdist and every
blocking wheel (manylinux/musllinux x86_64 + aarch64, macOS arm64 + x86_64),
verifies each by running the test suite against it, then uploads the sdist and
all blocking wheels to PyPI via
[Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC — no API
tokens are stored). The best-effort Windows wheel is never published.

To cut a release:

1. Bump `version` in [`pyproject.toml`](pyproject.toml) to the next 0.x value
   (minor = API/upstream change, patch = fix). This is the single source of
   truth: `ghostty_vt.__version__` is read back from the installed metadata, so
   there is nothing else to edit.
2. Create a GitHub release whose tag equals that version (a leading `v` is
   allowed, e.g. `v0.1.0`). Draft the notes from
   [`.github/release-notes-template.md`](.github/release-notes-template.md);
   the workflow also appends the pinned commit automatically.
3. Publishing the release builds, verifies, and uploads to PyPI. The publish job
   fails before uploading if the built version doesn't match the tag.

**Dry run:** trigger the Wheels workflow manually (`workflow_dispatch`) to build
and verify without publishing. Set the `publish_testpypi` input to additionally
upload to [TestPyPI](https://test.pypi.org/), rehearsing the full publish path.

Both PyPI and TestPyPI must be configured with this repository and workflow as a
trusted publisher, and the `pypi` / `testpypi` GitHub environments must exist.

## License

MIT — see [LICENSE](LICENSE). libghostty-vt is likewise MIT-licensed; its notice
is retained alongside the vendored source (`vendor/ghostty/LICENSE`).
