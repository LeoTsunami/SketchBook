"""Tests for reusable window chrome helpers."""

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QMainWindow, QPushButton

from gui.window_chrome import (
    WindowChromeBar,
    apply_glass_button_style,
    enable_frameless_window,
)


def test_enable_frameless_window_sets_hint(qtbot):
    """Enabling frameless mode sets the Qt frameless hint."""
    window = QMainWindow()
    qtbot.addWidget(window)
    enable_frameless_window(window)
    assert bool(window.windowFlags() & Qt.FramelessWindowHint)


def test_window_chrome_bar_updates_maximize_button(qtbot):
    """Chrome bar reflects maximize/restore state."""
    window = QMainWindow()
    qtbot.addWidget(window)
    chrome = WindowChromeBar("Test", window)
    qtbot.addWidget(chrome)
    window.showMaximized()
    chrome.sync_window_state()
    assert chrome._max_btn is not None
    assert chrome._max_btn.toolTip() == "Restore"


def test_window_chrome_bar_without_maximize_button(qtbot):
    """Chrome bar supports dialogs with close-only controls."""
    window = QMainWindow()
    qtbot.addWidget(window)
    chrome = WindowChromeBar("Dialog", window, show_minimize=False, show_maximize=False)
    qtbot.addWidget(chrome)
    chrome.sync_window_state()
    assert chrome._max_btn is None


def test_apply_glass_button_style_sets_stylesheet():
    """Glass helper attaches a stylesheet to both button variants."""
    normal = QPushButton("Normal")
    apply_glass_button_style(normal)
    assert "border-radius" in normal.styleSheet()

    primary = QPushButton("Primary")
    apply_glass_button_style(primary, primary=True)
    assert "rgba(82, 158, 255" in primary.styleSheet()
