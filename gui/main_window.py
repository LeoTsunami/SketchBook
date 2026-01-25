"""
Main window of the SketchBook application.
"""
from pathlib import Path
from typing import Dict, List, Set
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
    QSizePolicy
)
from qtpy.QtCore import (
    Qt,
    QThreadPool,
    QMetaObject,
    Q_ARG,
    Slot,
    QThread,
    QMimeData,
    QSize,
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
)
from core.settings import settings
from core.image_manager import ImageManager
from gui.image_import_worker import ImageImportWorker
from gui.image_grid import ImageGrid, ImageThumbnail
from gui.tag_widgets import DraggableTagChip
from gui.session_settings_dialog import SessionSettingsDialog
from qtpy.QtWidgets import QApplication
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
        self.thread_pool = QThreadPool()
        
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
        
        # Load initial images
        self.image_grid.load_images()
    
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
            # Scale logo to fit width (max 120px) while maintaining aspect ratio
            if pixmap.width() > 120:
                scaled_pixmap = pixmap.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
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
        
        # Title
        tags_tree_title = QLabel("Tags Library")
        tags_tree_title.setStyleSheet("font-size: 12px; font-weight: bold;")
        tags_tree_layout.addWidget(tags_tree_title)
        
        # Scrollable grid widget for tags
        self.tags_grid_container = QWidget()
        self.tags_grid_layout = QGridLayout(self.tags_grid_container)
        self.tags_grid_layout.setContentsMargins(0, 0, 0, 0)
        self.tags_grid_layout.setSpacing(10)

        self.tags_scroll_area = QScrollArea()
        self.tags_scroll_area.setWidgetResizable(True)
        self.tags_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tags_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tags_scroll_area.setFrameShape(QFrame.NoFrame)
        self.tags_scroll_area.setWidget(self.tags_grid_container)
        tags_tree_layout.addWidget(self.tags_scroll_area)
        
        # Load tags into grid
        self._load_tags_into_grid()
        
        left_splitter.addWidget(tags_tree_panel)
        
        # Bottom part: Session settings button
        bottom_panel = QWidget()
        bottom_layout = QVBoxLayout(bottom_panel)
        bottom_layout.setContentsMargins(10, 10, 10, 10)
        bottom_layout.setSpacing(10)
        
        # Label for number of images
        self.session_images_count_label = QLabel("Images: 0")
        self.session_images_count_label.setStyleSheet("font-size: 12px; font-weight: bold;")
        bottom_layout.addWidget(self.session_images_count_label)
        
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
        
        # Set splitter sizes (top: flexible, middle: flexible, bottom: minimal for session button)
        left_splitter.setSizes([300, 200, 100])
        
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
        
        # Add column control slider
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
        
        # Add widgets to layout with right alignment
        grid_controls.addStretch()
        grid_controls.addWidget(columns_label)
        grid_controls.addWidget(self.columns_slider)
        grid_controls.addWidget(self.columns_count)
        
        middle_layout.addLayout(grid_controls)
        
        # Create image grid
        self.image_grid = ImageGrid(self.image_manager)
        self.image_grid.set_columns(self.columns_slider.value())
        middle_layout.addWidget(self.image_grid)
        
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

    def _apply_category_filters(self) -> None:
        """Apply category/subtag filters to the image grid."""
        filtered_images = self._filter_images_by_category()
        filter_key = (
            frozenset(self._active_categories),
            frozenset(
                (category, frozenset(tags))
                for category, tags in self._active_subtags.items()
            ),
        )
        self.image_grid.load_images_from_list(filtered_images, filter_key)
        self._update_session_images_count(filtered_images)
        self._sync_tag_grid_state()

    def _update_session_images_count(self, filtered_images: List) -> None:
        """
        Update the label showing the number of images available for session.
        
        Args:
            filtered_images: Filtered images list.
        """
        count = len(filtered_images)
        self.session_images_count_label.setText(f"Images: {count}")
    
    def _on_session_settings_clicked(self):
        """Handle Session Settings button click."""
        # Get filtered images
        filtered_images = self._filter_images_by_category()
        
        image_count = len(filtered_images)
        
        # Create and show session settings dialog
        dialog = SessionSettingsDialog(self.image_manager, image_count, self)
        
        if dialog.exec_() == QDialog.Accepted and dialog.session_started:
            # Get session settings from dialog
            settings = dialog.get_session_settings()
            
            # Get session type
            session_type = settings["session_type"]
            
            # Get session parameters based on type
            if session_type == "Course":
                course_duration_minutes = settings["course_duration_minutes"]
                QMessageBox.information(
                    self,
                    "Session Configuration",
                    f"Starting Course session:\n"
                    f"- Duration: {course_duration_minutes} minutes\n"
                    f"- Images: {image_count}\n"
                    f"- Window Mode: {settings['window_mode']}"
                )
            else:  # Constant interval
                interval_text = settings["interval_duration"]
                QMessageBox.information(
                    self,
                    "Session Configuration",
                    f"Starting Constant interval session:\n"
                    f"- Interval: {interval_text}\n"
                    f"- Images: {image_count}\n"
                    f"- Window Mode: {settings['window_mode']}"
                )
            
            # TODO: Implement actual session start logic
    
    def _load_tags_into_grid(self):
        """Load tags from JSON into the tags grid."""
        while self.tags_grid_layout.count():
            item = self.tags_grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._category_buttons = {}
        self._subcategory_buttons = {}
        self._user_tag_buttons = {}
        self._subtag_to_category = {}
        
        # Load default tags from JSON
        default_tags_path = Path(__file__).parent / "ressources" / "default_tags.json"
        if default_tags_path.exists():
            try:
                import json
                with open(default_tags_path, "r", encoding="utf-8") as f:
                    default_tags = json.load(f)
                
                def collect_subtags(data, collected: List[str]) -> None:
                    """Recursively collect subtags from nested structures."""
                    if isinstance(data, list):
                        for item in data:
                            collect_subtags(item, collected)
                    elif isinstance(data, dict):
                        for key, value in data.items():
                            collected.append(key)
                            collect_subtags(value, collected)
                    elif isinstance(data, str):
                        collected.append(data)

                # Process each category at root level
                # Each category takes 2 rows, plus 1 row for separator (except last)
                categories_list = list(default_tags.items())
                
                # Calculate maximum number of columns needed for separators
                max_cols = 1  # At least column 0 for categories
                for category, tags in categories_list:
                    subtags: List[str] = []
                    collect_subtags(tags, subtags)
                    unique_subtags = list(dict.fromkeys(subtags))
                    max_cols = max(max_cols, len(unique_subtags) + 1)
                
                for category_idx, (category, tags) in enumerate(categories_list):
                    # Each category takes 2 rows, separator takes 1 row
                    row = category_idx * 3
                    # Category button in first column, spanning 2 rows
                    category_button = self._build_tag_button(category)
                    # Set size policy to prevent vertical expansion
                    category_button.setSizePolicy(
                        QSizePolicy.Preferred, QSizePolicy.Maximum
                    )
                    category_button.clicked.connect(
                        lambda _, name=category: self._on_tag_button_clicked(name)
                    )
                    self.tags_grid_layout.addWidget(category_button, row, 0, 2, 1)
                    self._category_buttons[category] = category_button

                    # Collect subtags
                    subtags: List[str] = []
                    collect_subtags(tags, subtags)
                    unique_subtags = list(dict.fromkeys(subtags))
                    
                    # Split subtags into two rows
                    mid_point = (len(unique_subtags) + 1) // 2
                    first_row_tags = unique_subtags[:mid_point]
                    second_row_tags = unique_subtags[mid_point:]
                    
                    subtag_buttons: Dict[str, QPushButton] = {}
                    # First row of subtags
                    for col, tag in enumerate(first_row_tags, start=1):
                        tag_button = self._build_tag_button(tag)
                        tag_button.clicked.connect(
                            lambda _, name=tag: self._on_tag_button_clicked(name)
                        )
                        self.tags_grid_layout.addWidget(tag_button, row, col)
                        subtag_buttons[tag] = tag_button
                        self._subtag_to_category[tag] = category
                        # Hide subtag buttons initially
                        tag_button.setVisible(False)
                    
                    # Second row of subtags
                    for col, tag in enumerate(second_row_tags, start=1):
                        tag_button = self._build_tag_button(tag)
                        tag_button.clicked.connect(
                            lambda _, name=tag: self._on_tag_button_clicked(name)
                        )
                        self.tags_grid_layout.addWidget(tag_button, row + 1, col)
                        subtag_buttons[tag] = tag_button
                        self._subtag_to_category[tag] = category
                        # Hide subtag buttons initially
                        tag_button.setVisible(False)

                    self._subcategory_buttons[category] = subtag_buttons
                    
                    # Add horizontal separator after each category (except the last one)
                    if category_idx < len(categories_list) - 1:
                        separator = QFrame()
                        separator.setFrameShape(QFrame.Shape.HLine)
                        separator.setFrameShadow(QFrame.Shadow.Sunken)
                        separator.setStyleSheet("QFrame { color: #666; }")
                        # Span separator across all columns
                        self.tags_grid_layout.addWidget(separator, row + 2, 0, 1, max_cols)

            except Exception as e:
                print(f"Error loading default tags: {str(e)}")
        
    def _find_tag_icon(self, tag: str) -> QIcon:
        """
        Resolve a tag icon based on the tag name.

        Args:
            tag: Tag name.

        Returns:
            QIcon: Icon for the tag or an empty icon if not found.
        """
        icons_dir = Path(__file__).parent / "ressources" / "icones" / "tags"
        if not icons_dir.exists():
            return QIcon()

        tag_lower = tag.lower()
        file_map = {path.stem.lower(): path for path in icons_dir.glob("*.png")}
        if tag_lower in file_map:
            return QIcon(str(file_map[tag_lower]))

        fallback_map = {
            "hands": "hand",
            "feet": "foot",
            "objects": "object",
        }
        fallback = fallback_map.get(tag_lower)
        if fallback and fallback in file_map:
            return QIcon(str(file_map[fallback]))

        return QIcon()

    def _invert_icon(self, icon: QIcon) -> QIcon:
        """
        Invert icon colors for better visibility.

        Args:
            icon: Original icon.

        Returns:
            QIcon: Inverted icon.
        """
        if icon.isNull():
            return icon
        pixmap = icon.pixmap(QSize(28, 28))
        image = pixmap.toImage()
        image.invertPixels(QImage.InvertRgb)
        return QIcon(QPixmap.fromImage(image))

    def _build_tag_button(self, tag: str) -> QPushButton:
        """
        Build a tag button with icon and label.

        Args:
            tag: Tag name.

        Returns:
            QPushButton: Configured tag button.
        """
        button = QPushButton(tag)
        icon = self._find_tag_icon(tag)
        if not icon.isNull():
            button.setIcon(self._invert_icon(icon))
            button.setIconSize(QSize(28, 28))
        button.setCheckable(False)
        button.setStyleSheet(
            "QPushButton { text-align: left; padding: 2px 4px; }"
        )
        return button

    def _on_tag_button_clicked(self, tag: str) -> None:
        """
        Toggle tag in filters from tag buttons.

        Args:
            tag: Tag name to toggle.
        """
        if tag in self._category_buttons:
            if tag in self._active_categories:
                self._active_categories.remove(tag)
                self._active_subtags.pop(tag, None)
            else:
                self._active_categories.add(tag)
                self._active_subtags.setdefault(tag, set())
        else:
            category = self._subtag_to_category.get(tag)
            if not category:
                return
            if category not in self._active_categories:
                self._active_categories.add(category)
            category_tags = self._active_subtags.setdefault(category, set())
            if tag in category_tags:
                category_tags.remove(tag)
            else:
                category_tags.add(tag)
        self._apply_category_filters()

    def _sync_tag_grid_state(self) -> None:
        """
        Sync tag grid button states with active filters.
        """
        active_tags = set(self._active_categories)
        for tags in self._active_subtags.values():
            active_tags.update(tags)
        for category, button in self._category_buttons.items():
            is_active = category in self._active_categories
            self._set_button_active(button, is_active)
            # Show/hide subtags based on category activation
            for tag, tag_button in self._subcategory_buttons.get(category, {}).items():
                tag_button.setVisible(is_active)
                self._set_button_active(tag_button, tag in active_tags)
        # User tags are intentionally omitted from the grid for now.

    def _filter_images_by_category(self) -> List:
        """
        Filter images by category (OR) and sub-tags (AND within category).

        Returns:
            List: Filtered image metadata list.
        """
        all_images = self.image_manager.db.list_images()
        if not self._active_categories:
            return all_images

        filtered_images = []
        for metadata in all_images:
            image_tags = set(metadata.tags)
            for category in self._active_categories:
                if category not in image_tags:
                    continue
                required = self._active_subtags.get(category, set())
                if required.issubset(image_tags):
                    filtered_images.append(metadata)
                    break
        return filtered_images

    def _set_button_active(self, button: QPushButton, active: bool) -> None:
        """
        Apply active styling to a tag button.

        Args:
            button: Button to update.
            active: Whether the button is active.
        """
        base_style = "QPushButton { text-align: left; padding: 2px 4px; }"
        if active:
            button.setStyleSheet(
                base_style + " QPushButton { background-color: #8ec5ff; }"
            )
        else:
            button.setStyleSheet(base_style)
    
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
        urls = event.mimeData().urls()
        paths = []
        for url in urls:
            path = Path(url.toLocalFile())
            if path.is_dir() or path.suffix.lower() in ImageManager.SUPPORTED_FORMATS:
                paths.append(path)
        
        if paths:
            self._import_images(paths)
            event.acceptProposedAction()
    
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

    def _import_images(self, paths: List[Path]):
        """
        Import images from paths.
        
        Args:
            paths: List of paths to import
        """
        # Create progress bar in status bar
        progress_bar = self._create_status_progress_bar()
        
        # Create and configure worker
        worker = ImageImportWorker(self.image_manager, paths)
        
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
        
        # Start worker
        if self.dev_mode:
            self.update_dev_progress_label("Starting import...")
            self.update_dev_progress_bar(0)
        else:
            self.statusBar().showMessage("Starting image import...")
        
        # Start worker and keep a reference to prevent garbage collection
        self.current_worker = worker
        self.thread_pool.start(worker)
    
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
            
            # Reload images and update tags
            self.image_grid.load_images()
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
        
        # - Import images
        import_action = QAction("&Import Images...", self)
        import_action.setShortcut("Ctrl+I")
        import_action.triggered.connect(self._on_import_images)
        file_menu.addAction(import_action)
        
        # - Import folder
        import_folder_action = QAction("Import &Folder...", self)
        import_folder_action.setShortcut("Ctrl+F")
        import_folder_action.triggered.connect(self._on_import_folder)
        file_menu.addAction(import_folder_action)
        
        file_menu.addSeparator()
        
        # - Exit
        exit_action = QAction("E&xit", self)
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
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Purge Error",
                    f"Error purging library: {str(e)}"
                )

    def _on_columns_changed(self, value: int):
        """Handle column slider value changes."""
        self.columns_count.setText(str(value))
        self.image_grid.set_columns(value)
        settings.set("ui.grid.columns", value)
    