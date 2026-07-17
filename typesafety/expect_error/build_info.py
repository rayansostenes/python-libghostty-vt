# Expect-error typesafety pins for the build_info domain.
#
# Never executed. Every statement below is a deliberate misuse of the public API.
# Each line tagged `# expect-error` MUST draw at least one diagnostic from every
# checker; the harness fails if any tagged line stops erroring (the type guard
# regressed) or if an untagged line errors (the suite itself is broken).
from __future__ import annotations

from ghostty_vt import BuildInfo, OptimizeMode, build_info

info = build_info()

build_info(1)  # expect-error: takes no arguments
BuildInfo()  # expect-error: missing every required field
_wrong: int = build_info()  # expect-error: BuildInfo is not an int
info.does_not_exist  # expect-error: no such attribute
OptimizeMode.DOES_NOT_EXIST  # expect-error: no such enum member
