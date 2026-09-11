"""Tests for core.semver."""

import pytest

from core.semver import bump_version, is_newer, normalize_version, parse_semver


def test_parse_and_normalize() -> None:
    """v-prefix is stripped and X.Y.Z is parsed."""
    assert normalize_version("v1.2.3") == "1.2.3"
    assert parse_semver("v0.1.1") == (0, 1, 1)


def test_parse_semver_rejects_bad() -> None:
    """Incomplete versions raise ValueError."""
    with pytest.raises(ValueError):
        parse_semver("1.0")


def test_bump_version() -> None:
    """Major/minor/patch bumps match SemVer rules."""
    assert bump_version("0.1.0", "patch") == "0.1.1"
    assert bump_version("0.1.9", "minor") == "0.2.0"
    assert bump_version("1.2.3", "major") == "2.0.0"


def test_is_newer() -> None:
    """Newer comparison is tuple-based; invalid strings are not newer."""
    assert is_newer("0.2.0", "0.1.9") is True
    assert is_newer("0.1.1", "0.1.1") is False
    assert is_newer("0.1.0", "0.2.0") is False
    assert is_newer("nope", "0.1.0") is False
