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

This is the ground floor of the build pipeline: project scaffold, a single
pinned upstream commit, an offline vendoring + static-library build. The cffi
bindings and the idiomatic Python API land in later milestones.

## Local development

Requires [uv](https://docs.astral.sh/uv/) and
[just](https://github.com/casey/just). The zig toolchain is pinned and provided
automatically through the `ziglang` dev dependency — no separate zig install is
needed.

```sh
just setup     # sync the dev environment (Python 3.14+, pinned zig)
just vendor    # fetch upstream at the pinned commit + prefetch zig deps (network)
just build     # build the static libghostty-vt from vendored source (offline)
just lint      # ruff lint
just fmt       # ruff format
just test      # run the test suite
```

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
travels with the vendored source and the built artifacts.
