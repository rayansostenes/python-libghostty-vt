<!--
Release notes template for python-libghostty-vt.

Copy this into the GitHub release body when drafting a release, or start from
GitHub's auto-generated notes and paste the "Pinned upstream commit" section
below in. The Wheels workflow also appends the pinned commit automatically on
publish (see .github/workflows/wheels.yml), so this template just makes the
information visible while drafting.

The release tag MUST equal the package version (a leading `v` is allowed, e.g.
tag `v0.1.0` for version `0.1.0`). Read the version from pyproject.toml
(project.version) and the pinned commit from ghostty-commit.txt.
-->

## Highlights

<!-- What changed in the idiomatic layer since the last release. -->

## Pinned upstream commit

Built from ghostty at pinned commit `<paste the full hash from ghostty-commit.txt>`.

The same commit is exposed at runtime as `ghostty_vt.GHOSTTY_COMMIT`, so a bug
report can name the exact upstream source these wheels were built against.

## Install

```sh
pip install python-libghostty-vt==<version>
```
