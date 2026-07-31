"""
Fullscreen or always-on-top slideshow window for drawing sessions.
Image full area; countdown (top-left); Escape = fullscreen->window, window->close;
Plein écran button (windowed); bottom bar: Previous, Next, Play/Pause.
"""

import time
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
    QStyle,
)
from qtpy.QtCore import (
    Qt,
    QTimer,
    Signal,
    QThreadPool,
    QVariantAnimation,
    QRectF,
    QEvent,
    QSize,
    QPoint,
)
from qtpy.QtGui import (
    QPixmap,
    QKeySequence,
    QShortcut,
    QFont,
    QPainter,
    QTransform,
    QGuiApplication,
    QKeyEvent,
    QIcon,
    QImage,
    QCursor,
)
from core.session_manager import SessionManager, load_course_config
from core.image_manager import ImageManager
from gui.session_timer import SessionTimer
from gui.image_loader_worker import ImageLoaderWorker
from gui.turnaround_scrub import (
    is_turnaround_meta,
    load_pose_pixmap,
    scrub_index_from_drag,
    turnaround_pose_setup,
)
from gui.turnaround_badge import TurnaroundViewerHintOverlay
from gui.icon_utils import invert_icon
from gui.image_viewer_window import ImageViewerWindow
from gui.window_chrome import (
    WindowChromeBar,
    apply_glass_button_style,
    enable_frameless_window,
)
from gui.thumbnail_fitting import FitMode
from gui.slideshow_image_layout import (
    display_scale_factor,
    layout_pixmap_item_in_rect,
    scene_display_rect,
)
from gui.session_countdown_sound import SessionCountdownSound
from utils.keep_awake import prevent_sleep, allow_sleep


class _SessionImageViewerWindow(ImageViewerWindow):
    """
    Same window as double-click on the grid (crop, rotate, zoom).
    Notifies the slideshow when closed so the slide reloads from disk.
    """

    def __init__(self, image_manager: ImageManager, slideshow: "SlideshowWindow"):
        self._slideshow = slideshow
        self._notify_slideshow_on_close: bool = True
        super().__init__(image_manager, slideshow)

    def closeEvent(self, event):
        """Restore session chrome and reload the current slide."""
        if self._notify_slideshow_on_close:
            self._slideshow._on_session_viewer_closed()
        super().closeEvent(event)


# Debug flags: set to True to enable debug output
# These flags control debug functions below - useful for troubleshooting
_DEBUG_SLIDESHOW_DIMENSIONS = (
    False  # Print dimension debug (viewport, scene rect, items)
)
_DEBUG_SPACE_PLAYPAUSE = False  # Print Space key / play-pause toggle debug
# UI auto-hide: show overlays + cursor on key/mouse, hide after inactivity
_UI_HIDE_AFTER_MS = 2000
# Get ready screen duration (seconds); countdown ticks 3, 2, 1
_GET_READY_DURATION_SEC = 3
# Course phase title screen duration (seconds); countdown ticks 5, 4, 3, 2, 1
_PHASE_TITLE_DURATION_SEC = 5

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
    """
    Debug function for slideshow dimensions (controlled by _DEBUG_SLIDESHOW_DIMENSIONS flag).

    Args:
        msg: Debug message to print.
    """
    if _DEBUG_SLIDESHOW_DIMENSIONS:
        pass  # debug: msg


def _dbg_space(msg: str) -> None:
    """
    Debug function for Space key / play-pause toggle (controlled by _DEBUG_SPACE_PLAYPAUSE flag).

    Args:
        msg: Debug message to print.
    """
    if _DEBUG_SPACE_PLAYPAUSE:
        pass  # debug: msg


def _get_media_icons():
    """Return (play_icon, pause_icon) from QStyle if available, inverted; else (None, None)."""
    style = QApplication.style()
    if style is None:
        return None, None
    play_icon = None
    pause_icon = None
    sp_play = getattr(QStyle, "SP_MediaPlay", None)
    sp_pause = getattr(QStyle, "SP_MediaPause", None)
    if sp_play is not None:
        try:
            play_icon = invert_icon(style.standardIcon(sp_play), 32)
        except Exception:
            pass
    if sp_pause is not None:
        try:
            pause_icon = invert_icon(style.standardIcon(sp_pause), 32)
        except Exception:
            pass
    return play_icon, pause_icon


class _OverlayContainer(QWidget):
    """Container: image full area; countdown; fullscreen btn; controls; get_ready and phase_title overlays."""

    resized = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sessionOverlayContainer")
        self._urgency_tint = None
        self._graphics_view = None
        self._countdown_frame = None
        self._fullscreen_btn = None
        self._controls_frame = None
        self._get_ready_frame = None
        self._phase_title_frame = None

    def set_content(
        self,
        graphics_view: QGraphicsView,
        countdown_frame: QFrame,
        fullscreen_btn: QPushButton,
        controls_frame: QFrame,
        get_ready_frame: Optional[QFrame] = None,
        phase_title_frame: Optional[QFrame] = None,
        urgency_tint: Optional[QWidget] = None,
    ) -> None:
        self._graphics_view = graphics_view
        self._countdown_frame = countdown_frame
        self._fullscreen_btn = fullscreen_btn
        self._controls_frame = controls_frame
        self._get_ready_frame = get_ready_frame
        self._phase_title_frame = phase_title_frame
        self._urgency_tint = urgency_tint
        if urgency_tint:
            urgency_tint.setParent(self)
        graphics_view.setParent(self)
        countdown_frame.setParent(self)
        fullscreen_btn.setParent(self)
        controls_frame.setParent(self)
        if get_ready_frame:
            get_ready_frame.setParent(self)
        if phase_title_frame:
            phase_title_frame.setParent(self)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        r = self.rect()
        if self._urgency_tint:
            self._urgency_tint.setGeometry(r)
            self._urgency_tint.lower()
        if self._graphics_view:
            self._graphics_view.setGeometry(r)
            self._graphics_view.raise_()
        if self._countdown_frame:
            self._countdown_frame.setGeometry(16, 16, 120, 56)
        if self._fullscreen_btn:
            self._fullscreen_btn.setGeometry(r.width() - 116, 16, 100, 40)
        if self._controls_frame:
            self._controls_frame.setGeometry(0, r.height() - 70, r.width(), 70)
        if self._get_ready_frame:
            self._get_ready_frame.setGeometry(r)
        if self._phase_title_frame:
            self._phase_title_frame.setGeometry(r)
        badge = getattr(self, "_turnaround_badge", None)
        if badge is not None:
            bottom_offset = 0
            if self._controls_frame and self._controls_frame.isVisible():
                bottom_offset = self._controls_frame.height() + 12
            badge.reposition(self, bottom_offset_y=bottom_offset)
        for w in (
            self._countdown_frame,
            self._fullscreen_btn,
            self._controls_frame,
            self._get_ready_frame,
            self._phase_title_frame,
        ):
            if w:
                w.raise_()
        if badge is not None and badge.isVisible():
            badge.raise_()
        self.resized.emit()


class SlideshowWindow(QMainWindow):
    """Fullscreen or always-on-top slideshow window for drawing sessions."""

    session_ended = Signal()  # Emitted when session ends (user closed or run finished)

    def __init__(
        self, session_manager: SessionManager, image_manager: ImageManager, parent=None
    ):
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
        # Initialize critical state before installing any event filters.
        self._init_complete: bool = False
        self._is_fullscreen = False
        self._session_viewer_open: bool = False
        self._session_image_viewer: Optional[_SessionImageViewerWindow] = None
        self._last_play_pause_toggle_time: float = 0.0
        self._resize_margin_px: int = 6
        self._turnaround_pose_ids: List[str] = []
        self._turnaround_pose_index: int = 0
        self._turnaround_root_id: Optional[str] = None
        self._turnaround_scrubbing: bool = False
        self._turnaround_scrub_start_x: float = 0.0
        self._turnaround_scrub_start_index: int = 0
        self._showing_get_ready: bool = False
        self._showing_phase_title: bool = False

        self.setWindowTitle("SketchBook - Drawing Session")
        enable_frameless_window(self)
        self.setMouseTracking(True)
        self.setCursor(
            Qt.BlankCursor
        )  # Hide cursor during session; window state set in start_session

        central_widget = QWidget()
        central_widget.setObjectName("slideshowCentralWidget")
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._chrome_bar = WindowChromeBar("Drawing Session", self)
        layout.addWidget(self._chrome_bar, 0)

        self._setup_image_display()
        self._setup_countdown_overlay()
        self._setup_get_ready_overlay()
        self._setup_phase_title_overlay()
        self._setup_fullscreen_button()
        self._setup_controls()  # Previous, Next, Play/Pause (timer) + Éditer
        self._urgency_tint_overlay = QWidget()
        self._urgency_tint_overlay.setObjectName("sessionUrgencyTint")
        self._urgency_tint_overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._urgency_tint_overlay.setAttribute(Qt.WA_StyledBackground, True)
        self._urgency_tint_overlay.hide()
        self._overlay_container = _OverlayContainer(self)
        self._overlay_container.set_content(
            self.graphics_view,
            self.countdown_frame,
            self.fullscreen_btn,
            self.controls_frame,
            self.get_ready_frame,
            self.phase_title_frame,
            urgency_tint=self._urgency_tint_overlay,
        )
        self._overlay_container.resized.connect(self._on_container_resized)
        layout.addWidget(self._overlay_container, 1)
        self._turnaround_badge = TurnaroundViewerHintOverlay(self._overlay_container)
        self._overlay_container._turnaround_badge = self._turnaround_badge

        self._setup_ui_auto_hide()  # Show overlays + cursor on key/mouse; hide after 2s inactivity
        self._overlay_container.installEventFilter(self)
        for w in (self.countdown_frame, self.fullscreen_btn, self.controls_frame):
            w.installEventFilter(self)  # Catch mouse move over overlay area

        self._setup_shortcuts()

        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(2)
        self.current_pixmap: Optional[QPixmap] = None
        self._first_image = True
        self._fade_animation: Optional[QVariantAnimation] = None
        self._fade_in_progress: bool = False
        self._hq_reload_timer = QTimer(self)
        self._hq_reload_timer.setSingleShot(True)
        self._hq_reload_timer.setInterval(200)
        self._hq_reload_timer.timeout.connect(self._maybe_reload_current_image_for_scale)
        # Title screen countdown (Get ready / phase): ticks every second, then calls done callback
        self._title_countdown_timer = QTimer(self)
        self._title_countdown_timer.setInterval(1000)
        self._title_countdown_timer.timeout.connect(self._on_title_countdown_tick)
        self._title_countdown_remaining: int = 0
        self._title_countdown_total: int = 1  # Duration (sec) for color ratio
        self._title_countdown_done_callback = (
            None  # Callable[[], None] when countdown reaches 0
        )
        # Step navigation: Get ready, phase titles and images are all steps (Next/Previous move one step)

        self._apply_theme()
        self._init_complete = True

    def _setup_image_display(self):
        """Set up the image display (two layers for crossfade). Will be placed full-size in container."""
        self.graphics_view = QGraphicsView()
        self.graphics_view.setObjectName("sessionGraphicsView")
        self.graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graphics_view.setRenderHint(QPainter.SmoothPixmapTransform)
        self.graphics_view.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.graphics_view.setAlignment(Qt.AlignCenter)
        self.graphics_view.setFrameShape(QFrame.NoFrame)
        self.graphics_view.setBackgroundBrush(Qt.transparent)
        self.graphics_view.setStyleSheet("""
            QGraphicsView {
                background: transparent;
                border: none;
            }
            """)
        self.graphics_view.viewport().setAutoFillBackground(False)
        self.graphics_view.viewport().setStyleSheet("background: transparent;")
        self.graphics_view.setFocusPolicy(
            Qt.StrongFocus
        )  # Reason: so Space is received by view first
        self.graphics_view.setMouseTracking(
            True
        )  # Reason: receive MouseMove without button pressed (show controls)
        self.graphics_view.viewport().setMouseTracking(
            True
        )  # QGraphicsView forwards to viewport

        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(Qt.transparent)
        self.graphics_view.setScene(self.scene)

        self.pixmap_item = QGraphicsPixmapItem()
        self.pixmap_item.setTransformationMode(Qt.SmoothTransformation)
        self.scene.addItem(self.pixmap_item)
        self.pixmap_item_next = QGraphicsPixmapItem()
        self.pixmap_item_next.setTransformationMode(Qt.SmoothTransformation)
        self.pixmap_item_next.setZValue(1)
        self.pixmap_item_next.setOpacity(0.0)
        self.scene.addItem(self.pixmap_item_next)
        # So Space is handled even when focus is on the view (first keypress)
        self.graphics_view.installEventFilter(self)
        # Mouse events go to the viewport, not the view; install filter there to catch MouseMove
        self.graphics_view.viewport().installEventFilter(self)

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

    def _setup_get_ready_overlay(self):
        """Full-screen overlay: 'Get ready, your drawing session is about to begin' (3s at session start)."""
        self.get_ready_frame = QFrame()
        self.get_ready_frame.setObjectName("getReadyFrame")
        self.get_ready_frame.setStyleSheet("background: rgba(0,0,0,0.85);")
        lay = QVBoxLayout(self.get_ready_frame)
        lay.setAlignment(Qt.AlignCenter)
        self.get_ready_label = QLabel(
            "Get ready, your drawing session is about to begin"
        )
        self.get_ready_label.setAlignment(Qt.AlignCenter)
        self.get_ready_label.setWordWrap(True)
        font = QFont()
        font.setPointSize(44)
        font.setBold(True)
        self.get_ready_label.setFont(font)
        lay.addWidget(self.get_ready_label)
        self.get_ready_frame.setVisible(False)

    def _setup_phase_title_overlay(self):
        """Full-screen overlay for course phases: title (e.g. WarmUp) + 'X Images of Y'."""
        self.phase_title_frame = QFrame()
        self.phase_title_frame.setObjectName("phaseTitleFrame")
        self.phase_title_frame.setStyleSheet("background: rgba(0,0,0,0.85);")
        lay = QVBoxLayout(self.phase_title_frame)
        lay.setSpacing(16)
        lay.setAlignment(Qt.AlignCenter)
        self.phase_title_label = QLabel("")
        self.phase_title_label.setAlignment(Qt.AlignCenter)
        font_title = QFont()
        font_title.setPointSize(52)
        font_title.setBold(True)
        self.phase_title_label.setFont(font_title)
        lay.addWidget(self.phase_title_label)
        self.phase_subtitle_label = QLabel("")
        self.phase_subtitle_label.setAlignment(Qt.AlignCenter)
        self.phase_subtitle_label.setWordWrap(True)
        font_sub = QFont()
        font_sub.setPointSize(28)
        self.phase_subtitle_label.setFont(font_sub)
        lay.addWidget(self.phase_subtitle_label)
        self.phase_title_frame.setVisible(False)

    def _setup_fullscreen_button(self):
        """Button to switch to fullscreen (visible only in windowed mode)."""
        self.fullscreen_btn = QPushButton("Plein écran")
        self.fullscreen_btn.setFixedSize(100, 40)
        self.fullscreen_btn.setFocusPolicy(Qt.NoFocus)  # Reason: Space must go to view
        self.fullscreen_btn.clicked.connect(self._switch_to_fullscreen)
        apply_glass_button_style(self.fullscreen_btn, primary=True)
        self.fullscreen_btn.setVisible(False)

    def _setup_controls(self):
        """Bottom bar: Previous, Play/Pause, Next; Éditer opens the same viewer as grid double-click."""
        self.controls_frame = QFrame()
        self.controls_frame.setObjectName("controlsFrame")
        self.controls_frame.setMinimumHeight(70)
        self.controls_frame.setVisible(True)

        bar = QHBoxLayout(self.controls_frame)
        bar.setContentsMargins(16, 8, 16, 8)
        bar.setSpacing(12)

        self.prev_button = QPushButton("← Préc.")
        self.prev_button.setFixedSize(90, 40)
        self.prev_button.setFocusPolicy(
            Qt.NoFocus
        )  # Reason: Space must go to view, not trigger button
        self.prev_button.clicked.connect(self._previous_image)
        apply_glass_button_style(self.prev_button)
        bar.addWidget(self.prev_button)

        # Play/Pause only (timer logic runs in hidden SessionTimer; countdown stays top-left)
        self.play_pause_btn = QPushButton("Play")
        self.play_pause_btn.setObjectName("playPauseBtn")
        self.play_pause_btn.setFixedSize(90, 40)
        self.play_pause_btn.setFocusPolicy(
            Qt.NoFocus
        )  # Reason: Space must go to view, not trigger button
        self.play_pause_btn.clicked.connect(self._on_play_pause_clicked)
        apply_glass_button_style(self.play_pause_btn, primary=True)
        bar.addWidget(self.play_pause_btn)
        self._icon_play, self._icon_pause = _get_media_icons()

        self.next_button = QPushButton("Suiv. →")
        self.next_button.setFixedSize(90, 40)
        self.next_button.setFocusPolicy(
            Qt.NoFocus
        )  # Reason: Space must go to view, not trigger button
        self.next_button.clicked.connect(self._next_image)
        apply_glass_button_style(self.next_button)
        bar.addWidget(self.next_button)

        bar.addStretch()

        self.edit_session_btn = QPushButton("Éditer")
        self.edit_session_btn.setFixedSize(90, 40)
        self.edit_session_btn.setFocusPolicy(Qt.NoFocus)
        self.edit_session_btn.setToolTip(
            "Même visionneuse que le double-clic sur la grille (crop, rotation)"
        )
        self.edit_session_btn.clicked.connect(self._on_session_edit_clicked)
        apply_glass_button_style(self.edit_session_btn)
        self.edit_session_btn.hide()
        bar.addWidget(self.edit_session_btn)

        # Timer widget: hidden, drives countdown (top-left) and session logic (timer_finished)
        self.timer_widget = SessionTimer(self)
        self.timer_widget.setVisible(False)
        self.timer_widget.timer_finished.connect(self._on_timer_finished)
        self.timer_widget.timer_updated.connect(self._on_timer_updated)
        self._countdown_sound = SessionCountdownSound(self)

    def _set_session_nav_visible(self, visible: bool) -> None:
        """Show or hide Précédent / Pause / Suivant (Éditer handled separately)."""
        self.prev_button.setVisible(visible)
        self.play_pause_btn.setVisible(visible)
        self.next_button.setVisible(visible)

    def _on_session_edit_clicked(self) -> None:
        """Open the grid image viewer (crop, rotate) while keeping the session paused."""
        image_id = self.session_manager.get_current_image_id()
        if not image_id:
            return
        self._session_viewer_open = True
        self._set_session_nav_visible(False)
        self.edit_session_btn.hide()
        if self._session_image_viewer is None:
            self._session_image_viewer = _SessionImageViewerWindow(
                self.image_manager, self
            )
        self._session_image_viewer.set_image(image_id)
        self._session_image_viewer.show()
        self._session_image_viewer.raise_()
        self._session_image_viewer.activateWindow()

    def _on_session_viewer_closed(self) -> None:
        """Reload slide after the user closed the editor; restore chrome; stay paused."""
        if not self._session_viewer_open:
            return
        self._session_viewer_open = False
        self.current_pixmap = None
        self._do_load_current_image()
        self._sync_session_edit_visibility()

    def _close_session_viewer_if_open(self) -> None:
        """Close the image viewer without duplicating reload (closeEvent calls _on_session_viewer_closed)."""
        if self._session_image_viewer and self._session_image_viewer.isVisible():
            self._session_image_viewer.close()

    def _sync_session_edit_visibility(self) -> None:
        """Éditer visible only when paused on an image step; chrome hidden while viewer is open."""
        if not hasattr(self, "edit_session_btn"):
            return
        paused = self.timer_widget.is_running and self.timer_widget.is_paused
        has_image = self.session_manager.get_current_image_id() is not None
        can_edit = (
            paused
            and not self._showing_get_ready
            and not self._showing_phase_title
            and not self._fade_in_progress
            and has_image
        )
        if self._session_viewer_open:
            self._set_session_nav_visible(False)
            self.edit_session_btn.hide()
            return
        self._set_session_nav_visible(True)
        self.edit_session_btn.setVisible(can_edit)

    def _setup_ui_auto_hide(self):
        """Setup 2s inactivity timer; show overlays + cursor on key/mouse, hide after inactivity (no fade)."""
        self._hide_ui_timer = QTimer(self)
        self._hide_ui_timer.setSingleShot(True)
        self._hide_ui_timer.timeout.connect(self._hide_ui)

    def _show_ui_and_restart_timer(self):
        """Show controls and cursor, (re)start 2s hide timer; countdown (timer) is always visible."""
        self._hide_ui_timer.stop()
        self.countdown_frame.setVisible(True)  # Timer always visible
        self.fullscreen_btn.setVisible(not self._is_fullscreen)  # Only in windowed mode
        self.controls_frame.setVisible(True)
        if self._is_fullscreen:
            self.setCursor(Qt.ArrowCursor)
        else:
            # Reason: keep resize cursor feedback on window edges while overlays are shown.
            self._update_resize_cursor(self.mapFromGlobal(QCursor.pos()))
        self._hide_ui_timer.start(_UI_HIDE_AFTER_MS)
        self._reposition_turnaround_hint()

    def _hide_ui(self):
        """Hide controls and cursor after inactivity; countdown (timer) stays visible."""
        if self._session_viewer_open:
            self._hide_ui_timer.start(_UI_HIDE_AFTER_MS)
            return
        self.fullscreen_btn.setVisible(False)
        self.controls_frame.setVisible(False)
        self.setCursor(Qt.BlankCursor)
        self._reposition_turnaround_hint()

    def _reposition_turnaround_hint(self) -> None:
        """Keep the turnaround hint centered above session controls when visible."""
        badge = getattr(self, "_turnaround_badge", None)
        if badge is None or not badge.isVisible():
            return
        bottom_offset = 0
        if self.controls_frame.isVisible():
            bottom_offset = self.controls_frame.height() + 12
        badge.reposition(self._overlay_container, bottom_offset_y=bottom_offset)

    def _setup_shortcuts(self):
        """Keyboard: Space = toggle pause/play (via eventFilter/keyPressEvent only, to avoid double trigger). Left/Right = prev/next, Escape = fullscreen->window or close."""
        # Do NOT use QShortcut for Space: it would fire in addition to eventFilter and toggle twice
        self.next_shortcut = QShortcut(QKeySequence("Right"), self)
        self.next_shortcut.activated.connect(self._next_image)
        self.prev_shortcut = QShortcut(QKeySequence("Left"), self)
        self.prev_shortcut.activated.connect(self._previous_image)
        self.exit_shortcut = QShortcut(QKeySequence("Escape"), self)
        self.exit_shortcut.activated.connect(self._on_escape)

    def _apply_theme(self):
        """Apply theme-aware styles."""
        from core.settings import settings
        from gui.theme_qss_utils import extract_qmainwindow_rule_from_theme

        theme_key = settings.get("ui.theme", "dark")
        qmw_rule = extract_qmainwindow_rule_from_theme(theme_key)
        if not qmw_rule:
            qmw_rule = """
                QMainWindow {
                    background-color: #1e1e1e;
                    color: #ffffff;
                }
            """
        # Match main window chrome; transparent stack so gradient/solid shows in letterbox.
        session_chrome = qmw_rule + """
                QWidget#slideshowCentralWidget {
                    background: transparent;
                }
                QWidget#sessionOverlayContainer {
                    background: transparent;
                }
                QGraphicsView#sessionGraphicsView {
                    background: transparent;
                    border: none;
                }
            """

        if theme_key == "dark":
            # Dark theme (countdown frame uses same as controls for visibility)
            self.setStyleSheet(session_chrome + """
                QFrame {
                    background-color: rgba(30, 30, 30, 0.9);
                    border: none;
                }
                QFrame#countdownFrame {
                    background-color: rgba(30, 30, 30, 0.85);
                    border-radius: 6px;
                }
                QFrame#controlsFrame {
                    background: transparent;
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
                QPushButton#playPauseBtnPaused {
                    background-color: #4b6eaf;
                    border: 1px solid #5a7fbf;
                }
                QPushButton#playPauseBtnPaused:hover {
                    background-color: #5a7fbf;
                }
                QFrame#getReadyFrame QLabel, QFrame#phaseTitleFrame QLabel {
                    color: #ffffff;
                }
            """)
        else:
            # Light theme
            self.setStyleSheet(session_chrome + """
                QFrame {
                    background-color: rgba(255, 255, 255, 0.9);
                    border: none;
                }
                QFrame#countdownFrame {
                    background-color: rgba(255, 255, 255, 0.85);
                    border-radius: 6px;
                }
                QFrame#controlsFrame {
                    background: transparent;
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
                QPushButton#playPauseBtnPaused {
                    background-color: #4b6eaf;
                    color: #ffffff;
                    border: 1px solid #3d5a8c;
                }
                QPushButton#playPauseBtnPaused:hover {
                    background-color: #5a7fbf;
                }
                QFrame#getReadyFrame QLabel, QFrame#phaseTitleFrame QLabel {
                    color: #ffffff;
                }
            """)
        if hasattr(self, "graphics_view"):
            self._apply_session_urgency_tint(0.0)

    def start_session(
        self,
        image_ids: List[str],
        session_type: str,
        course_duration_minutes: Optional[int] = None,
        interval_seconds: Optional[int] = None,
        window_mode: str = "FullScreen",
        course_config_path: Optional[Path] = None,
        shuffle_iteration: int = 0,
        use_exact_order: bool = False,
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
            shuffle_iteration: Iteration counter for shuffle (matches grid shuffle counter).

        Returns:
            True if session started (run has at least one image), False otherwise.
        """
        course_config: Optional[Dict[str, Any]] = None
        if (
            session_type == "Course"
            and course_config_path
            and course_config_path.exists()
        ):
            course_config = load_course_config(course_config_path)

        ok = self.session_manager.start_session(
            image_ids=image_ids,
            session_type=session_type,
            course_duration_minutes=course_duration_minutes,
            interval_seconds=interval_seconds,
            window_mode=window_mode,
            course_config=course_config,
            shuffle_iteration=shuffle_iteration,
            use_exact_order=use_exact_order,
        )
        if not ok:
            return False

        self._session_type = session_type

        # Always start in PLAY: clear previous timer state
        self.timer_widget.stop_timer()

        # Window mode: FullScreen or Window always on top
        self._is_fullscreen = window_mode != "Window always on top"
        self._chrome_bar.setVisible(not self._is_fullscreen)
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

        # Countdown display for first image (timer starts after "Get ready")
        dur = self.session_manager.get_current_duration()
        self.timer_widget.set_duration(dur)
        m, s = dur // 60, dur % 60
        self.countdown_label.setText(f"{m:02d}:{s:02d}")
        self._apply_countdown_color(dur)

        self._first_image = True
        self.phase_title_frame.setVisible(False)
        self.get_ready_frame.setVisible(True)
        self.countdown_frame.raise_()  # Timer visible during title screens
        self._showing_get_ready = True
        self._showing_phase_title = False

        # Show window first; start 3s countdown (3, 2, 1) then hide "Get ready" and start timer + first image
        self.show()
        self.raise_()
        self.activateWindow()
        QTimer.singleShot(0, self._give_focus_to_view)
        _dbg_space(f"session started, focusWidget={QApplication.focusWidget()}")
        self._show_ui_and_restart_timer()
        if self._is_fullscreen:
            self.setWindowState(Qt.WindowFullScreen)

            def _delayed_fit_after_fullscreen():
                _dbg("delayed (100ms) fitInView after setWindowState(WindowFullScreen)")
                self._fit_scene_in_view()

            QTimer.singleShot(100, _delayed_fit_after_fullscreen)
        self._start_title_countdown(_GET_READY_DURATION_SEC, self._on_get_ready_done)
        prevent_sleep()  # Keep display and system awake during session
        return True

    def _start_title_countdown(self, duration_sec: int, on_done) -> None:
        """Start countdown on title screen: update label every second, then call on_done."""
        self._title_countdown_timer.stop()
        self._title_countdown_total = max(1, duration_sec)
        self._title_countdown_remaining = self._title_countdown_total
        self._title_countdown_done_callback = on_done
        self._update_title_countdown_label()
        self._apply_countdown_color(
            self._title_countdown_remaining, self._title_countdown_total
        )
        self._title_countdown_timer.start()

    def _on_title_countdown_tick(self) -> None:
        """Every second during title screen: decrement and update label; at 0 call done callback."""
        self._title_countdown_remaining -= 1
        if self._title_countdown_remaining <= 0:
            self._title_countdown_timer.stop()
            self._title_countdown_remaining = 0
            cb = self._title_countdown_done_callback
            self._title_countdown_done_callback = None
            if cb:
                cb()
            return
        self._update_title_countdown_label()
        self._apply_countdown_color(
            self._title_countdown_remaining, self._title_countdown_total
        )

    def _update_title_countdown_label(self) -> None:
        """Set countdown label to current title countdown (e.g. 00:03)."""
        s = self._title_countdown_remaining
        self.countdown_label.setText(f"00:{s:02d}")

    def _on_get_ready_done(self):
        """After 3s countdown 'Get ready': hide overlay, start timer (PLAY), load first image (or phase title)."""
        self.get_ready_frame.setVisible(False)
        self._showing_get_ready = False
        self.timer_widget.start_timer()
        self._sync_play_pause_button()
        self._load_current_image()

    def _cancel_get_ready_if_visible(self) -> None:
        """Stop Get ready countdown and hide overlay when user clicks Next."""
        self._title_countdown_timer.stop()
        self._title_countdown_done_callback = None
        if self.get_ready_frame.isVisible():
            self.get_ready_frame.setVisible(False)
        self._showing_get_ready = False

    def _cancel_phase_title_if_visible(self) -> None:
        """Stop phase title countdown and hide overlay when user navigates with Next/Previous."""
        self._title_countdown_timer.stop()
        self._title_countdown_done_callback = None
        if self.phase_title_frame.isVisible():
            self.phase_title_frame.setVisible(False)
        self._showing_phase_title = False

    def _load_current_image(self, skip_phase_title: bool = False):
        """Load the current step: in Course mode show phase title first if at phase start, unless skip_phase_title."""
        idx = self.session_manager.get_run_index()
        phase_info = self.session_manager.get_phase_info_at_index(idx)
        if phase_info is not None and not skip_phase_title:
            self._showing_phase_title = True
            phase_name, count, duration_sec = phase_info
            if duration_sec < 60:
                timing = f"{duration_sec}s"
            elif duration_sec % 60 == 0:
                timing = f"{duration_sec // 60} min"
            else:
                timing = f"{duration_sec // 60} min {duration_sec % 60}"
            self.phase_title_label.setText(phase_name)
            self.phase_subtitle_label.setText(f"{count} Images of {timing}")
            self.phase_title_frame.setVisible(True)
            self.phase_title_frame.raise_()
            self.countdown_frame.raise_()  # Timer visible during phase title
            self.timer_widget.pause_timer()  # Pause during title so first image gets full duration
            self._start_title_countdown(
                _PHASE_TITLE_DURATION_SEC, self._on_phase_title_done
            )
            return
        self._showing_phase_title = False
        self._do_load_current_image()

    def _on_phase_title_done(self):
        """After phase title countdown: hide overlay, sync timer to current image, resume, load image."""
        self.phase_title_frame.setVisible(False)
        self._showing_phase_title = False
        self._sync_timer_to_current_image()
        self.timer_widget.start_timer()
        self._sync_play_pause_button()
        self._do_load_current_image()

    def _do_load_current_image(self):
        """Load the current image for display (worker)."""
        image_id = self.session_manager.get_current_image_id()
        if not image_id:
            return

        # Get image metadata
        metadata = self.image_manager.get_image_metadata(image_id)
        if not metadata:
            return

        poses, middle = turnaround_pose_setup(self.image_manager, image_id)
        self._turnaround_pose_ids = poses
        self._turnaround_pose_index = middle
        self._turnaround_root_id = image_id if is_turnaround_meta(metadata) else None
        self._turnaround_scrubbing = False
        if hasattr(self, "_turnaround_badge"):
            self._turnaround_badge.set_visible_for_turnaround(
                self._turnaround_root_id is not None
            )

        # Load first pose for turnaround roots; otherwise the image path.
        if self._turnaround_root_id is not None:
            rel = None
            from core.turnaround import resolve_pose_path

            rel = resolve_pose_path(self.image_manager, metadata, middle)
            image_path = self.image_manager.image_dir / (rel or metadata.path)
        else:
            image_path = self.image_manager.image_dir / metadata.path
        vw, vh = self._get_viewport_size()
        target_w, target_h = self._get_image_load_target()
        worker = ImageLoaderWorker(
            image_id,
            image_path,
            (target_w, target_h),
            FitMode.FIT_ALL,
            emit_fast=False,
        )

        worker.signals.finished.connect(self._on_image_loaded)
        worker.signals.error.connect(self._on_image_error)

        self.thread_pool.start(worker)

    def _apply_session_turnaround_pose(self, pose_index: int) -> None:
        """
        Instantly swap the session display to another turnaround pose.

        Args:
            pose_index: Target pose index.
        """
        if self._turnaround_root_id is None or len(self._turnaround_pose_ids) < 2:
            return
        metadata = self.image_manager.get_image_metadata(self._turnaround_root_id)
        if not is_turnaround_meta(metadata):
            return
        idx = max(0, min(len(self._turnaround_pose_ids) - 1, pose_index))
        if idx == self._turnaround_pose_index and self.current_pixmap is not None:
            return
        pixmap = load_pose_pixmap(self.image_manager, metadata, idx)
        if pixmap is None:
            return
        self._turnaround_pose_index = idx
        self.current_pixmap = pixmap
        # Instant swap — do not run session crossfade (that is for step changes).
        self._scale_and_display_pixmap(pixmap)

    def _on_image_loaded(self, image_id: str, pixmap: QPixmap):
        """Handle loaded image (HQ pixmap from ``ImageLoaderWorker.finished``)."""
        self.current_pixmap = pixmap
        self._update_image_display()

    def _on_image_error(self, image_id: str, error_msg: str):
        """Handle image loading error."""
        # Create a placeholder image
        placeholder = QPixmap(800, 600)
        placeholder.fill(Qt.gray)

        self.current_pixmap = placeholder
        self._update_image_display()

    def _get_image_load_target(self) -> tuple[int, int]:
        """
        Target box for ``ImageLoaderWorker`` (logical pixels, fit-all inside box).

        Uses current viewport size with a Full HD floor so HQ pixmaps are not
        upscaled on large displays (avoids blocky edges).
        """
        vw, vh = self._get_viewport_size()
        return (max(vw, 1920), max(vh, 1080))

    def _needs_higher_res_reload(self) -> bool:
        """True when the cached pixmap would be upscaled noticeably on screen."""
        if self.current_pixmap is None or self.current_pixmap.isNull():
            return False
        scale = display_scale_factor(
            self.current_pixmap, self._get_scene_display_rect(), FitMode.FIT_ALL
        )
        return scale > 1.05

    def _maybe_reload_current_image_for_scale(self) -> None:
        """Reload the slide at higher resolution if the viewport grew."""
        if (
            self._fade_in_progress
            or self._showing_get_ready
            or self._showing_phase_title
            or self._session_viewer_open
        ):
            return
        if not self._needs_higher_res_reload():
            return
        if not self.session_manager.get_current_image_id():
            return
        self._do_load_current_image()

    def _get_viewport_size(self):
        """Return (width, height) in logical pixels for the graphics viewport."""
        vp = self.graphics_view.viewport()
        vw, vh = vp.width(), vp.height()
        if vw > 0 and vh > 0:
            return (vw, vh)
        # Fallback: container rect (viewport may be 0 before first show/fullscreen).
        r = self._overlay_container.rect()
        return (max(1, r.width()), max(1, r.height()))

    def _get_scene_display_rect(self) -> QRectF:
        """Return the fixed viewport-sized scene rect used for all slide layouts."""
        vw, vh = self._get_viewport_size()
        return scene_display_rect(vw, vh)

    def _sync_view_transform_to_viewport(self) -> None:
        """
        Map scene coordinates 1:1 onto the viewport (no fitInView letterboxing).

        Reason: fitInView(scene_rect, KeepAspectRatio) letterboxes the whole scene
        when scene and viewport sizes differ slightly, shrinking already-fitted images.
        """
        rect = self._get_scene_display_rect()
        self.scene.setSceneRect(rect)
        self.graphics_view.resetTransform()
        vp_w = self.graphics_view.viewport().width()
        vp_h = self.graphics_view.viewport().height()
        if vp_w > 0 and vp_h > 0 and rect.width() > 0 and rect.height() > 0:
            self.graphics_view.scale(vp_w / rect.width(), vp_h / rect.height())
        self._debug_dimensions("_sync_view_transform_to_viewport")

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

    def _layout_pixmap_item_in_scene(
        self, item: QGraphicsPixmapItem, pixmap: QPixmap
    ) -> None:
        """Scale and center ``pixmap`` on ``item`` inside the fixed scene rect."""
        layout_pixmap_item_in_rect(item, pixmap, self._get_scene_display_rect())

    def _relayout_scene_pixmaps(self) -> None:
        """Re-layout visible pixmap layers after viewport resize."""
        if not self.pixmap_item.pixmap().isNull():
            self._layout_pixmap_item_in_scene(
                self.pixmap_item, self.pixmap_item.pixmap()
            )
        if (
            not self.pixmap_item_next.pixmap().isNull()
            and self.pixmap_item_next.opacity() > 0.0
        ):
            self._layout_pixmap_item_in_scene(
                self.pixmap_item_next, self.pixmap_item_next.pixmap()
            )

    def _fit_scene_in_view(self) -> None:
        """Sync scene rect to viewport and map scene coords 1:1 (images fill via layout)."""
        self._sync_view_transform_to_viewport()

    def _debug_dimensions(self, label: str) -> None:
        """Print viewport, scene rect, itemsBoundingRect (fitInView maps this to viewport)."""
        if not _DEBUG_SLIDESHOW_DIMENSIONS:
            return
        vp = self.graphics_view.viewport()
        vpw, vph = vp.width(), vp.height()
        sr = self.scene.sceneRect()
        ibr = self.scene.itemsBoundingRect()
        _dbg(f"--- {label} ---")
        _dbg(
            f"viewport: ({vpw}, {vph})  sceneRect: ({sr.width():.1f}, {sr.height():.1f})  itemsBoundingRect: ({ibr.width():.1f}, {ibr.height():.1f})"
        )
        for name, item in [
            ("pixmap_item", self.pixmap_item),
            ("pixmap_item_next", self.pixmap_item_next),
        ]:
            pix = item.pixmap()
            if pix.isNull():
                _dbg(f"{name}: pixmap=null")
            else:
                _dbg(f"{name}: pixmap=({pix.width()}, {pix.height()})")
        _dbg("")

    def _scale_and_display_pixmap(self, pixmap: QPixmap) -> None:
        """Lay out pixmap on the back layer at full viewport size; hide front layer."""
        if pixmap.isNull():
            return
        vw, vh = self._get_viewport_size()
        if vw <= 0 or vh <= 0:
            QTimer.singleShot(50, lambda: self._scale_and_display_pixmap(pixmap))
            return
        self._layout_pixmap_item_in_scene(self.pixmap_item, pixmap)
        self.pixmap_item.setOpacity(1.0)
        self.pixmap_item_next.setOpacity(0.0)
        self._fit_scene_in_view()

    def _give_focus_to_view(self) -> None:
        """Set keyboard focus to the graphics view so Space is handled by eventFilter (first press works)."""
        self.graphics_view.setFocus(Qt.OtherFocusReason)
        _dbg_space(
            f"_give_focus_to_view done, focusWidget={QApplication.focusWidget()}"
        )

    def _on_container_resized(self) -> None:
        """On resize: defer relayout until viewport geometry is final."""
        _dbg("_on_container_resized: scheduling relayout")
        QTimer.singleShot(0, self._relayout_and_sync_view)

    def _relayout_and_sync_view(self) -> None:
        """Re-layout pixmaps for the current viewport, then sync the view transform."""
        self._relayout_scene_pixmaps()
        self._fit_scene_in_view()
        if self._needs_higher_res_reload():
            self._hq_reload_timer.start()

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
            if not self.pixmap_item_next.pixmap().isNull():
                self._layout_pixmap_item_in_scene(
                    self.pixmap_item, self.pixmap_item_next.pixmap()
                )
            self.pixmap_item.setOpacity(1.0)
            self.pixmap_item_next.setOpacity(0.0)

        # Crossfade: both layers at full fit-in-view size; old fades out as new fades in.
        self.pixmap_item.setOpacity(1.0)
        self._layout_pixmap_item_in_scene(self.pixmap_item_next, self.current_pixmap)
        self.pixmap_item_next.setOpacity(0.0)
        self._fit_scene_in_view()
        self._start_fade_animation()

    def _start_fade_animation(self):
        """Start the crossfade (called after resize/repaint so image is at correct size)."""
        self._fade_in_progress = True
        self._sync_session_edit_visibility()
        self._fade_animation = QVariantAnimation(self)
        self._fade_animation.setStartValue(0.0)
        self._fade_animation.setEndValue(1.0)
        self._fade_animation.setDuration(400)
        self._fade_animation.valueChanged.connect(self._on_fade_value_changed)
        self._fade_animation.finished.connect(self._on_fade_finished)
        self._fade_animation.start()

    def _on_fade_value_changed(self, value):
        """Cross-dissolve: new layer fades in while old layer fades out."""
        opacity = float(value)
        self.pixmap_item_next.setOpacity(opacity)
        self.pixmap_item.setOpacity(1.0 - opacity)

    def _on_fade_finished(self):
        """After fade: move new image to back layer (already at correct scale)."""
        self._layout_pixmap_item_in_scene(
            self.pixmap_item, self.pixmap_item_next.pixmap()
        )
        self.pixmap_item.setOpacity(1.0)
        self.pixmap_item_next.setOpacity(0.0)
        self._fade_in_progress = False
        self._sync_session_edit_visibility()
        if self._fade_animation:
            self._fade_animation.valueChanged.disconnect(self._on_fade_value_changed)
            self._fade_animation.finished.disconnect(self._on_fade_finished)

    def _next_image(self):
        """Go to the next step: Get ready -> first phase/image, phase title -> image, image -> next phase title or image."""
        self._close_session_viewer_if_open()
        if self._showing_get_ready:
            self._cancel_get_ready_if_visible()
            self._sync_timer_to_current_image()
            self.timer_widget.start_timer()
            self._load_current_image()
            return
        if self._showing_phase_title:
            self._cancel_phase_title_if_visible()
            self._sync_timer_to_current_image()
            self.timer_widget.start_timer()
            self._load_current_image(skip_phase_title=True)
            return
        self._cancel_phase_title_if_visible()
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
        self._countdown_sound.reset()
        m, s = dur // 60, dur % 60
        self.countdown_label.setText(f"{m:02d}:{s:02d}")
        self._apply_countdown_color(dur)

    def _previous_image(self):
        """Go to the previous step: image -> phase title if phase start, or Get ready if at first image."""
        self._close_session_viewer_if_open()
        if self._showing_get_ready:
            return
        if self._showing_phase_title:
            self._cancel_phase_title_if_visible()
            idx = self.session_manager.get_run_index()
            if idx == 0:
                self.get_ready_frame.setVisible(True)
                self.get_ready_frame.raise_()
                self.countdown_frame.raise_()
                self._showing_get_ready = True
                self.timer_widget.pause_timer()
                self._start_title_countdown(
                    _GET_READY_DURATION_SEC, self._on_get_ready_done
                )
            else:
                self.session_manager.previous_image()
                self._sync_timer_to_current_image()
                self.timer_widget.start_timer()
                self._load_current_image()
            return
        idx = self.session_manager.get_run_index()
        if idx == 0:
            phase_info = self.session_manager.get_phase_info_at_index(0)
            if phase_info is not None:
                self._load_current_image()
            else:
                self.get_ready_frame.setVisible(True)
                self.get_ready_frame.raise_()
                self.countdown_frame.raise_()
                self._showing_get_ready = True
                self.timer_widget.pause_timer()
                self._start_title_countdown(
                    _GET_READY_DURATION_SEC, self._on_get_ready_done
                )
            return
        self.session_manager.previous_image()
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
        self._chrome_bar.setVisible(True)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setWindowState(Qt.WindowMaximized)
        self.show()
        self.fullscreen_btn.setVisible(True)
        self._fit_scene_in_view()

    def _switch_to_fullscreen(self):
        """Switch to fullscreen from windowed mode."""
        self._is_fullscreen = True
        self._chrome_bar.setVisible(False)
        self.fullscreen_btn.setVisible(False)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.setWindowState(Qt.WindowFullScreen)
        self.show()
        self._fit_scene_in_view()

    def changeEvent(self, event) -> None:
        """Keep custom chrome controls synchronized with window state."""
        super().changeEvent(event)
        if hasattr(self, "_chrome_bar"):
            self._chrome_bar.sync_window_state()

    def _sync_play_pause_button(self):
        """Set button to 'Play' (with icon) when paused, 'Pause' (with icon) when playing; blue when paused."""
        is_playing = self.timer_widget.is_running and not self.timer_widget.is_paused
        if is_playing:
            self.play_pause_btn.setText("Pause")
            if self._icon_pause and not self._icon_pause.isNull():
                self.play_pause_btn.setIcon(self._icon_pause)
            else:
                self.play_pause_btn.setIcon(QIcon())
            self.play_pause_btn.setObjectName("playPauseBtn")
        else:
            self.play_pause_btn.setText("Play")
            if self._icon_play and not self._icon_play.isNull():
                self.play_pause_btn.setIcon(self._icon_play)
            else:
                self.play_pause_btn.setIcon(QIcon())
            self.play_pause_btn.setObjectName("playPauseBtnPaused")
        self.play_pause_btn.style().unpolish(self.play_pause_btn)
        self.play_pause_btn.style().polish(self.play_pause_btn)
        self._sync_session_edit_visibility()

    def _toggle_controls(self):
        """Show/hide bottom bar (reserved for later; not bound to Space)."""
        self.controls_frame.setVisible(not self.controls_frame.isVisible())

    def _on_play_pause_clicked(self):
        """Toggle play/pause; button shows Play when paused, Pause when playing."""
        now = time.monotonic()
        if now - self._last_play_pause_toggle_time < 0.15:
            _dbg_space("_on_play_pause_clicked ignored (debounce)")
            return
        self._last_play_pause_toggle_time = now
        _dbg_space(
            f"_on_play_pause_clicked called | is_running={self.timer_widget.is_running} "
            f"is_paused={self.timer_widget.is_paused}"
        )
        if not self.timer_widget.is_running:
            self.timer_widget.start_timer()
        else:
            self.timer_widget.pause_timer()  # toggles pause <-> resume
        # Reason: leaving pause for play should close crop/rotate tools (session continues).
        if self.timer_widget.is_running and not self.timer_widget.is_paused:
            self._close_session_viewer_if_open()
        self._sync_play_pause_button()
        _dbg_space(
            f"after toggle | is_running={self.timer_widget.is_running} is_paused={self.timer_widget.is_paused}"
        )

    def _apply_countdown_color(
        self, remaining_seconds: int, total_seconds: Optional[int] = None
    ):
        """Set countdown label color and session background tint toward red near end."""
        total = max(
            1,
            (
                total_seconds
                if total_seconds is not None
                else self.timer_widget.total_seconds
            ),
        )
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
        self._apply_session_urgency_tint(ratio)

    def _apply_session_urgency_tint(self, time_left_ratio: float) -> None:
        """
        Apply a light red wash over the theme gradient as the timer runs out.

        The window gradient ramp stays visible underneath; only letterbox areas
        pick up the tint (via a transparent overlay under the graphics view).

        Args:
            time_left_ratio: Seconds remaining divided by total duration (1 → start, 0 → end).
        """
        urgency = max(0.0, min(1.0, 1.0 - time_left_ratio))
        max_alpha = 0.16
        alpha = urgency * max_alpha
        tint = getattr(self, "_urgency_tint_overlay", None)
        if tint is None:
            return
        if alpha < 0.02:
            tint.hide()
            return
        alpha_i = int(alpha * 255)
        tint.show()
        tint.setStyleSheet(f"background-color: rgba(210, 55, 55, {alpha_i});")
        tint.lower()
        if hasattr(self, "graphics_view"):
            self.graphics_view.raise_()

    def _on_timer_updated(self, remaining_seconds: int):
        """Sync countdown label, urgency tint, and final-second ticks."""
        m = remaining_seconds // 60
        s = remaining_seconds % 60
        self.countdown_label.setText(f"{m:02d}:{s:02d}")
        self._apply_countdown_color(remaining_seconds)
        if remaining_seconds == 0:
            self._countdown_sound.play_final_tick()
        elif remaining_seconds <= 10 and self.timer_widget.is_timer_running():
            self._countdown_sound.play_tick_if_needed(remaining_seconds)

    def _on_timer_finished(self):
        """Handle timer completion: final tick, then auto-advance."""
        self._countdown_sound.play_final_tick()
        self._next_image()
        if self.controls_frame.isVisible():
            self._sync_play_pause_button()

    def showEvent(self, event):
        """Re-fit when window is shown so viewport has final size."""
        super().showEvent(event)
        _dbg("showEvent: scheduling fitInView in 0ms")
        QTimer.singleShot(0, self._fit_scene_in_view)

    def eventFilter(self, obj, event):
        """Catch Space on graphics view; show UI on any key, mouse move, or mouse click."""
        if not self._init_complete:
            return super().eventFilter(obj, event)
        if not self._is_fullscreen and event.type() == QEvent.MouseMove:
            global_pos = (
                event.globalPosition().toPoint()
                if hasattr(event, "globalPosition")
                else None
            )
            if global_pos is not None:
                self._update_resize_cursor(self.mapFromGlobal(global_pos))
        # Viewport receives mouse events (QGraphicsView delegates to viewport())
        if obj == self.graphics_view.viewport():
            if (
                self._turnaround_root_id is not None
                and len(self._turnaround_pose_ids) >= 2
            ):
                if (
                    event.type() == QEvent.MouseButtonPress
                    and event.button() == Qt.LeftButton
                ):
                    self._turnaround_scrubbing = True
                    self._turnaround_scrub_start_x = float(event.pos().x())
                    self._turnaround_scrub_start_index = self._turnaround_pose_index
                    self._show_ui_and_restart_timer()
                    return True
                if event.type() == QEvent.MouseMove and self._turnaround_scrubbing:
                    new_idx = scrub_index_from_drag(
                        self._turnaround_scrub_start_x,
                        float(event.pos().x()),
                        self._turnaround_scrub_start_index,
                        len(self._turnaround_pose_ids),
                    )
                    self._apply_session_turnaround_pose(new_idx)
                    self._show_ui_and_restart_timer()
                    return True
                if (
                    event.type() == QEvent.MouseButtonRelease
                    and event.button() == Qt.LeftButton
                    and self._turnaround_scrubbing
                ):
                    self._turnaround_scrubbing = False
                    self._show_ui_and_restart_timer()
                    return True
            if (
                not self._is_fullscreen
                and event.type() == QEvent.MouseButtonPress
                and event.button() == Qt.LeftButton
            ):
                gp = (
                    event.globalPosition().toPoint()
                    if hasattr(event, "globalPosition")
                    else None
                )
                if gp is not None:
                    edges = self._get_resize_edges_at_pos(self.mapFromGlobal(gp))
                    if self._try_start_system_resize(edges):
                        return True
            if event.type() in (
                QEvent.MouseMove,
                QEvent.MouseButtonPress,
                QEvent.MouseButtonRelease,
            ):
                self._show_ui_and_restart_timer()
                return False
        if obj == self.graphics_view:
            if (
                not self._is_fullscreen
                and event.type() == QEvent.MouseButtonPress
                and event.button() == Qt.LeftButton
            ):
                gp = (
                    event.globalPosition().toPoint()
                    if hasattr(event, "globalPosition")
                    else None
                )
                if gp is not None:
                    edges = self._get_resize_edges_at_pos(self.mapFromGlobal(gp))
                    if self._try_start_system_resize(edges):
                        return True
            if event.type() in (
                QEvent.MouseMove,
                QEvent.MouseButtonPress,
                QEvent.MouseButtonRelease,
            ):
                self._show_ui_and_restart_timer()
                return False
            if event.type() == QEvent.KeyPress:
                self._show_ui_and_restart_timer()
                if event.key() == Qt.Key_Space and not event.isAutoRepeat():
                    _dbg_space(
                        "eventFilter: Space on graphics_view, toggling play/pause"
                    )
                    self._on_play_pause_clicked()
                    return True
        if obj == self._overlay_container and event.type() in (
            QEvent.MouseMove,
            QEvent.MouseButtonPress,
            QEvent.MouseButtonRelease,
        ):
            if (
                not self._is_fullscreen
                and event.type() == QEvent.MouseButtonPress
                and event.button() == Qt.LeftButton
            ):
                gp = (
                    event.globalPosition().toPoint()
                    if hasattr(event, "globalPosition")
                    else None
                )
                if gp is not None:
                    edges = self._get_resize_edges_at_pos(self.mapFromGlobal(gp))
                    if self._try_start_system_resize(edges):
                        return True
            self._show_ui_and_restart_timer()
            return False
        if obj in (
            self.countdown_frame,
            self.fullscreen_btn,
            self.controls_frame,
        ) and event.type() in (
            QEvent.MouseMove,
            QEvent.MouseButtonPress,
            QEvent.MouseButtonRelease,
        ):
            if (
                not self._is_fullscreen
                and event.type() == QEvent.MouseButtonPress
                and event.button() == Qt.LeftButton
            ):
                gp = (
                    event.globalPosition().toPoint()
                    if hasattr(event, "globalPosition")
                    else None
                )
                if gp is not None:
                    edges = self._get_resize_edges_at_pos(self.mapFromGlobal(gp))
                    if self._try_start_system_resize(edges):
                        return True
            self._show_ui_and_restart_timer()
            return False
        return super().eventFilter(obj, event)

    def _get_resize_edges_at_pos(self, pos: QPoint) -> Qt.Edges:
        """Return edge mask for frameless resize hit-test in windowed mode."""
        if self._is_fullscreen or self.isMaximized():
            return Qt.Edges()
        rect = self.rect()
        margin = self._resize_margin_px
        edges = Qt.Edges()
        if pos.x() <= margin:
            edges |= Qt.LeftEdge
        elif pos.x() >= rect.width() - margin:
            edges |= Qt.RightEdge
        if pos.y() <= margin:
            edges |= Qt.TopEdge
        elif pos.y() >= rect.height() - margin:
            edges |= Qt.BottomEdge
        return edges

    def _update_resize_cursor(self, pos: QPoint) -> None:
        """Show resize cursor when hovering window edges in windowed frameless mode."""
        if self._is_fullscreen:
            return
        edges = self._get_resize_edges_at_pos(pos)
        if edges in (Qt.LeftEdge, Qt.RightEdge):
            self.setCursor(Qt.SizeHorCursor)
        elif edges in (Qt.TopEdge, Qt.BottomEdge):
            self.setCursor(Qt.SizeVerCursor)
        elif edges in (Qt.TopEdge | Qt.LeftEdge, Qt.BottomEdge | Qt.RightEdge):
            self.setCursor(Qt.SizeFDiagCursor)
        elif edges in (Qt.TopEdge | Qt.RightEdge, Qt.BottomEdge | Qt.LeftEdge):
            self.setCursor(Qt.SizeBDiagCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def _try_start_system_resize(self, edges: Qt.Edges) -> bool:
        """Delegate frameless resize to native window system when possible."""
        if not edges:
            return False
        handle = self.windowHandle()
        if handle is None or not hasattr(handle, "startSystemResize"):
            return False
        return bool(handle.startSystemResize(edges))

    def keyPressEvent(self, event: QKeyEvent):
        """Catch Space at window level; show UI on any key."""
        self._show_ui_and_restart_timer()
        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            _dbg_space("keyPressEvent: Space on window, toggling play/pause")
            self._on_play_pause_clicked()
            event.accept()
            return
        super().keyPressEvent(event)

    def mouseMoveEvent(self, event):
        """Ensure edge/corner resize cursor is shown consistently in windowed mode."""
        if not self._is_fullscreen:
            pos = (
                event.position().toPoint()
                if hasattr(event, "position")
                else event.pos()
            )
            self._update_resize_cursor(pos)
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        """Start native system resize when pressing window borders in windowed mode."""
        if not self._is_fullscreen and event.button() == Qt.LeftButton:
            pos = (
                event.position().toPoint()
                if hasattr(event, "position")
                else event.pos()
            )
            edges = self._get_resize_edges_at_pos(pos)
            if self._try_start_system_resize(edges):
                event.accept()
                return
        super().mousePressEvent(event)

    def resizeEvent(self, event):
        """Handle resize events; container.resized will trigger re-scale and display."""
        super().resizeEvent(event)

    def closeEvent(self, event):
        """Handle window close event: end session and notify parent to re-show main window."""
        if self._session_image_viewer is not None:
            self._session_image_viewer._notify_slideshow_on_close = False
            self._session_image_viewer.close()
            self._session_image_viewer = None
        self._session_viewer_open = False
        allow_sleep()  # Restore normal power behavior (screen can sleep again)
        if self.session_manager.session_run:
            self.session_ended.emit()
        self.session_manager.end_session()
        self.setCursor(Qt.ArrowCursor)
        super().closeEvent(event)
