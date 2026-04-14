"""Tests for gui.theme_qss_utils."""

from gui.theme_qss_utils import (
    _extract_first_qmainwindow_rule,
    extract_qmainwindow_rule_from_theme,
)


def test_extract_qmainwindow_dark_contains_gradient():
    """Dark theme QSS should expose a QMainWindow rule with gradient stops."""
    rule = extract_qmainwindow_rule_from_theme("dark")
    assert rule is not None
    assert rule.startswith("QMainWindow")
    assert "qlineargradient" in rule
    assert "#171220" in rule


def test_extract_qmainwindow_light_is_solid_block():
    """Light theme uses a simple QMainWindow rule."""
    rule = extract_qmainwindow_rule_from_theme("light")
    assert rule is not None
    assert "background-color" in rule


def test_extract_missing_theme_returns_none():
    """Unknown theme name yields None (no file)."""
    assert extract_qmainwindow_rule_from_theme("definitely_missing_theme_xyz") is None


def test_extract_none_when_no_qmainwindow():
    """No selector returns None."""
    assert _extract_first_qmainwindow_rule("QLabel { color: blue; }") is None
