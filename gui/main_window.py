"""
Main window of the SketchBook application.
"""
from pathlib import Path
from typing import List
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
    QTreeWidgetItem
)
from qtpy.QtCore import Qt, QThreadPool, QMetaObject, Q_ARG, Slot, QThread
from qtpy.QtGui import QAction, QActionGroup, QDragEnterEvent, QDropEvent, QPixmap
from core.settings import settings
from core.image_manager import ImageManager
from gui.image_import_worker import ImageImportWorker
from gui.image_grid import ImageGrid, ImageThumbnail
from gui.tag_manager import TagManager, DraggableTagChip
from qtpy.QtWidgets import QApplication
from qtpy.QtGui import QDrag
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
        
        # Update available tags
        self._update_available_tags()
        
        # Update session images count with initial filters
        initial_filters = self.tag_manager.get_filters()
        self._update_session_images_count(initial_filters)
    
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
        
        # Logo at the top
        logo_path = Path(__file__).parent / "ressources" / "icones" / "SketchBook_logo.png"
        if logo_path.exists():
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
            tag_manager_layout.addWidget(logo_label)
        
        # Create tag manager
        self.tag_manager = TagManager()
        self.tag_manager.filters_changed.connect(self._on_filters_changed)
        self.tag_manager.tags_modified.connect(self._update_available_tags)
        tag_manager_layout.addWidget(self.tag_manager, 1)  # Stretch factor = 1 to expand
        
        left_splitter.addWidget(tag_manager_panel)
        
        # Middle part: Tags tree widget
        tags_tree_panel = QWidget()
        tags_tree_layout = QVBoxLayout(tags_tree_panel)
        tags_tree_layout.setContentsMargins(10, 10, 10, 10)
        tags_tree_layout.setSpacing(5)
        
        # Title
        tags_tree_title = QLabel("Tags Library")
        tags_tree_title.setStyleSheet("font-size: 12px; font-weight: bold;")
        tags_tree_layout.addWidget(tags_tree_title)
        
        # Tree widget for tags (with custom drag support)
        self.tags_tree = DraggableTreeWidget()
        self.tags_tree.setHeaderLabel("Tags")
        self.tags_tree.setRootIsDecorated(True)
        self.tags_tree.setDragEnabled(True)
        self.tags_tree.setDragDropMode(QTreeWidget.DragOnly)
        # Enable drag for items
        self.tags_tree.itemDoubleClicked.connect(self._on_tree_item_double_clicked)
        tags_tree_layout.addWidget(self.tags_tree)
        
        # Load tags into tree
        self._load_tags_into_tree()
        
        left_splitter.addWidget(tags_tree_panel)
        
        # Bottom part: Session parameters
        bottom_panel = QWidget()
        bottom_layout = QVBoxLayout(bottom_panel)
        bottom_layout.setContentsMargins(10, 10, 10, 10)
        bottom_layout.setSpacing(10)
        
        # Label for number of images
        self.session_images_count_label = QLabel("Images: 0")
        self.session_images_count_label.setStyleSheet("font-size: 12px; font-weight: bold;")
        bottom_layout.addWidget(self.session_images_count_label)
        
        # Session type combobox
        session_type_label = QLabel("Session Type:")
        session_type_label.setStyleSheet("font-size: 11px;")
        bottom_layout.addWidget(session_type_label)
        
        self.session_type_combo = QComboBox()
        self.session_type_combo.addItems(["Course", "Constant interval"])
        self.session_type_combo.currentTextChanged.connect(self._on_session_type_changed)
        bottom_layout.addWidget(self.session_type_combo)
        
        # Course duration (shown when "Course" is selected)
        self.course_duration_label = QLabel("Course Duration:")
        self.course_duration_label.setStyleSheet("font-size: 11px;")
        bottom_layout.addWidget(self.course_duration_label)
        
        self.course_duration_spin = QSpinBox()
        self.course_duration_spin.setRange(10, 300)  # 10 to 300 minutes
        self.course_duration_spin.setSingleStep(10)  # Step of 10 minutes
        self.course_duration_spin.setSuffix(" minutes")
        self.course_duration_spin.setValue(30)  # Default 30 minutes
        bottom_layout.addWidget(self.course_duration_spin)
        
        # Constant interval duration (shown when "Constant interval" is selected)
        self.interval_duration_label = QLabel("Image Duration:")
        self.interval_duration_label.setStyleSheet("font-size: 11px;")
        self.interval_duration_label.setVisible(False)
        bottom_layout.addWidget(self.interval_duration_label)
        
        self.interval_duration_combo = QComboBox()
        self.interval_duration_combo.addItems(["30 seconds", "1 minute", "3 minutes", "5 minutes", "10 minutes", "20 minutes"])
        self.interval_duration_combo.setVisible(False)
        bottom_layout.addWidget(self.interval_duration_combo)
        
        # Window Mode combobox
        window_mode_label = QLabel("Window Mode:")
        window_mode_label.setStyleSheet("font-size: 11px;")
        bottom_layout.addWidget(window_mode_label)
        
        self.window_mode_combo = QComboBox()
        self.window_mode_combo.addItems(["FullScreen", "Window always on top"])
        bottom_layout.addWidget(self.window_mode_combo)
        
        # Add stretch to push button to bottom
        bottom_layout.addStretch()
        
        # Start Session button
        self.start_session_btn = QPushButton("Start Session")
        self.start_session_btn.setStyleSheet("""
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
        self.start_session_btn.clicked.connect(self._on_start_session_clicked)
        bottom_layout.addWidget(self.start_session_btn)
        
        # Initialize session type UI (default to "Course")
        self._on_session_type_changed("Course")
        
        left_splitter.addWidget(bottom_panel)
        
        # Set splitter sizes (top: flexible, middle: flexible, bottom: fixed for session controls)
        left_splitter.setSizes([300, 200, 200])
        
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
    
    def _update_available_tags(self):
        """Update the list of available tags in the tag manager."""
        # Collect all unique tags from the database
        all_tags = set()
        for metadata in self.image_manager.db.list_images():
            all_tags.update(metadata.tags)
        
        self.tag_manager.set_available_tags(sorted(all_tags))
    
    def _on_filters_changed(self, filters: dict):
        """
        Handle changes in advanced tag filters.
        
        Args:
            filters: Dictionary with "and" and "or" sets of tags
        """
        # Update image grid with new filter
        self.image_grid.load_images_with_advanced_filter(filters)
        
        # Update session images count
        self._update_session_images_count(filters)
    
    def _update_session_images_count(self, filters: dict):
        """
        Update the label showing the number of images available for session.
        
        Args:
            filters: Dictionary with "and" and "or" sets of tags
        """
        # Get filtered images
        filtered_images = self.image_manager.db.search_images_advanced(
            and_tags=filters.get("and", set()),
            or_tags=filters.get("or", set())
        )
        
        count = len(filtered_images)
        self.session_images_count_label.setText(f"Images: {count}")
    
    def _on_session_type_changed(self, session_type: str):
        """
        Handle session type change.
        
        Args:
            session_type: "Course" or "Constant interval"
        """
        if session_type == "Course":
            # Show course duration controls
            self.course_duration_label.setVisible(True)
            self.course_duration_spin.setVisible(True)
            # Hide interval duration controls
            self.interval_duration_label.setVisible(False)
            self.interval_duration_combo.setVisible(False)
        else:  # Constant interval
            # Hide course duration controls
            self.course_duration_label.setVisible(False)
            self.course_duration_spin.setVisible(False)
            # Show interval duration controls
            self.interval_duration_label.setVisible(True)
            self.interval_duration_combo.setVisible(True)
    
    def _on_start_session_clicked(self):
        """Handle Start Session button click."""
        # Get current filters
        filters = self.tag_manager.get_filters()
        
        # Get filtered images
        filtered_images = self.image_manager.db.search_images_advanced(
            and_tags=filters.get("and", set()),
            or_tags=filters.get("or", set())
        )
        
        if not filtered_images:
            QMessageBox.warning(
                self,
                "No Images Available",
                "No images match the current tag filters. Please adjust your filters."
            )
            return
        
        # Get session type
        session_type = self.session_type_combo.currentText()
        
        # Get session parameters based on type
        if session_type == "Course":
            course_duration_minutes = self.course_duration_spin.value()
            QMessageBox.information(
                self,
                "Session Configuration",
                f"Starting Course session:\n"
                f"- Duration: {course_duration_minutes} minutes\n"
                f"- Images: {len(filtered_images)}"
            )
        else:  # Constant interval
            interval_text = self.interval_duration_combo.currentText()
            QMessageBox.information(
                self,
                "Session Configuration",
                f"Starting Constant interval session:\n"
                f"- Interval: {interval_text}\n"
                f"- Images: {len(filtered_images)}"
            )
        
        # TODO: Implement actual session start logic
    
    def _load_tags_into_tree(self):
        """Load tags from JSON and user tags into the tree widget."""
        self.tags_tree.clear()
        
        # Load default tags from JSON
        default_tags_path = Path(__file__).parent / "ressources" / "default_tags.json"
        if default_tags_path.exists():
            try:
                import json
                with open(default_tags_path, "r", encoding="utf-8") as f:
                    default_tags = json.load(f)
                
                # Add default tags section
                default_root = QTreeWidgetItem(self.tags_tree)
                default_root.setText(0, "Default Tags")
                default_root.setExpanded(True)
                
                # Process each category
                for category, tags in default_tags.items():
                    category_item = QTreeWidgetItem(default_root)
                    category_item.setText(0, category)
                    category_item.setExpanded(True)
                    
                    # Check if tags is a list or dict
                    if isinstance(tags, list):
                        # Simple list of tags
                        for tag in tags:
                            tag_item = QTreeWidgetItem(category_item)
                            tag_item.setText(0, tag)
                            tag_item.setFlags(tag_item.flags() | Qt.ItemIsDragEnabled)
                    elif isinstance(tags, dict):
                        # Nested structure (e.g., Type: {Human: [...], Animal: [...]})
                        for sub_category, sub_tags in tags.items():
                            # Sub-category can be both a category and a tag
                            sub_category_item = QTreeWidgetItem(category_item)
                            sub_category_item.setText(0, sub_category)
                            sub_category_item.setExpanded(True)
                            # Make sub-category draggable as a tag
                            sub_category_item.setFlags(sub_category_item.flags() | Qt.ItemIsDragEnabled)
                            
                            # Add tags under sub-category
                            for tag in sub_tags:
                                tag_item = QTreeWidgetItem(sub_category_item)
                                tag_item.setText(0, tag)
                                tag_item.setFlags(tag_item.flags() | Qt.ItemIsDragEnabled)
            except Exception as e:
                print(f"Error loading default tags: {str(e)}")
        
        # Add user tags section
        user_root = QTreeWidgetItem(self.tags_tree)
        user_root.setText(0, "User Tags")
        user_root.setExpanded(True)
        
        # Get user tags from database
        user_tags = set()
        for metadata in self.image_manager.db.list_images():
            user_tags.update(metadata.tags)
        
        # Filter out default tags
        default_tag_set = set()
        if default_tags_path.exists():
            try:
                import json
                with open(default_tags_path, "r", encoding="utf-8") as f:
                    default_tags_data = json.load(f)
                
                def extract_tags(data, tag_set):
                    """Recursively extract all tags from nested structure."""
                    if isinstance(data, list):
                        tag_set.update(data)
                    elif isinstance(data, dict):
                        for key, value in data.items():
                            tag_set.add(key)  # Category name is also a tag
                            extract_tags(value, tag_set)
                
                extract_tags(default_tags_data, default_tag_set)
            except Exception:
                pass
        
        # Add user tags that are not in default tags
        user_only_tags = sorted(user_tags - default_tag_set)
        for tag in user_only_tags:
            tag_item = QTreeWidgetItem(user_root)
            tag_item.setText(0, tag)
            tag_item.setFlags(tag_item.flags() | Qt.ItemIsDragEnabled)
        
        if not user_only_tags:
            no_tags_item = QTreeWidgetItem(user_root)
            no_tags_item.setText(0, "(No user tags yet)")
            no_tags_item.setFlags(no_tags_item.flags() & ~Qt.ItemIsEnabled)
    
    def _on_tree_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """
        Handle double-click on tree item to add tag to AND zone.
        
        Args:
            item: The clicked tree item
            column: Column index (always 0 for single column)
        """
        # Only add if item is draggable (i.e., it's a tag, not a category header)
        if item.flags() & Qt.ItemIsDragEnabled:
            tag_text = item.text(0)
            self.tag_manager.add_tag_to_and(tag_text)
    
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
    