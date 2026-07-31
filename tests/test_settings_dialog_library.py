"""Tests for SettingsDialog library location helpers."""

from pathlib import Path

import pytest
from qtpy.QtWidgets import QDialog

from core.user_data import user_data
from gui.settings_dialog import SettingsDialog


def test_settings_dialog_shows_current_data_dir(qtbot, tmp_path, monkeypatch):
    """Dialog path field reflects user_data base directory."""
    monkeypatch.setattr(user_data, "get_base_dir", lambda: tmp_path)
    monkeypatch.setattr(user_data, "is_data_dir_locked_by_env", lambda: False)
    dialog = SettingsDialog()
    qtbot.addWidget(dialog)
    assert dialog.data_dir_edit.text() == str(tmp_path.resolve())
    assert dialog.get_chosen_data_dir() == tmp_path.resolve()


def test_is_data_dir_locked_by_env(monkeypatch):
    """Env SKETCHBOOK_DATA_DIR locks the path for Settings UI."""
    monkeypatch.delenv("SKETCHBOOK_DATA_DIR", raising=False)
    assert user_data.is_data_dir_locked_by_env() is False
    monkeypatch.setenv("SKETCHBOOK_DATA_DIR", str(Path.home() / "SketchBookEnv"))
    assert user_data.is_data_dir_locked_by_env() is True


def test_set_base_dir_persists_config(tmp_path, monkeypatch):
    """set_base_dir writes config and updates get_base_dir."""
    config = tmp_path / "cfg" / ".sketchbook_config.json"
    config.parent.mkdir(parents=True)
    monkeypatch.setattr(user_data, "_config_path", config)
    monkeypatch.delenv("SKETCHBOOK_DATA_DIR", raising=False)
    target = tmp_path / "library"
    assert user_data.set_base_dir(target) is True
    assert user_data.get_base_dir() == target.resolve()
    assert (target / "images").is_dir()
    assert config.exists()
