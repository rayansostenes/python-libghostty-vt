# python-libghostty-vt

Idiomatic, fully typed Python bindings for
[libghostty-vt](https://github.com/ghostty-org/ghostty) — the C-ABI terminal
(VT) library extracted from [Ghostty](https://ghostty.org).

- **Distribution name:** `python-libghostty-vt`
- **Import name:** `ghostty_vt`

> [!WARNING]
> Early development. The upstream C API is explicitly unstable ("public
> alpha"), and these bindings are not yet published. Expect breaking changes.

## Status

Early tracer bullet: a complete path through every layer for a single tiny
domain. A cffi API-mode extension (per [ADR 0001](docs/adr/0001-cffi-api-mode-bindings.md))
statically links the zig-built libghostty-vt and exposes its `build_info` domain
through a private raw layer and a typed idiomatic layer. The remaining domains
and the full raw surface land in later milestones.

```python
import ghostty_vt

info = ghostty_vt.build_info()
info.simd              # bool: SIMD code paths enabled
info.kitty_graphics    # bool: Kitty graphics support
info.optimize          # OptimizeMode.RELEASE_FAST
info.version           # "0.1.0-dev"

ghostty_vt.GHOSTTY_COMMIT  # the pinned upstream commit, baked at build time
```

## Local development

Requires [uv](https://docs.astral.sh/uv/) and
[just](https://github.com/casey/just). The zig toolchain is pinned and provided
automatically through the `ziglang` dev dependency — no separate zig install is
needed.

```sh
just setup     # sync the dev environment (Python 3.14+, pinned zig)
just vendor    # fetch upstream at the pinned commit + prefetch zig deps (network)
just build     # build the raw-layer cffi extension in place (offline)
just build-lib # build only the static libghostty-vt from vendored source (offline)
just lint      # ruff lint
just fmt       # ruff format
just test      # run the test suite with 100% branch coverage enforced
```

After `just vendor`, `just build` compiles the extension (building the static
library first if needed) so `just test` can import `ghostty_vt`.

Run `just` with no arguments to list every recipe.

## Vendoring

The single pinned upstream commit lives in [`ghostty-commit.txt`](ghostty-commit.txt)
— exactly one place. `just vendor` fetches the Ghostty source at that commit
into `vendor/ghostty/` (gitignored) and prefetches its zig build dependencies
into `vendor/zig-cache/`, so `just build` runs with no network access. Upstream's
MIT license notice is retained alongside the vendored source.

Bumping upstream is a one-hash edit to `ghostty-commit.txt` followed by
`just vendor`. The pinned zig version tracks upstream's minimum and is bumped
via the `ziglang` pin in [`pyproject.toml`](pyproject.toml).

## License

MIT — see [LICENSE](LICENSE). libghostty-vt is likewise MIT-licensed; its notice
is retained alongside the vendored source (`vendor/ghostty/LICENSE`).
