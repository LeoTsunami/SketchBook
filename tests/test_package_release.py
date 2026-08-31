"""Unit tests for package_release helpers (no PyInstaller)."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "package_release.py"


def _load_module():
    """Load package_release.py as a module without executing main."""
    spec = importlib.util.spec_from_file_location("package_release", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_bump_version_patch():
    """Patch bump increments the last number."""
    mod = _load_module()
    assert mod.bump_version("0.1.0", "patch") == "0.1.1"
    assert mod.bump_version("0.1.9", "minor") == "0.2.0"
    assert mod.bump_version("1.2.3", "major") == "2.0.0"


def test_parse_semver_rejects_bad():
    """Invalid versions raise ValueError."""
    mod = _load_module()
    with pytest.raises(ValueError):
        mod.parse_semver("1.0")
