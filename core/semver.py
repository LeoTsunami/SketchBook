"""
Semantic version helpers (MAJOR.MINOR.PATCH).

Shared by the packager and the GitHub update check.
"""

from __future__ import annotations

import re

_SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def normalize_version(version: str) -> str:
    """
    Strip a leading ``v`` and surrounding whitespace.

    Args:
        version: Raw version or git tag (e.g. ``v1.2.3``).

    Returns:
        str: Version without a ``v`` prefix.
    """
    return version.strip().lstrip("vV").strip()


def parse_semver(version: str) -> tuple[int, int, int]:
    """
    Parse a X.Y.Z version string.

    Args:
        version: Version text (``v`` prefix allowed).

    Returns:
        tuple[int, int, int]: Major, minor, patch.

    Raises:
        ValueError: If the format is invalid.
    """
    cleaned = normalize_version(version)
    match = _SEMVER.fullmatch(cleaned)
    if not match:
        raise ValueError(f"Invalid version (expected X.Y.Z): {version!r}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def bump_version(current: str, part: str) -> str:
    """
    Bump major, minor, or patch.

    Args:
        current: Current X.Y.Z version.
        part: One of ``major``, ``minor``, ``patch``.

    Returns:
        str: New version string.

    Raises:
        ValueError: If ``part`` is unknown or ``current`` is invalid.
    """
    major, minor, patch = parse_semver(current)
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    if part == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"Unknown bump part: {part}")


def is_newer(candidate: str, current: str) -> bool:
    """
    Return True if ``candidate`` is a higher SemVer than ``current``.

    Args:
        candidate: Proposed version (tag prefix allowed).
        current: Installed version.

    Returns:
        bool: True when candidate > current. False if either is unparseable.
    """
    try:
        return parse_semver(candidate) > parse_semver(current)
    except ValueError:
        return False
