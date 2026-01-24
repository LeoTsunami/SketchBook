"""
Tests for the tag manager search behavior.
"""
import pytest
from gui.tag_manager import TagManager


@pytest.fixture
def tag_manager(qtbot):
    """Create a TagManager instance."""
    manager = TagManager()
    qtbot.addWidget(manager)
    return manager


def test_resolve_tag_case_insensitive(tag_manager):
    """Test resolving tags with different casing."""
    tag_manager.set_available_tags(["Human", "Portrait"])
    assert tag_manager._resolve_tag("human") == "Human"
    assert tag_manager._resolve_tag("PORTRAIT") == "Portrait"


def test_resolve_tag_empty_text(tag_manager):
    """Test resolving an empty tag returns None."""
    tag_manager.set_available_tags(["Human"])
    assert tag_manager._resolve_tag("") is None


def test_invalid_tag_shows_feedback(tag_manager):
    """Test invalid tag entry does not add tags."""
    tag_manager.set_available_tags(["Human"])
    tag_manager.search_input.setText("UnknownTag")
    tag_manager._on_search_return()
    assert tag_manager.and_zone.get_tags() == set()
    assert "border" in tag_manager.search_input.styleSheet()


def test_toggle_tag_adds_and_removes(tag_manager):
    """Test toggling a tag adds then removes it."""
    tag_manager.set_available_tags(["Human"])
    tag_manager.toggle_tag("Human")
    assert tag_manager.and_zone.get_tags() == {"Human"}
    tag_manager.toggle_tag("Human")
    assert tag_manager.and_zone.get_tags() == set()
