# Typesafety suite

Never-executed Python files that pin the idiomatic layer's public types. They are
type-checked, not run: importing them needs only the stubs and source, never the
compiled extension.

## Layout

- `positive/<domain>.py` — `typing.assert_type` pins for the domain's public API.
  These must draw **zero** diagnostics from every checker; a drift in any inferred
  public type turns them red.
- `expect_error/<domain>.py` — deliberate misuse of the public API. Every line
  tagged `# expect-error` must draw **at least one** diagnostic from every checker;
  no other line may. A misuse that stops being flagged means a type guard
  regressed.
- `pyrightconfig.json` — strict config shared by pyright and basedpyright when they
  check the suite (resolves `ghostty_vt` from `../src`).

Seed the suite with a new file per domain as each domain ships.

## Running

```sh
just typesafety
```

The harness (`scripts/typesafety.py`) runs, over the suite:

- **mypy, pyright, basedpyright, ty, pyrefly** — all at the latest stable version
  resolved by `uv` at run time. A checker release can therefore turn CI red without
  a code change; this is accepted.
- **Pylance's bundled pyright** — resolved from the pylance-release repo and run
  additionally whenever it differs from the latest pyright, so the VS Code editor
  experience is gated too.
- **`pyright --verifytypes`** — gates 100% public-symbol type completeness against
  the installed package (hence `just typesafety` builds and installs first).

The harness parses each checker's diagnostics and fails if any positive file draws
a diagnostic, any tagged misuse stops erroring, or completeness drops below 100%.
