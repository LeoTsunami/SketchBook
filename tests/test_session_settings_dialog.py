"""Tests for session settings dialog UI behavior."""

from qtpy.QtCore import Qt

from gui.session_settings_dialog import SessionSettingsDialog


def test_dialog_is_frameless_and_has_styled_spinbox(qtbot):
    """Dialog uses custom frameless chrome and keeps spinbox themed styling."""
    dialog = SessionSettingsDialog(image_manager=None, image_count=10)
    qtbot.addWidget(dialog)
    assert bool(dialog.windowFlags() & Qt.FramelessWindowHint)
    css = dialog.styleSheet()
    assert "QComboBox, QSpinBox" in css
