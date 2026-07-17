"""Setuptools shim wiring the cffi raw-layer extension into the build.

All static metadata lives in ``pyproject.toml``. cffi's out-of-line (API mode)
extension is declared via ``cffi_modules``, which has no ``pyproject.toml``
equivalent, so this minimal shim remains. Building the extension also builds the
static libghostty-vt from the vendored source when absent; see
``src/ghostty_vt/_cffi_build.py``.
"""

from setuptools import setup

setup(cffi_modules=["src/ghostty_vt/_cffi_build.py:ffibuilder"])
