"""
Tests for the tab system layout (Life Drawing / WhiteBoard / Market).
"""

import pytest
from qtpy.QtWidgets import QApplication, QStackedWidget

from gui.main_window import MainWindow


@pytest.fixture
def main_window(qtbot):
    """Create a MainWindow instance with tag grid and image list loaded."""
    window = MainWindow()
    qtbot.addWidget(window)
    window.run_startup_load_for_tests()
    return window


def test_content_stack_has_three_pages(main_window):
    """Expected: the QStackedWidget holds exactly 3 pages (Life Drawing, WhiteBoard, Market)."""
    stack = main_window._content_stack
    assert isinstance(stack, QStackedWidget)
    assert stack.count() == 3


def test_default_tab_is_life_drawing(main_window):
    """Expected: on startup the first tab (index 0) is active."""
    assert main_window._content_stack.currentIndex() == 0
    assert main_window._life_drawing_controls.isVisible()


def test_switch_to_whiteboard_hides_controls(main_window):
    """Switching to tab 1 should hide Life Drawing controls and show page 1."""
    main_window._on_tab_changed(1)
    QApplication.processEvents()
    assert main_window._content_stack.currentIndex() == 1
    assert not main_window._life_drawing_controls.isVisible()


def test_switch_back_to_life_drawing_shows_controls(main_window):
    """Switching back to tab 0 should restore Life Drawing controls."""
    main_window._on_tab_changed(2)
    QApplication.processEvents()
    assert not main_window._life_drawing_controls.isVisible()

    main_window._on_tab_changed(0)
    QApplication.processEvents()
    assert main_window._content_stack.currentIndex() == 0
    assert main_window._life_drawing_controls.isVisible()


def test_tab_button_group_has_correct_count(main_window):
    """The button group should contain one button per tab name."""
    buttons = main_window._tab_button_group.buttons()
    assert len(buttons) == len(main_window.TAB_NAMES)


def test_image_grid_accessible_on_life_drawing_tab(main_window):
    """Failure guard: the image grid must still be reachable after the stack refactor."""
    assert hasattr(main_window, "image_grid")
    assert main_window.image_grid is not None
