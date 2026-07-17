"""Header-to-cdef generation tooling for the libghostty-vt raw layer.

Build-time tooling that lives outside the shipped ``ghostty_vt`` package. See
``_generator`` for the pipeline and ``__main__`` for the CLI (``just gen-cdef``).
"""

from __future__ import annotations

from gen_cdef._generator import (
    UMBRELLA,
    VT_HEADER_PREFIX,
    GeneratorError,
    Section,
    discover_headers,
    generate_cdef,
    preprocess,
    repo_root,
    split_sections,
    verify,
)

__all__ = [
    "UMBRELLA",
    "VT_HEADER_PREFIX",
    "GeneratorError",
    "Section",
    "discover_headers",
    "generate_cdef",
    "preprocess",
    "repo_root",
    "split_sections",
    "verify",
]
