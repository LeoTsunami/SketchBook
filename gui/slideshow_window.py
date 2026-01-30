"""
Fullscreen or always-on-top slideshow window for drawing sessions.
Image full area + countdown overlay (top-left). No bottom bar.
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
from qtpy.QtCore import Qt, QTimer, Signal, QThreadPool, QVariantAnimation, QRectF
from qtpy.QtGui import (
    QPixmap,
    QKeySequence,
    QShortcut,
    QFont,
    QPainter,
    QTransform,
    QGuiApplication,
)
from core.session_manager import SessionManager, load_course_config
from core.image_manager import ImageManager
from gui.session_timer import SessionTimer
from gui.image_loader_worker import ImageLoaderWorker


class _OverlayContainer(QWidget):
    """Container: image view full area + countdown overlay (top-left)."""

    resized = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._graphics_view = None
        self._countdown_frame = None

    def set_content(
        self,
        graphics_view: QGraphicsView,
        countdown_frame: QFrame,
    ) -> None:
        self._graphics_view = graphics_view
        self._countdown_frame = countdown_frame
        graphics_view.setParent(self)
        countdown_frame.setParent(self)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        r = self.rect()
        if self._graphics_view:
            self._graphics_view.setGeometry(r)
        if self._countdown_frame:
            self._countdown_frame.setGeometry(16, 16, 120, 56)
            self._countdown_frame.raise_()
        self.resized.emit()


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

        # Image + countdown only
        self._setup_image_display()
        self._setup_countdown_overlay()
        self._setup_timer_hidden()  # Timer logic for countdown and auto-advance, no UI
        self._overlay_container = _OverlayContainer(self)
        self._overlay_container.set_content(self.graphics_view, self.countdown_frame)
        self._overlay_container.resized.connect(self._on_container_resized)
        layout.addWidget(self._overlay_container, 1)

        self._setup_shortcuts()

        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(2)
        self.current_pixmap: Optional[QPixmap] = None
        self._first_image = True
        self._fade_animation: Optional[QVariantAnimation] = None
        self._is_fullscreen = False

        self._apply_theme()
    
    def _setup_image_display(self):
        """Set up the image display (two layers for crossfade). Will be placed full-size in container."""
        self.graphics_view = QGraphicsView()
        self.graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graphics_view.setRenderHint(QPainter.SmoothPixmapTransform)
        self.graphics_view.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.graphics_view.setStyleSheet("background: black;")  # Letterbox color when ratio differs

        self.scene = QGraphicsScene()
        self.graphics_view.setScene(self.scene)

        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)
        self.pixmap_item_next = QGraphicsPixmapItem()
        self.pixmap_item_next.setZValue(1)
        self.pixmap_item_next.setOpacity(0.0)
        self.scene.addItem(self.pixmap_item_next)

    def _setup_countdown_overlay(self):
        """Countdown frame (overlay top-left)."""
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

    def _setup_timer_hidden(self):
        """Timer for countdown and auto-advance; no visible UI."""
        self.timer_widget = SessionTimer()
        self.timer_widget.setParent(self)
        self.timer_widget.setVisible(False)
        self.timer_widget.timer_finished.connect(self._on_timer_finished)
        self.timer_widget.timer_updated.connect(self._on_timer_updated)

    def _setup_shortcuts(self):
        """Keyboard: Left/Right = prev/next, Escape = close session."""
        self.next_shortcut = QShortcut(QKeySequence("Right"), self)
        self.next_shortcut.activated.connect(self._next_image)
        self.prev_shortcut = QShortcut(QKeySequence("Left"), self)
        self.prev_shortcut.activated.connect(self._previous_image)
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
        self._is_fullscreen = window_mode != "Window always on top"
        if self._is_fullscreen:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
            self.setWindowState(Qt.WindowFullScreen)
        else:
            self.setWindowState(Qt.WindowNoState)
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        # Countdown + timer
        dur = self.session_manager.get_current_duration()
        self.timer_widget.set_duration(dur)
        m, s = dur // 60, dur % 60
        self.countdown_label.setText(f"{m:02d}:{s:02d}")
        self._apply_countdown_color(dur)

        # Auto-start timer so countdown decreases immediately (no need to press S/Start)
        self.timer_widget.start_timer()

        self._first_image = True
        self._load_current_image()

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
    
    def _get_viewport_size(self):
        """Return (width, height) in *logical* pixels (for view transform)."""
        vp = self.graphics_view.viewport()
        return (vp.width(), vp.height())

    def _get_screen_dpr(self):
        """Device pixel ratio of the screen this window is on."""
        try:
            screen = self.screen()
            if screen:
                return screen.devicePixelRatio()
        except Exception:
            pass
        return 1.0

    def _get_display_size_sources(self):
        """Return dict of (name -> (width, height) logical) from different Qt sources.
        Useful to see what each API returns and pick the right one.
        """
        out = {}
        try:
            app = QApplication.instance()
            if app:
                primary = QGuiApplication.primaryScreen()
                if primary:
                    g = primary.geometry()
                    out["primaryScreen.geometry()"] = (g.width(), g.height())
                    ag = primary.availableGeometry()
                    out["primaryScreen.availableGeometry()"] = (ag.width(), ag.height())
        except Exception as e:
            out["primaryScreen"] = (0, 0)

        try:
            screen = self.screen()
            if screen:
                g = screen.geometry()
                out["window.screen().geometry()"] = (g.width(), g.height())
                ag = screen.availableGeometry()
                out["window.screen().availableGeometry()"] = (ag.width(), ag.height())
        except Exception:
            out["window.screen()"] = (0, 0)

        try:
            out["window.size()"] = (self.width(), self.height())
            out["window.frameGeometry()"] = (
                self.frameGeometry().width(),
                self.frameGeometry().height(),
            )
        except Exception:
            out["window"] = (0, 0)

        try:
            container = getattr(self, "_overlay_container", None)
            if container:
                out["container.rect()"] = (container.width(), container.height())
        except Exception:
            pass

        try:
            vp = self.graphics_view.viewport()
            out["graphics_view.viewport()"] = (vp.width(), vp.height())
        except Exception:
            pass

        return out

    def _get_viewport_physical_size(self):
        """Return (width, height) for scaling: prefer screen size in fullscreen, else viewport physical."""
        dpr = self._get_screen_dpr()
        if self._is_fullscreen:
            try:
                screen = self.screen()
                if screen:
                    g = screen.geometry()
                    w, h = g.width(), g.height()
                    if w > 0 and h > 0:
                        return (
                            max(1, int(round(w * dpr))),
                            max(1, int(round(h * dpr))),
                        )
            except Exception:
                pass
        vp = self.graphics_view.viewport()
        w, h = vp.width(), vp.height()
        return (max(1, int(round(w * dpr))), max(1, int(round(h * dpr))))

    def _fit_scene_in_view(self) -> None:
        """Fit the scene contents in the viewport (Qt standard: fitInView with scene rect, not view rect).
        Call after setting pixmaps and on resize. See e.g. Stack Overflow 9654222.
        """
        rect = self.scene.itemsBoundingRect()
        if rect.isEmpty():
            return
        self.scene.setSceneRect(rect)
        self.graphics_view.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)

    def _scale_and_display_pixmap(self, pixmap: QPixmap) -> None:
        """Set pixmap at original size, then fit scene in viewport via fitInView (no manual scaling)."""
        if pixmap.isNull():
            return
        vw, vh = self._get_viewport_size()
        if vw <= 0 or vh <= 0:
            QTimer.singleShot(50, lambda: self._scale_and_display_pixmap(pixmap))
            return
        self.pixmap_item.setPixmap(pixmap)
        self.pixmap_item_next.setPixmap(pixmap)
        self.pixmap_item_next.setOpacity(0.0)
        self._fit_scene_in_view()

    def _on_container_resized(self) -> None:
        """On resize: refit scene in viewport (fitInView with scene rect)."""
        self._fit_scene_in_view()

    def _update_image_display(self):
        """Update the image display: set pixmap, fit in view; optional crossfade for subsequent images."""
        if not self.current_pixmap:
            return
        vw, vh = self._get_viewport_size()
        if vw <= 0 or vh <= 0:
            QTimer.singleShot(50, self._update_image_display)
            return

        if self._first_image:
            self._scale_and_display_pixmap(self.current_pixmap)
            self._first_image = False
            return

        # Stop any running fade
        if self._fade_animation:
            self._fade_animation.stop()
            self.pixmap_item.setPixmap(self.pixmap_item_next.pixmap())
            self.pixmap_item_next.setOpacity(0.0)

        # Crossfade: new image on top layer at original size
        self.pixmap_item_next.setPixmap(self.current_pixmap)
        self.pixmap_item_next.setOpacity(0.0)
        self._fit_scene_in_view()

        self._fade_animation = QVariantAnimation(self)
        self._fade_animation.setStartValue(0.0)
        self._fade_animation.setEndValue(1.0)
        self._fade_animation.setDuration(400)
        self._fade_animation.valueChanged.connect(self._on_fade_value_changed)
        self._fade_animation.finished.connect(self._on_fade_finished)
        self._fade_animation.start()

    def _on_fade_value_changed(self, value):
        """Update overlay opacity during fade."""
        self.pixmap_item_next.setOpacity(float(value))

    def _on_fade_finished(self):
        """After fade: move new image to back layer, refit."""
        self.pixmap_item.setPixmap(self.pixmap_item_next.pixmap())
        self.pixmap_item_next.setOpacity(0.0)
        self._fit_scene_in_view()
        if self._fade_animation:
            self._fade_animation.valueChanged.disconnect(self._on_fade_value_changed)
            self._fade_animation.finished.disconnect(self._on_fade_finished)
    
    def _next_image(self):
        """Go to the next image."""
        if self.session_manager.advance_image():
            self._sync_timer_to_current_image()
            self.timer_widget.start_timer()
            self._load_current_image()
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
        self._apply_countdown_color(dur)

    def _previous_image(self):
        """Go to the previous image."""
        if self.session_manager.previous_image():
            self._sync_timer_to_current_image()
            self.timer_widget.start_timer()
            self._load_current_image()

    def _apply_countdown_color(self, remaining_seconds: int):
        """Set countdown label color: more red as remaining time approaches 0."""
        total = max(1, self.timer_widget.total_seconds)
        ratio = remaining_seconds / total  # 1 = full time left, 0 = no time
        from core.settings import settings
        dark = settings.get("ui.theme") == "dark"
        if dark:
            g, b = int(255 * ratio), int(255 * ratio)
            self.countdown_label.setStyleSheet(
                f"color: rgb(255, {g}, {b}); font-weight: bold;"
            )
        else:
            r = int(255 * (1 - ratio))
            self.countdown_label.setStyleSheet(
                f"color: rgb({r}, 0, 0); font-weight: bold;"
            )

    def _on_timer_updated(self, remaining_seconds: int):
        """Sync countdown label (top-left) with timer; color shifts to red as time approaches 0."""
        m = remaining_seconds // 60
        s = remaining_seconds % 60
        self.countdown_label.setText(f"{m:02d}:{s:02d}")
        self._apply_countdown_color(remaining_seconds)

    def _on_timer_finished(self):
        """Handle timer completion: auto-advance to next image or end session."""
        self._next_image()
    
    def resizeEvent(self, event):
        """Handle resize events; container.resized will trigger re-scale and display."""
        super().resizeEvent(event)
    
    def closeEvent(self, event):
        """Handle window close event: end session and notify parent to re-show main window."""
        if self.session_manager.session_run:
            self.session_ended.emit()
        self.session_manager.end_session()
        self.setCursor(Qt.ArrowCursor)
        super().closeEvent(event) 