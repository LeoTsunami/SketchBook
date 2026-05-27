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


def test_constant_interval_defaults_to_7m30(qtbot):
    """Constant interval controls default to 7 minutes 30 seconds."""
    dialog = SessionSettingsDialog(image_manager=None, image_count=10)
    qtbot.addWidget(dialog)
    dialog.session_type_combo.setCurrentText("Constant interval")
    assert dialog.interval_minutes_spin.value() == 7
    assert dialog.interval_tens_seconds_spin.value() == 3


def test_constant_interval_settings_returns_interval_seconds(qtbot):
    """Dialog returns computed seconds from minutes + tens-of-seconds."""
    dialog = SessionSettingsDialog(image_manager=None, image_count=10)
    qtbot.addWidget(dialog)
    dialog.session_type_combo.setCurrentText("Constant interval")
    dialog.interval_minutes_spin.setValue(12)
    dialog.interval_tens_seconds_spin.setValue(4)
    payload = dialog.get_session_settings()
    assert payload["interval_minutes"] == 12
    assert payload["interval_tens_seconds"] == 4
    assert payload["interval_seconds"] == 760
