"""
Fullscreen slideshow window for drawing sessions.
"""
from pathlib import Path
from typing import Optional, List
from qtpy.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QApplication
)
from qtpy.QtCore import Qt, QTimer, Signal, QRect, QSize, QThreadPool
from qtpy.QtGui import QPixmap, QImage, QKeySequence, QShortcut, QFont, QPainter
from core.session_manager import SessionManager, DrawingSession
from core.image_manager import ImageManager
from gui.session_timer import SessionTimer
from gui.image_loader_worker import ImageLoaderWorker


class SlideshowWindow(QMainWindow):
    """Fullscreen slideshow window for drawing sessions."""
    
    session_ended = Signal()  # Emitted when session ends
    
    def __init__(self, session_manager: SessionManager, image_manager: ImageManager, parent=None):
        """
        Initialize the slideshow window.
        
        Args:
            session_manager: Session manager instance
            image_manager: Image manager instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.session_manager = session_manager
        self.image_manager = image_manager
        
        # Set up fullscreen window
        self.setWindowTitle("SketchBook - Drawing Session")
        self.setWindowState(Qt.WindowFullScreen)
        self.setCursor(Qt.BlankCursor)  # Hide cursor during session
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create layout
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create image display
        self._setup_image_display(layout)
        
        # Create controls overlay
        self._setup_controls(layout)
        
        # Set up keyboard shortcuts
        self._setup_shortcuts()
        
        # Thread pool for image loading
        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(2)
        
        # Current image cache
        self.current_pixmap: Optional[QPixmap] = None
        
        # Apply theme
        self._apply_theme()
        
        # Connect session manager
        self.session_manager = session_manager
    
    def _setup_image_display(self, layout):
        """Set up the image display area."""
        # Create graphics view for image display
        self.graphics_view = QGraphicsView()
        self.graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graphics_view.setRenderHint(QPainter.SmoothPixmapTransform)
        self.graphics_view.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        
        # Create graphics scene
        self.scene = QGraphicsScene()
        self.graphics_view.setScene(self.scene)
        
        # Create pixmap item
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)
        
        layout.addWidget(self.graphics_view, 1)  # Take most of the space
    
    def _setup_controls(self, layout):
        """Set up the controls overlay."""
        # Create controls frame
        self.controls_frame = QFrame()
        self.controls_frame.setFixedHeight(120)
        self.controls_frame.setVisible(False)  # Hidden by default
        
        controls_layout = QVBoxLayout(self.controls_frame)
        controls_layout.setContentsMargins(20, 10, 20, 10)
        
        # Top row: Progress and timer
        top_row = QHBoxLayout()
        
        # Progress label
        self.progress_label = QLabel("Image 1 of 5")
        self.progress_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self.progress_label.setFont(font)
        top_row.addWidget(self.progress_label)
        
        top_row.addStretch()
        
        # Timer widget
        self.timer_widget = SessionTimer()
        self.timer_widget.timer_finished.connect(self._on_timer_finished)
        top_row.addWidget(self.timer_widget)
        
        controls_layout.addLayout(top_row)
        
        # Bottom row: Navigation buttons
        bottom_row = QHBoxLayout()
        
        # Previous button
        self.prev_button = QPushButton("← Previous")
        self.prev_button.clicked.connect(self._previous_image)
        self.prev_button.setFixedSize(100, 40)
        bottom_row.addWidget(self.prev_button)
        
        bottom_row.addStretch()
        
        # Session info
        self.session_info = QLabel("Session: Standard (2min)")
        self.session_info.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(10)
        self.session_info.setFont(font)
        bottom_row.addWidget(self.session_info)
        
        bottom_row.addStretch()
        
        # Next button
        self.next_button = QPushButton("Next →")
        self.next_button.clicked.connect(self._next_image)
        self.next_button.setFixedSize(100, 40)
        bottom_row.addWidget(self.next_button)
        
        controls_layout.addLayout(bottom_row)
        
        layout.addWidget(self.controls_frame)
    
    def _setup_shortcuts(self):
        """Set up keyboard shortcuts."""
        # Show/hide controls
        self.show_controls_shortcut = QShortcut(QKeySequence("Space"), self)
        self.show_controls_shortcut.activated.connect(self._toggle_controls)
        
        # Navigation
        self.next_shortcut = QShortcut(QKeySequence("Right"), self)
        self.next_shortcut.activated.connect(self._next_image)
        
        self.prev_shortcut = QShortcut(QKeySequence("Left"), self)
        self.prev_shortcut.activated.connect(self._previous_image)
        
        # Timer controls
        self.start_stop_shortcut = QShortcut(QKeySequence("S"), self)
        self.start_stop_shortcut.activated.connect(self._toggle_timer)
        
        self.pause_shortcut = QShortcut(QKeySequence("P"), self)
        self.pause_shortcut.activated.connect(self._pause_timer)
        
        # Exit
        self.exit_shortcut = QShortcut(QKeySequence("Escape"), self)
        self.exit_shortcut.activated.connect(self.close)
    
    def _apply_theme(self):
        """Apply theme-aware styles."""
        from core.settings import settings
        
        if settings.get("ui.theme") == "dark":
            # Dark theme
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #1e1e1e;
                }
                QFrame {
                    background-color: rgba(30, 30, 30, 0.9);
                    border: none;
                }
                QLabel {
                    color: #ffffff;
                }
                QPushButton {
                    background-color: #3c3f41;
                    color: #ffffff;
                    border: 1px solid #4d4d4d;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #4b6eaf;
                }
                QPushButton:pressed {
                    background-color: #3d5a8c;
                }
                QPushButton:disabled {
                    background-color: #2b2b2b;
                    color: #666666;
                    border: 1px solid #3c3c3c;
                }
            """)
        else:
            # Light theme
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #ffffff;
                }
                QFrame {
                    background-color: rgba(255, 255, 255, 0.9);
                    border: none;
                }
                QLabel {
                    color: #000000;
                }
                QPushButton {
                    background-color: #f0f0f0;
                    color: #000000;
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #e5e5e5;
                }
                QPushButton:pressed {
                    background-color: #d0d0d0;
                }
                QPushButton:disabled {
                    background-color: #f5f5f5;
                    color: #999999;
                    border: 1px solid #e0e0e0;
                }
            """)
    
    def start_session(self, session: DrawingSession):
        """
        Start a drawing session.
        
        Args:
            session: Session to start
        """
        self.current_session = session
        self.session_manager.start_session(session)
        
        # Update UI
        self.session_info.setText(f"Session: {session.preset.name}")
        self.timer_widget.set_duration(session.preset.duration_seconds)
        
        # Load first image
        self._load_current_image()
        self._update_progress()
        
        # Show window
        self.show()
        self.raise_()
        self.activateWindow()
    
    def _load_current_image(self):
        """Load the current image for display."""
        image_id = self.session_manager.get_current_image_id()
        if not image_id:
            return
        
        # Get image metadata
        metadata = self.image_manager.get_image_metadata(image_id)
        if not metadata:
            return
        
        # Load image asynchronously
        image_path = self.image_manager.image_dir / metadata.path
        worker = ImageLoaderWorker(image_id, image_path, (1920, 1080))  # Full HD max
        
        worker.signals.finished.connect(self._on_image_loaded)
        worker.signals.error.connect(self._on_image_error)
        
        self.thread_pool.start(worker)
    
    def _on_image_loaded(self, image_id: str, pixmaps: tuple):
        """Handle loaded image."""
        fast_pixmap, high_quality_pixmap = pixmaps
        
        # Store the high quality pixmap
        self.current_pixmap = high_quality_pixmap
        
        # Update display
        self._update_image_display()
    
    def _on_image_error(self, image_id: str, error_msg: str):
        """Handle image loading error."""
        # Create a placeholder image
        placeholder = QPixmap(800, 600)
        placeholder.fill(Qt.gray)
        
        self.current_pixmap = placeholder
        self._update_image_display()
    
    def _update_image_display(self):
        """Update the image display."""
        if not self.current_pixmap:
            return
        
        # Set the pixmap
        self.pixmap_item.setPixmap(self.current_pixmap)
        
        # Fit the image to the view
        self.graphics_view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
    
    def _update_progress(self):
        """Update the progress display."""
        current, total, time_remaining = self.session_manager.get_session_progress()
        self.progress_label.setText(f"Image {current} of {total}")
    
    def _next_image(self):
        """Go to the next image."""
        if self.session_manager.advance_image():
            self._load_current_image()
            self._update_progress()
            self.timer_widget.reset_timer()
        else:
            # Session ended
            self.session_ended.emit()
            self.close()
    
    def _previous_image(self):
        """Go to the previous image."""
        if self.session_manager.previous_image():
            self._load_current_image()
            self._update_progress()
            self.timer_widget.reset_timer()
    
    def _toggle_controls(self):
        """Toggle the visibility of controls."""
        self.controls_frame.setVisible(not self.controls_frame.isVisible())
        
        # Show cursor when controls are visible
        if self.controls_frame.isVisible():
            self.setCursor(Qt.ArrowCursor)
        else:
            self.setCursor(Qt.BlankCursor)
    
    def _toggle_timer(self):
        """Toggle timer start/stop."""
        if self.timer_widget.is_timer_running():
            self.timer_widget.stop_timer()
        else:
            self.timer_widget.start_timer()
    
    def _pause_timer(self):
        """Pause/resume timer."""
        self.timer_widget.pause_timer()
    
    def _on_timer_finished(self):
        """Handle timer completion."""
        # Auto-advance if enabled
        if self.current_session and self.current_session.preset.auto_advance:
            self._next_image()
    
    def resizeEvent(self, event):
        """Handle resize events to maintain image fit."""
        super().resizeEvent(event)
        if self.current_pixmap:
            self._update_image_display()
    
    def closeEvent(self, event):
        """Handle window close event."""
        # End the session
        if self.session_manager.get_current_session():
            self.session_manager.end_session()
        
        # Restore cursor
        self.setCursor(Qt.ArrowCursor)
        
        super().closeEvent(event) 