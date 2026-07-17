"""Header-to-cdef generation tooling for the libghostty-vt raw layer.

Build-time tooling that lives outside the shipped ``ghostty_vt`` package. See
``_generator`` for the pipeline and ``__main__`` for the CLI (``just gen-cdef``).
"""

from __future__ import annotations

from gen_cdef._generator import (
    DEFAULT_HEADERS,
    UMBRELLA,
    GeneratorError,
    Section,
    generate_cdef,
    preprocess,
    split_sections,
    verify,
)

__all__ = [
    "DEFAULT_HEADERS",
    "UMBRELLA",
    "GeneratorError",
    "Section",
    "generate_cdef",
    "preprocess",
    "split_sections",
    "verify",
]
