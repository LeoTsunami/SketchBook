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


def test_tag_grid_state_on_filter(main_window):
    """Test category button state based on filters."""
    main_window._load_tags_into_grid()
    assert main_window._category_buttons
    category = next(iter(main_window._category_buttons.keys()))
    button = main_window._category_buttons[category]
    subtag_buttons = main_window._subcategory_buttons.get(category, {})

    # Check subtags are initially hidden
    if subtag_buttons:
        first_subtag = next(iter(subtag_buttons.values()))
        assert not first_subtag.isVisible()

    main_window._on_tag_button_clicked(category)
    # Check subtags are visible when category is active
    if subtag_buttons:
        first_subtag = next(iter(subtag_buttons.values()))
        assert first_subtag.isVisible()

    main_window._on_tag_button_clicked(category)
    # Check subtags are hidden when category is inactive
    if subtag_buttons:
        first_subtag = next(iter(subtag_buttons.values()))
        assert not first_subtag.isVisible()


def test_filter_images_by_category(main_window, monkeypatch):
    """Test OR categories with AND subtags."""
    from core.image_db import ImageMetadata
    from datetime import datetime

    images = [
        ImageMetadata(
            id="img1",
            path="a.jpg",
            original_filename="a.jpg",
            import_date=datetime.now(),
            width=100,
            height=100,
            file_size=1,
            format="JPEG",
            tags=["Human", "Male", "Portrait"],
            notes="",
        ),
        ImageMetadata(
            id="img2",
            path="b.jpg",
            original_filename="b.jpg",
            import_date=datetime.now(),
            width=100,
            height=100,
            file_size=1,
            format="JPEG",
            tags=["Animal", "Bird"],
            notes="",
        ),
        ImageMetadata(
            id="img3",
            path="c.jpg",
            original_filename="c.jpg",
            import_date=datetime.now(),
            width=100,
            height=100,
            file_size=1,
            format="JPEG",
            tags=["Human", "Female"],
            notes="",
        ),
    ]

    monkeypatch.setattr(main_window.image_manager.db, "list_images", lambda: images)

    main_window._active_categories = {"Human", "Animal"}
    main_window._active_subtags = {"Human": {"Male", "Portrait"}, "Animal": {"Bird"}}
    result_ids = {image.id for image in main_window._filter_images_by_category()}
    assert result_ids == {"img1", "img2"}


def test_get_default_tags_with_nested_data(main_window, tmp_path):
    """Test loading nested default tags from JSON."""
    tags_path = tmp_path / "default_tags.json"
    tags_path.write_text(
        """
        {
          "Objects": [
            "Small",
            {"Vehicle": ["Car", "Bike"]}
          ],
          "Camera": ["Wide"]
        }
        """,
        encoding="utf-8",
    )
    tags = main_window._get_default_tags_from_path(tags_path)
    assert "Objects" in tags
    assert "Small" in tags
    assert "Vehicle" in tags
    assert "Car" in tags
    assert "Bike" in tags
    assert "Camera" in tags
    assert "Wide" in tags

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


def test_toggle_tag_library_selection(main_window):
    """Tag library selection: add and remove user tags with Ctrl+click (logic only)."""
    main_window._tag_library_selection = set()
    main_window._toggle_tag_library_selection("TagA")
    assert main_window._tag_library_selection == {"TagA"}
    main_window._toggle_tag_library_selection("TagB")
    assert main_window._tag_library_selection == {"TagA", "TagB"}
    main_window._toggle_tag_library_selection("TagA")
    assert main_window._tag_library_selection == {"TagB"}


def test_enter_exit_parent_select_mode(main_window):
    """Parent-to-tag mode: enter shows bar and state, exit hides bar and clears selection."""
    main_window._enter_parent_select_mode({"MyTag"})
    assert main_window._parent_select_mode is True
    assert main_window._tags_to_parent == {"MyTag"}
    assert main_window._parent_select_bar.isVisible()
    assert not main_window._parent_ok_btn.isEnabled()
    main_window._exit_parent_select_mode()
    assert main_window._parent_select_mode is False
    assert main_window._tags_to_parent == set()
    assert not main_window._parent_select_bar.isVisible()
    assert main_window._tag_library_selection == set()


def test_parent_select_ok_updates_placements(main_window, monkeypatch):
    """When OK in parent-select mode, placements are saved with parent_tag or category."""
    from core import user_tags_config

    saved_placements = {}
    saved_icons = {}
    saved_registered = []

    def capture_save(placements, icons, registered_only=None):
        saved_placements.clear()
        saved_placements.update(placements)
        saved_icons.update(icons)
        if registered_only is not None:
            saved_registered[:] = registered_only
        return True

    monkeypatch.setattr(user_tags_config, "save_config", capture_save)
    main_window._user_tags_config = {
        "placements": {"Child1": {"category": "Human"}, "Child2": {"category": "Animal"}},
        "icons": {},
        "registered_only": [],
    }
    main_window._tags_to_parent = {"Child1", "Child2"}
    main_window._parent_select_key = "Portrait"
    main_window._parent_select_role = "tag"
    main_window._parent_select_mode = True
    monkeypatch.setattr(main_window, "_load_tags_into_grid", lambda: None)

    main_window._on_parent_select_ok()

    assert saved_placements.get("Child1") == {"parent_tag": "Portrait"}
    assert saved_placements.get("Child2") == {"parent_tag": "Portrait"}
    assert not main_window._parent_select_mode