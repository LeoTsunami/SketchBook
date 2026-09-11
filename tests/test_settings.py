"""Unit tests for the Settings manager."""

import json
import os
import pytest
from pathlib import Path
from core.settings import Settings


@pytest.fixture
def temp_settings_file(tmp_path):
    """Create a temporary settings file for testing."""
    settings_file = tmp_path / "test_settings.json"
    return str(settings_file)


def test_settings_creation(temp_settings_file):
    """Test settings file creation with defaults."""
    settings = Settings(temp_settings_file)
    assert Path(temp_settings_file).exists()
    assert settings.get("version") == "0.1.0"
    assert settings.get("ui.theme") == "dark"
    assert settings.get("database.type") == "sqlite"


def test_settings_get_default(temp_settings_file):
    """Test getting setting with default value."""
    settings = Settings(temp_settings_file)
    assert settings.get("nonexistent", "default") == "default"
    assert settings.get("ui.nonexistent", 123) == 123


def test_settings_set_and_save(temp_settings_file):
    """Test setting and saving values."""
    settings = Settings(temp_settings_file)

    # Test simple set
    settings.set("ui.theme", "light")
    assert settings.get("ui.theme") == "light"

    # Test nested set
    settings.set("images.formats", ["png", "webp"])
    assert settings.get("images.formats") == ["png", "webp"]

    # Test save and reload
    settings.save()
    new_settings = Settings(temp_settings_file)
    assert new_settings.get("ui.theme") == "light"
    assert new_settings.get("images.formats") == ["png", "webp"]


def test_settings_reset(temp_settings_file):
    """Test resetting settings to defaults."""
    settings = Settings(temp_settings_file)

    # Change some values
    settings.set("ui.theme", "light")
    settings.set("ui.language", "en")

    # Reset
    settings.reset()

    # Verify defaults are restored
    assert settings.get("ui.theme") == "dark"
    assert settings.get("ui.language") == "fr"


def test_settings_all_property(temp_settings_file):
    """Test getting all settings."""
    settings = Settings(temp_settings_file)
    all_settings = settings.all

    # Verify it's a copy
    all_settings["ui"]["theme"] = "modified"
    assert settings.get("ui.theme") == "dark"  # Original unchanged
