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
    QLabel
)
from qtpy.QtCore import Qt, QThreadPool, QMetaObject, Q_ARG, Slot, QThread
from qtpy.QtGui import QAction, QActionGroup, QDragEnterEvent, QDropEvent
from core.settings import settings
from core.image_manager import ImageManager
from gui.image_import_worker import ImageImportWorker

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
    
    def _setup_ui(self):
        """Set up the main UI components."""
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create layout
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 10)
    
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
        self._apply_theme()
    
    def _apply_theme(self):
        """Apply the current theme from settings."""
        if settings.get("ui.theme") == "dark":
            # Dark theme palette
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QMenuBar {
                    background-color: #3c3f41;
                    color: #ffffff;
                }
                QMenuBar::item:selected {
                    background-color: #4b6eaf;
                }
                QMenu {
                    background-color: #3c3f41;
                    color: #ffffff;
                }
                QMenu::item:selected {
                    background-color: #4b6eaf;
                }
                QStatusBar {
                    background-color: #3c3f41;
                    color: #ffffff;
                }
            """)
        else:
            # Light theme
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #ffffff;
                    color: #000000;
                }
                QMenuBar {
                    background-color: #f0f0f0;
                    color: #000000;
                }
                QMenuBar::item:selected {
                    background-color: #0078d7;
                    color: #ffffff;
                }
                QMenu {
                    background-color: #ffffff;
                    color: #000000;
                }
                QMenu::item:selected {
                    background-color: #0078d7;
                    color: #ffffff;
                }
                QStatusBar {
                    background-color: #f0f0f0;
                    color: #000000;
                }
            """)
    
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
                image_dir = Path(settings.get("images.storage_path", "data/images"))
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