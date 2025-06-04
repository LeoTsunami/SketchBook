"""
Tests for the main window.
"""
import pytest
from qtpy.QtCore import Qt
from gui.main_window import MainWindow
from core.settings import settings

@pytest.fixture
def main_window(qtbot):
    """Create a MainWindow instance."""
    window = MainWindow()
    qtbot.addWidget(window)
    return window

def test_window_title(main_window):
    """Test window title."""
    assert main_window.windowTitle() == "SketchBook"

def test_window_size(main_window):
    """Test initial window size."""
    assert main_window.size().width() == 1280
    assert main_window.size().height() == 800

def test_menu_structure(main_window):
    """Test menu bar structure."""
    menu_bar = main_window.menuBar()
    
    # Check menu titles
    menus = [menu.title() for menu in menu_bar.findChildren(menu_bar.__class__)]
    assert "&File" in menus
    assert "&View" in menus
    assert "&Help" in menus
    
    # Check File menu actions
    file_menu = menu_bar.findChild(menu_bar.__class__, "&File")
    actions = [action.text() for action in file_menu.actions()]
    assert "&Import Images..." in actions
    assert "E&xit" in actions

def test_theme_switching(main_window, qtbot):
    """Test theme switching."""
    # Get initial theme
    initial_theme = settings.get("ui.theme")
    
    # Switch to opposite theme
    new_theme = "light" if initial_theme == "dark" else "dark"
    main_window._set_theme(new_theme)
    
    # Verify theme was changed
    assert settings.get("ui.theme") == new_theme
    
    # Switch back
    main_window._set_theme(initial_theme)
    assert settings.get("ui.theme") == initial_theme

def test_status_bar(main_window):
    """Test status bar."""
    status_bar = main_window.statusBar()
    assert status_bar is not None
    assert status_bar.currentMessage() == "Ready"

def test_about_dialog(main_window, qtbot):
    """Test about dialog."""
    # Find and trigger about action
    help_menu = main_window.menuBar().findChild(main_window.menuBar().__class__, "&Help")
    about_action = next(action for action in help_menu.actions() if action.text() == "&About")
    
    # Click should not raise any exception
    about_action.trigger() 