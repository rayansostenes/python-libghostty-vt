#!/usr/bin/env python3
"""Run the typesafety suite: five checkers, plus Pylance's pyright, plus verifytypes.

The suite under ``typesafety/`` is never executed. It pins the idiomatic layer's
public types at compile time:

* ``positive/`` files use ``typing.assert_type`` and must draw *zero* diagnostics
  from every checker; any drift in an inferred public type turns them red.
* ``expect_error/`` files deliberately misuse the API; every line tagged
  ``# expect-error`` must draw *at least one* diagnostic from every checker, and
  no other line may. A misuse that stops being flagged means a type guard
  regressed; a flagged untagged line means the suite itself is broken.

mypy and pyright run from the project's pinned dev environment -- the same
versions that gate PR CI -- because they must share the environment where
``ghostty_vt`` is built and installed (needed for the suite's imports and for
``--verifytypes``). basedpyright, ty, and pyrefly are not project dependencies,
so ``uv`` resolves each to the latest stable at run time -- a checker release can
therefore break this suite without a code change, which is accepted. The pyright
version bundled by Pylance (VS Code's Python extension) is resolved from the
pylance-release repo and run additionally when it differs from the latest
pyright, so the editor experience is gated too.

``pyright --verifytypes`` gates 100% public-symbol type completeness against the
installed package, so the harness requires ``ghostty_vt`` to be built and
installed in the active environment (``just build``).

Exit code is 0 only if every check passes.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SUITE_DIR = REPO_ROOT / "typesafety"
POSITIVE_DIR = SUITE_DIR / "positive"
EXPECT_ERROR_DIR = SUITE_DIR / "expect_error"
SRC_DIR = REPO_ROOT / "src"
PYRIGHT_CONFIG = SUITE_DIR / "pyrightconfig.json"

PACKAGE = "ghostty_vt"
EXPECT_ERROR_MARKER = "# expect-error"

# pyright is pinned in dev-deps with the [nodejs] extra so node ships as a
# uv-cached PyPI wheel instead of being fetched from nodejs.org at run time
# (setup-uv's cache does not cover pyright-python's node download). Every pyright
# invocation must carry that extra; basedpyright bundles its own node.
PYRIGHT_SPEC = "pyright[nodejs]"

# Pylance publishes the pyright version it bundles here, as {"pyrightVersion": ...}.
PYLANCE_RELEASE_URL = (
    "https://raw.githubusercontent.com/microsoft/pylance-release/"
    "main/releases/latest-release.json"
)
NETWORK_TIMEOUT = 20

# A diagnostic reduced to what the suite cares about: which file, which line.
Location = tuple[Path, int]


@dataclass
class CheckResult:
    """Outcome of running one checker over the whole suite."""

    checker: str
    failures: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures


def _suite_files(directory: Path) -> list[Path]:
    return sorted(p.resolve() for p in directory.glob("*.py"))


def _expected_error_lines(path: Path) -> set[int]:
    """1-based line numbers tagged as intentional misuse in an expect-error file.

    A tag is an inline ``# expect-error`` comment trailing a statement; prose that
    merely mentions the marker (e.g. this module's own docstring-comment) lives on
    a pure-comment line and is ignored.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    return {
        number
        for number, text in enumerate(lines, start=1)
        if EXPECT_ERROR_MARKER in text and not text.lstrip().startswith("#")
    }


def _run(
    cmd: list[str], env_extra: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _resolve_reported_path(raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


# --- Per-checker diagnostic collectors -------------------------------------
#
# Each collector runs one checker over every suite file and returns the set of
# (file, line) pairs it reports as errors. Warnings and notes are ignored: the
# suite asserts only on hard type errors, which every checker agrees on.


def _collect_mypy(files: list[str]) -> set[Location]:
    result = _run(
        [
            "uv",
            "run",
            "--with",
            "mypy",
            "mypy",
            "--strict",
            "--python-version",
            "3.14",
            "--no-error-summary",
            "--no-color-output",
            "--show-column-numbers",
            *files,
        ],
        env_extra={"MYPYPATH": str(SRC_DIR)},
    )
    pattern = re.compile(r"^(?P<path>.+?\.py):(?P<line>\d+):(?:\d+:)?\s*error:")
    found: set[Location] = set()
    for line in result.stdout.splitlines():
        match = pattern.match(line)
        if match:
            found.add((_resolve_reported_path(match["path"]), int(match["line"])))
    return found


def _collect_pyright_like(binary: str, spec: str) -> set[Location]:
    result = _run(
        [
            "uv",
            "run",
            "--with",
            spec,
            binary,
            "--project",
            str(PYRIGHT_CONFIG),
            "--outputjson",
        ]
    )
    # pyright prints the JSON report to stdout; a non-zero exit is expected
    # whenever the expect-error files draw diagnostics.
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(
            f"{binary}: could not parse --outputjson report:\n"
            f"{result.stdout}\n{result.stderr}"
        ) from None
    found: set[Location] = set()
    for diag in report.get("generalDiagnostics", []):
        if diag.get("severity") != "error":
            continue
        line = diag["range"]["start"]["line"] + 1  # pyright lines are 0-based
        found.add((_resolve_reported_path(diag["file"]), line))
    return found


def _collect_ty(files: list[str]) -> set[Location]:
    result = _run(
        [
            "uv",
            "run",
            "--with",
            "ty",
            "ty",
            "check",
            "--output-format",
            "concise",
            "--extra-search-path",
            "src",
            "--python-version",
            "3.14",
            *files,
        ]
    )
    pattern = re.compile(r"^(?P<path>.+?\.py):(?P<line>\d+):\d+:\s*error\[")
    found: set[Location] = set()
    for line in result.stdout.splitlines():
        match = pattern.match(line)
        if match:
            found.add((_resolve_reported_path(match["path"]), int(match["line"])))
    return found


def _collect_pyrefly(files: list[str]) -> set[Location]:
    with tempfile.NamedTemporaryFile(suffix=".json", mode="r", delete=False) as handle:
        out_path = handle.name
    _run(
        [
            "uv",
            "run",
            "--with",
            "pyrefly",
            "pyrefly",
            "check",
            "--output-format",
            "json",
            "--output",
            out_path,
            "--search-path",
            "src",
            "--python-version",
            "3.14",
            *files,
        ]
    )
    report = json.loads(Path(out_path).read_text(encoding="utf-8"))
    Path(out_path).unlink(missing_ok=True)
    found: set[Location] = set()
    for diag in report.get("errors", []):
        if diag.get("severity") != "error":
            continue
        found.add((_resolve_reported_path(diag["path"]), int(diag["line"])))
    return found


# --- Validation -------------------------------------------------------------


def _validate(checker: str, reported: set[Location]) -> CheckResult:
    result = CheckResult(checker)
    positive_files = _suite_files(POSITIVE_DIR)
    expect_error_files = _suite_files(EXPECT_ERROR_DIR)

    for path in positive_files:
        stray = sorted(line for file, line in reported if file == path)
        if stray:
            result.failures.append(
                f"positive/{path.name}: unexpected diagnostics on line(s) "
                f"{stray} (positive pins must check clean)"
            )

    for path in expect_error_files:
        expected = _expected_error_lines(path)
        actual = {line for file, line in reported if file == path}
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        if missing:
            result.failures.append(
                f"expect_error/{path.name}: misuse on line(s) {missing} was NOT "
                f"flagged (a type guard regressed)"
            )
        if unexpected:
            result.failures.append(
                f"expect_error/{path.name}: diagnostics on untagged line(s) "
                f"{unexpected} (unexpected)"
            )
    return result


def _verify_types(spec: str, label: str) -> CheckResult:
    result = CheckResult(f"{label} --verifytypes")
    proc = _run(
        [
            "uv",
            "run",
            "--with",
            spec,
            "pyright",
            "--verifytypes",
            PACKAGE,
            "--outputjson",
        ]
    )
    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError:
        result.failures.append(
            f"could not parse --verifytypes report:\n{proc.stdout}\n{proc.stderr}"
        )
        return result
    completeness = report.get("typeCompleteness", {})
    score = completeness.get("completenessScore", 0.0)
    if score < 1.0:
        unknown = [
            symbol["name"]
            for symbol in completeness.get("symbols", [])
            if not symbol.get("isTypeKnown", True)
        ]
        result.failures.append(
            f"type completeness is {score:.1%}, not 100%"
            + (f"; incomplete symbols: {unknown}" if unknown else "")
        )
    return result


# --- Pylance pyright resolution --------------------------------------------


class PylanceResolutionError(RuntimeError):
    """The Pylance-bundled pyright version could not be resolved."""


def _latest_pyright_version() -> str:
    proc = _run(["uv", "run", "--with", PYRIGHT_SPEC, "pyright", "--version"])
    match = re.search(r"(\d+\.\d+\.\d+)", proc.stdout)
    if not match:
        raise RuntimeError(f"could not read pyright version from: {proc.stdout!r}")
    return match.group(1)


def _pylance_pyright_version() -> str:
    """Resolve the pyright version Pylance bundles, or raise.

    A network or JSON failure raises rather than returning ``None``: silently
    skipping the Pylance leg would let a Pylance-specific regression pass with a
    green suite, so the caller turns any resolution failure into a hard failure.
    """
    try:
        with urllib.request.urlopen(
            PYLANCE_RELEASE_URL, timeout=NETWORK_TIMEOUT
        ) as resp:
            payload = json.load(resp)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise PylanceResolutionError(
            f"could not fetch pylance-release metadata: {exc}"
        ) from exc
    version = payload.get("pyrightVersion")
    if not isinstance(version, str):
        raise PylanceResolutionError(
            "pylance-release JSON has no string pyrightVersion field"
        )
    return version


# --- Orchestration ----------------------------------------------------------


def _print_result(result: CheckResult) -> None:
    if result.ok:
        print(f"  PASS  {result.checker}")
    else:
        print(f"  FAIL  {result.checker}")
        for failure in result.failures:
            print(f"          {failure}")


def main() -> int:
    files = [
        str(path.relative_to(REPO_ROOT))
        for path in _suite_files(POSITIVE_DIR) + _suite_files(EXPECT_ERROR_DIR)
    ]
    if not files:
        print("error: no suite files found under typesafety/", file=sys.stderr)
        return 1

    latest_pyright = _latest_pyright_version()

    # (label, diagnostic collector) for every file-checking run.
    collectors: list[tuple[str, Callable[[], set[Location]]]] = [
        ("mypy", lambda: _collect_mypy(files)),
        (
            f"pyright=={latest_pyright} (latest)",
            lambda: _collect_pyright_like("pyright", PYRIGHT_SPEC),
        ),
        ("basedpyright", lambda: _collect_pyright_like("basedpyright", "basedpyright")),
        ("ty", lambda: _collect_ty(files)),
        ("pyrefly", lambda: _collect_pyrefly(files)),
    ]

    # (spec, label) for every --verifytypes run.
    verifytypes_runs: list[tuple[str, str]] = [
        (PYRIGHT_SPEC, f"pyright=={latest_pyright} (latest)")
    ]

    results: list[CheckResult] = []

    try:
        pylance_pyright: str | None = _pylance_pyright_version()
    except PylanceResolutionError as exc:
        # A resolution failure is a hard failure, not a silent skip: the Pylance
        # gate is an acceptance criterion, so a green suite must never mean it
        # was quietly dropped.
        failure = CheckResult("Pylance pyright resolution")
        failure.failures.append(f"{exc}; the Pylance gate was not enforced")
        results.append(failure)
        pylance_pyright = None
        _print_result(failure)
        print()

    if pylance_pyright is None:
        pass  # failure already recorded above
    elif pylance_pyright == latest_pyright:
        print(
            f"Pylance bundles pyright {pylance_pyright} == latest {latest_pyright}: "
            "no extra run needed.\n"
        )
    else:
        spec = f"pyright[nodejs]=={pylance_pyright}"
        label = f"pyright=={pylance_pyright} (Pylance)"
        collectors.append((label, lambda s=spec: _collect_pyright_like("pyright", s)))
        verifytypes_runs.append((spec, label))
        print(
            f"Pylance bundles pyright {pylance_pyright} "
            f"(latest is {latest_pyright}): running both.\n"
        )

    print("Checkers over the suite:")
    for label, collector in collectors:
        reported = collector()
        results.append(_validate(label, reported))
        _print_result(results[-1])

    print("\nType completeness (verifytypes):")
    for spec, label in verifytypes_runs:
        results.append(_verify_types(spec, label))
        _print_result(results[-1])

    failed = [r for r in results if not r.ok]
    print()
    if failed:
        print(f"typesafety: FAILED ({len(failed)} of {len(results)} checks)")
        return 1
    print(f"typesafety: OK ({len(results)} checks passed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
