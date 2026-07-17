"""CLI for the cdef generator: ``python -m gen_cdef`` (wired to ``just gen-cdef``).

Regenerates the committed raw-layer cdef from the vendored headers. The pinned
commit and default paths are resolved relative to the repo root so the recipe
takes no arguments in the common case.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from gen_cdef._generator import GeneratorError, generate_cdef, repo_root


def main(argv: list[str] | None = None) -> int:
    root = repo_root()
    parser = argparse.ArgumentParser(
        prog="gen_cdef",
        description="Generate the libghostty-vt raw-layer cdef from vendored headers.",
    )
    parser.add_argument(
        "--include-dir",
        type=Path,
        default=root / "vendor" / "ghostty" / "include",
        help="Directory holding the vendored ghostty/vt headers.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "src" / "ghostty_vt" / "_cdef.h",
        help="Path to write the generated cdef to.",
    )
    parser.add_argument(
        "--header",
        action="append",
        dest="headers",
        metavar="ghostty/vt/NAME.h",
        help="Include-relative header to emit (repeatable; defaults to the full "
        "surface discovered from the umbrella).",
    )
    args = parser.parse_args(argv)

    headers = tuple(args.headers) if args.headers else None
    commit_file = root / "ghostty-commit.txt"
    commit = commit_file.read_text().strip() if commit_file.is_file() else None

    try:
        cdef = generate_cdef(
            include_dir=args.include_dir, headers=headers, commit=commit
        )
    except GeneratorError as exc:
        print(f"gen-cdef: error: {exc}", file=sys.stderr)
        return 1

    args.output.write_text(cdef)
    header_count = cdef.count("/* ---- ")
    print(
        f"gen-cdef: wrote {args.output} "
        f"({header_count} header(s), pinned {commit or 'unknown'})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
