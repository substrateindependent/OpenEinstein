"""Unit tests for semantic versioning utilities (Story 2.1)."""

from __future__ import annotations

import pytest

from openeinstein.skills.versioning import (
    parse_version,
    is_compatible,
    version_satisfies_constraint,
)


# ── parse_version ──


def test_parse_version_basic() -> None:
    assert parse_version("1.2.3") == (1, 2, 3)


def test_parse_version_zero() -> None:
    assert parse_version("0.0.0") == (0, 0, 0)


def test_parse_version_large_numbers() -> None:
    assert parse_version("10.200.3000") == (10, 200, 3000)


def test_parse_version_with_pre_release() -> None:
    """Pre-release tags are stripped; only major.minor.patch used."""
    assert parse_version("1.2.3-alpha") == (1, 2, 3)


def test_parse_version_with_build_metadata() -> None:
    """Build metadata is stripped."""
    assert parse_version("1.2.3+build.42") == (1, 2, 3)


def test_parse_version_with_pre_release_and_build() -> None:
    assert parse_version("2.0.0-rc.1+build.123") == (2, 0, 0)


def test_parse_version_invalid_latest() -> None:
    with pytest.raises(ValueError, match="Invalid"):
        parse_version("latest")


def test_parse_version_invalid_two_parts() -> None:
    with pytest.raises(ValueError, match="Invalid"):
        parse_version("1.0")


def test_parse_version_invalid_single_number() -> None:
    with pytest.raises(ValueError, match="Invalid"):
        parse_version("1")


def test_parse_version_invalid_empty_string() -> None:
    with pytest.raises(ValueError, match="Invalid"):
        parse_version("")


def test_parse_version_invalid_non_numeric() -> None:
    with pytest.raises(ValueError, match="Invalid"):
        parse_version("a.b.c")


# ── is_compatible ──


def test_is_compatible_same_major() -> None:
    assert is_compatible("1.2.3", "1.0.0") is True


def test_is_compatible_same_major_different_minor() -> None:
    assert is_compatible("2.5.0", "2.1.0") is True


def test_is_compatible_different_major() -> None:
    assert is_compatible("1.0.0", "2.0.0") is False


def test_is_compatible_zero_major() -> None:
    """0.x versions are compatible with each other."""
    assert is_compatible("0.1.0", "0.2.0") is True


def test_is_compatible_zero_vs_one() -> None:
    assert is_compatible("0.1.0", "1.0.0") is False


# ── version_satisfies_constraint ──


def test_satisfies_exact_match() -> None:
    assert version_satisfies_constraint("1.2.3", "==1.2.3") is True


def test_satisfies_exact_no_match() -> None:
    assert version_satisfies_constraint("1.2.4", "==1.2.3") is False


def test_satisfies_gte() -> None:
    assert version_satisfies_constraint("1.2.3", ">=1.2.0") is True


def test_satisfies_gte_exact() -> None:
    assert version_satisfies_constraint("1.2.0", ">=1.2.0") is True


def test_satisfies_gte_below() -> None:
    assert version_satisfies_constraint("1.1.9", ">=1.2.0") is False


def test_satisfies_lt() -> None:
    assert version_satisfies_constraint("1.9.9", "<2.0.0") is True


def test_satisfies_lt_at_boundary() -> None:
    assert version_satisfies_constraint("2.0.0", "<2.0.0") is False


def test_satisfies_lte() -> None:
    assert version_satisfies_constraint("2.0.0", "<=2.0.0") is True


def test_satisfies_lte_above() -> None:
    assert version_satisfies_constraint("2.0.1", "<=2.0.0") is False


def test_satisfies_gt() -> None:
    assert version_satisfies_constraint("1.2.1", ">1.2.0") is True


def test_satisfies_gt_exact() -> None:
    assert version_satisfies_constraint("1.2.0", ">1.2.0") is False


def test_satisfies_range_gte_lt() -> None:
    """Range constraint: >=1.2.0,<2.0.0"""
    assert version_satisfies_constraint("1.5.0", ">=1.2.0,<2.0.0") is True
    assert version_satisfies_constraint("2.0.0", ">=1.2.0,<2.0.0") is False
    assert version_satisfies_constraint("1.1.9", ">=1.2.0,<2.0.0") is False


def test_satisfies_range_gte_lte() -> None:
    assert version_satisfies_constraint("1.5.0", ">=1.0.0,<=1.5.0") is True
    assert version_satisfies_constraint("1.5.1", ">=1.0.0,<=1.5.0") is False


def test_satisfies_complex_range() -> None:
    """Three constraints chained."""
    assert version_satisfies_constraint("1.3.0", ">=1.0.0,<2.0.0,>1.2.0") is True
    assert version_satisfies_constraint("1.2.0", ">=1.0.0,<2.0.0,>1.2.0") is False


def test_satisfies_bare_version_treated_as_exact() -> None:
    """A bare version string without operator is treated as ==."""
    assert version_satisfies_constraint("1.2.3", "1.2.3") is True
    assert version_satisfies_constraint("1.2.4", "1.2.3") is False


# ── Import smoke test ──


def test_versioning_importable_from_skills() -> None:
    """parse_version and version_satisfies_constraint importable from openeinstein.skills."""
    from openeinstein.skills import parse_version as pv
    from openeinstein.skills import version_satisfies_constraint as vsc

    assert pv is not None
    assert vsc is not None
