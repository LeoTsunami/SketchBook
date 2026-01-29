"""
Fullscreen or always-on-top slideshow window for drawing sessions.
Shows countdown top-right; play/pause/prev/next in bottom bar.
"""
from pathlib import Path
from typing import Optional, List, Dict, Any
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
    QApplication,
    QGridLayout,
)
from qtpy.QtCore import Qt, QTimer, Signal, QThreadPool
from qtpy.QtGui import QPixmap, QKeySequence, QShortcut, QFont, QPainter
from core.session_manager import SessionManager, load_course_config
from core.image_manager import ImageManager
from gui.session_timer import SessionTimer
from gui.image_loader_worker import ImageLoaderWorker


class SlideshowWindow(QMainWindow):
    """Fullscreen or always-on-top slideshow window for drawing sessions."""

    session_ended = Signal()  # Emitted when session ends (user closed or run finished)

    def __init__(self, session_manager: SessionManager, image_manager: ImageManager, parent=None):
        """
        Initialize the slideshow window.

        Args:
            session_manager: Session manager instance
            image_manager: Image manager instance
            parent: Parent widget (e.g. main window, for hide/show)
        """
        super().__init__(parent)
        self.session_manager = session_manager
        self.image_manager = image_manager

        self.setWindowTitle("SketchBook - Drawing Session")
        self.setCursor(Qt.BlankCursor)  # Hide cursor during session; window state set in start_session

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._setup_image_display(layout)
        # Countdown overlay top-right (always visible)
        self._setup_countdown_overlay(layout)
        self._setup_controls(layout)

        self._setup_shortcuts()

        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(2)
        self.current_pixmap: Optional[QPixmap] = None

        self._apply_theme()
    
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

    def _setup_countdown_overlay(self, layout):
        """Countdown label top-right over the image area (sibling above graphics_view)."""
        top_row = QHBoxLayout()
        top_row.addStretch()
        self.countdown_frame = QFrame()
        self.countdown_frame.setObjectName("countdownFrame")
        self.countdown_frame.setFixedSize(120, 56)
        countdown_layout = QVBoxLayout(self.countdown_frame)
        countdown_layout.setContentsMargins(8, 4, 8, 4)
        self.countdown_label = QLabel("00:00")
        self.countdown_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(22)
        font.setBold(True)
        self.countdown_label.setFont(font)
        countdown_layout.addWidget(self.countdown_label)
        top_row.addWidget(self.countdown_frame)
        layout.insertLayout(0, top_row)

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
        
        # Timer widget (controls bar)
        self.timer_widget = SessionTimer()
        self.timer_widget.timer_finished.connect(self._on_timer_finished)
        self.timer_widget.timer_updated.connect(self._on_timer_updated)
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
            # Dark theme (countdown frame uses same as controls for visibility)
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #1e1e1e;
                }
                QFrame {
                    background-color: rgba(30, 30, 30, 0.9);
                    border: none;
                }
                QFrame#countdownFrame {
                    background-color: rgba(30, 30, 30, 0.85);
                    border-radius: 6px;
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
                QFrame#countdownFrame {
                    background-color: rgba(255, 255, 255, 0.85);
                    border-radius: 6px;
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
    
    def start_session(
        self,
        image_ids: List[str],
        session_type: str,
        course_duration_minutes: Optional[int] = None,
        interval_seconds: Optional[int] = None,
        window_mode: str = "FullScreen",
        course_config_path: Optional[Path] = None,
    ) -> bool:
        """
        Start a drawing session from filtered image IDs and settings.

        Args:
            image_ids: Filtered image IDs (will be shuffled).
            session_type: "Course" or "Constant interval".
            course_duration_minutes: For Course: 10, 20, ..., 60.
            interval_seconds: For Constant: seconds per image.
            window_mode: "FullScreen" or "Window always on top".
            course_config_path: Path to session_configs.json for Course.

        Returns:
            True if session started (run has at least one image), False otherwise.
        """
        course_config: Optional[Dict[str, Any]] = None
        if session_type == "Course" and course_config_path and course_config_path.exists():
            course_config = load_course_config(course_config_path)

        ok = self.session_manager.start_session(
            image_ids=image_ids,
            session_type=session_type,
            course_duration_minutes=course_duration_minutes,
            interval_seconds=interval_seconds,
            window_mode=window_mode,
            course_config=course_config,
        )
        if not ok:
            return False

        # Window mode: FullScreen or Window always on top
        if window_mode == "Window always on top":
            self.setWindowState(Qt.WindowNoState)
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
            self.setWindowState(Qt.WindowFullScreen)

        # UI
        self.session_info.setText(f"Session: {self.session_manager.get_session_display_name()}")
        dur = self.session_manager.get_current_duration()
        self.timer_widget.set_duration(dur)
        m, s = dur // 60, dur % 60
        self.countdown_label.setText(f"{m:02d}:{s:02d}")

        self._load_current_image()
        self._update_progress()

        self.show()
        self.raise_()
        self.activateWindow()
        return True
    
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
            self._sync_timer_to_current_image()
            self._load_current_image()
            self._update_progress()
        else:
            self.session_ended.emit()
            self.close()

    def _sync_timer_to_current_image(self):
        """Set timer duration to current image and reset countdown display."""
        dur = self.session_manager.get_current_duration()
        self.timer_widget.set_duration(dur)
        self.timer_widget.reset_timer()
        m, s = dur // 60, dur % 60
        self.countdown_label.setText(f"{m:02d}:{s:02d}")

    def _previous_image(self):
        """Go to the previous image."""
        if self.session_manager.previous_image():
            self._sync_timer_to_current_image()
            self._load_current_image()
            self._update_progress()
    
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
    
    def _on_timer_updated(self, remaining_seconds: int):
        """Sync countdown label (top-right) with timer."""
        m = remaining_seconds // 60
        s = remaining_seconds % 60
        self.countdown_label.setText(f"{m:02d}:{s:02d}")

    def _on_timer_finished(self):
        """Handle timer completion: auto-advance to next image or end session."""
        self._next_image()
    
    def resizeEvent(self, event):
        """Handle resize events to maintain image fit."""
        super().resizeEvent(event)
        if self.current_pixmap:
            self._update_image_display()
    
    def closeEvent(self, event):
        """Handle window close event: end session and notify parent to re-show main window."""
        if self.session_manager.session_run:
            self.session_ended.emit()
        self.session_manager.end_session()
        self.setCursor(Qt.ArrowCursor)
        super().closeEvent(event) 