"""
Tests for main.py startup helpers (theme fonts).
"""

from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def _qapp(qapp):
    """pytest-qt provides qapp; ensure Qt is initialized for font APIs."""
    return qapp


def test_load_theme_fonts_skips_registration_for_dark_theme(_qapp):
    """
    Dark theme QSS uses Segoe UI; embedded Kalam must not be registered at startup.
    """
    from main import load_theme_fonts

    with patch("main.QFontDatabase.addApplicationFont") as add_font:
        load_theme_fonts("dark")
        add_font.assert_not_called()


def test_load_theme_fonts_registers_kalam_when_file_present(_qapp):
    """
    Kalam-using themes should register the bundled TTF when it exists on disk.
    """
    import main as main_module

    from main import load_theme_fonts

    kalam = (
        Path(main_module.__file__).resolve().parent
        / "gui"
        / "ressources"
        / "fonts"
        / "Kalam"
        / "Kalam-Regular.ttf"
    )
    if not kalam.is_file():
        pytest.skip("Bundled Kalam font not present in this checkout")

    with patch("main.QFontDatabase.addApplicationFont", return_value=1) as add_font:
        with patch(
            "main.QFontDatabase.applicationFontFamilies", return_value=["Kalam"]
        ):
            load_theme_fonts("light")
        add_font.assert_called_once()
