"""Tests for GitHub remote parsing used by the packager."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "windows_installer.py"


def _load_module():
    """Load windows_installer.py without requiring scripts as a package."""
    spec = importlib.util.spec_from_file_location("windows_installer", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_parse_github_remote_https() -> None:
    """HTTPS origin URLs yield owner/repo."""
    mod = _load_module()
    assert mod.parse_github_remote("https://github.com/acme/SketchBook.git") == (
        "acme",
        "SketchBook",
    )


def test_parse_github_remote_ssh() -> None:
    """SSH origin URLs yield owner/repo."""
    mod = _load_module()
    assert mod.parse_github_remote("git@github.com:acme/SketchBook.git") == (
        "acme",
        "SketchBook",
    )


def test_parse_github_remote_rejects_non_github() -> None:
    """Non-GitHub remotes are ignored."""
    mod = _load_module()
    assert mod.parse_github_remote("https://gitlab.com/acme/SketchBook.git") is None
