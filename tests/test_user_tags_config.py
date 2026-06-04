"""
Tests for user tags configuration (placements and icons).
"""
import json
from pathlib import Path

import pytest

from core import user_tags_config


@pytest.fixture
def config_path(tmp_path, monkeypatch):
    """Point user data config to tmp_path."""
    def fake_path():
        return tmp_path / "user_tags_config.json"
    monkeypatch.setattr(user_tags_config, "get_config_path", fake_path)
    return tmp_path / "user_tags_config.json"


def test_load_config_missing_returns_defaults(config_path):
    """When file does not exist, load_config returns default structure."""
    assert not config_path.exists()
    cfg = user_tags_config.load_config()
    assert cfg["placements"] == {}
    assert cfg["icons"] == {}
    assert cfg["registered_only"] == []
    assert cfg["custom_shelves"] == []


def test_save_and_load_config(config_path):
    """Save then load returns same placements and icons."""
    placements = {"MyTag": {"category": "Human"}}
    icons = {"MyTag": "Hand.png"}
    user_tags_config.save_config(placements, icons, ["MyTag"])
    cfg = user_tags_config.load_config()
    assert cfg["placements"] == placements
    assert cfg["icons"] == icons
    assert cfg["registered_only"] == ["MyTag"]


def test_get_placement(config_path):
    """get_placement returns placement for a tag."""
    placements = {"TagA": {"category": "Animal"}}
    user_tags_config.save_config(placements, {}, None)
    cfg = user_tags_config.load_config()
    assert user_tags_config.get_placement(cfg, "TagA") == {"category": "Animal"}
    assert user_tags_config.get_placement(cfg, "Missing") is None


def test_save_preserves_custom_shelves_when_not_passed(config_path):
    """Saving tags without custom_shelves keeps existing shelves."""
    shelves = [{"name": "Lighting:", "filter": "or", "tags": []}]
    user_tags_config.save_config({}, {}, [], custom_shelves=shelves)
    user_tags_config.save_config({"T": {"category": "Human"}}, {}, ["T"])
    cfg = user_tags_config.load_config()
    assert cfg["custom_shelves"] == shelves
    assert cfg["placements"] == {"T": {"category": "Human"}}


def test_rename_in_config():
    """rename_in_config updates keys from old to new name."""
    placements = {"Old": {"category": "Human"}}
    icons = {"Old": "Hand.png"}
    user_tags_config.rename_in_config(placements, icons, "Old", "New")
    assert "Old" not in placements and placements.get("New") == {"category": "Human"}
    assert "Old" not in icons and icons.get("New") == "Hand.png"
