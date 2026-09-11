"""Tests for bootstrap stdio handling in windowed PyInstaller builds."""

import sys

from bootstrap import ensure_stdio
from main import _configure_stdio


def test_ensure_stdio_replaces_none_streams(monkeypatch) -> None:
    """Dummy streams are attached when stdout/stderr are None."""
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    ensure_stdio()
    assert sys.stdout is not None
    assert sys.stderr is not None
    sys.stdout.write("ok")
    sys.stderr.write("ok")


def test_configure_stdio_ignores_none_streams(monkeypatch) -> None:
    """``reconfigure`` is skipped when the GUI process has no console."""
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    _configure_stdio()
