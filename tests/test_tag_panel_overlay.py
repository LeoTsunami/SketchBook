"""
Tests for the TagPanelOverlay floating widget.
"""

import pytest
from qtpy.QtWidgets import QWidget, QLabel
from qtpy.QtCore import QPoint
from gui.tag_panel_overlay import TagPanelOverlay


@pytest.fixture
def parent_widget(qtbot):
    """A parent widget to host the overlay."""
    parent = QWidget()
    parent.setFixedSize(800, 600)
    qtbot.addWidget(parent)
    parent.show()
    return parent


@pytest.fixture
def overlay(parent_widget):
    """A TagPanelOverlay parented to the fixture widget."""
    panel = TagPanelOverlay(parent_widget)
    return panel


def test_overlay_starts_hidden(overlay):
    """Overlay should be hidden and offscreen after construction."""
    assert not overlay.isVisible()
    assert not overlay.is_panel_visible()
    assert overlay.pos().x() < 0


def test_show_animated_makes_visible(overlay, qtbot):
    """show_animated should make the panel visible and set is_panel_visible True."""
    overlay.show_animated()
    assert overlay.is_panel_visible()
    assert overlay.isVisible()


def test_hide_animated_after_show(overlay, qtbot):
    """hide_animated should begin closing the panel."""
    overlay.show_animated()
    qtbot.wait(50)
    overlay.hide_animated()
    assert not overlay.is_panel_visible()


def test_set_content_widget(overlay):
    """set_content_widget should reparent the widget into the overlay layout."""
    label = QLabel("Test content")
    overlay.set_content_widget(label)
    assert label.parentWidget() is not None
    assert overlay._layout.count() == 1


def test_lock_dismiss_prevents_hide(overlay, qtbot):
    """lock_dismiss(True) should prevent hide_animated from running."""
    overlay.show_animated()
    overlay.lock_dismiss(True)
    overlay.hide_animated()
    assert overlay.is_panel_visible()
    overlay.lock_dismiss(False)
    overlay.hide_animated()
    assert not overlay.is_panel_visible()


def test_reposition_updates_height(overlay, parent_widget):
    """reposition should match the panel height to the parent."""
    parent_widget.setFixedSize(800, 400)
    overlay.reposition()
    assert overlay.height() == 400


def test_double_show_is_noop(overlay):
    """Calling show_animated twice should not restart the animation."""
    overlay.show_animated()
    overlay.show_animated()
    assert overlay.is_panel_visible()


def test_double_hide_is_noop(overlay, qtbot):
    """Calling hide_animated when already hidden is a no-op."""
    overlay.hide_animated()
    assert not overlay.is_panel_visible()


def test_panel_width(overlay):
    """Overlay should have the configured fixed width."""
    assert overlay.width() == TagPanelOverlay.PANEL_WIDTH
