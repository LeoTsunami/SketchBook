"""
Main window of the SketchBook application.
"""
from pathlib import Path
from typing import Any, Dict, List, Set, Optional, Tuple
from qtpy.QtWidgets import (
    QMainWindow,
    QMenuBar,
    QMenu,
    QFileDialog,
    QMessageBox,
    QStatusBar,
    QWidget,
    QVBoxLayout,
    QProgressBar,
    QDockWidget,
    QTextEdit,
    QLabel,
    QSplitter,
    QHBoxLayout,
    QSlider,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QComboBox,
    QSpinBox,
    QTreeWidget,
    QTreeWidgetItem,
    QDialog,
    QGridLayout,
    QFrame,
    QSizePolicy,
    QCompleter,
    QInputDialog,
    QMenu,
)
from qtpy.QtCore import (
    Qt,
    QThreadPool,
    QMetaObject,
    Q_ARG,
    Slot,
    QThread,
    QTimer,
    QMimeData,
    QSize,
    QStringListModel,
    QUrl,
    Signal,
    QEvent,
    QObject,
)
from qtpy.QtGui import (
    QAction,
    QActionGroup,
    QDragEnterEvent,
    QDropEvent,
    QPixmap,
    QDrag,
    QPainter,
    QIcon,
    QImage,
    QCursor,
)
from core.settings import settings
from core.image_manager import ImageManager
from core.image_db import ImageMetadata
from core import user_tags_config
from gui.image_import_worker import ImageImportWorker
from gui.image_grid import ImageGrid, ImageThumbnail
from gui.tag_widgets import DraggableTagChip
from gui.add_tag_dialog import AddTagDialog, IconPickerDialog
from gui.tag_apply_worker import TagApplyWorker
from gui.session_settings_dialog import SessionSettingsDialog
from gui.image_viewer_window import ImageViewerWindow
from gui.slideshow_window import SlideshowWindow
from core.session_manager import SessionManager
from qtpy.QtWidgets import QApplication
from gui.icon_utils import find_tag_icon, invert_icon
import os
import json


class DraggableTreeWidget(QTreeWidget):
    """Tree widget that supports dragging tags to drop zones."""
    
    def startDrag(self, supportedActions):
        """Start drag operation from tree widget."""
        item = self.currentItem()
        if not item or not (item.flags() & Qt.ItemIsDragEnabled):
            return
        
        tag_text = item.text(0)
        
        # Create drag
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(tag_text)
        drag.setMimeData(mime_data)
        
        # Create drag pixmap
        pixmap = QPixmap(100, 20)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setPen(Qt.white)
        painter.drawText(pixmap.rect(), Qt.AlignCenter, tag_text)
        painter.end()
        drag.setPixmap(pixmap)
        
        # Execute drag
        drag.exec_(Qt.MoveAction)


# MIME type for drag from tag library (reposition user tag); plain text used for drop on images
TAG_LIBRARY_MIME = "application/x-sketchbook-tag-library"


class TagGridDropFilter(QObject):
    """Event filter to accept tag-library drag/drop on the tag grid container."""

    def __init__(self, main_window: "MainWindow"):
        super().__init__(main_window)
        self._main = main_window

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj != self._main.tags_grid_container:
            return False
        try:
            _drag_enter = QEvent.Type.DragEnter
            _drop_type = QEvent.Type.Drop
        except AttributeError:
            _drag_enter = QEvent.DragEnter
            _drop_type = QEvent.Drop
        if event.type() == _drag_enter:
            if event.mimeData().hasFormat(TAG_LIBRARY_MIME):
                event.acceptProposedAction()
            return True
        if event.type() == _drop_type:
            self._main._on_tag_grid_drop(event)
            return True
        return False


class DraggableTagButton(QPushButton):
    """Tag button in the tag library that can be dragged onto images."""

    contextMenuRequested = Signal(str)

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self._drag_start_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        """Emit signal so main window can show Rename (user tags only)."""
        self.contextMenuRequested.emit(self.text())
        event.accept()

    def mouseMoveEvent(self, event):
        if (
            event.buttons() & Qt.LeftButton
            and self._drag_start_pos is not None
            and (event.pos() - self._drag_start_pos).manhattanLength() >= 10
        ):
            tag_text = self.text()
            if not tag_text:
                return

            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(tag_text)
            # Mark drag from tag library so grid can accept drop for repositioning (user tags only)
            if self.property("userTag"):
                mime_data.setData(TAG_LIBRARY_MIME, tag_text.encode("utf-8"))
            drag.setMimeData(mime_data)

            # Simple pixmap with tag text for visual feedback
            pixmap = QPixmap(120, 28)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setPen(Qt.white)
            painter.drawText(pixmap.rect(), Qt.AlignCenter, tag_text)
            painter.end()
            drag.setPixmap(pixmap)

            drag.exec_(Qt.MoveAction)
            return

        super().mouseMoveEvent(event)

def apply_global_stylesheet():
    app = QApplication.instance()
    theme = settings.get("ui.theme", "dark")
    qss_path = os.path.join(os.path.dirname(__file__), "styles", f"style_{theme}.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    else:
        app.setStyleSheet("")

class MainWindow(QMainWindow):
    """Main window of the application."""
    
    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        
        # Initialize managers
        self.image_manager = ImageManager()
        self.session_manager = SessionManager()
        self.thread_pool = QThreadPool()

        # Session slideshow window (created when needed, parent=self for hide/show)
        self._slideshow_window: Optional[SlideshowWindow] = None
        
        # Dev mode flag
        self.dev_mode = settings.get("ui.dev_mode", False)
        
        # Progress bar reference
        self.status_progress_bar = None
        self._category_buttons: Dict[str, QPushButton] = {}
        self._subcategory_buttons: Dict[str, Dict[str, QPushButton]] = {}
        self._user_tag_buttons: Dict[str, QPushButton] = {}
        self._active_categories: Set[str] = set()
        self._active_subtags: Dict[str, Set[str]] = {}
        self._subtag_to_category: Dict[str, str] = {}
        self._user_tags_config: Dict[str, Any] = {}  # Loaded in _load_tags_into_grid
        # Temporary icon override for live preview in "Change icon" dialog; key = tag, value = icon filename or None
        self._icon_preview_override: Dict[str, Optional[str]] = {}
        self._shuffle_counter: int = 0  # Counter for shuffle iterations (increments on each shuffle)
        self._course_random_images_list: List[ImageMetadata] = []  # Global list of ALL images in random order (only changed by shuffle button)
        self._filtered_course_random_list: List[ImageMetadata] = []  # Filtered list from grid (same as what's displayed)

        # Window setup
        self.setWindowTitle("SketchBook")
        self.resize(1280, 800)
        
        # Initialize UI
        self._setup_ui()
        self._setup_menu()
        self._setup_statusbar()
        self._setup_dev_tools()
        
        # Apply theme
        self._apply_theme()
        
        # Enable drag and drop
        self.setAcceptDrops(True)
        
        # Maximize window on startup
        self.showMaximized()
        
        # Load initial images (will be sorted by _apply_category_filters which is called in _setup_ui)
        # Don't call load_images here as _apply_category_filters will handle it
    
    def _setup_ui(self):
        """Set up the main UI components."""
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Set up the main image browser layout
        self._setup_image_browser()
        
        # Update session images count with initial filters
        self._apply_category_filters()

    def _setup_image_browser(self):
        """Set up the Image Browser with 2-panel splitter layout."""
        # Create main splitter (horizontal)
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setChildrenCollapsible(False)
        
        # === LEFT PANEL: Vertical Splitter with Tag Manager ===
        left_splitter = QSplitter(Qt.Vertical)
        left_splitter.setChildrenCollapsible(False)
        
        # Top part: Tag Manager (search bar + drop zones)
        tag_manager_panel = QWidget()
        tag_manager_layout = QVBoxLayout(tag_manager_panel)
        tag_manager_layout.setContentsMargins(10, 10, 10, 10)
        tag_manager_layout.setSpacing(10)
        tag_manager_layout.setAlignment(Qt.AlignTop)
        
        # Logo and text at the top
        logo_path = Path(__file__).parent / "ressources" / "icones" / "SketchBook_logo.png"
        if logo_path.exists():
            logo_container = QWidget()
            logo_container_layout = QHBoxLayout(logo_container)
            logo_container_layout.setContentsMargins(0, 0, 0, 0)
            logo_container_layout.setSpacing(10)
            
            # Logo
            logo_label = QLabel()
            pixmap = QPixmap(str(logo_path))
            # Scale logo to fit width (max 100px) while maintaining aspect ratio
            if pixmap.width() > 100:
                scaled_pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                logo_label.setPixmap(scaled_pixmap)
            else:
                logo_label.setPixmap(pixmap)
            logo_label.setAlignment(Qt.AlignCenter)
            logo_label.setStyleSheet("background-color: transparent;")
            logo_container_layout.addWidget(logo_label)
            
            # Text next to logo (on two lines with Caveat font)
            welcome_text = QLabel("What do you want\nto draw today?")
            welcome_text.setObjectName("welcome_text")
            welcome_text.setStyleSheet("font-family: 'Caveat'; font-size: 24px; font-weight: bold; background-color: transparent;")
            welcome_text.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            logo_container_layout.addWidget(welcome_text)
            
            tag_manager_layout.addWidget(logo_container)
        
        tag_manager_layout.addStretch()
        
        left_splitter.addWidget(tag_manager_panel)
        
        # Middle part: Tags grid
        tags_tree_panel = QWidget()
        tags_tree_layout = QVBoxLayout(tags_tree_panel)
        tags_tree_layout.setContentsMargins(10, 10, 10, 10)
        tags_tree_layout.setSpacing(5)
        
        # Title row: "Tags Library" + small blue "+" button
        tags_header_layout = QHBoxLayout()
        tags_header_layout.setContentsMargins(0, 0, 0, 0)
        tags_tree_title = QLabel("Tags Library")
        tags_tree_title.setStyleSheet("font-size: 12px; font-weight: bold;")
        tags_header_layout.addWidget(tags_tree_title)
        tags_header_layout.addStretch()
        add_tag_btn = QPushButton("+ Create tag")
        add_tag_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-size: 12px;
                font-weight: bold;
                padding: 6px 12px;
                border: none;
                border-radius: 4px;
                min-width: 90px;
            }
            QPushButton:hover { background-color: #1976D2; }
            QPushButton:pressed { background-color: #0D47A1; }
        """)
        add_tag_btn.setToolTip("Add a new tag to the library")
        add_tag_btn.clicked.connect(self._on_add_user_tag_clicked)
        tags_header_layout.addWidget(add_tag_btn)
        tags_tree_layout.addLayout(tags_header_layout)

        # Scrollable grid widget for tags
        self.tags_grid_container = QWidget()
        self.tags_grid_layout = QGridLayout(self.tags_grid_container)
        self.tags_grid_layout.setContentsMargins(0, 0, 0, 0)
        self.tags_grid_layout.setSpacing(10)
        # Align content to top
        self.tags_grid_layout.setAlignment(Qt.AlignTop)

        self.tags_scroll_area = QScrollArea()
        self.tags_scroll_area.setWidgetResizable(True)
        self.tags_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tags_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tags_scroll_area.setFrameShape(QFrame.NoFrame)
        self.tags_scroll_area.setWidget(self.tags_grid_container)
        tags_tree_layout.addWidget(self.tags_scroll_area)
        self.tags_grid_container.setAcceptDrops(True)
        self._tag_grid_drop_filter = TagGridDropFilter(self)
        self.tags_grid_container.installEventFilter(self._tag_grid_drop_filter)

        # Load tags into grid
        self._load_tags_into_grid()
        
        left_splitter.addWidget(tags_tree_panel)
        
        # Search and filter panel: Search bar and AND/OR zones
        search_filter_panel = QWidget()
        search_filter_layout = QVBoxLayout(search_filter_panel)
        search_filter_layout.setContentsMargins(10, 10, 10, 10)
        search_filter_layout.setSpacing(10)
        
        # Title
        search_filter_title = QLabel("Search & Filters")
        search_filter_title.setStyleSheet("font-size: 12px; font-weight: bold;")
        search_filter_layout.addWidget(search_filter_title)
        
        # Search bar
        search_layout = QHBoxLayout()
        
        self.tag_search_input = QLineEdit()
        self.tag_search_input.setPlaceholderText("Search tags")
        self.tag_search_input.returnPressed.connect(self._on_tag_search_return)
        search_layout.addWidget(self.tag_search_input)
        
        # Set up tag search completer (only user tags)
        self._update_tag_search_completer()
        
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self._clear_all_tag_filters)
        search_layout.addWidget(clear_btn)
        
        search_filter_layout.addLayout(search_layout)
        
        # Filter zones (AND/OR)
        zones_layout = QHBoxLayout()
        zones_layout.setSpacing(8)
        
        from gui.tag_widgets import TagDropZone
        self.and_zone = TagDropZone("AND (all required)")
        self.and_zone.tag_dropped.connect(self._on_tag_filter_changed)
        self.and_zone.tags_modified.connect(self._on_tag_filter_changed)
        zones_layout.addWidget(self.and_zone, 1)
        
        self.or_zone = TagDropZone("OR (at least one)")
        self.or_zone.tag_dropped.connect(self._on_tag_filter_changed)
        self.or_zone.tags_modified.connect(self._on_tag_filter_changed)
        zones_layout.addWidget(self.or_zone, 1)
        
        search_filter_layout.addLayout(zones_layout)
        
        # Hide Search & Filters panel for now (full Tags Library mode)
        search_filter_panel.setVisible(False)
        left_splitter.addWidget(search_filter_panel)
        
        # Bottom part: Session settings button
        bottom_panel = QWidget()
        bottom_layout = QVBoxLayout(bottom_panel)
        bottom_layout.setContentsMargins(10, 10, 10, 10)
        bottom_layout.setSpacing(10)
        
        # Add stretch to push button to bottom
        bottom_layout.addStretch()
        
        # Session Settings button
        self.session_settings_btn = QPushButton("Session Settings")
        self.session_settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.session_settings_btn.clicked.connect(self._on_session_settings_clicked)
        bottom_layout.addWidget(self.session_settings_btn)
        
        left_splitter.addWidget(bottom_panel)
        
        # Set splitter sizes (top: minimal, Tags Library: maximum, bottom: minimal)
        # Tags Library (index 1) gets maximum space, others get minimum
        # Note: search_filter_panel (index 2) is hidden but still in splitter
        left_splitter.setSizes([100, 1000, 0, 100])
        # Set stretch factors: Tags Library gets priority
        left_splitter.setStretchFactor(0, 1)   # Top (logo/welcome)
        left_splitter.setStretchFactor(1, 10)  # Tags Library (maximum)
        left_splitter.setStretchFactor(2, 0)   # Search & Filters (hidden)
        left_splitter.setStretchFactor(3, 1)   # Bottom (Session Settings)
        
        # Add left splitter to main splitter
        main_splitter.addWidget(left_splitter)
        
        # === MIDDLE PANEL: Image Grid ===
        middle_panel = QWidget()
        middle_layout = QVBoxLayout(middle_panel)
        middle_layout.setContentsMargins(10, 10, 10, 10)
        middle_layout.setSpacing(10)
        
        # Create grid controls
        grid_controls = QHBoxLayout()
        grid_controls.setContentsMargins(0, 0, 10, 0)
        
        # Label for number of images and selection info (left side)
        self.session_images_count_label = QLabel("Images: 0")
        self.session_images_count_label.setStyleSheet("font-size: 12px; font-weight: bold;")
        grid_controls.addWidget(self.session_images_count_label)
        self.selection_info_label = QLabel("")
        self.selection_info_label.setStyleSheet("font-size: 12px; font-weight: bold; color: #7eb8da;")
        grid_controls.addWidget(self.selection_info_label)
        
        # Add sort combo box with shuffle button
        grid_controls.addStretch()
        
        # Shuffle button (only visible for "Session Course Random")
        self.shuffle_button = QPushButton("Shuffle")
        self.shuffle_button.setFixedWidth(70)
        self.shuffle_button.setStyleSheet("""
            QPushButton {
                background-color: #3c3f41;
                color: #ffffff;
                border: 1px solid #4d4d4d;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #4b6eaf;
            }
            QPushButton:pressed {
                background-color: #3d5a8c;
            }
        """)
        self.shuffle_button.clicked.connect(self._on_shuffle_clicked)
        self.shuffle_button.hide()  # Hidden by default
        grid_controls.addWidget(self.shuffle_button)
        
        sort_label = QLabel("Sort:")
        sort_label.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            "Most Recent First",
            "Oldest First",
            "Filename A→Z",
            "Filename Z→A",
            "Lightest First",
            "Heaviest First",
            "Session Course Random"
        ])
        self.sort_combo.setCurrentIndex(0)  # Default: Most Recent First
        self.sort_combo.setFixedWidth(150)
        self.sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        
        grid_controls.addWidget(sort_label)
        grid_controls.addWidget(self.sort_combo)
        
        # Add column control slider (right side)
        columns_label = QLabel("Columns:")
        columns_label.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        self.columns_slider = QSlider(Qt.Horizontal)
        self.columns_slider.setMinimum(3)
        self.columns_slider.setMaximum(10)
        self.columns_slider.setValue(settings.get("ui.grid.columns", 4))
        self.columns_slider.setTickPosition(QSlider.NoTicks)
        self.columns_slider.setFixedWidth(100)
        self.columns_slider.valueChanged.connect(self._on_columns_changed)
        
        # Add column count label
        self.columns_count = QLabel(str(self.columns_slider.value()))
        self.columns_count.setStyleSheet("color: #aaaaaa; font-size: 11px;")
        
        grid_controls.addWidget(columns_label)
        grid_controls.addWidget(self.columns_slider)
        grid_controls.addWidget(self.columns_count)
        
        middle_layout.addLayout(grid_controls)
        
        # Create image grid
        print("Creating image grid")
        self.image_grid = ImageGrid(self.image_manager)
        self.image_grid.set_columns(self.columns_slider.value())
        self.image_grid.image_double_clicked.connect(self._on_image_clicked)
        self.image_grid.tag_remove_progress.connect(
            self._handle_tag_remove_progress,
            Qt.QueuedConnection,
        )
        self.image_grid.tag_remove_finished.connect(
            self._handle_tag_remove_finished,
            Qt.QueuedConnection,
        )
        self.image_grid.tag_remove_error.connect(
            self._handle_tag_remove_error,
            Qt.QueuedConnection,
        )
        self.image_grid.selection_changed.connect(self._on_selection_changed)
        self.image_grid.grid_needs_refresh.connect(self._apply_category_filters)
        self.image_grid.set_import_drop_callback(self._import_from_urls)
        middle_layout.addWidget(self.image_grid)

        # Lazy-created image viewer window (one window, reused)
        self._image_viewer_window = None
        
        # Add middle panel to splitter
        main_splitter.addWidget(middle_panel)
        
        # Set splitter sizes (left: 150px minimum, middle: flexible)
        main_splitter.setSizes([150, 800])
        
        # Add main splitter to layout
        layout = self.centralWidget().layout()
        layout.addWidget(main_splitter)
    
    def _get_default_tags_from_path(self, default_tags_path: Path) -> Set[str]:
        """
        Load default tags from a JSON file and include category names.

        Args:
            default_tags_path: Path to the default tags JSON file.

        Returns:
            set: Default tags including category names.
        """
        if not default_tags_path.exists():
            return set()

        try:
            with open(default_tags_path, "r", encoding="utf-8") as f:
                default_tags_data = json.load(f)
        except Exception as exc:
            print(f"Error loading default tags: {str(exc)}")
            return set()

        tag_set: Set[str] = set()

        def extract_tags(data) -> None:
            """Recursively extract all tags from nested structure."""
            if isinstance(data, list):
                for item in data:
                    extract_tags(item)
            elif isinstance(data, dict):
                for key, value in data.items():
                    tag_set.add(key)
                    extract_tags(value)
            elif isinstance(data, str):
                tag_set.add(data)

        extract_tags(default_tags_data)
        return tag_set

    def _get_default_tags(self) -> Set[str]:
        """
        Load default tags from JSON and include category names.

        Returns:
            set: Default tags including category names.
        """
        default_tags_path = Path(__file__).parent / "ressources" / "default_tags.json"
        return self._get_default_tags_from_path(default_tags_path)
    
    def _get_user_tags(self) -> Set[str]:
        """
        Get all user-defined tags: from DB (excluding default) plus registered-only (added via UI).

        Returns:
            set: User-defined tags.
        """
        default_tags = self._get_default_tags()
        all_tags = set()
        for metadata in self.image_manager.db.list_images():
            all_tags.update(metadata.tags)
        from_db = all_tags - default_tags
        registered = set(getattr(self, "_user_tags_config", {}).get("registered_only", []))
        return from_db | registered

    def _apply_category_filters(self) -> None:
        """Apply category/subtag filters to the image grid."""
        # Get current sort order
        sort_by = self._get_current_sort_order()
        
        if sort_by == "course_random":
            # Use the global course_random list and filter it (keeping order)
            if not self._course_random_images_list:
                self._initialize_course_random_list()
            
            # Start with the global random list
            images_to_display = self._course_random_images_list
            
            # Apply category filters (keep order, just filter which images are shown)
            images_to_display = self._filter_images_by_category_from_list(images_to_display)
            # Apply AND/OR filters
            images_to_display = self._apply_and_or_filters(images_to_display)
            
            shuffle_iteration = self._shuffle_counter
        else:
            # Normal filtering and sorting for other sort modes
            filtered_images = self._filter_images_by_category()
            filtered_images = self._apply_and_or_filters(filtered_images)
            shuffle_iteration = 0
            images_to_display = self.image_manager.db._sort_images(filtered_images, sort_by)
        
        filter_key = (
            frozenset(self._active_categories),
            frozenset(
                (category, frozenset(tags))
                for category, tags in self._active_subtags.items()
            ),
            sort_by,
            shuffle_iteration  # Include shuffle iteration in filter key
        )
        self.image_grid.load_images_from_list(images_to_display, filter_key)
        self._update_session_images_count(images_to_display)
        self._sync_tag_grid_state()
        
        # Store filtered list for session (for course_random mode only)
        if sort_by == "course_random":
            self._filtered_course_random_list = images_to_display.copy()
            # Debug: print what's stored for grid
            first_5_ids = [img.id for img in images_to_display[:5]]
            print(f"[DEBUG] GRID DISPLAY - {len(images_to_display)} images | First 5 IDs: {first_5_ids}")
    
    def _filter_images_by_category_from_list(self, images: List[ImageMetadata]) -> List[ImageMetadata]:
        """
        Filter images from a given list by category/subtag filters (keeps original order).
        
        Args:
            images: List of images to filter (order will be preserved).
            
        Returns:
            Filtered list of images in the same order.
        """
        if not self._active_categories and not self._active_subtags:
            return images
        
        filtered = []
        for metadata in images:
            image_tags = metadata.tags
            
            # Check category match (OR logic between categories)
            category_match = False
            if not self._active_categories:
                category_match = True  # No category selected = show all
            else:
                for category in self._active_categories:
                    # Check if image has this category tag
                    if category in image_tags:
                        # Check subtags (AND logic within category)
                        subtags = self._active_subtags.get(category, set())
                        if not subtags:
                            # No subtags selected for this category = match
                            category_match = True
                            break
                        else:
                            # All selected subtags must be present (AND)
                            if subtags.issubset(image_tags):
                                category_match = True
                                break
            
            if category_match:
                filtered.append(metadata)
        
        return filtered
    
    def _get_current_sort_order(self) -> str:
        """
        Get the current sort order from the combo box.
        
        Returns:
            Sort order string
        """
        sort_map = {
            0: "import_date_desc",  # Most Recent First
            1: "import_date_asc",   # Oldest First
            2: "filename_asc",      # Filename A→Z
            3: "filename_desc",     # Filename Z→A
            4: "file_size_asc",     # Lightest First
            5: "file_size_desc",    # Heaviest First
            6: "course_random",     # Session Course Random
        }
        return sort_map.get(self.sort_combo.currentIndex(), "import_date_desc")
    
    def _on_sort_changed(self, index: int):
        """Handle sort order change."""
        # Show/hide shuffle button based on selected sort
        is_random_sort = index == 6  # "Session Course Random" is index 6
        self.shuffle_button.setVisible(is_random_sort)
        
        # Reset shuffle counter when switching away from random sort
        if not is_random_sort:
            self._shuffle_counter = 0
            self._course_random_images_list = []  # Clear stored course random list
            self._filtered_course_random_list = []  # Clear filtered list
        
        # If switching to random sort, initialize the global random list if empty
        if is_random_sort and not self._course_random_images_list:
            self._initialize_course_random_list()
        
        # Reapply filters with new sort order
        self._apply_category_filters()
    
    def _on_shuffle_clicked(self):
        """Handle shuffle button click - regenerate random order for ALL images."""
        # Update global shuffle timestamp for more random variation
        import time
        from core.image_db import _shuffle_timestamp
        import core.image_db as image_db_module
        image_db_module._shuffle_timestamp = int(time.time() * 1000000)  # Use microseconds
        
        # Increment shuffle counter to generate new order
        self._shuffle_counter += 1
        # Regenerate the global random list with new seed
        self._initialize_course_random_list()
        # Reapply filters (order stays the same, just filter which images are shown)
        self._apply_category_filters()
    
    def _initialize_course_random_list(self):
        """Initialize the global course_random list with ALL images in random order."""
        # Get ALL images from database
        all_images = self.image_manager.db.list_images()
        
        # Apply random shuffle with current shuffle counter
        self._course_random_images_list = self.image_manager.db._sort_images(
            all_images, 
            "course_random", 
            shuffle_iteration=self._shuffle_counter
        )
        
        # Debug: print the global list
        print(f"[DEBUG] INIT/SHUFFLE: Generated random list ({len(self._course_random_images_list)} images)")
        print(f"[DEBUG] First 5 IDs: {[img.id for img in self._course_random_images_list[:5]]}")
    
    def _apply_and_or_filters(self, images: List) -> List:
        """
        Apply AND/OR filters to the image list (only on user tags).
        This is a filtering layer on top of category filters.
        
        Args:
            images: List of image metadata to filter.
            
        Returns:
            List: Filtered image metadata list.
        """
        and_tags = self.and_zone.get_tags()
        or_tags = self.or_zone.get_tags()
        
        if not and_tags and not or_tags:
            return images
        
        # Get default tags to filter them out
        default_tags = self._get_default_tags()
        
        filtered_images = []
        for metadata in images:
            # Extract only user tags from image (exclude default tags)
            image_user_tags = set(metadata.tags) - default_tags
            
            # AND: all tags must be present in user tags
            if and_tags and not and_tags.issubset(image_user_tags):
                continue
            
            # OR: at least one tag must be present in user tags
            if or_tags and not or_tags.intersection(image_user_tags):
                continue
            
            filtered_images.append(metadata)
        
        return filtered_images

    def _update_session_images_count(self, filtered_images: List) -> None:
        """
        Update the label showing the number of images available for session.
        
        Args:
            filtered_images: Filtered images list.
        """
        count = len(filtered_images)
        self.session_images_count_label.setText(f"Images: {count}")
        # Refresh selection info (in case filtered list changed)
        self._update_selection_info_label(list(self.image_grid.selected_images))

    def _on_selection_changed(self, image_ids: List[str]) -> None:
        """Update selection info label when grid selection changes."""
        self._update_selection_info_label(image_ids)

    def _update_selection_info_label(self, image_ids: List[str]) -> None:
        """
        Update the label showing selected count and total size in MB.
        Uses actual file size on disk (not DB cache) so the displayed weight is real.
        
        Args:
            image_ids: List of selected image IDs.
        """
        if not image_ids:
            self.selection_info_label.setText("")
            return
        total_bytes = 0
        image_dir = self.image_manager.image_dir
        for image_id in image_ids:
            meta = self.image_manager.get_image_metadata(image_id)
            if not meta:
                continue
            # Use current file size on disk so displayed weight matches Explorer
            file_path = image_dir / meta.path
            if file_path.exists():
                try:
                    total_bytes += file_path.stat().st_size
                except OSError:
                    total_bytes += meta.file_size  # fallback to DB value
            else:
                total_bytes += meta.file_size
        total_mb = total_bytes / (1024 * 1024)
        self.selection_info_label.setText(f"  |  Selected: {len(image_ids)} | {total_mb:.2f} MB")
    
    def _on_session_settings_clicked(self):
        """Handle Session Settings button click: open dialog then start session window."""
        # Get current sort order
        sort_by = self._get_current_sort_order()
        
        if sort_by == "course_random":
            # Use the EXACT same filtered list as the grid (stored in _filtered_course_random_list)
            if not self._filtered_course_random_list:
                # If not set, get it from grid's current display
                filtered_images = list(self.image_grid.all_images) if hasattr(self.image_grid, 'all_images') else []
                if not filtered_images:
                    # Fallback: regenerate filters
                    if not self._course_random_images_list:
                        self._initialize_course_random_list()
                    filtered_images = self._course_random_images_list
                    filtered_images = self._filter_images_by_category_from_list(filtered_images)
                    filtered_images = self._apply_and_or_filters(filtered_images)
            else:
                # Use the stored filtered list (same as grid)
                filtered_images = self._filtered_course_random_list
            
            # Debug: print first 5 elements sent to session
            first_5_ids = [img.id for img in filtered_images[:5]]
            print(f"[DEBUG] SESSION BEGIN - {len(filtered_images)} images | First 5 IDs: {first_5_ids}")
            
            shuffle_iteration = self._shuffle_counter
        else:
            # For other sort modes, get current filtered images
            filtered_images = self._filter_images_by_category()
            filtered_images = self._apply_and_or_filters(filtered_images)
            filtered_images = self.image_manager.db._sort_images(filtered_images, sort_by)
            shuffle_iteration = 0
        
        image_count = len(filtered_images)

        dialog = SessionSettingsDialog(self.image_manager, image_count, self)
        if dialog.exec_() != QDialog.Accepted or not dialog.session_started:
            return

        settings_dict = dialog.get_session_settings()
        session_type = settings_dict["session_type"]
        window_mode = settings_dict["window_mode"]
        # Use image IDs in the stored order (for course_random) or current order (for others)
        image_ids = [m.id for m in filtered_images]
        
        # Debug: print IDs being sent
        print(f"[DEBUG] _on_session_settings_clicked: Sending {len(image_ids)} IDs to session")
        print(f"[DEBUG] _on_session_settings_clicked: First 5 IDs: {image_ids[:5]}")

        course_duration_minutes: Optional[int] = None
        interval_seconds: Optional[int] = None

        if session_type == "Course":
            course_duration_minutes = settings_dict["course_duration_minutes"]
        else:
            # Map "30 seconds" -> 30, "1 minute" -> 60, etc.
            interval_text = settings_dict.get("interval_duration", "1 minute")
            _interval_map = {
                "30 seconds": 30,
                "1 minute": 60,
                "3 minutes": 180,
                "5 minutes": 300,
                "10 minutes": 600,
                "20 minutes": 1200,
            }
            interval_seconds = _interval_map.get(interval_text, 60)

        if self._slideshow_window is None:
            self._slideshow_window = SlideshowWindow(
                self.session_manager, self.image_manager, parent=self
            )
            self._slideshow_window.session_ended.connect(self._on_session_ended)

        course_config_path = Path(__file__).resolve().parent / "ressources" / "session_configs.json"
        # For course_random mode, use exact order (no reshuffle in session)
        use_exact_order = (sort_by == "course_random")
        started = self._slideshow_window.start_session(
            image_ids=image_ids,
            session_type=session_type,
            shuffle_iteration=shuffle_iteration,
            course_duration_minutes=course_duration_minutes,
            interval_seconds=interval_seconds,
            window_mode=window_mode,
            course_config_path=course_config_path,
            use_exact_order=use_exact_order,
        )
        if started:
            self.hide()
        else:
            QMessageBox.warning(
                self,
                "Session",
                "Could not start session. For Course, use a duration of 10, 20, 30, 40, 50 or 60 minutes.",
            )

    def _on_session_ended(self):
        """Re-show main window when session window is closed."""
        self.show()
        self.raise_()
        self.activateWindow()
    
    def _build_subtags_for_category(
        self,
        category: str,
        default_subtags: List[str],
        user_tags: List[str],
        placements: Dict[str, Any],
    ) -> List[str]:
        """
        Build ordered subtag list for a category: default tags + user tags by placement.
        User tags with placement "category" are appended; with "parent_tag" inserted after parent.
        Multiple passes ensure nested parent_tag (child of a user tag) is inserted after its parent.
        """
        result = list(dict.fromkeys(default_subtags))
        for ut in user_tags:
            pl = placements.get(ut)
            if pl is None:
                if category == "Miscellaneous:":
                    result.append(ut)
                continue
            if pl.get("category") == category:
                if ut not in result:
                    result.append(ut)
        # Multiple passes so tags with parent_tag are inserted after their parent (parent may be user tag)
        changed = True
        while changed:
            changed = False
            for ut in user_tags:
                pl = placements.get(ut)
                if pl is None or "parent_tag" not in pl:
                    continue
                parent = pl["parent_tag"]
                if parent in result and ut not in result:
                    idx = result.index(parent) + 1
                    result.insert(idx, ut)
                    changed = True
        return result

    def _load_tags_into_grid(self):
        """Load tags from JSON and user config into the tags grid."""
        while self.tags_grid_layout.count():
            item = self.tags_grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._category_buttons = {}
        self._subcategory_buttons = {}
        self._subcategory_containers = {}
        self._subcategory_tag_order = {}
        self._user_tag_buttons = {}
        self._subtag_to_category = {}

        self._user_tags_config = user_tags_config.load_config()
        placements = self._user_tags_config.get("placements", {})
        user_tags_list = sorted(self._get_user_tags())
        user_tags_set = self._get_user_tags()

        # Load default tags from JSON
        default_tags_path = Path(__file__).parent / "ressources" / "default_tags.json"
        if default_tags_path.exists():
            try:
                import json as _json
                with open(default_tags_path, "r", encoding="utf-8") as f:
                    default_tags = _json.load(f)

                def collect_subtags(data, collected: List[str]) -> None:
                    if isinstance(data, list):
                        for item in data:
                            collect_subtags(item, collected)
                    elif isinstance(data, dict):
                        for key, value in data.items():
                            collected.append(key)
                            collect_subtags(value, collected)
                    elif isinstance(data, str):
                        collected.append(data)

                categories_list = list(default_tags.items())
                max_cols = 3
                max_tags_per_row = 3
                current_row = 0
                for category_idx, (category, tags) in enumerate(categories_list):
                    is_label_category = category in ["Miscellaneous:", "Camera-Angle:"]
                    default_st: List[str] = []
                    collect_subtags(tags, default_st)
                    default_st = list(dict.fromkeys(default_st))
                    unique_subtags = self._build_subtags_for_category(
                        category, default_st, user_tags_list, placements
                    )
                    self._subcategory_tag_order[category] = list(unique_subtags)

                    row = current_row
                    if is_label_category:
                        category_label = QLabel(category)
                        category_label.setStyleSheet("font-weight: bold; font-size: 12px; padding: 4px; background-color: transparent;")
                        category_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                        self.tags_grid_layout.addWidget(category_label, row, 0, 1, max_cols)
                    else:
                        category_button = self._build_tag_button(category, is_user_tag=False)
                        category_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
                        category_button.clicked.connect(
                            lambda _, name=category: self._on_tag_button_clicked(name)
                        )
                        category_button.setProperty("tagGridRole", "category")
                        category_button.setProperty("tagGridKey", category)
                        self.tags_grid_layout.addWidget(category_button, row, 0, 1, max_cols)
                        self._category_buttons[category] = category_button

                    tag_container = QWidget()
                    tag_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
                    tag_container.setMinimumHeight(0)
                    tag_container_layout = QGridLayout(tag_container)
                    tag_container_layout.setContentsMargins(0, 0, 0, 0)
                    tag_container_layout.setSpacing(10)
                    subtag_buttons: Dict[str, QPushButton] = {}
                    for idx, tag in enumerate(unique_subtags):
                        is_user_tag = tag in user_tags_set
                        tag_button = self._build_tag_button(tag, is_user_tag=is_user_tag)
                        tag_name, category_name = tag, category
                        tag_button.clicked.connect(
                            lambda _=False, t=tag_name, c=category_name: self._on_tag_button_clicked(t, c)
                        )
                        tag_button.setProperty("tagGridRole", "tag")
                        tag_button.setProperty("tagGridKey", tag)
                        tag_button.contextMenuRequested.connect(self._on_tag_context_menu_requested)
                        tr, tc = idx // max_tags_per_row, idx % max_tags_per_row
                        tag_container_layout.addWidget(tag_button, tr, tc)
                        subtag_buttons[tag] = tag_button
                        self._subtag_to_category[tag] = category
                        tag_button.setVisible(is_label_category)

                    self.tags_grid_layout.addWidget(tag_container, row + 1, 0, 1, max_cols)
                    self._subcategory_containers[category] = tag_container
                    self._subcategory_buttons[category] = subtag_buttons

                    current_row = row + 2
                    if category_idx < len(categories_list) - 1:
                        separator = QFrame()
                        separator.setFrameShape(QFrame.Shape.HLine)
                        separator.setFrameShadow(QFrame.Shadow.Sunken)
                        separator.setStyleSheet("QFrame { color: #666; }")
                        self.tags_grid_layout.addWidget(separator, current_row, 0, 1, max_cols)
                        current_row += 1

            except Exception as e:
                print(f"Error loading default tags: {str(e)}")

        max_row = 0
        for i in range(self.tags_grid_layout.count()):
            item = self.tags_grid_layout.itemAt(i)
            if item:
                row, col, row_span, col_span = self.tags_grid_layout.getItemPosition(i)
                max_row = max(max_row, row + row_span - 1)
        if max_row >= 0:
            self.tags_grid_layout.setRowStretch(max_row + 1, 1)
        self._sync_tag_grid_state()


    def _build_tag_button(self, tag: str, is_user_tag: bool = False) -> QPushButton:
        """
        Build a tag button with icon and label.

        Args:
            tag: Tag name.
            is_user_tag: If True, tag can be renamed and repositioned (drag onto category/tag).

        Returns:
            QPushButton: Configured tag button.
        """
        button = DraggableTagButton(tag)
        button.setObjectName("TagGridButton")
        button.setProperty("userTag", is_user_tag)
        overrides = getattr(self, "_icon_preview_override", {})
        user_config = getattr(self, "_user_tags_config", {})
        icon = find_tag_icon(tag, user_config=user_config, icon_preview_override=overrides)
        if not icon.isNull():
            button.setIcon(invert_icon(icon, 28))
            button.setIconSize(QSize(28, 28))
        button.setCheckable(False)
        button.setStyleSheet(
            "QPushButton { text-align: left; padding: 2px 4px; }"
        )
        return button

    def _on_icon_preview(self, tag: str, icon_filename: Optional[str]) -> None:
        """Live preview: show the chosen icon on the tag button while the icon picker dialog is open."""
        self._icon_preview_override[tag] = icon_filename
        self._update_tag_button_icon(tag)

    def _update_tag_button_icon(self, tag: str) -> None:
        """
        Update the icon of the existing tag button for `tag` without rebuilding the grid.
        Keeps category expand/collapse state unchanged.
        """
        category = self._subtag_to_category.get(tag)
        if not category:
            return
        subtag_buttons = self._subcategory_buttons.get(category, {})
        btn = subtag_buttons.get(tag)
        if not btn:
            return
        overrides = getattr(self, "_icon_preview_override", {})
        user_config = getattr(self, "_user_tags_config", {})
        icon = find_tag_icon(tag, user_config=user_config, icon_preview_override=overrides)
        if not icon.isNull():
            btn.setIcon(invert_icon(icon, 28))
            btn.setIconSize(QSize(28, 28))
        else:
            btn.setIcon(QIcon())
            btn.setIconSize(QSize(28, 28))  # Keep size so layout does not jump

    def _on_tag_button_clicked(self, tag: str, category_override: Optional[str] = None) -> None:
        """
        Toggle tag in filters from tag buttons.

        Args:
            tag: Tag name to toggle.
            category_override: When set, use this category (for tags that appear in multiple categories, e.g. Weapon).
        """
        # Label categories are not real tags and should never be added to active categories
        label_categories = ["Miscellaneous:", "Camera-Angle:"]

        if tag in self._category_buttons:
            if tag in self._active_categories:
                self._active_categories.remove(tag)
                self._active_subtags.pop(tag, None)
            else:
                self._active_categories.add(tag)
                self._active_subtags.setdefault(tag, set())
        else:
            category = category_override if category_override is not None else self._subtag_to_category.get(tag)
            if not category:
                return
            
            # For label categories, don't add them to active_categories
            # Just manage their sub-tags directly
            if category in label_categories:
                category_tags = self._active_subtags.setdefault(category, set())
                if tag in category_tags:
                    category_tags.remove(tag)
                    # If no more tags in this label category, remove it from active_subtags
                    if not category_tags:
                        self._active_subtags.pop(category, None)
                else:
                    category_tags.add(tag)
            else:
                # For regular categories, add category to active_categories if needed
                if category not in self._active_categories:
                    self._active_categories.add(category)
                category_tags = self._active_subtags.setdefault(category, set())
                if tag in category_tags:
                    category_tags.remove(tag)
                else:
                    category_tags.add(tag)
        self._apply_category_filters()
        self._sync_tag_grid_state()

    def _on_tag_search_return(self) -> None:
        """Handle tag search input return key press (only for user tags)."""
        text = self.tag_search_input.text().strip()
        if not text:
            return
        
        # Resolve tag (case-insensitive) - only in user tags
        user_tags = self._get_user_tags()
        resolved_tag = None
        text_lower = text.lower()
        for tag in user_tags:
            if tag.lower() == text_lower:
                resolved_tag = tag
                break
        
        if not resolved_tag:
            # Invalid tag - could add feedback animation here
            self.tag_search_input.clear()
            return
        
        # Add to AND zone by default
        self.and_zone.add_tag(resolved_tag)
        self.tag_search_input.clear()
        self._apply_category_filters()
    
    def _on_tag_filter_changed(self, tag: str = None) -> None:
        """
        Handle tag filter change from AND/OR zones.
        
        Args:
            tag: Tag that was added/removed (optional, for tag_dropped signal).
        """
        self._apply_category_filters()
        self._sync_tag_grid_state()
    
    def _clear_all_tag_filters(self) -> None:
        """Clear all tag filters (category, AND, and OR)."""
        self._active_categories.clear()
        self._active_subtags.clear()
        self.and_zone.clear_tags()
        self.or_zone.clear_tags()
        self._apply_category_filters()
        self._sync_tag_grid_state()

    def _on_tag_context_menu_requested(self, tag_text: str) -> None:
        """Show context menu for tag button; only user tags get Rename and Change icon."""
        user_tags = self._get_user_tags()
        if tag_text not in user_tags:
            return
        menu = QMenu(self)
        rename_action = menu.addAction("Rename...")
        change_icon_action = menu.addAction("Change icon...")
        action = menu.exec_(QCursor.pos())
        if action == change_icon_action:
            cfg = self._user_tags_config
            current = cfg.get("icons", {}).get(tag_text)
            dialog = IconPickerDialog(
                self,
                current_icon=current,
                on_icon_changed=lambda filename: self._on_icon_preview(tag_text, filename),
            )
            result = dialog.exec_()
            # Clear preview override so _update_tag_button_icon uses config again
            self._icon_preview_override.pop(tag_text, None)
            if result == QDialog.DialogCode.Accepted:
                icons = dict(cfg.get("icons", {}))
                chosen = dialog.get_icon_filename()
                if chosen:
                    icons[tag_text] = chosen
                else:
                    icons.pop(tag_text, None)
                user_tags_config.save_config(
                    cfg.get("placements", {}),
                    icons,
                    cfg.get("registered_only"),
                )
                self._user_tags_config = user_tags_config.load_config()
            # Restore or apply final icon from config (revert on Cancel, keep on OK)
            self._update_tag_button_icon(tag_text)
            return
        if action == rename_action:
            new_name, ok = QInputDialog.getText(
                self, "Rename tag", "New name:", text=tag_text
            )
            if ok and new_name and new_name.strip() and new_name.strip() != tag_text:
                new_name = new_name.strip()
                default_tags = self._get_default_tags()
                if new_name in default_tags:
                    QMessageBox.warning(
                        self,
                        "Rename tag",
                        "This name is reserved for a default tag.",
                    )
                    return
                n = self.image_manager.db.rename_tag(tag_text, new_name)
                cfg = self._user_tags_config
                placements = cfg.get("placements", {})
                icons = cfg.get("icons", {})
                user_tags_config.rename_in_config(placements, icons, tag_text, new_name)
                ro = cfg.get("registered_only", [])
                if tag_text in ro:
                    ro = [new_name if t == tag_text else t for t in ro]
                user_tags_config.save_config(placements, icons, ro)
                self._user_tags_config = user_tags_config.load_config()
                self._load_tags_into_grid()
                self._update_tag_search_completer()
                self._apply_category_filters()
                self._sync_tag_grid_state()
                QMessageBox.information(
                    self,
                    "Rename tag",
                    f"Tag renamed on {n} image(s).",
                )

    def _on_tag_grid_drop(self, event: "QDropEvent") -> None:
        """Reposition a user tag when dropped on a category or tag in the grid."""
        if not event.mimeData().hasFormat(TAG_LIBRARY_MIME):
            return
        raw = event.mimeData().data(TAG_LIBRARY_MIME)
        dropped_tag = bytes(raw).decode("utf-8") if raw else ""
        if dropped_tag not in self._get_user_tags():
            return
        pos = event.position().toPoint() if hasattr(event.position(), "toPoint") else event.pos()
        child = self.tags_grid_container.childAt(pos)
        while child and child != self.tags_grid_container and not child.property("tagGridRole"):
            child = child.parentWidget() if hasattr(child, "parentWidget") else None
        if not child or not child.property("tagGridRole"):
            return
        role = child.property("tagGridRole")
        key = child.property("tagGridKey")
        if dropped_tag == key:
            return
        if role == "category":
            placement = {"category": key}
        elif role == "tag":
            placement = {"parent_tag": key}
        else:
            return
        cfg = self._user_tags_config
        placements = dict(cfg.get("placements", {}))
        placements[dropped_tag] = placement
        user_tags_config.save_config(
            placements,
            cfg.get("icons", {}),
            cfg.get("registered_only"),
        )
        self._user_tags_config = user_tags_config.load_config()
        self._load_tags_into_grid()
        self._sync_tag_grid_state()

    def _on_add_user_tag_clicked(self) -> None:
        """Open dialog to add a new user tag (name + optional icon)."""
        dialog = AddTagDialog(self)
        if dialog.exec_() != QDialog.DialogCode.Accepted:
            return
        tag_name = dialog.get_tag_name()
        icon_file = dialog.get_icon_filename()
        if not tag_name or not tag_name.strip():
            return
        tag_name = tag_name.strip()
        default_tags = self._get_default_tags()
        if tag_name in default_tags:
            QMessageBox.warning(self, "Add tag", "This name is reserved for a default tag.")
            return
        user_tags = self._get_user_tags()
        if tag_name in user_tags:
            QMessageBox.information(self, "Add tag", "This tag already exists.")
            return
        cfg = getattr(self, "_user_tags_config", user_tags_config.load_config())
        self._user_tags_config = cfg
        placements = dict(cfg.get("placements", {}))
        icons = dict(cfg.get("icons", {}))
        registered = list(cfg.get("registered_only", []))
        placements[tag_name] = {"category": "Miscellaneous:"}
        if icon_file:
            icons[tag_name] = icon_file
        if tag_name not in registered:
            registered.append(tag_name)
        user_tags_config.save_config(placements, icons, registered)
        self._user_tags_config = user_tags_config.load_config()
        self._load_tags_into_grid()
        self._update_tag_search_completer()
        self._sync_tag_grid_state()

    def _update_tag_search_completer(self) -> None:
        """Update the tag search completer with current user tags."""
        user_tags = list(self._get_user_tags())
        completer = QCompleter()
        completer.setModel(QStringListModel(user_tags))
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        self.tag_search_input.setCompleter(completer)
        self.tag_search_completer = completer
    
    def reload_default_tags(self) -> None:
        """
        Reload default tags from JSON file and refresh the tag grid.
        Useful when default_tags.json is modified.
        """
        # Clear current filters to avoid inconsistencies
        self._active_categories.clear()
        self._active_subtags.clear()
        
        # Reload tags into grid
        self._load_tags_into_grid()
        
        # Update completer with new user tags
        self._update_tag_search_completer()
        
        # Reapply filters (will be empty, so shows all images)
        self._apply_category_filters()

    def _get_children_of_tag(self, tag: str) -> List[str]:
        """Return list of tags whose placement has parent_tag = tag (tags that belong to this sub-category)."""
        placements = self._user_tags_config.get("placements", {})
        return [
            t for t, pl in placements.items()
            if isinstance(pl, dict) and pl.get("parent_tag") == tag
        ]

    def _sync_tag_grid_state(self) -> None:
        """
        Sync tag grid button states with active filters.
        Child tags (placement parent_tag) are only visible when the parent tag is selected.
        When a selected tag is a sub-category (has children), its row is shown first, then
        its children on the next row(s), then the rest. Rebuilds each category's tag container
        layout with only visible tags so the grid has no holes.
        """
        max_cols = 3
        placements = self._user_tags_config.get("placements", {})
        for category, button in self._category_buttons.items():
            is_active = category in self._active_categories
            self._set_button_active(button, is_active)
            category_subtags = self._active_subtags.get(category, set())
            for tag, tag_button in self._subcategory_buttons.get(category, {}).items():
                pl = placements.get(tag)
                parent_tag = pl.get("parent_tag") if isinstance(pl, dict) else None
                if parent_tag is not None:
                    tag_button.setVisible(is_active and parent_tag in category_subtags)
                else:
                    tag_button.setVisible(is_active)
                self._set_button_active(tag_button, tag in category_subtags)

        # Label categories: set visibility
        label_categories = ["Miscellaneous:", "Camera-Angle:"]
        for label_category in label_categories:
            if label_category in self._subcategory_buttons:
                label_subtags = self._active_subtags.get(label_category, set())
                for tag, tag_button in self._subcategory_buttons[label_category].items():
                    pl = placements.get(tag)
                    parent_tag = pl.get("parent_tag") if isinstance(pl, dict) else None
                    if parent_tag is not None:
                        tag_button.setVisible(parent_tag in label_subtags)
                    else:
                        tag_button.setVisible(True)
                    self._set_button_active(tag_button, tag in label_subtags)

        # Rebuild each category container with only visible tags (no holes).
        # When a selected tag is a sub-category (has children), show it first then its children on the next row(s), then the rest.
        label_categories_set = {"Miscellaneous:", "Camera-Angle:"}
        for category in self._subcategory_tag_order:
            if category in label_categories_set:
                continue
            container = self._subcategory_containers.get(category)
            if not container:
                continue
            layout = container.layout()
            if not layout:
                continue
            while layout.count():
                layout.takeAt(0)
            tag_order = self._subcategory_tag_order[category]
            category_subtags = self._active_subtags.get(category, set())
            subtag_buttons = self._subcategory_buttons.get(category, {})
            # Clear child-row style from all buttons; will set only on children when expanded
            for btn in subtag_buttons.values():
                btn.setProperty("tagChildRow", "false")
                btn.style().unpolish(btn)
                btn.style().polish(btn)

            expanded_parent = None
            for t in category_subtags:
                if self._get_children_of_tag(t):
                    expanded_parent = t
                    break
            if expanded_parent is not None and expanded_parent in tag_order:
                idx_t = tag_order.index(expanded_parent)
                before = tag_order[:idx_t]
                after = tag_order[idx_t + 1:]
                children = [c for c in self._get_children_of_tag(expanded_parent) if c in tag_order]
                rest = [x for x in after if x not in children]
                # Segment 1: before + sub-category (stays in place)
                # Then new row → Segment 2: children (slightly blue)
                # Then new row → Segment 3: rest
                idx = 0
                for tag in before + [expanded_parent]:
                    btn = subtag_buttons.get(tag)
                    if btn and btn.isVisible():
                        row, col = idx // max_cols, idx % max_cols
                        layout.addWidget(btn, row, col)
                        idx += 1
                # Force next row before children
                idx = ((idx + max_cols - 1) // max_cols) * max_cols
                for tag in children:
                    btn = subtag_buttons.get(tag)
                    if btn and btn.isVisible():
                        row, col = idx // max_cols, idx % max_cols
                        layout.addWidget(btn, row, col)
                        btn.setProperty("tagChildRow", "true")
                        btn.style().unpolish(btn)
                        btn.style().polish(btn)
                        idx += 1
                # Force next row before rest
                idx = ((idx + max_cols - 1) // max_cols) * max_cols
                for tag in rest:
                    btn = subtag_buttons.get(tag)
                    if btn and btn.isVisible():
                        row, col = idx // max_cols, idx % max_cols
                        layout.addWidget(btn, row, col)
                        idx += 1
            else:
                idx = 0
                for tag in tag_order:
                    btn = subtag_buttons.get(tag)
                    if btn and btn.isVisible():
                        row, col = idx // max_cols, idx % max_cols
                        layout.addWidget(btn, row, col)
                        idx += 1

    @staticmethod
    def _normalize_tag_for_match(tag: str) -> str:
        """
        Normalize tag for case- and separator-insensitive comparison.
        e.g. "Wide-Angle", "wideAngle", "wide angle" all become "wideangle".
        """
        if not tag:
            return ""
        return tag.lower().replace(" ", "").replace("-", "").replace("_", "")

    def _filter_images_by_category(self) -> List:
        """
        Filter images by category (OR) and sub-tags (AND within category).
        Label categories (e.g. Camera-Angle) are applied as a global AND constraint:
        e.g. Human + Wide-Angle => images that are Human AND Wide-Angle.
        Tag matching is case- and separator-insensitive (Wide-Angle matches wideAngle, etc.).
        """
        # Get current sort order and apply it
        sort_by = self._get_current_sort_order()
        all_images = self.image_manager.db.list_images(sort_by)

        # Label categories are not real tags; their sub-tags constrain all category results (AND)
        label_categories = ["Miscellaneous:", "Camera-Angle:"]
        constraining_tags: Set[str] = set()
        for label_cat in label_categories:
            constraining_tags.update(self._active_subtags.get(label_cat, set()))

        # Check if there are any active filters (regular categories or constraining tags)
        has_active_filters = bool(self._active_categories) or bool(constraining_tags)
        if not has_active_filters:
            return all_images

        constraining_normalized = {self._normalize_tag_for_match(t) for t in constraining_tags}

        # Step 1: images matching at least one active regular category (with its sub-tags)
        if self._active_categories:
            category_matched = []
            for metadata in all_images:
                image_tags_norm = {self._normalize_tag_for_match(t) for t in metadata.tags}
                for category in self._active_categories:
                    if self._normalize_tag_for_match(category) not in image_tags_norm:
                        continue
                    required = self._active_subtags.get(category, set())
                    required_norm = {self._normalize_tag_for_match(t) for t in required}
                    if required_norm.issubset(image_tags_norm):
                        category_matched.append(metadata)
                        break
        else:
            # No category selected: start from all images (then apply constraining tags only)
            category_matched = list(all_images)

        # Step 2: apply constraining tags (label categories) as global AND
        if not constraining_normalized:
            return category_matched
        filtered_images = [
            m for m in category_matched
            if constraining_normalized.issubset({self._normalize_tag_for_match(t) for t in m.tags})
        ]
        return filtered_images

    def _set_button_active(self, button: QPushButton, active: bool) -> None:
        """
        Apply active styling to a tag button via property so QSS applies highlight.
        """
        button.setProperty("tagActive", "true" if active else "false")
        button.style().unpolish(button)
        button.style().polish(button)
        button.update()
    
    # Tree-based tag handling removed in favor of button grid.
    
    def _setup_dev_tools(self):
        """Set up development tools dock widget."""
        # Create dock widget for dev tools
        self.dev_dock = QDockWidget("Development Log", self)
        self.dev_dock.setAllowedAreas(Qt.BottomDockWidgetArea)
        self.dev_dock.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetFloatable)
        
        # Create widget for dock content
        dev_widget = QWidget()
        dev_layout = QVBoxLayout(dev_widget)
        
        # Add progress section
        progress_layout = QVBoxLayout()
        self.dev_progress_label = QLabel("No import in progress")
        self.dev_progress_bar = QProgressBar()
        self.dev_progress_bar.setVisible(False)
        progress_layout.addWidget(self.dev_progress_label)
        progress_layout.addWidget(self.dev_progress_bar)
        dev_layout.addLayout(progress_layout)
        
        # Add log text area
        self.dev_log = QTextEdit()
        self.dev_log.setReadOnly(True)
        self.dev_log.setLineWrapMode(QTextEdit.NoWrap)
        self.dev_log.setStyleSheet("""
            QTextEdit {
                font-family: monospace;
                background-color: #1e1e1e;
                color: #d4d4d4;
            }
        """)
        dev_layout.addWidget(self.dev_log)
        
        # Set dock widget content
        self.dev_dock.setWidget(dev_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dev_dock)
        
        # Initially hide dock
        self.dev_dock.setVisible(self.dev_mode)
    
    @Slot(str)
    def update_status_message(self, message: str):
        """Update status bar message from any thread."""
        self.statusBar().showMessage(message)
    
    @Slot(int)
    def update_progress_bar(self, progress: int):
        """Update progress bar value from any thread."""
        if hasattr(self, 'current_progress_bar'):
            self.current_progress_bar.setValue(progress)
    
    @Slot(str)
    def update_dev_progress_label(self, text: str):
        """Update dev progress label from any thread."""
        if self.dev_mode and hasattr(self, 'dev_progress_label'):
            self.dev_progress_label.setText(text)
    
    @Slot(int)
    def update_dev_progress_bar(self, progress: int):
        """Update dev progress bar from any thread."""
        if self.dev_mode and hasattr(self, 'dev_progress_bar'):
            self.dev_progress_bar.setVisible(True)
            self.dev_progress_bar.setValue(progress)
    
    @Slot(str, str)
    def add_log_message(self, message: str, level: str = "INFO"):
        """Add a log message from any thread."""
        if self.dev_mode:
            self._log_message(message, level)
    
    def _log_message(self, message: str, level: str = "INFO"):
        """
        Log a message to the dev log.
        
        Args:
            message: Message to log
            level: Log level (INFO, WARNING, ERROR)
        """
        if not hasattr(self, 'dev_log'):
            return
            
        # Format message with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {level}: {message}"
        
        # Add color based on level
        color = {
            "INFO": "#d4d4d4",
            "WARNING": "#dcdcaa",
            "ERROR": "#f14c4c"
        }.get(level, "#d4d4d4")
        
        # Add to log
        self.dev_log.append(f'<span style="color: {color}">{formatted}</span>')
        
        # Scroll to bottom
        self.dev_log.verticalScrollBar().setValue(
            self.dev_log.verticalScrollBar().maximum()
        )

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter events for file drops."""
        if event.mimeData().hasUrls():
            # Accept both files and directories
            urls = event.mimeData().urls()
            for url in urls:
                path = Path(url.toLocalFile())
                if path.is_dir() or path.suffix.lower() in ImageManager.SUPPORTED_FORMATS:
                    event.acceptProposedAction()
                    return
    
    def dropEvent(self, event: QDropEvent):
        """Handle file drop events."""
        self._import_from_urls(event.mimeData().urls())
        event.acceptProposedAction()

    def closeEvent(self, event):
        """Flush pending image DB save before closing so no changes are lost."""
        if hasattr(self, "image_manager") and self.image_manager is not None:
            self.image_manager.db.flush_pending_save()
        super().closeEvent(event)

    def _import_from_urls(self, urls: List[QUrl]):
        """Import images from dropped URLs (files/folders). Used by main window drop and by grid/thumbnail forward."""
        paths = []
        for url in urls:
            path = Path(url.toLocalFile())
            if path.is_dir() or path.suffix.lower() in ImageManager.SUPPORTED_FORMATS:
                paths.append(path)
        if paths:
            self._import_images(paths)

    def _create_status_progress_bar(self):
        """Create and set up the status bar progress bar."""
        # Remove any existing progress bar
        self._cleanup_progress_bars()
        
        # Create new progress bar
        progress_bar = QProgressBar()
        progress_bar.setMinimumWidth(400)
        progress_bar.setMinimumHeight(20)
        progress_bar.setMaximumHeight(20)
        progress_bar.setTextVisible(True)
        progress_bar.setFormat("Preparing import...")
        
        # Add to status bar with permanent widget (stays on the right)
        self.statusBar().addPermanentWidget(progress_bar)
        self.status_progress_bar = progress_bar
        return progress_bar

    def _cleanup_progress_bars(self):
        """Clean up all progress bars."""
        try:
            # Clean up main progress bar
            if self.status_progress_bar is not None:
                self.statusBar().removeWidget(self.status_progress_bar)
                self.status_progress_bar.deleteLater()
                self.status_progress_bar = None
            
            # Clean up dev progress bar
            if self.dev_mode and hasattr(self, 'dev_progress_bar'):
                self.dev_progress_bar.setVisible(False)
                self.dev_progress_bar.setValue(0)
                self.dev_progress_label.setText("No import in progress")
        except Exception as e:
            print(f"Error during cleanup: {e}")

    def _count_images_to_import(self, paths: List[Path]) -> Tuple[List[Path], Optional[Path]]:
        """
        Count images to import and get the first image path for preview.
        
        Args:
            paths: List of paths to check
            
        Returns:
            Tuple of (list of image paths, first image path for preview)
        """
        all_images = []
        first_image = None
        
        for path in paths:
            try:
                if path.is_dir():
                    found_images = self.image_manager.find_images_in_directory(path)
                    all_images.extend(found_images)
                    if first_image is None and found_images:
                        first_image = found_images[0]
                else:
                    if path.suffix.lower() in ImageManager.SUPPORTED_FORMATS:
                        all_images.append(path)
                        if first_image is None:
                            first_image = path
            except Exception as e:
                print(f"Error scanning path {path}: {str(e)}")
        
        return all_images, first_image
    
    def _import_images(self, paths: List[Path]):
        """
        Import images from paths.
        
        Args:
            paths: List of paths to import
        """
        # Count images and get first image for preview
        image_paths, first_image_path = self._count_images_to_import(paths)
        
        if not image_paths:
            QMessageBox.warning(
                self,
                "No Images Found",
                "No valid images found to import."
            )
            return
        
        # Show import dialog
        from gui.import_dialog import ImportDialog
        dialog = ImportDialog(
            self,
            image_manager=self.image_manager,
            image_paths=image_paths,
            first_image_path=first_image_path
        )
        
        if dialog.exec_() != QDialog.Accepted:
            return
        
        # Get selected tags
        selected_tags = dialog.get_selected_tags()
        
        # Create progress bar in status bar
        progress_bar = self._create_status_progress_bar()
        
        # Create and configure worker with tags
        worker = ImageImportWorker(self.image_manager, image_paths, selected_tags)
        
        # Connect signals with queued connections to ensure thread safety
        worker.signals.progress.connect(
            lambda current, total: self._handle_progress_update(current, total),
            Qt.QueuedConnection
        )
        
        worker.signals.log.connect(
            self.add_log_message,
            Qt.QueuedConnection
        )
        
        # Connect finished signal with explicit slot
        worker.signals.finished.connect(
            self._handle_import_finished,
            Qt.QueuedConnection
        )
        
        worker.signals.error.connect(
            self._handle_import_error,
            Qt.QueuedConnection
        )
        worker.signals.image_imported.connect(
            self._on_image_imported,
            Qt.QueuedConnection
        )
        
        # Start worker
        if self.dev_mode:
            self.update_dev_progress_label("Starting import...")
            self.update_dev_progress_bar(0)
        else:
            self.statusBar().showMessage("Starting image import...")
        
        # Start worker and keep a reference to prevent garbage collection
        self.current_worker = worker
        self.thread_pool.start(worker)

    # === Bulk tag application (for drag & drop onto many images) ===

    def apply_tag_to_images_async(self, tag: str, image_ids: List[str]) -> None:
        """
        Apply a tag to many images in a background thread with progress.

        Args:
            tag: Tag to apply.
            image_ids: List of image IDs to update.
        """
        if not image_ids:
            return

        # Create progress bar in status bar
        progress_bar = self._create_status_progress_bar()
        progress_bar.setFormat(f"Applying tag '{tag}'...")

        worker = TagApplyWorker(self.image_manager, image_ids, tag)

        # Progress updates
        worker.signals.progress.connect(
            lambda current, total: self._handle_tag_apply_progress(tag, current, total),
            Qt.QueuedConnection,
        )

        # Completion
        worker.signals.finished.connect(
            lambda total: self._handle_tag_apply_finished(tag, image_ids, total),
            Qt.QueuedConnection,
        )

        # Errors
        worker.signals.error.connect(
            self._handle_tag_apply_error,
            Qt.QueuedConnection,
        )

        # Start worker
        self.statusBar().showMessage(f"Applying tag '{tag}' to images...")
        self.current_worker = worker
        self.thread_pool.start(worker)

    def _handle_tag_apply_progress(self, tag: str, current: int, total: int) -> None:
        """Update progress bar while applying tags."""
        if total <= 0:
            return
        progress = int(current * 100 / total)

        if self.status_progress_bar is not None:
            self.status_progress_bar.setValue(progress)
            self.status_progress_bar.setFormat(
                f"Applying tag '{tag}': {current}/{total} ({progress}%)"
            )

        if self.dev_mode:
            self.update_dev_progress_bar(progress)
            self.update_dev_progress_label(
                f"Applying tag '{tag}': {current}/{total} images updated"
            )

    def _handle_tag_apply_finished(
        self, tag: str, image_ids: List[str], total: int
    ) -> None:
        """Handle completion of tag application; refresh thumbnails in batches to keep UI responsive."""
        try:
            if self.status_progress_bar is not None:
                self.status_progress_bar.setValue(100)
                self.status_progress_bar.setFormat(
                    f"Applying tag '{tag}': completed"
                )
                self.status_progress_bar.repaint()

            # Clean up progress bar
            self._cleanup_progress_bars()

            # Refresh only thumbnails that exist in the grid (visible pool or loaded set)
            to_refresh = [
                image_id
                for image_id in image_ids
                if image_id in self.image_grid.thumbnails
            ]
            if not to_refresh:
                return
            # Process in batches so the event loop can run between batches (no UI freeze)
            batch_size = 20
            index_holder = [0]  # mutable so closure can update

            def process_next_batch() -> None:
                start = index_holder[0]
                end = min(start + batch_size, len(to_refresh))
                grid_thumbnails = self.image_grid.thumbnails
                for i in range(start, end):
                    image_id = to_refresh[i]
                    if image_id in grid_thumbnails:
                        grid_thumbnails[image_id].refresh_tags()
                index_holder[0] = end
                if end < len(to_refresh):
                    QTimer.singleShot(0, process_next_batch)

            QTimer.singleShot(0, process_next_batch)
        except Exception:
            self._cleanup_progress_bars()

    def _handle_tag_apply_error(self, error_msg: str) -> None:
        """Handle error during tag application."""
        self._cleanup_progress_bars()
        self.add_log_message(f"Error while applying tag: {error_msg}", "ERROR")

    def _handle_tag_remove_progress(self, tag: str, current: int, total: int) -> None:
        """Update progress bar while removing tag (worker runs in grid)."""
        if total <= 0:
            return
        if self.status_progress_bar is None:
            self._create_status_progress_bar()
            self.status_progress_bar.setFormat(f"Removing tag '{tag}'...")
        progress = int(current * 100 / total)
        self.status_progress_bar.setValue(progress)
        self.status_progress_bar.setFormat(
            f"Removing tag '{tag}': {current}/{total} ({progress}%)"
        )
        if self.dev_mode:
            self.update_dev_progress_bar(progress)
            self.update_dev_progress_label(
                f"Removing tag '{tag}': {current}/{total} images updated"
            )

    def _handle_tag_remove_finished(
        self, tag: str, image_ids: List[str], total: int
    ) -> None:
        """Handle completion of tag removal (thumbnails refreshed by grid)."""
        try:
            if self.status_progress_bar is not None:
                self.status_progress_bar.setValue(100)
                self.status_progress_bar.setFormat(
                    f"Removing tag '{tag}': completed"
                )
                self.status_progress_bar.repaint()
            self._cleanup_progress_bars()
        except Exception:
            self._cleanup_progress_bars()

    def _handle_tag_remove_error(self, error_msg: str) -> None:
        """Handle error during tag removal."""
        self._cleanup_progress_bars()
        self.add_log_message(f"Error while removing tag: {error_msg}", "ERROR")

    def _handle_progress_update(self, current: int, total: int):
        """Handle progress update from worker thread."""
        progress = int(current * 100 / total)
        
        # Update main progress bar
        if self.status_progress_bar is not None:
            self.status_progress_bar.setValue(progress)
            self.status_progress_bar.setFormat(f"Importing: {current}/{total} ({progress}%)")
        
        # Update dev mode progress
        if self.dev_mode:
            self.update_dev_progress_bar(progress)
            self.update_dev_progress_label(f"Importing: {current}/{total} images processed")
    
    def _on_image_imported(self, image_id: str) -> None:
        """Add the newly imported image at the top of the grid (no full refresh)."""
        meta = self.image_manager.get_image_metadata(image_id)
        if meta:
            self.image_grid.prepend_image(meta)

    def _handle_import_finished(self, successful: int, duplicates: int, total: int):
        """Handle import completion from worker thread."""
        try:
            # Update final progress before cleanup
            if self.status_progress_bar is not None:
                self.status_progress_bar.setValue(100)
                self.status_progress_bar.setFormat("Import completed")
                # Force the progress bar to update
                self.status_progress_bar.repaint()
            
            # Show result message first
            if successful == 0:
                if duplicates == total:
                    msg = f"All {total} images were already imported"
                    self.add_log_message(msg, "WARNING")
                    self.update_status_message(msg)
                else:
                    msg = "Failed to import any images. Please check the file formats"
                    self.add_log_message(msg, "ERROR")
                    self.update_status_message(msg)
            else:
                message = f"Successfully imported {successful} out of {total} images"
                if duplicates > 0:
                    message += f" ({duplicates} duplicates skipped)"
                self.update_status_message(message)
            
            # Update dev UI
            if self.dev_mode:
                self.update_dev_progress_label("Import completed")
            
            # Force UI update
            QThread.msleep(100)  # Give time for UI to update
            
            # Clean up all progress bars
            self._cleanup_progress_bars()
            # Refresh grid once at end of import
            self._apply_category_filters()
            self._update_available_tags()
            
        except Exception as e:
            print(f"Error in import finished handler: {e}")
            self._cleanup_progress_bars()
    
    def _handle_import_error(self, error_msg: str):
        """Handle import error from worker thread."""
        try:
            # Clean up all progress bars
            self._cleanup_progress_bars()
            
            # Update dev UI
            if self.dev_mode:
                self.update_dev_progress_label("Import failed")
            
            # Show error message
            msg = f"Error importing images: {error_msg}"
            self.add_log_message(msg, "ERROR")
            self.update_status_message(msg)
            
        except Exception as e:
            print(f"Error in error handler: {e}")
            self._cleanup_progress_bars()
    
    def _on_import_images(self):
        """Handle image import action."""
        formats = " ".join(f"*{fmt}" for fmt in ImageManager.SUPPORTED_FORMATS)
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Import Images",
            "",
            f"Images ({formats})"
        )
        
        if paths:
            self._import_images([Path(p) for p in paths])
    
    def _on_import_folder(self):
        """Handle folder import action."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Import Folder",
            ""
        )
        
        if folder:
            self._import_images([Path(folder)])
    
    def _setup_menu(self):
        """Set up the menu bar."""
        # File menu
        file_menu = self.menuBar().addMenu("&File")
        # Set minimum width to prevent text overlap with keyboard shortcuts
        file_menu.setMinimumWidth(220)
        
        # - Import images
        import_action = QAction("Import Images", self)
        import_action.setShortcut("Ctrl+I")
        import_action.triggered.connect(self._on_import_images)
        file_menu.addAction(import_action)
        
        # - Import folder
        import_folder_action = QAction("Import Folder", self)
        import_folder_action.setShortcut("Ctrl+F")
        import_folder_action.triggered.connect(self._on_import_folder)
        file_menu.addAction(import_folder_action)
        
        file_menu.addSeparator()
        
        # - Settings
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self._show_settings)
        file_menu.addAction(settings_action)
        
        file_menu.addSeparator()
        
        # - Exit
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = self.menuBar().addMenu("&View")
        
        # - Theme submenu
        theme_menu = QMenu("&Theme", self)
        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)
        
        light_theme_action = QAction("&Light", self)
        light_theme_action.setCheckable(True)
        light_theme_action.triggered.connect(lambda: self._set_theme("light"))
        theme_group.addAction(light_theme_action)
        
        dark_theme_action = QAction("&Dark", self)
        dark_theme_action.setCheckable(True)
        dark_theme_action.triggered.connect(lambda: self._set_theme("dark"))
        theme_group.addAction(dark_theme_action)
        
        # Set initial check state
        if settings.get("ui.theme") == "dark":
            dark_theme_action.setChecked(True)
        else:
            light_theme_action.setChecked(True)
        
        theme_menu.addAction(light_theme_action)
        theme_menu.addAction(dark_theme_action)
        view_menu.addMenu(theme_menu)
        
        # Tools menu
        tools_menu = self.menuBar().addMenu("&Tools")
        
        # - Dev mode toggle
        dev_mode_action = QAction("Enable &Developer Mode", self)
        dev_mode_action.setCheckable(True)
        dev_mode_action.setChecked(self.dev_mode)
        dev_mode_action.triggered.connect(self._toggle_dev_mode)
        tools_menu.addAction(dev_mode_action)
        
        # - Purge library (only visible in dev mode)
        self.purge_action = QAction("&Purge Image Library...", self)
        self.purge_action.triggered.connect(self._purge_library)
        self.purge_action.setVisible(self.dev_mode)
        tools_menu.addAction(self.purge_action)
        
        # - Reload default tags
        reload_tags_action = QAction("&Reload Default Tags", self)
        reload_tags_action.triggered.connect(self.reload_default_tags)
        tools_menu.addAction(reload_tags_action)
        
        # Help menu
        help_menu = self.menuBar().addMenu("&Help")
        
        # - About
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _setup_statusbar(self):
        """Set up the status bar."""
        status_bar = self.statusBar()
        status_bar.setMinimumHeight(24)  # Ensure status bar is tall enough
        status_bar.showMessage("Ready")
    
    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About SketchBook",
            "SketchBook - A desktop application for timed life drawing sessions.\n\n"
            "Version: 0.1.0"
        )
    
    def _show_settings(self):
        """Show settings dialog."""
        from gui.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self)
        # Store current theme before dialog opens
        old_theme = settings.get("ui.theme", "dark")
        if dialog.exec_() == QDialog.Accepted:
            # Apply theme (settings are already saved by dialog.accept())
            new_theme = settings.get("ui.theme", "dark")
            if new_theme != old_theme:
                # Apply the theme immediately
                apply_global_stylesheet()
    
    def _set_theme(self, theme: str):
        """
        Set application theme.
        
        Args:
            theme: Theme name ('light' or 'dark')
        """
        settings.set("ui.theme", theme)
        settings.save()
        apply_global_stylesheet()
        # Styles are now handled by global QSS, no need to call individual _apply_theme methods
    
    def _apply_theme(self):
        """Apply the current theme from settings."""
        apply_global_stylesheet()
    
    def _toggle_dev_mode(self, enabled: bool):
        """
        Toggle developer mode.
        
        Args:
            enabled: Whether dev mode should be enabled
        """
        self.dev_mode = enabled
        settings.set("ui.dev_mode", enabled)
        settings.save()
        
        # Update UI
        self.purge_action.setVisible(enabled)
        self.dev_dock.setVisible(enabled)
        
        # Show status message
        self.statusBar().showMessage(
            "Developer mode enabled" if enabled else "Developer mode disabled",
            3000  # Show for 3 seconds
        )
        
        if enabled:
            self.add_log_message("Developer mode enabled")
    
    def _purge_library(self):
        """Purge the entire image library."""
        if not self.dev_mode:
            return
            
        result = QMessageBox.warning(
            self,
            "Purge Library",
            "This will delete ALL images and metadata from the library.\n"
            "This action cannot be undone!\n\n"
            "Are you sure you want to continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result == QMessageBox.Yes:
            try:
                # Delete all image files
                from core.user_data import user_data
                image_dir = user_data.get_images_dir()
                if image_dir.exists():
                    for file in image_dir.glob("*"):
                        if file.is_file() and file.suffix.lower() in ImageManager.SUPPORTED_FORMATS:
                            file.unlink()
                
                # Clear metadata database
                self.image_manager.db._images = {}
                self.image_manager.db._save_db()
                
                QMessageBox.information(
                    self,
                    "Library Purged",
                    "The image library has been successfully purged."
                )
                
                self.statusBar().showMessage("Library purged successfully")
                self._apply_category_filters()
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Purge Error",
                    f"Error purging library: {str(e)}"
                )

    def _on_columns_changed(self, value: int):
        """Handle column slider value changes and persist to user settings."""
        self.columns_count.setText(str(value))
        self.image_grid.set_columns(value)
        settings.set("ui.grid.columns", value)
        settings.save()

    def _on_image_clicked(self, image_id: str):
        """Open the image in a large viewer window."""
        if self._image_viewer_window is None:
            self._image_viewer_window = ImageViewerWindow(self.image_manager, self)
        if self._image_viewer_window.set_image(image_id):
            self._image_viewer_window.show()
            self._image_viewer_window.raise_()
            self._image_viewer_window.activateWindow()
    