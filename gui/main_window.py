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
    QTabWidget,
    QScrollArea
)
from qtpy.QtCore import Qt, QThreadPool, QMetaObject, Q_ARG, Slot, QThread, QSize
from qtpy.QtGui import QAction, QActionGroup, QDragEnterEvent, QDropEvent, QPixmap, QPixmap
from core.settings import settings
from core.image_manager import ImageManager
from core.session_manager import SessionManager
from gui.image_import_worker import ImageImportWorker
from gui.image_grid import ImageGrid, ImageThumbnail
from gui.tag_manager import TagManager, DraggableTagChip
from gui.slideshow_window import SlideshowWindow
from gui.session_dialog import SessionDialog
from qtpy.QtWidgets import QApplication
import os

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
        self.session_manager = SessionManager()
        
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
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)  # Modern tab style
        
        # Center the tab bar buttons
        self._center_tab_bar()
        
        # Create tabs
        self._setup_image_browser_tab()
        self._setup_session_tab()
        
        # Add tab widget to layout (content takes full size)
        layout.addWidget(self.tab_widget)
        
        # Update available tags
        self._update_available_tags()
    
    def _setup_image_browser_tab(self):
        """Set up the Image Browser tab with 3-panel splitter layout."""
        # Create main splitter (horizontal)
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setChildrenCollapsible(False)
        
        # === LEFT PANEL: Tag Manager ===
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(10)
        left_layout.setAlignment(Qt.AlignTop)  # Align content to top
        
        # Create tag manager
        self.tag_manager = TagManager()
        self.tag_manager.filters_changed.connect(self._on_filters_changed)
        self.tag_manager.tags_modified.connect(self._update_available_tags)
        left_layout.addWidget(self.tag_manager)
        
        # Add stretch to push content to top
        left_layout.addStretch()
        
        # Add left panel to splitter
        main_splitter.addWidget(left_panel)
        
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
        self.image_grid.image_clicked.connect(self._on_image_clicked)
        self.image_grid.selection_changed.connect(self._on_image_selection_changed)
        self.image_grid.session_images_selected.connect(self._on_session_images_selected)
        self.image_grid.set_columns(self.columns_slider.value())
        middle_layout.addWidget(self.image_grid)
        
        # Add middle panel to splitter
        main_splitter.addWidget(middle_panel)
        
        # === RIGHT PANEL: Selected Image View ===
        self.right_panel = QWidget()
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(10)
        
        # Create selected image view
        self.selected_image_view = self._create_selected_image_view()
        right_layout.addWidget(self.selected_image_view)
        
        # Add right panel to splitter
        main_splitter.addWidget(self.right_panel)
        
        # Hide right panel by default (only show when image is selected)
        self.right_panel.setVisible(False)
        
        # Set splitter sizes (left: 150px minimum, middle: flexible, right: 0 when hidden)
        main_splitter.setSizes([150, 800, 0])
        
        # Add tab
        self.tab_widget.addTab(main_splitter, "Image Browser")
    
    def _setup_session_tab(self):
        """Set up the Drawing Session configuration tab."""
        # Create tab widget
        session_widget = QWidget()
        session_layout = QVBoxLayout(session_widget)
        session_layout.setContentsMargins(20, 20, 20, 20)
        session_layout.setSpacing(15)
        
        # Import SessionDialog components for reuse
        from qtpy.QtWidgets import (
            QComboBox,
            QSpinBox,
            QCheckBox,
            QGroupBox,
            QFormLayout,
            QTextEdit,
            QListWidget,
            QListWidgetItem
        )
        
        # Session preset selection
        preset_group = QGroupBox("Session Preset")
        preset_layout = QFormLayout(preset_group)
        
        self.session_preset_combo = QComboBox()
        self.session_preset_combo.currentTextChanged.connect(self._on_session_preset_changed)
        preset_layout.addRow("Preset:", self.session_preset_combo)
        
        self.session_preset_description = QTextEdit()
        self.session_preset_description.setMaximumHeight(80)
        self.session_preset_description.setReadOnly(True)
        preset_layout.addRow("Description:", self.session_preset_description)
        
        session_layout.addWidget(preset_group)
        
        # Session settings
        settings_group = QGroupBox("Session Settings")
        settings_layout = QFormLayout(settings_group)
        
        self.session_duration_spin = QSpinBox()
        self.session_duration_spin.setRange(10, 3600)  # 10 seconds to 1 hour
        self.session_duration_spin.setSuffix(" seconds")
        self.session_duration_spin.setValue(120)
        settings_layout.addRow("Duration:", self.session_duration_spin)
        
        self.session_image_count_spin = QSpinBox()
        self.session_image_count_spin.setRange(1, 50)
        self.session_image_count_spin.setValue(5)
        settings_layout.addRow("Images per session:", self.session_image_count_spin)
        
        self.session_auto_advance_check = QCheckBox("Auto-advance to next image")
        self.session_auto_advance_check.setChecked(True)
        settings_layout.addRow("", self.session_auto_advance_check)
        
        self.session_loop_check = QCheckBox("Loop session")
        self.session_loop_check.setChecked(False)
        settings_layout.addRow("", self.session_loop_check)
        
        session_layout.addWidget(settings_group)
        
        # Selected images section
        images_group = QGroupBox("Selected Images")
        images_layout = QVBoxLayout(images_group)
        
        self.session_image_list = QListWidget()
        self.session_image_list.setMaximumHeight(200)
        images_layout.addWidget(self.session_image_list)
        
        # Add button to select images from browser
        select_images_btn = QPushButton("Select Images from Browser")
        select_images_btn.clicked.connect(self._on_select_images_for_session)
        images_layout.addWidget(select_images_btn)
        
        session_layout.addWidget(images_group)
        
        # Start session button
        start_session_btn = QPushButton("Start Drawing Session")
        start_session_btn.setMinimumHeight(40)
        start_session_btn.clicked.connect(self._on_start_session_from_tab)
        session_layout.addWidget(start_session_btn)
        
        session_layout.addStretch()
        
        # Add tab
        self.tab_widget.addTab(session_widget, "Drawing Session")
        
        # Load presets
        self._load_session_presets()
    
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
    
    def _on_image_clicked(self, image_id: str):
        """
        Handle image click events.
        
        Args:
            image_id: ID of the clicked image
        """
        # Update selected image view and show panel
        self._update_selected_image_view(image_id)
        self._show_selected_image_panel()
    
    def _on_image_selection_changed(self, image_ids: List[str]):
        """
        Handle image selection changes.
        
        Args:
            image_ids: List of selected image IDs
        """
        # If only one image is selected, show it in the right panel
        if len(image_ids) == 1:
            self._update_selected_image_view(image_ids[0])
            self._show_selected_image_panel()
        elif len(image_ids) > 1:
            # Multiple images selected - show count or first image
            self._update_selected_image_view(image_ids[0])
            self._show_selected_image_panel()
        else:
            # No image selected - hide the panel
            self._hide_selected_image_panel()
            self._clear_selected_image_view()
    
    def _on_session_images_selected(self, image_ids: List[str]):
        """
        Handle selection of images for drawing session.
        
        Args:
            image_ids: List of selected image IDs
        """
        if not image_ids:
            QMessageBox.warning(self, "No Images Selected", "Please select at least one image for the drawing session.")
            return
        
        # Update session tab with selected images
        self._update_session_image_list(image_ids)
        
        # Switch to Drawing Session tab
        self.tab_widget.setCurrentIndex(1)
    
    def _start_drawing_session(self, session):
        """
        Start a drawing session.
        
        Args:
            session: Drawing session to start
        """
        # Create slideshow window
        self.slideshow_window = SlideshowWindow(self.session_manager, self.image_manager, self)
        self.slideshow_window.session_ended.connect(self._on_session_ended)
        
        # Start the session
        self.slideshow_window.start_session(session)
    
    def _on_session_ended(self):
        """Handle session end."""
        # Update available tags in case new tags were added during session
        self._update_available_tags()
        
        # Show completion message
        QMessageBox.information(self, "Session Complete", "Drawing session completed!")
    
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
        # Re-center tab bar after theme application
        self._center_tab_bar()
    
    def _center_tab_bar(self):
        """Center the tab bar buttons."""
        # Get the tab bar
        tab_bar = self.tab_widget.tabBar()
        if tab_bar:
            # Set expanding to False so tabs don't stretch
            tab_bar.setExpanding(False)
            # Use a layout to center the tabs
            # This is done by setting the tab bar's minimum width and using alignment
            # Actually, we need to access the tab bar's parent and use a layout
            # But since QTabBar is internal, we'll use a workaround with stylesheet
            # The stylesheet approach with margins might work better
            pass
    
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
    
    def _load_session_presets(self):
        """Load available presets into the session tab combo box."""
        presets = self.session_manager.get_presets()
        
        self.session_preset_combo.clear()
        for preset_name in presets.keys():
            self.session_preset_combo.addItem(preset_name)
        
        # Select first preset if available
        if self.session_preset_combo.count() > 0:
            self.session_preset_combo.setCurrentIndex(0)
            self._on_session_preset_changed(self.session_preset_combo.currentText())
    
    def _on_session_preset_changed(self, preset_name: str):
        """Handle preset selection change in session tab."""
        if not preset_name:
            return
        
        presets = self.session_manager.get_presets()
        preset = presets.get(preset_name)
        
        if preset:
            # Update description
            self.session_preset_description.setText(preset.description)
            
            # Update settings
            self.session_duration_spin.setValue(preset.duration_seconds)
            self.session_image_count_spin.setValue(preset.image_count)
            self.session_auto_advance_check.setChecked(preset.auto_advance)
            self.session_loop_check.setChecked(preset.loop_session)
    
    def _on_select_images_for_session(self):
        """Switch to Image Browser tab to select images for session."""
        # Switch to Image Browser tab
        self.tab_widget.setCurrentIndex(0)
        
        # Show message to user
        QMessageBox.information(
            self,
            "Select Images",
            "Please select images from the Image Browser tab, then return to the Drawing Session tab to start your session."
        )
    
    def _on_start_session_from_tab(self):
        """Start drawing session from the session tab."""
        # Get selected images from the list
        selected_image_ids = []
        for i in range(self.session_image_list.count()):
            item = self.session_image_list.item(i)
            image_id = item.data(Qt.UserRole)
            if image_id:
                selected_image_ids.append(image_id)
        
        if not selected_image_ids:
            QMessageBox.warning(
                self,
                "No Images Selected",
                "Please select images from the Image Browser tab first."
            )
            return
        
        # Get current preset or create custom one
        preset_name = self.session_preset_combo.currentText()
        presets = self.session_manager.get_presets()
        
        if preset_name in presets:
            # Use existing preset but update with current settings
            from core.session_manager import SessionPreset
            preset = SessionPreset(
                name=preset_name,
                description=presets[preset_name].description,
                duration_seconds=self.session_duration_spin.value(),
                image_count=self.session_image_count_spin.value(),
                auto_advance=self.session_auto_advance_check.isChecked(),
                loop_session=self.session_loop_check.isChecked(),
                tags=presets[preset_name].tags
            )
        else:
            # Create custom preset
            from core.session_manager import SessionPreset
            preset = SessionPreset(
                name="Custom Session",
                description="Custom drawing session",
                duration_seconds=self.session_duration_spin.value(),
                image_count=self.session_image_count_spin.value(),
                auto_advance=self.session_auto_advance_check.isChecked(),
                loop_session=self.session_loop_check.isChecked()
            )
        
        # Limit images to selected count
        session_images = selected_image_ids[:self.session_image_count_spin.value()]
        
        # Create session
        session = self.session_manager.create_session(preset, session_images)
        
        # Start the session
        self._start_drawing_session(session)
    
    def _create_selected_image_view(self) -> QWidget:
        """Create the selected image view widget for the right panel."""
        view_widget = QWidget()
        view_layout = QVBoxLayout(view_widget)
        view_layout.setContentsMargins(0, 0, 0, 0)
        view_layout.setSpacing(10)
        
        # Title
        title_label = QLabel("Selected Image")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px;")
        view_layout.addWidget(title_label)
        
        # Scroll area for image
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setAlignment(Qt.AlignCenter)
        scroll_area.setStyleSheet("background-color: #1e1e1e; border: none;")
        
        # Image label
        self.selected_image_label = QLabel()
        self.selected_image_label.setAlignment(Qt.AlignCenter)
        self.selected_image_label.setStyleSheet("background-color: #2b2b2b; border: 1px solid #4d4d4d;")
        self.selected_image_label.setText("No image selected")
        self.selected_image_label.setMinimumHeight(400)
        self.selected_image_label.setScaledContents(False)  # We'll handle scaling manually
        
        scroll_area.setWidget(self.selected_image_label)
        view_layout.addWidget(scroll_area)
        
        # Image info
        self.selected_image_info = QTextEdit()
        self.selected_image_info.setReadOnly(True)
        self.selected_image_info.setMaximumHeight(150)
        self.selected_image_info.setPlaceholderText("Image information will appear here...")
        view_layout.addWidget(self.selected_image_info)
        
        return view_widget
    
    def _update_selected_image_view(self, image_id: str):
        """
        Update the selected image view with the given image.
        
        Args:
            image_id: ID of the image to display
        """
        # Get image metadata
        metadata = self.image_manager.db.get_image(image_id)
        if not metadata:
            self._clear_selected_image_view()
            return
        
        # Load and display image
        image_path = Path(metadata.file_path)
        if image_path.exists():
            pixmap = QPixmap(str(image_path))
            if not pixmap.isNull():
                # Get scroll area size to calculate available space
                scroll_area = self.selected_image_label.parent()
                if scroll_area and hasattr(scroll_area, 'viewport'):
                    viewport_size = scroll_area.viewport().size()
                    max_width = viewport_size.width() - 20
                    max_height = viewport_size.height() - 20
                else:
                    # Fallback to label size
                    label_size = self.selected_image_label.size()
                    max_width = label_size.width() - 20 if label_size.width() > 0 else pixmap.width()
                    max_height = label_size.height() - 20 if label_size.height() > 0 else pixmap.height()
                
                # Scale pixmap to fit available space while maintaining aspect ratio
                if max_width > 0 and max_height > 0:
                    scaled_pixmap = pixmap.scaled(
                        max_width,
                        max_height,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                    self.selected_image_label.setPixmap(scaled_pixmap)
                    # Adjust label size to fit pixmap
                    self.selected_image_label.resize(scaled_pixmap.size())
                else:
                    # Use original pixmap if size calculation fails
                    self.selected_image_label.setPixmap(pixmap)
                    self.selected_image_label.resize(pixmap.size())
            else:
                self.selected_image_label.setText("Failed to load image")
                self.selected_image_label.resize(QSize(400, 400))
        else:
            self.selected_image_label.setText("Image file not found")
            self.selected_image_label.resize(QSize(400, 400))
        
        # Update image info
        info_text = f"<b>Filename:</b> {metadata.original_filename}<br>"
        info_text += f"<b>Path:</b> {metadata.file_path}<br>"
        info_text += f"<b>Size:</b> {metadata.width} x {metadata.height}<br>"
        info_text += f"<b>Added:</b> {metadata.added_at}<br>"
        if metadata.tags:
            info_text += f"<b>Tags:</b> {', '.join(sorted(metadata.tags))}<br>"
        else:
            info_text += "<b>Tags:</b> None<br>"
        
        self.selected_image_info.setHtml(info_text)
    
    def _clear_selected_image_view(self):
        """Clear the selected image view."""
        self.selected_image_label.clear()
        self.selected_image_label.setText("No image selected")
        self.selected_image_info.clear()
        self.selected_image_info.setPlaceholderText("Image information will appear here...")
    
    def _show_selected_image_panel(self):
        """Show the selected image panel."""
        if hasattr(self, 'right_panel') and not self.right_panel.isVisible():
            self.right_panel.setVisible(True)
            # Adjust splitter sizes to show the right panel
            splitter = self.right_panel.parent()
            if splitter and isinstance(splitter, QSplitter):
                current_sizes = splitter.sizes()
                if len(current_sizes) == 3:
                    # Calculate new sizes: keep left and middle, add right
                    total_width = sum(current_sizes)
                    left_size = current_sizes[0]
                    middle_size = total_width - left_size - 400  # Reserve 400px for right panel
                    right_size = 400
                    splitter.setSizes([left_size, middle_size, right_size])
    
    def _hide_selected_image_panel(self):
        """Hide the selected image panel."""
        if hasattr(self, 'right_panel') and self.right_panel.isVisible():
            self.right_panel.setVisible(False)
            # Adjust splitter sizes to hide the right panel
            splitter = self.right_panel.parent()
            if splitter and isinstance(splitter, QSplitter):
                current_sizes = splitter.sizes()
                if len(current_sizes) == 3:
                    # Redistribute space to left and middle panels
                    total_width = sum(current_sizes)
                    left_size = current_sizes[0]
                    middle_size = total_width - left_size
                    splitter.setSizes([left_size, middle_size, 0])
    
    def _update_session_image_list(self, image_ids: List[str]):
        """Update the session image list with selected images."""
        self.session_image_list.clear()
        
        for image_id in image_ids:
            metadata = self.image_manager.get_image_metadata(image_id)
            if metadata:
                display_name = metadata.original_filename
                if metadata.tags:
                    display_name += f" ({', '.join(metadata.tags)})"
                
                item = QListWidgetItem(display_name)
                item.setData(Qt.UserRole, image_id)
                self.session_image_list.addItem(item) 