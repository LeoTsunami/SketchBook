"""
Fullscreen or always-on-top slideshow window for drawing sessions.
Image full area; countdown (top-left); Escape = fullscreen->window, window->close;
Plein écran button (windowed); bottom bar: Previous, Next, Play/Pause.
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

# Set to True to print dimension debug to console (viewport, scene rect, items)
_DEBUG_SLIDESHOW_DIMENSIONS = False

# --- Qui contient quoi (hiérarchie) ---
# On utilise fitInView(scene.itemsBoundingRect(), KeepAspectRatio) pour un vrai fullscreen :
# la vue projette le rect des items sur tout le viewport. Pixmaps à taille d'origine dans la scène.
#
# QMainWindow → central widget → _OverlayContainer (fullscreen)
#   ├── QGraphicsView (fullscreen) → viewport() (fullscreen, zone peinte)
#   │     └── scene (sceneRect = items rect) → fitInView() = transformation vue pour remplir le viewport
#   │           ├── pixmap_item
#   │           └── pixmap_item_next
#   ├── countdown_frame, fullscreen_btn, controls_frame (overlays)


def _dbg(msg: str) -> None:
    if _DEBUG_SLIDESHOW_DIMENSIONS:
        print(f"[Slideshow DEBUG] {msg}")


class _OverlayContainer(QWidget):
    """Container: image full area; countdown (top-left); fullscreen btn (top-right); controls (bottom)."""

    resized = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._graphics_view = None
        self._countdown_frame = None
        self._fullscreen_btn = None
        self._controls_frame = None

    def set_content(
        self,
        graphics_view: QGraphicsView,
        countdown_frame: QFrame,
        fullscreen_btn: QPushButton,
        controls_frame: QFrame,
    ) -> None:
        self._graphics_view = graphics_view
        self._countdown_frame = countdown_frame
        self._fullscreen_btn = fullscreen_btn
        self._controls_frame = controls_frame
        graphics_view.setParent(self)
        countdown_frame.setParent(self)
        fullscreen_btn.setParent(self)
        controls_frame.setParent(self)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        r = self.rect()
        if self._graphics_view:
            self._graphics_view.setGeometry(r)
        if self._countdown_frame:
            self._countdown_frame.setGeometry(16, 16, 120, 56)
        if self._fullscreen_btn:
            self._fullscreen_btn.setGeometry(r.width() - 116, 16, 100, 40)
        if self._controls_frame:
            self._controls_frame.setGeometry(0, r.height() - 100, r.width(), 100)
        for w in (self._countdown_frame, self._fullscreen_btn, self._controls_frame):
            if w:
                w.raise_()
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

        self._setup_image_display()
        self._setup_countdown_overlay()
        self._setup_fullscreen_button()
        self._setup_controls()  # Previous, Next, Play/Pause (timer)
        self._overlay_container = _OverlayContainer(self)
        self._overlay_container.set_content(
            self.graphics_view,
            self.countdown_frame,
            self.fullscreen_btn,
            self.controls_frame,
        )
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

    def _setup_fullscreen_button(self):
        """Button to switch to fullscreen (visible only in windowed mode)."""
        self.fullscreen_btn = QPushButton("Plein écran")
        self.fullscreen_btn.setFixedSize(100, 40)
        self.fullscreen_btn.clicked.connect(self._switch_to_fullscreen)
        self.fullscreen_btn.setVisible(False)

    def _setup_controls(self):
        """Bottom bar: Previous, Next, timer (Play/Pause/Reset)."""
        self.controls_frame = QFrame()
        self.controls_frame.setFixedHeight(100)
        self.controls_frame.setVisible(False)

        bar = QHBoxLayout(self.controls_frame)
        bar.setContentsMargins(16, 8, 16, 8)
        bar.setSpacing(12)

        self.prev_button = QPushButton("← Préc.")
        self.prev_button.setFixedSize(90, 40)
        self.prev_button.clicked.connect(self._previous_image)
        bar.addWidget(self.prev_button)

        self.timer_widget = SessionTimer()
        self.timer_widget.timer_finished.connect(self._on_timer_finished)
        self.timer_widget.timer_updated.connect(self._on_timer_updated)
        bar.addWidget(self.timer_widget)

        self.next_button = QPushButton("Suiv. →")
        self.next_button.setFixedSize(90, 40)
        self.next_button.clicked.connect(self._next_image)
        bar.addWidget(self.next_button)

    def _setup_shortcuts(self):
        """Keyboard: Space = toggle bar, Left/Right = prev/next, Escape = fullscreen->window or close."""
        self.space_shortcut = QShortcut(QKeySequence("Space"), self)
        self.space_shortcut.activated.connect(self._toggle_controls)
        self.next_shortcut = QShortcut(QKeySequence("Right"), self)
        self.next_shortcut.activated.connect(self._next_image)
        self.prev_shortcut = QShortcut(QKeySequence("Left"), self)
        self.prev_shortcut.activated.connect(self._previous_image)
        self.exit_shortcut = QShortcut(QKeySequence("Escape"), self)
        self.exit_shortcut.activated.connect(self._on_escape)
    
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
            self.fullscreen_btn.setVisible(False)
        else:
            self.setWindowState(Qt.WindowNoState)
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
            self.fullscreen_btn.setVisible(True)
            # Size window to 80% of user screen, centered
            screen = QGuiApplication.primaryScreen()
            if screen:
                ag = screen.availableGeometry()
                w = int(ag.width() * 0.8)
                h = int(ag.height() * 0.8)
                x = ag.x() + (ag.width() - w) // 2
                y = ag.y() + (ag.height() - h) // 2
                self.setGeometry(x, y, w, h)

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

        # Show first, then set fullscreen (required on Windows for fullscreen to apply)
        self.show()
        self.raise_()
        self.activateWindow()
        if self._is_fullscreen:
            self.setWindowState(Qt.WindowFullScreen)
            # Re-layout after fullscreen: viewport size is only final after resize (Qt/Windows)
            def _delayed_fit_after_fullscreen():
                _dbg("delayed (100ms) fitInView after setWindowState(WindowFullScreen)")
                self._fit_scene_in_view()
            QTimer.singleShot(100, _delayed_fit_after_fullscreen)
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
        """Return (width, height) in logical pixels. Use container size if viewport not yet sized (e.g. before show/fullscreen)."""
        vp = self.graphics_view.viewport()
        vw, vh = vp.width(), vp.height()
        if vw > 0 and vh > 0:
            return (vw, vh)
        # Fallback: container rect (viewport may be 0 before show/fullscreen resize)
        r = self._overlay_container.rect()
        return (max(1, r.width()), max(1, r.height()))

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
        """Fit the scene (items rect) in the viewport via fitInView. Real fullscreen (Qt does scale/center)."""
        rect = self.scene.itemsBoundingRect()
        if rect.isEmpty():
            return
        self.scene.setSceneRect(rect)
        self.graphics_view.fitInView(rect, Qt.KeepAspectRatio)
        self._debug_dimensions("_fit_scene_in_view")

    def _debug_dimensions(self, label: str) -> None:
        """Print viewport, scene rect, itemsBoundingRect (fitInView maps this to viewport)."""
        if not _DEBUG_SLIDESHOW_DIMENSIONS:
            return
        vp = self.graphics_view.viewport()
        vpw, vph = vp.width(), vp.height()
        sr = self.scene.sceneRect()
        ibr = self.scene.itemsBoundingRect()
        _dbg(f"--- {label} ---")
        _dbg(f"viewport: ({vpw}, {vph})  sceneRect: ({sr.width():.1f}, {sr.height():.1f})  itemsBoundingRect: ({ibr.width():.1f}, {ibr.height():.1f})")
        for name, item in [("pixmap_item", self.pixmap_item), ("pixmap_item_next", self.pixmap_item_next)]:
            pix = item.pixmap()
            if pix.isNull():
                _dbg(f"{name}: pixmap=null")
            else:
                _dbg(f"{name}: pixmap=({pix.width()}, {pix.height()})")
        _dbg("")

    def _scale_and_display_pixmap(self, pixmap: QPixmap) -> None:
        """Set pixmap at original size on both layers, then fitInView (real fullscreen)."""
        if pixmap.isNull():
            return
        vw, vh = self._get_viewport_size()
        if vw <= 0 or vh <= 0:
            QTimer.singleShot(50, lambda: self._scale_and_display_pixmap(pixmap))
            return
        self.pixmap_item.setPixmap(pixmap)
        self.pixmap_item_next.setPixmap(pixmap)
        self.pixmap_item_next.setOpacity(0.0)
        self.pixmap_item.setScale(1.0)
        self.pixmap_item.setPos(0, 0)
        self.pixmap_item_next.setScale(1.0)
        self.pixmap_item_next.setPos(0, 0)
        self._fit_scene_in_view()

    def _on_container_resized(self) -> None:
        """On resize: refit scene in viewport (fitInView)."""
        _dbg("_on_container_resized: fitInView")
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

        # Crossfade: set new image, fitInView (real fullscreen), then fade after paint (évite resize pendant le fondu).
        self.pixmap_item_next.setPixmap(self.current_pixmap)
        self.pixmap_item_next.setOpacity(0.0)
        self.pixmap_item_next.setScale(1.0)
        self.pixmap_item_next.setPos(0, 0)
        self._fit_scene_in_view()
        self.graphics_view.viewport().repaint()
        QApplication.processEvents()
        QTimer.singleShot(80, self._start_fade_animation)

    def _start_fade_animation(self):
        """Start the crossfade (called after resize/repaint so image is at correct size)."""
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

    def _on_escape(self):
        """Escape: fullscreen -> switch to window; window -> close session."""
        if self._is_fullscreen:
            self._switch_to_window()
        else:
            self.close()

    def _switch_to_window(self):
        """Leave fullscreen: switch to window always on top, maximized (title bar + close X visible)."""
        self._is_fullscreen = False
        # Keep existing flags and ensure close/minimize/maximize buttons are available
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowStaysOnTopHint
            | Qt.WindowCloseButtonHint
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
        )
        self.setWindowState(Qt.WindowMaximized)
        self.show()
        self.fullscreen_btn.setVisible(True)
        self._fit_scene_in_view()

    def _switch_to_fullscreen(self):
        """Switch to fullscreen from windowed mode."""
        self._is_fullscreen = True
        self.fullscreen_btn.setVisible(False)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.setWindowState(Qt.WindowFullScreen)
        self.show()
        self._fit_scene_in_view()

    def _toggle_controls(self):
        """Show/hide bottom bar (Previous, Next, Play/Pause)."""
        self.controls_frame.setVisible(not self.controls_frame.isVisible())
        if self.controls_frame.isVisible():
            self.setCursor(Qt.ArrowCursor)
        else:
            self.setCursor(Qt.BlankCursor)

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
    
    def showEvent(self, event):
        """Re-fit when window is shown so viewport has final size."""
        super().showEvent(event)
        _dbg("showEvent: scheduling fitInView in 0ms")
        QTimer.singleShot(0, self._fit_scene_in_view)

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