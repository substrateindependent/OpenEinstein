"""Semantic versioning utilities for pack/skill version comparison."""

from __future__ import annotations

import re

_SEMVER_RE = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<pre>[0-9A-Za-z\-\.]+))?"
    r"(?:\+(?P<build>[0-9A-Za-z\-\.]+))?$"
)

_CONSTRAINT_RE = re.compile(
    r"^(?P<op>>=|<=|>|<|==)?(?P<version>\d+\.\d+\.\d+.*)$"
)


def parse_version(s: str) -> tuple[int, int, int]:
    """Parse a semver string into (major, minor, patch).

    Pre-release and build metadata are accepted but stripped from the result.

    Raises:
        ValueError: If *s* is not a valid semver string.
    """
    m = _SEMVER_RE.match(s)
    if m is None:
        raise ValueError(f"Invalid semver string: {s!r}")
    return int(m.group("major")), int(m.group("minor")), int(m.group("patch"))


def is_compatible(v1: str, v2: str) -> bool:
    """Check whether two versions share the same major version."""
    return parse_version(v1)[0] == parse_version(v2)[0]


def version_satisfies_constraint(version: str, constraint: str) -> bool:
    """Check whether *version* satisfies a constraint expression.

    Supported operators: ``==``, ``>=``, ``<=``, ``>``, ``<``.
    Multiple constraints can be comma-separated (all must be satisfied).
    A bare version string (no operator) is treated as ``==``.

    Examples::

        version_satisfies_constraint("1.5.0", ">=1.2.0,<2.0.0")  # True
        version_satisfies_constraint("2.0.0", ">=1.2.0,<2.0.0")  # False
    """
    parsed = parse_version(version)
    parts = [c.strip() for c in constraint.split(",")]
    for part in parts:
        if not _check_single_constraint(parsed, part):
            return False
    return True


def _check_single_constraint(version: tuple[int, int, int], constraint: str) -> bool:
    m = _CONSTRAINT_RE.match(constraint)
    if m is None:
        raise ValueError(f"Invalid constraint: {constraint!r}")
    op = m.group("op") or "=="
    target = parse_version(m.group("version"))
    if op == "==":
        return version == target
    if op == ">=":
        return version >= target
    if op == "<=":
        return version <= target
    if op == ">":
        return version > target
    if op == "<":
        return version < target
    raise ValueError(f"Unknown operator: {op!r}")
