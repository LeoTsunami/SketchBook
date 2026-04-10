"""
Tests for the main window.
"""
import pytest
from pathlib import Path
from PIL import Image
from qtpy.QtCore import Qt, QEvent, QMimeData, QUrl, QPoint, QRect
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


def test_deactivate_category_clears_subtags_and_tag_filters(main_window):
    """Disabling a category clears its subtags and related AND/OR tags."""
    main_window._load_tags_into_grid()
    main_window._active_categories = {"Animal"}
    main_window._active_subtags = {"Animal": {"Terrestrial"}}
    main_window.and_zone.add_tag("Animal")
    main_window.and_zone.add_tag("Terrestrial")
    main_window.or_zone.add_tag("Terrestrial")

    main_window._on_tag_button_clicked("Animal")

    assert "Animal" not in main_window._active_categories
    assert "Animal" not in main_window._active_subtags
    assert "Animal" not in main_window.and_zone.get_tags()
    assert "Terrestrial" not in main_window.and_zone.get_tags()
    assert "Terrestrial" not in main_window.or_zone.get_tags()


def test_deactivate_category_removes_hidden_residual_and_or_tags(main_window):
    """Disabling category removes AND/OR tags mapped to it, even if not in visible descendants."""
    main_window._load_tags_into_grid()
    main_window._active_categories = {"Animal"}
    main_window._active_subtags = {"Animal": {"Terrestrial"}}
    main_window._subtag_to_category["Emu"] = "Animal"
    main_window.and_zone.add_tag("Emu")
    main_window.or_zone.add_tag("Emu")

    main_window._on_tag_button_clicked("Animal")

    assert "Emu" not in main_window.and_zone.get_tags()
    assert "Emu" not in main_window.or_zone.get_tags()


def test_deactivate_subcategory_clears_descendants_and_filters(main_window):
    """Disabling a sub-category removes descendant active tags and related AND/OR filters."""
    main_window._load_tags_into_grid()
    main_window._active_categories = {"Animal"}
    main_window._active_subtags = {"Animal": {"Terrestrial", "Felin", "Emu"}}
    main_window._user_tags_config.setdefault("placements", {})
    main_window._user_tags_config["placements"].update(
        {
            "Felin": {"parent_tag": "Terrestrial"},
            "Emu": {"parent_tag": "Felin"},
        }
    )
    main_window._subtag_to_category["Felin"] = "Animal"
    main_window._subtag_to_category["Emu"] = "Animal"
    main_window.and_zone.add_tag("Felin")
    main_window.and_zone.add_tag("Emu")
    main_window.or_zone.add_tag("Emu")

    main_window._on_tag_button_clicked("Felin", "Animal")

    active_subtags = main_window._active_subtags.get("Animal", set())
    assert "Felin" not in active_subtags
    assert "Emu" not in active_subtags
    assert "Felin" not in main_window.and_zone.get_tags()
    assert "Emu" not in main_window.and_zone.get_tags()
    assert "Emu" not in main_window.or_zone.get_tags()


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


def test_tag_library_finish_selection_expected_use_drag_adds_selection() -> None:
    """Modifier+drag selection adds intersecting user tags."""
    window = MainWindow.__new__(MainWindow)
    window._tag_library_selection_start = QPoint(0, 0)
    window._tag_library_selection = set()
    window._last_selected_tag = None
    window._tag_library_is_selecting = True
    window._tag_library_drag_start_tag = "TagA"
    window._tag_library_drag_start_button = object()
    window._sync_tag_grid_state = lambda: None
    window._get_user_tag_buttons_viewport_rects = lambda: [
        ("TagA", QRect(0, 0, 20, 20)),
        ("TagB", QRect(30, 0, 20, 20)),
    ]

    window._tag_library_finish_selection(QPoint(35, 10), Qt.ControlModifier)

    assert window._tag_library_selection == {"TagA", "TagB"}


def test_tag_library_finish_selection_edge_case_click_without_drag() -> None:
    """Modifier click without drag does not alter selection."""
    window = MainWindow.__new__(MainWindow)
    window._tag_library_selection_start = QPoint(10, 10)
    window._tag_library_selection = set()
    window._last_selected_tag = None
    window._tag_library_is_selecting = True
    window._tag_library_drag_start_tag = "TagA"
    window._tag_library_drag_start_button = object()
    window._sync_tag_grid_state = lambda: None
    window._get_user_tag_buttons_viewport_rects = lambda: [("TagA", QRect(0, 0, 20, 20))]

    window._tag_library_finish_selection(QPoint(12, 11), Qt.ControlModifier)

    assert window._tag_library_selection == set()


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


class _ImageLike:
    """Lightweight image object for session start slicing tests."""

    def __init__(self, image_id: str) -> None:
        self.id = image_id


def test_slice_images_from_start_expected_use() -> None:
    """Return list from selected image when ID exists."""
    images = [_ImageLike("a"), _ImageLike("b"), _ImageLike("c")]

    sliced = MainWindow._slice_images_from_start(images, "b")

    assert [img.id for img in sliced] == ["b", "c"]


def test_slice_images_from_start_edge_case_first_image() -> None:
    """Keep full list when selected image is already first."""
    images = [_ImageLike("a"), _ImageLike("b"), _ImageLike("c")]

    sliced = MainWindow._slice_images_from_start(images, "a")

    assert [img.id for img in sliced] == ["a", "b", "c"]


def test_slice_images_from_start_failure_case_unknown_image() -> None:
    """Fallback to full list when selected image does not exist."""
    images = [_ImageLike("a"), _ImageLike("b"), _ImageLike("c")]

    sliced = MainWindow._slice_images_from_start(images, "missing")

    assert [img.id for img in sliced] == ["a", "b", "c"]


def test_expand_tags_with_descendants_expected_use() -> None:
    """Selecting a parent tag includes all nested child tags."""
    window = MainWindow.__new__(MainWindow)
    window._user_tags_config = {
        "placements": {
            "Felin": {"parent_tag": "Terrestrial"},
            "Chat": {"parent_tag": "Felin"},
            "Tiger": {"parent_tag": "Felin"},
            "Lion": {"parent_tag": "Felin"},
        }
    }
    expanded = window._expand_tags_with_descendants({"Felin"})
    assert expanded == {"Felin", "Chat", "Tiger", "Lion"}


def test_expand_tags_with_descendants_edge_case_leaf_tag() -> None:
    """Selecting a leaf tag returns only itself."""
    window = MainWindow.__new__(MainWindow)
    window._user_tags_config = {
        "placements": {
            "Felin": {"parent_tag": "Terrestrial"},
            "Chat": {"parent_tag": "Felin"},
        }
    }
    expanded = window._expand_tags_with_descendants({"Chat"})
    assert expanded == {"Chat"}


def test_get_all_descendants_failure_case_cycle_safe() -> None:
    """A cyclic parent chain does not recurse forever and stays finite."""
    window = MainWindow.__new__(MainWindow)
    window._user_tags_config = {
        "placements": {
            "A": {"parent_tag": "B"},
            "B": {"parent_tag": "A"},
        }
    }
    descendants = window._get_all_descendants("A")
    assert descendants == {"A", "B"}


def test_active_category_filter_data_recursive_group_or_expected_use() -> None:
    """Selected sub-category builds OR group with all recursive descendants."""
    window = MainWindow.__new__(MainWindow)
    window._user_tags_config = {
        "placements": {
            "Felin": {"parent_tag": "Terrestrial"},
            "Chat": {"parent_tag": "Felin"},
            "Tiger": {"parent_tag": "Felin"},
            "Lion": {"parent_tag": "Felin"},
        }
    }
    window._active_categories = {"Animal"}
    window._active_subtags = {"Animal": {"Felin"}}
    window._subcategory_buttons = {"Animal": {"Terrestrial": object(), "Felin": object()}}
    window._normalize_tag_for_match = MainWindow._normalize_tag_for_match

    filter_data = window._get_active_category_filter_data()
    allowed_norm, required_groups_norm = filter_data[0]

    assert "animal" in allowed_norm
    assert len(required_groups_norm) == 1
    assert required_groups_norm[0] == {"felin", "chat", "tiger", "lion"}


def test_with_expand_icon_expected_use() -> None:
    """Expandable entries show arrow icon prefix."""
    assert MainWindow._with_expand_icon("Felin", True, False).endswith(" ▶")
    assert MainWindow._with_expand_icon("Felin", True, True).endswith(" ▼")


def test_with_expand_icon_edge_case_no_children() -> None:
    """Non-expandable entries keep plain label."""
    assert MainWindow._with_expand_icon("Chat", False, False) == "Chat"


def test_get_tag_depth_in_category_failure_case_cycle_safe() -> None:
    """Depth computation remains finite when hierarchy contains a cycle."""
    window = MainWindow.__new__(MainWindow)
    window._user_tags_config = {
        "placements": {
            "A": {"parent_tag": "B"},
            "B": {"parent_tag": "A"},
        }
    }
    window._subtag_to_category = {"A": "Animal", "B": "Animal"}
    depth = window._get_tag_depth_in_category("A", "Animal")
    assert isinstance(depth, int)
    assert depth >= 0


def test_event_filter_hover_tag_button_expected_use_opens_sidebar() -> None:
    """Hovering the floating button opens the collapsed sidebar."""
    window = MainWindow.__new__(MainWindow)
    window.tag_filters_floating_btn = object()
    window.left_panel_container = object()
    window._left_panel_expanded = False
    window._left_panel_animating = False
    called = {"n": 0}
    window._toggle_left_sidebar = lambda: called.__setitem__("n", called["n"] + 1)

    event = QEvent(QEvent.Type.Enter)
    consumed = window.eventFilter(window.tag_filters_floating_btn, event)

    assert consumed is False
    assert called["n"] == 1


def test_event_filter_leave_sidebar_edge_case_collapsed_no_action() -> None:
    """Leaving sidebar while already collapsed does not trigger toggle."""
    window = MainWindow.__new__(MainWindow)
    window.left_panel_container = object()
    window._left_panel_expanded = False
    window._left_panel_animating = False
    called = {"n": 0}
    window._toggle_left_sidebar = lambda: called.__setitem__("n", called["n"] + 1)

    event = QEvent(QEvent.Type.Leave)
    consumed = window.eventFilter(window.left_panel_container, event)

    assert consumed is False
    assert called["n"] == 0


def test_event_filter_leave_sidebar_expected_use_closes_sidebar() -> None:
    """Leaving expanded sidebar triggers auto-collapse."""
    window = MainWindow.__new__(MainWindow)
    window.left_panel_container = object()
    window._left_panel_expanded = True
    window._left_panel_animating = False
    called = {"n": 0}
    window._toggle_left_sidebar = lambda: called.__setitem__("n", called["n"] + 1)

    event = QEvent(QEvent.Type.Leave)
    consumed = window.eventFilter(window.left_panel_container, event)

    assert consumed is False
    assert called["n"] == 1


def test_event_filter_leave_sidebar_failure_case_animating_no_action() -> None:
    """Leaving sidebar during animation does not trigger re-collapse."""
    window = MainWindow.__new__(MainWindow)
    window.left_panel_container = object()
    window._left_panel_expanded = True
    window._left_panel_animating = True
    called = {"n": 0}
    window._toggle_left_sidebar = lambda: called.__setitem__("n", called["n"] + 1)

    event = QEvent(QEvent.Type.Leave)
    consumed = window.eventFilter(window.left_panel_container, event)

    assert consumed is False
    assert called["n"] == 0