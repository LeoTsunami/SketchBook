"""
Tests for the main window.
"""
import pytest
from pathlib import Path
from PIL import Image
from qtpy.QtCore import Qt, QMimeData, QUrl
from qtpy.QtGui import QDragEnterEvent, QDropEvent
from gui.main_window import MainWindow
from core.settings import settings

@pytest.fixture
def main_window(qtbot):
    """Create a MainWindow instance."""
    window = MainWindow()
    qtbot.addWidget(window)
    return window

@pytest.fixture
def sample_image(tmp_path):
    """Create a sample test image."""
    image_path = tmp_path / "test.jpg"
    image = Image.new('RGB', (100, 100), color='red')
    image.save(image_path, 'JPEG')
    return image_path

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

def test_import_dialog(main_window, qtbot, tmp_path, monkeypatch):
    """Test image import via dialog."""
    # Create test image
    test_image = tmp_path / "test.jpg"
    Image.new('RGB', (100, 100), color='red').save(test_image)
    
    # Mock file dialog
    def mock_get_files(*args, **kwargs):
        return [str(test_image)], None
    
    monkeypatch.setattr(
        main_window.findChild(main_window.menuBar().__class__, "&File"),
        "getOpenFileNames",
        mock_get_files
    )
    
    # Trigger import action
    import_action = next(
        action for action in main_window.menuBar().actions()
        if "&Import Images..." in action.text()
    )
    import_action.trigger()
    
    # Verify status message
    assert "Successfully imported 1 images" in main_window.statusBar().currentMessage()

def test_drag_and_drop(main_window, qtbot, sample_image):
    """Test drag and drop image import."""
    # Create mime data with image URL
    mime_data = QMimeData()
    mime_data.setUrls([QUrl.fromLocalFile(str(sample_image))])
    
    # Simulate drag enter
    drag_event = QDragEnterEvent(
        main_window.pos(),
        Qt.CopyAction,
        mime_data,
        Qt.LeftButton,
        Qt.NoModifier
    )
    main_window.dragEnterEvent(drag_event)
    assert drag_event.isAccepted()
    
    # Simulate drop
    drop_event = QDropEvent(
        main_window.pos(),
        Qt.CopyAction,
        mime_data,
        Qt.LeftButton,
        Qt.NoModifier
    )
    main_window.dropEvent(drop_event)
    assert drop_event.isAccepted()
    
    # Verify status message
    assert "Successfully imported 1 images" in main_window.statusBar().currentMessage()

def test_invalid_drop(main_window, qtbot, tmp_path):
    """Test dropping invalid files."""
    # Create invalid file
    invalid_file = tmp_path / "test.txt"
    invalid_file.write_text("Not an image")
    
    # Create mime data with invalid URL
    mime_data = QMimeData()
    mime_data.setUrls([QUrl.fromLocalFile(str(invalid_file))])
    
    # Simulate drag enter
    drag_event = QDragEnterEvent(
        main_window.pos(),
        Qt.CopyAction,
        mime_data,
        Qt.LeftButton,
        Qt.NoModifier
    )
    main_window.dragEnterEvent(drag_event)
    assert not drag_event.isAccepted() 