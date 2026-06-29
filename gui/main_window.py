"""
Main window of the SketchBook application.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Set, Optional, Tuple, TYPE_CHECKING
from qtpy.QtWidgets import (
    QMainWindow,
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
    QRubberBand,
    QApplication,
    QLayout,
    QGraphicsDropShadowEffect,
    QToolButton,
    QStackedWidget,
    QButtonGroup,
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
    QRect,
    QPoint,
    QVariantAnimation,
    QEasingCurve,
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
    QColor,
    QPen,
    QConicalGradient,
    QBrush,
    QFontMetrics,
    QFont,
)
from core.settings import settings
from core.image_manager import ImageManager
from core.image_db import ImageMetadata
from core import user_tags_config
from gui.image_import_worker import ImageImportWorker
from gui.image_grid import ImageGrid, ImageThumbnail
from gui.thumbnail_fitting import FitMode
from gui.tag_widgets import DraggableTagChip
from gui.add_tag_dialog import AddTagDialog, IconPickerDialog
from gui.add_shelf_dialog import AddShelfDialog
from gui.tag_apply_worker import TagApplyWorker, TagLibraryDeleteWorker
from gui.tag_panel_overlay import TagPanelOverlay
from gui.tag_shelves import (
    MISCELLANEOUS_SHELF,
    is_tag_shelf,
    load_default_tags_taxonomy,
    merge_custom_shelves,
    normalize_shelf_name,
    parse_category_tags,
    shelf_categories_with_filter,
)
from gui.startup_sort_worker import StartupSortRunnable, StartupSortSignals
from core.session_manager import SessionManager
from gui.grid_display_flyout import GridDisplayFlyout
from gui.trace_icon_button import ORANGE_TRACE, TraceIconButton
from gui.sort_flyout import SortFlyout
from gui.icon_utils import find_tag_icon, invert_icon, load_white_icon
from gui.tag_library.theme import tag_library_floating_button_stylesheet
from gui.tag_library import (
    TagLibraryPanel,
    TagFilterState,
    DraggableTagButton,
    WrappingDraggableTagButton,
    apply_chip_style,
    drag_pixmap_with_shadow,
    grab_chip_for_drag,
    get_chip_drag_source,
    build_chip_drag_pixmap,
    prepare_chip_drag_pixmap,
    chip_drag_hot_spot,
    apply_drag_cursor_offset,
    TAG_LIBRARY_MIME,
    TAG_LIBRARY_MULTI_MIME,
    mime_data_looks_like_tag_library_drag,
)
import os
import json

if TYPE_CHECKING:
    from gui.slideshow_window import SlideshowWindow


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
# MIME for multi-tag drag (all selected tags when dropping on images)
TAG_LIBRARY_MULTI_MIME = "application/x-sketchbook-tag-library-multi"
# Subtag cells: fit 3 columns inside scroll viewport (no horizontal scroll).
TAG_LIBRARY_TAG_GRID_COLUMNS = 3
TAG_LIBRARY_TAG_GRID_SPACING_PX = 3
TAG_LIBRARY_TAG_CELL_WIDTH_TRIM_PX = 6
TAG_LIBRARY_CATEGORY_WIDTH_TRIM_PX = 14
TAG_LIBRARY_SHELF_GRID_PADDING_PX = 3
# QFrame#TagDropZone uses 2px dashed border on each side (style_*.qss).
TAG_LIBRARY_DROP_ZONE_BORDER_PX = 4
TAG_LIBRARY_TAG_CELL_INSET_PX = 1
TAG_LIBRARY_TAG_CELL_ALIGN = Qt.AlignHCenter | Qt.AlignVCenter
TAG_LIBRARY_TAG_BORDER_LIGHTER_PCT = 145
TAG_LIBRARY_TAG_BORDER_WIDTH_PX = 2
TAG_LIBRARY_TAG_STYLE_V_PADDING_PX = 3
TAG_LIBRARY_TAG_MAX_HEIGHT_PX = 88
TAG_LIBRARY_TAG_SHADOW_BLUR_PX = 7
TAG_LIBRARY_TAG_SHADOW_OFFSET_PX = 2
TAG_LIBRARY_TAG_SHADOW_ALPHA = 100
TAG_LIBRARY_OVERLAY_HORIZONTAL_MARGIN_PX = 20  # TagPanelOverlay layout left+right (10+10)
# Sort combo: short visible labels, longer tooltips (index matches sort_map).
SORT_OPTIONS: list[tuple[str, str]] = [
    ("Most recent", "Most Recent First"),
    ("Oldest", "Oldest First"),
    ("A→Z", "Filename A→Z"),
    ("Z→A", "Filename Z→A"),
    ("Lightest", "Lightest First"),
    ("Heaviest", "Heaviest First"),
    ("Random", "Session Course Random"),
]
# Vertical scrollbar gutter only (do not also shrink grid width or we get h-scroll).
TAG_LIBRARY_SCROLLBAR_INSET_RIGHT_PX = 0
TAG_LIBRARY_SCROLLBAR_INSET_BOTTOM_PX = 10
TAG_LIBRARY_VIEWPORT_RIGHT_GUTTER_PX = 8
TAG_LIBRARY_GRID_TOP_MARGIN_PX = 6
# Typography (px) for tag library buttons.
TAG_LIBRARY_FONT_SUBTAG_PX = 16
TAG_LIBRARY_FONT_CATEGORY_PX = 15
TAG_LIBRARY_FONT_SHELF_TITLE_PX = 13
# Compact tag chips in the library grid (width computed from panel viewport).
TAG_LIBRARY_TAG_ICON_PX = 20
TAG_LIBRARY_CATEGORY_ICON_PX = 24
TAG_LIBRARY_TAG_MIN_HEIGHT_PX = 36
TAG_LIBRARY_CATEGORY_MIN_HEIGHT_PX = 36
TAG_LIBRARY_TAG_CELL_MIN_WIDTH_PX = 48


def tag_library_subtle_border_color(bg: QColor) -> str:
    """
    Return an outline color slightly lighter than the tag fill.

    Args:
        bg: Tag background color.

    Returns:
        str: CSS color name.
    """
    return bg.lighter(TAG_LIBRARY_TAG_BORDER_LIGHTER_PCT).name()


def tag_library_idle_border_css(bg: QColor) -> str:
    """
    Build the default (non-active) tag border declaration.

    Args:
        bg: Tag background color.

    Returns:
        str: CSS border fragment (e.g. ``2px solid #3a4b5c``).
    """
    color = tag_library_subtle_border_color(bg)
    w = TAG_LIBRARY_TAG_BORDER_WIDTH_PX
    return f"{w}px solid {color}"


def mime_data_looks_like_tag_library_drag(mime: Any) -> bool:
    """
    Return True if mime data likely comes from a tag-library drag (assign or reparent).

    Args:
        mime: QMimeData from a drag event, or None.

    Returns:
        bool: True if the drag should reopen the collapsed tag rail when hovering it.
    """
    if mime is None:
        return False
    try:
        if mime.hasFormat(TAG_LIBRARY_MIME) or mime.hasFormat(TAG_LIBRARY_MULTI_MIME):
            return True
        return bool(mime.hasText() and mime.text().strip())
    except (AttributeError, TypeError):
        return False


class SessionTraceButton(QPushButton):
    """Glass-like button with animated border trace around its contour."""

    def __init__(self, text: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(text, parent)
        self._trace_progress = 0.0
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumSize(208, 58)
        self.setStyleSheet(
            "QPushButton { background: transparent; border: none; color: transparent; }"
        )
        self._trace_anim = QVariantAnimation(self)
        self._trace_anim.setDuration(2200)
        self._trace_anim.setStartValue(0.0)
        self._trace_anim.setEndValue(1.0)
        self._trace_anim.setEasingCurve(QEasingCurve.Linear)
        self._trace_anim.setLoopCount(-1)
        self._trace_anim.valueChanged.connect(self._on_trace_value_changed)
        self._trace_anim.start()

    def sizeHint(self) -> QSize:
        """Keep the same practical footprint as the previous Start session button."""
        return QSize(208, 58)

    def minimumSizeHint(self) -> QSize:
        """Return minimum size for stable overlay placement."""
        return QSize(208, 58)

    def _on_trace_value_changed(self, value: object) -> None:
        """Update trace progression and repaint.

        Args:
            value: Animated progress ratio in [0, 1].
        """
        self._trace_progress = float(value)
        self.update()

    def paintEvent(self, event) -> None:
        """Custom paint: glass fill + moving border trace."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = self.rect().adjusted(3, 3, -3, -3)
        radius = 14.0

        if self.isDown():
            bg = QColor(77, 125, 180, 152)
        elif self.underMouse():
            bg = QColor(110, 156, 210, 142)
        else:
            bg = QColor(96, 142, 194, 128)

        painter.setPen(Qt.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(rect, radius, radius)

        base_pen = QPen(QColor(204, 222, 240, 122), 2.0)
        painter.setPen(base_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, radius, radius)

        # Reason: moving conical gradient gives a continuous perimeter trace with no pause.
        trace_gradient = QConicalGradient(rect.center(), -self._trace_progress * 360.0)
        trace_gradient.setColorAt(0.00, QColor(120, 188, 255, 70))
        trace_gradient.setColorAt(0.10, QColor(178, 227, 255, 255))
        trace_gradient.setColorAt(0.22, QColor(110, 180, 245, 85))
        trace_gradient.setColorAt(0.45, QColor(120, 188, 255, 70))
        trace_gradient.setColorAt(1.00, QColor(120, 188, 255, 70))
        trace_pen = QPen(QBrush(trace_gradient), 2.5)
        trace_pen.setCapStyle(Qt.RoundCap)
        trace_pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(trace_pen)
        painter.drawRoundedRect(rect, radius, radius)

        text_pen = QPen(QColor(245, 251, 255))
        painter.setPen(text_pen)
        font = painter.font()
        font.setBold(True)
        font.setPointSize(18)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, self.text())


class TagLibraryResizeFilter(QObject):
    """Resize tag-library cells when the scroll viewport width changes."""

    def __init__(self, main_window: "MainWindow"):
        super().__init__(main_window)
        self._main = main_window

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        try:
            resize_type = QEvent.Type.Resize
        except AttributeError:
            resize_type = QEvent.Resize
        if event.type() == resize_type:
            QTimer.singleShot(0, self._main._apply_tag_library_cell_widths)
        return False


class TagLibraryWheelFilter(QObject):
    """Block wheel propagation to the image grid when tag scroll is at an edge."""

    def __init__(self, scroll_area: QScrollArea):
        super().__init__(scroll_area)
        self._scroll = scroll_area

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        try:
            wheel_type = QEvent.Type.Wheel
        except AttributeError:
            wheel_type = QEvent.Wheel
        if event.type() != wheel_type:
            return False
        bar = self._scroll.verticalScrollBar()
        if bar is None:
            return False
        delta = event.angleDelta().y()
        if delta == 0 and hasattr(event, "pixelDelta"):
            delta = event.pixelDelta().y()
        if delta == 0:
            return False
        at_top = bar.value() <= bar.minimum()
        at_bottom = bar.value() >= bar.maximum()
        if (delta > 0 and at_top) or (delta < 0 and at_bottom):
            event.accept()
            return True
        return False


class TagGridDropFilter(QObject):
    """Event filter to accept tag-library drag/drop on the tag library panel."""

    def __init__(self, main_window: "MainWindow"):
        super().__init__(main_window)
        self._main = main_window

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        panel = getattr(self._main, "_tag_library_panel", None)
        if panel is None or obj != panel:
            return False
        try:
            _drag_enter = QEvent.Type.DragEnter
            _drag_move = QEvent.Type.DragMove
            _drag_leave = QEvent.Type.DragLeave
            _drop_type = QEvent.Type.Drop
        except AttributeError:
            _drag_enter = QEvent.DragEnter
            _drag_move = QEvent.DragMove
            _drag_leave = QEvent.DragLeave
            _drop_type = QEvent.Drop
        if event.type() == _drag_enter:
            if event.mimeData().hasFormat(TAG_LIBRARY_MIME):
                event.acceptProposedAction()
            else:
                event.ignore()
            return True
        if event.type() == _drag_move:
            if event.mimeData().hasFormat(TAG_LIBRARY_MIME):
                event.acceptProposedAction()
                pos = (
                    event.position().toPoint()
                    if hasattr(event, "position")
                    and hasattr(event.position(), "toPoint")
                    else event.pos()
                )
                target = self._main._get_tag_grid_drop_target_at(pos)
                self._main._set_tag_grid_drop_highlight(target)
                self._main._on_tag_grid_drag_hover(target)
            else:
                event.ignore()
            return True
        if event.type() == _drag_leave:
            self._main._set_tag_grid_drop_highlight(None)
            self._main._tag_grid_hover_expand_cancel()
            return False
        if event.type() == _drop_type:
            self._main._on_tag_grid_drop(event)
            return True
        return False


def apply_global_stylesheet():
    app = QApplication.instance()
    theme = settings.get("ui.theme", "dark")
    qss_path = os.path.join(os.path.dirname(__file__), "styles", f"style_{theme}.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    else:
        app.setStyleSheet("")


THEME_OPTIONS = [
    ("Light", "light"),
    ("Dark", "dark"),
    ("Neon Night", "neon_night"),
    ("Sunset Glass", "sunset_glass"),
    ("Midnight Ocean", "midnight_ocean"),
]


class MainWindow(QMainWindow):
    """Main window of the application."""

    def __init__(self):
        """Initialize the main window."""
        super().__init__()

        # Initialize managers (DB preload overlaps with UI build below)
        self.image_manager = ImageManager()
        self.image_manager.start_db_preload()
        self.session_manager = SessionManager()
        self.thread_pool = QThreadPool()
        self._startup_sort_signals = StartupSortSignals()
        self._startup_sort_signals.finished.connect(self._on_startup_sort_finished)
        self._startup_load_done = False
        self._startup_scheduled = False

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
        self._tag_shelf_filter_modes: Dict[str, str] = {}  # shelf name -> "and"|"or"
        # Temporary icon override for live preview in "Change icon" dialog; key = tag, value = icon filename or None
        self._icon_preview_override: Dict[str, Optional[str]] = {}
        self._shuffle_counter: int = (
            0  # Counter for shuffle iterations (increments on each shuffle)
        )
        self._course_random_images_list: List[ImageMetadata] = (
            []
        )  # Global list of ALL images in random order (only changed by shuffle button)
        self._filtered_course_random_list: List[ImageMetadata] = (
            []
        )  # Filtered list from grid (same as what's displayed)
        # Tag library: Ctrl+click selection for "Parent to tag..." (user tags only)
        self._tag_library_selection: Set[str] = set()
        # Parent-to-tag mode: tags to move, chosen parent key/role, and bar widgets
        self._parent_select_mode: bool = False
        self._tags_to_parent: Set[str] = set()
        self._parent_select_key: Optional[str] = None  # category or tag name
        self._parent_select_role: Optional[str] = None  # "category" or "tag"
        # Tag library selection (drag, shift-range, ctrl-toggle): display order and drag state
        self._user_tag_display_order: List[str] = (
            []
        )  # user tag names in grid order (for shift range)
        self._last_selected_tag: Optional[str] = None
        self._tag_library_selection_start: Optional[QPoint] = None  # viewport coords
        self._tag_library_is_selecting: bool = False
        self._tag_library_drag_start_tag: Optional[str] = (
            None  # when press on user tag, for drag-from-tag
        )
        self._tag_library_drag_start_button: Optional[QWidget] = None
        self._tag_grid_drop_highlight_widget: Optional[QWidget] = (
            None  # widget highlighted as drop target during drag
        )
        self._tag_drop_was_on_grid: bool = (
            False  # True when last drop was on tag grid (reparent), so button was destroyed
        )
        self._tag_drag_in_progress: bool = False
        self._tag_drag_scroll_timer: Optional[QTimer] = (
            None  # auto-scroll tag library during drag
        )
        self._tag_panel_drag_outside_poll_timer: Optional[QTimer] = (
            None  # cursor poll: QDrag often skips Leave on the overlay (Windows)
        )
        self._tag_grid_hover_expand_timer: Optional[QTimer] = (
            None  # expand category/tag after 0.8s hover during drag
        )
        self._tag_grid_hover_target: Optional[Tuple[str, str]] = (
            None  # (role, key) under cursor
        )
        self._hover_blink_timer: Optional[QTimer] = None
        self._hover_blink_widget: Optional[QWidget] = None
        self._hover_blink_state: bool = False
        self._drag_ghost_placeholders: List[Tuple[QWidget, Any, Any, int, int, int, int]] = []

        # Window setup
        self.setWindowTitle("SketchBook")
        self.resize(1280, 800)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        self._is_window_dragging = False
        self._window_drag_offset = QPoint()
        self._resize_margin_px = 6
        self._resize_edges = Qt.Edges()

        # Menus must exist before top chrome (menu buttons next to logo)
        self._setup_statusbar()
        self._setup_menu()
        self._setup_ui()
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
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._setup_top_chrome_bar(layout)
        self._setup_tab_bar(layout)
        self._setup_content_stack(layout)
        self._setup_floating_logo()

        # Tag grid + image list load deferred to first show (see showEvent).

    def _setup_floating_logo(self) -> None:
        """Place the logo above the top chrome (does not affect chrome height)."""
        cw = self.centralWidget()
        if not cw:
            return
        self._logo_float_height_px = 84
        logo_path = (
            Path(__file__).resolve().parent
            / "ressources"
            / "icones"
            / "SketchBook_logo_B.png"
        )
        self._logo_label = QLabel(cw)
        self._logo_label.setAttribute(Qt.WA_TranslucentBackground)
        self._logo_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        logo_shadow = QGraphicsDropShadowEffect(self._logo_label)
        logo_shadow.setBlurRadius(34)
        logo_shadow.setOffset(0, 6)
        logo_shadow.setColor(QColor(0, 0, 0, 210))
        self._logo_label.setGraphicsEffect(logo_shadow)
        logo_pix = QPixmap(str(logo_path))
        if not logo_pix.isNull():
            self._logo_label.setPixmap(
                logo_pix.scaledToHeight(
                    self._logo_float_height_px, Qt.SmoothTransformation
                )
            )
            self._logo_label.adjustSize()
        else:
            self._logo_label.hide()
        self._logo_label.raise_()
        QTimer.singleShot(0, self._position_floating_logo)

    def _position_floating_logo(self) -> None:
        """Keep the branding logo pinned to the top-left above other central content."""
        if not hasattr(self, "_logo_label") or not self._logo_label.isVisible():
            return
        m = 8
        self._logo_label.move(m, m)
        self._logo_label.raise_()
        self._grid_viewport_top_inset = TagPanelOverlay.VIEWPORT_MARGIN_PX
        if hasattr(self, "_tag_panel_overlay"):
            self._tag_panel_overlay.set_top_inset(self._grid_viewport_top_inset)

    def resizeEvent(self, event) -> None:
        """Re-anchor floating logo when the main window geometry changes."""
        super().resizeEvent(event)
        self._position_floating_logo()
        self._position_floating_grid_overlays()

    def showEvent(self, event) -> None:
        """Defer heavy DB/tag/grid work until after the empty window can paint."""
        super().showEvent(event)
        if self._startup_scheduled:
            return
        self._startup_scheduled = True
        QTimer.singleShot(0, self._deferred_startup_load)
        QTimer.singleShot(0, self._update_shuffle_floating_visibility)

    def _deferred_startup_load(self) -> None:
        """
        Load tag library UI and image grid after first frame.

        Sorting runs in the global QThreadPool when not in course_random mode.
        """
        if self._startup_load_done:
            return
        self.statusBar().showMessage("Loading library…", 0)
        self._load_tags_into_grid()
        sort_by = self._get_current_sort_order()
        if sort_by == "course_random":
            self._apply_category_filters()
            self._finalize_startup_load()
            return
        worker = StartupSortRunnable(
            self.image_manager.db,
            sort_by,
            self._shuffle_counter,
            self._startup_sort_signals,
        )
        QThreadPool.globalInstance().start(worker)

    def _on_startup_sort_finished(self, result: object) -> None:
        """Apply filters on the main thread using background-sorted metadata."""
        if self._startup_load_done:
            return
        if isinstance(result, Exception):
            self._apply_category_filters()
        else:
            self._apply_category_filters(_pre_sorted_images=result)
        self._finalize_startup_load()

    def _finalize_startup_load(self) -> None:
        """Mark startup complete, restore status, run deferred DB maintenance."""
        self._startup_load_done = True
        self.statusBar().showMessage("Ready")
        self.image_manager.run_import_date_backfill()

    def run_startup_load_for_tests(self) -> None:
        """
        Synchronously load tags + grid (for unit tests that never show the window).

        Skips the background sort thread so tests stay deterministic.
        """
        if self._startup_load_done:
            return
        self._load_tags_into_grid()
        self._apply_category_filters()
        self._finalize_startup_load()

    def _setup_top_chrome_bar(self, main_layout: QVBoxLayout) -> None:
        """
        Build line 1: **File / View / Tools / Help** menus + window control buttons.

        Grid controls (Shuffle, Sort, Columns, Display) live in line 2 (tab bar).
        Logo is not in this row (see ``_setup_floating_logo``).

        Args:
            main_layout: Central widget vertical layout (receives this row as first item).
        """
        self._top_chrome_bar = QWidget()
        self._top_chrome_bar.setObjectName("TopChromeBar")
        top_row = QHBoxLayout(self._top_chrome_bar)
        top_row.setContentsMargins(6, 0, 6, 0)
        top_row.setSpacing(6)

        # Reason: floating logo overlaps this strip; keep menus to the right of its footprint.
        logo_reserve = QWidget(self._top_chrome_bar)
        logo_reserve.setFixedWidth(100)
        logo_reserve.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        top_row.addWidget(logo_reserve, 0, Qt.AlignVCenter)

        for label, menu_attr in (
            ("File", "_file_menu"),
            ("View", "_view_menu"),
            ("Tools", "_tools_menu"),
            ("Help", "_help_menu"),
        ):
            m = getattr(self, menu_attr, None)
            if m is None:
                continue
            mb = QToolButton(self._top_chrome_bar)
            mb.setText(label)
            mb.setMenu(m)
            mb.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            mb.setToolButtonStyle(Qt.ToolButtonTextOnly)
            mb.setAutoRaise(True)
            mb.setStyleSheet("""
                QToolButton {
                    color: #e0e0e0;
                    font-size: 11px;
                    font-weight: bold;
                    padding: 4px 10px;
                    border: 1px solid transparent;
                    border-radius: 4px;
                    background-color: transparent;
                }
                QToolButton:hover {
                    background-color: rgba(255, 255, 255, 0.09);
                    border-color: rgba(255, 255, 255, 0.12);
                }
                QToolButton::menu-indicator { width: 0px; }
            """)
            top_row.addWidget(mb, 0, Qt.AlignVCenter)

        top_row.addStretch(1)

        self._window_min_btn = QPushButton("-", self._top_chrome_bar)
        self._window_min_btn.setToolTip("Minimize")
        self._window_min_btn.setFixedSize(30, 22)
        self._window_min_btn.clicked.connect(self.showMinimized)

        self._window_max_btn = QPushButton("□", self._top_chrome_bar)
        self._window_max_btn.setToolTip("Maximize")
        self._window_max_btn.setFixedSize(30, 22)
        self._window_max_btn.clicked.connect(self._toggle_maximize_restore)

        self._window_close_btn = QPushButton("X", self._top_chrome_bar)
        self._window_close_btn.setToolTip("Close")
        self._window_close_btn.setFixedSize(30, 22)
        self._window_close_btn.clicked.connect(self.close)

        for btn in (self._window_min_btn, self._window_max_btn, self._window_close_btn):
            btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(45, 48, 52, 0.9);
                    color: #e0e0e0;
                    border: 1px solid #555;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: rgba(60, 64, 70, 0.95);
                    border-color: #6b9bd1;
                }
                QPushButton:pressed {
                    background-color: rgba(35, 38, 42, 0.95);
                }
            """)

        self._window_close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(140, 45, 45, 0.9);
                color: #ffffff;
                border: 1px solid #8a3a3a;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(180, 55, 55, 0.95);
                border-color: #d17a7a;
            }
            QPushButton:pressed {
                background-color: rgba(120, 35, 35, 0.95);
            }
        """)

        top_row.addWidget(self._window_min_btn, 0, Qt.AlignVCenter)
        top_row.addWidget(self._window_max_btn, 0, Qt.AlignVCenter)
        top_row.addWidget(self._window_close_btn, 0, Qt.AlignVCenter)

        self._top_chrome_bar.setFixedHeight(38)
        main_layout.addWidget(self._top_chrome_bar, 0)

    # ------------------------------------------------------------------
    # Line 2: tab buttons + per-tab tool controls
    # ------------------------------------------------------------------

    TAB_NAMES = ("Life Drawing", "WhiteBoard", "Market")

    def _setup_tab_bar(self, main_layout: QVBoxLayout) -> None:
        """
        Build line 2: tab buttons on the left, grid controls on the right.

        Grid controls are wrapped in ``_life_drawing_controls`` so they can be
        hidden when the active tab is not Life Drawing.

        Args:
            main_layout: Central widget vertical layout.
        """
        self._tab_bar_widget = QWidget()
        self._tab_bar_widget.setObjectName("TabBarRow")
        row = QHBoxLayout(self._tab_bar_widget)
        row.setContentsMargins(6, 0, 6, 0)
        row.setSpacing(0)

        # Reason: keep tab buttons out from under the floating logo.
        tab_logo_reserve = QWidget(self._tab_bar_widget)
        tab_logo_reserve.setFixedWidth(100)
        tab_logo_reserve.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        row.addWidget(tab_logo_reserve, 0, Qt.AlignVCenter)

        self._tab_button_group = QButtonGroup(self)
        self._tab_button_group.setExclusive(True)

        for idx, name in enumerate(self.TAB_NAMES):
            btn = QPushButton(name, self._tab_bar_widget)
            btn.setCheckable(True)
            btn.setObjectName("TabButton")
            if idx == 0:
                btn.setChecked(True)
            self._tab_button_group.addButton(btn, idx)
            row.addWidget(btn, 0, Qt.AlignVCenter)

        row.addStretch(1)

        # Life Drawing controls (Shuffle, Sort, Columns, Display)
        self._life_drawing_controls = QWidget(self._tab_bar_widget)
        ctrl_layout = QHBoxLayout(self._life_drawing_controls)
        ctrl_layout.setContentsMargins(0, 0, 0, 0)
        ctrl_layout.setSpacing(6)

        grid_icon_px = 18

        sort_icon = load_white_icon("sort.png", grid_icon_px)
        grid_display_icon = load_white_icon("imageGrid.png", grid_icon_px)
        self._sort_flyout = SortFlyout(sort_icon, self._life_drawing_controls)
        self.sort_combo = self._sort_flyout.sort_combo
        for short_label, tooltip_label in SORT_OPTIONS:
            self.sort_combo.addItem(short_label)
            self.sort_combo.setItemData(
                self.sort_combo.count() - 1,
                f"Sort by: {tooltip_label}",
                Qt.ToolTipRole,
            )
        default_sort_index = settings.get("ui.grid.sort_index", 6)
        if not 0 <= default_sort_index < self.sort_combo.count():
            default_sort_index = 6
        self.sort_combo.setCurrentIndex(default_sort_index)
        self.sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        self.sort_combo.setToolTip(
            f"Sort by: {SORT_OPTIONS[self.sort_combo.currentIndex()][1]}"
        )

        self._grid_display_flyout = GridDisplayFlyout(
            grid_display_icon, self._life_drawing_controls
        )
        self.columns_slider = self._grid_display_flyout.columns_slider
        self.columns_count = self._grid_display_flyout.columns_count
        self.fit_mode_combo = self._grid_display_flyout.fit_mode_combo
        self.columns_slider.setValue(settings.get("ui.grid.columns", 4))
        self.columns_count.setText(str(self.columns_slider.value()))
        self.columns_slider.valueChanged.connect(self._on_columns_changed)
        stored_fit = settings.get("ui.grid.fit_mode", None)
        if stored_fit is None:
            default_fit = FitMode.CROP_ALL.value
        else:
            default_fit = int(stored_fit)
        if not 0 <= default_fit < self.fit_mode_combo.count():
            default_fit = FitMode.CROP_ALL.value
        self.fit_mode_combo.setCurrentIndex(default_fit)
        self.fit_mode_combo.currentIndexChanged.connect(self._on_fit_mode_changed)

        ctrl_layout.addWidget(self._sort_flyout, 0, Qt.AlignVCenter)
        ctrl_layout.addWidget(self._grid_display_flyout, 0, Qt.AlignVCenter)

        self._life_drawing_flyout_collapse_timer = QTimer(self)
        self._life_drawing_flyout_collapse_timer.setSingleShot(True)
        self._life_drawing_flyout_collapse_timer.timeout.connect(
            self._collapse_life_drawing_flyouts
        )

        row.addWidget(self._life_drawing_controls, 0, Qt.AlignVCenter)

        self._tab_bar_widget.setFixedHeight(42)
        main_layout.addWidget(self._tab_bar_widget, 0)

        self._tab_button_group.idClicked.connect(self._on_tab_changed)

    # ------------------------------------------------------------------
    # Content stack (one page per tab)
    # ------------------------------------------------------------------

    def _setup_content_stack(self, main_layout: QVBoxLayout) -> None:
        """
        Create a QStackedWidget with one page per tab.

        Page 0 = Life Drawing (image grid + overlays).
        Pages 1-2 = placeholder coming-soon panels.

        Args:
            main_layout: Central widget vertical layout.
        """
        self._content_stack = QStackedWidget()

        # Page 0: Life Drawing
        life_drawing_page = self._setup_image_browser()
        self._content_stack.addWidget(life_drawing_page)

        # Page 1: WhiteBoard (placeholder)
        wb_page = self._make_placeholder_page("WhiteBoard", "Coming soon")
        self._content_stack.addWidget(wb_page)

        # Page 2: Market (placeholder)
        market_page = self._make_placeholder_page("Market", "Coming soon")
        self._content_stack.addWidget(market_page)

        self._content_stack.setCurrentIndex(0)
        self._schedule_life_drawing_flyout_collapse()
        self._update_shuffle_floating_visibility()
        main_layout.addWidget(self._content_stack, 1)

    @staticmethod
    def _make_placeholder_page(title: str, subtitle: str) -> QWidget:
        """
        Create a placeholder page with centered text.

        Args:
            title: Large heading text.
            subtitle: Smaller text below.

        Returns:
            QWidget: The placeholder page.
        """
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        heading = QLabel(title)
        heading.setAlignment(Qt.AlignCenter)
        heading.setStyleSheet("font-size: 28px; font-weight: bold; color: #ffffff;")
        sub = QLabel(subtitle)
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("font-size: 14px; color: rgba(255, 255, 255, 0.5);")
        layout.addWidget(heading)
        layout.addWidget(sub)
        return page

    def _on_tab_changed(self, index: int) -> None:
        """
        Switch the visible page and show/hide per-tab controls.

        Args:
            index: Tab index (0 = Life Drawing, 1 = WhiteBoard, 2 = Market).
        """
        self._content_stack.setCurrentIndex(index)
        self._life_drawing_controls.setVisible(index == 0)
        if index == 0:
            self._schedule_life_drawing_flyout_collapse()
        else:
            self._life_drawing_flyout_collapse_timer.stop()
            self._collapse_life_drawing_flyouts()
        self._update_shuffle_floating_visibility()

    def _update_shuffle_floating_visibility(self) -> None:
        """Show the floating shuffle button only on Life Drawing + Random sort."""
        if not hasattr(self, "shuffle_button"):
            return
        on_life_drawing = (
            not hasattr(self, "_content_stack")
            or self._content_stack.currentIndex() == 0
        )
        is_random_sort = (
            hasattr(self, "sort_combo") and self.sort_combo.currentIndex() == 6
        )
        self.shuffle_button.setVisible(on_life_drawing and is_random_sort)
        QTimer.singleShot(0, self._position_floating_grid_overlays)

    def _schedule_life_drawing_flyout_collapse(self) -> None:
        """Collapse sort/grid flyouts shortly after the Life Drawing tab appears."""
        self._life_drawing_flyout_collapse_timer.start(1000)

    def _collapse_life_drawing_flyouts(self) -> None:
        """Force both toolbar flyouts back to their icon-only state."""
        if hasattr(self, "_sort_flyout"):
            self._sort_flyout.force_collapse()
        if hasattr(self, "_grid_display_flyout"):
            self._grid_display_flyout.force_collapse()

    def _toggle_maximize_restore(self) -> None:
        """Toggle between maximized and normal window states."""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        self._update_window_controls_for_state()

    def _update_window_controls_for_state(self) -> None:
        """Refresh maximize button label/tooltip based on current window state."""
        if not hasattr(self, "_window_max_btn"):
            return
        if self.isMaximized():
            self._window_max_btn.setText("❐")
            self._window_max_btn.setToolTip("Restore")
        else:
            self._window_max_btn.setText("□")
            self._window_max_btn.setToolTip("Maximize")

    def mousePressEvent(self, event) -> None:
        """Start window drag when pressing on the custom top chrome background."""
        if event.button() == Qt.LeftButton:
            self._resize_edges = self._get_resize_edges_at_pos(
                event.position().toPoint()
                if hasattr(event, "position")
                else event.pos()
            )
            if self._try_start_system_resize(self._resize_edges):
                event.accept()
                return
            pos = (
                event.position().toPoint()
                if hasattr(event, "position")
                else event.pos()
            )
            drag_bars = [
                getattr(self, "_top_chrome_bar", None),
                getattr(self, "_tab_bar_widget", None),
            ]
            for bar in drag_bars:
                if bar and bar.geometry().contains(pos):
                    target = self.childAt(pos)
                    if target in (bar,):
                        self._is_window_dragging = True
                        self._window_drag_offset = (
                            event.globalPosition().toPoint()
                            - self.frameGeometry().topLeft()
                            if hasattr(event, "globalPosition")
                            else event.globalPos() - self.frameGeometry().topLeft()
                        )
                        event.accept()
                        return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        """Move frameless window while dragging top chrome; update resize cursor."""
        if not (event.buttons() & Qt.LeftButton):
            self._update_resize_cursor(
                event.position().toPoint()
                if hasattr(event, "position")
                else event.pos()
            )
        if self._is_window_dragging and (event.buttons() & Qt.LeftButton):
            if self.isMaximized():
                self.showNormal()
                self._update_window_controls_for_state()
            gp = (
                event.globalPosition().toPoint()
                if hasattr(event, "globalPosition")
                else event.globalPos()
            )
            self.move(gp - self._window_drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        """Stop frameless window drag."""
        if event.button() == Qt.LeftButton:
            self._is_window_dragging = False
            self._resize_edges = Qt.Edges()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        """Double-click top chrome or tab bar background to maximize/restore."""
        if event.button() == Qt.LeftButton:
            pos = (
                event.position().toPoint()
                if hasattr(event, "position")
                else event.pos()
            )
            drag_bars = [
                getattr(self, "_top_chrome_bar", None),
                getattr(self, "_tab_bar_widget", None),
            ]
            for bar in drag_bars:
                if bar and bar.geometry().contains(pos):
                    target = self.childAt(pos)
                    if target in (bar,):
                        self._toggle_maximize_restore()
                        event.accept()
                        return
        super().mouseDoubleClickEvent(event)

    def changeEvent(self, event) -> None:
        """Keep custom window controls in sync with native window state changes."""
        super().changeEvent(event)
        self._update_window_controls_for_state()

    def _get_resize_edges_at_pos(self, pos: QPoint) -> Qt.Edges:
        """Return edge mask for frameless resize hit-test."""
        if self.isMaximized():
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
        """Show resize cursor when hovering window edges in frameless mode."""
        edges = self._get_resize_edges_at_pos(pos)
        if edges in (Qt.LeftEdge, Qt.RightEdge):
            self.setCursor(Qt.SizeHorCursor)
        elif edges in (Qt.TopEdge, Qt.BottomEdge):
            self.setCursor(Qt.SizeVerCursor)
        elif edges in (
            Qt.TopEdge | Qt.LeftEdge,
            Qt.BottomEdge | Qt.RightEdge,
        ):
            self.setCursor(Qt.SizeFDiagCursor)
        elif edges in (
            Qt.TopEdge | Qt.RightEdge,
            Qt.BottomEdge | Qt.LeftEdge,
        ):
            self.setCursor(Qt.SizeBDiagCursor)
        else:
            self.unsetCursor()

    def _try_start_system_resize(self, edges: Qt.Edges) -> bool:
        """Delegate frameless resize to the native window system when possible."""
        if not edges:
            return False
        handle = self.windowHandle()
        if handle is None or not hasattr(handle, "startSystemResize"):
            return False
        return bool(handle.startSystemResize(edges))

    def _setup_image_browser(self) -> QWidget:
        """
        Set up the Image Browser with floating tag panel overlay.

        Returns:
            QWidget: The middle panel containing the image grid and overlays.
        """
        # Space below the floating logo so tag rail / panel do not sit under it.
        # (_logo_float_height_px is set later in _setup_floating_logo; default matches it.)
        self._grid_viewport_top_inset = 2

        # === IMAGE GRID (takes full width, no splitter) ===
        middle_panel = QWidget()
        middle_layout = QVBoxLayout(middle_panel)
        # Keep the left rail fully flush with the window edge.
        middle_layout.setContentsMargins(0, 10, 10, 10)
        middle_layout.setSpacing(10)

        self.image_grid = ImageGrid(self.image_manager)
        # Reason: keep floating tag rail at absolute left while leaving visual room
        # before thumbnails so it does not overlap image content.
        self.image_grid.grid.setContentsMargins(50, 8, 8, 8)
        self.image_grid.set_columns(self.columns_slider.value())
        self.image_grid.set_fit_mode(FitMode(self.fit_mode_combo.currentIndex()))
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
        self.image_grid.start_session_from_image_requested.connect(
            self._on_start_session_from_grid_image
        )
        self.image_grid.grid_needs_refresh.connect(self._apply_category_filters)
        self.image_grid.set_import_drop_callback(self._import_from_urls)
        middle_layout.addWidget(self.image_grid)

        vp = self.image_grid.viewport()

        # Floating control: session button on image viewport.
        self.session_settings_btn = SessionTraceButton("Start session", vp)
        shadow = QGraphicsDropShadowEffect(self.session_settings_btn)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(88, 162, 255, 160))
        self.session_settings_btn.setGraphicsEffect(shadow)
        self.session_settings_btn.clicked.connect(self._on_session_settings_clicked)
        self.session_settings_btn.raise_()

        shuffle_icon = load_white_icon("shuffle.png", 96)
        self.shuffle_button = TraceIconButton(
            shuffle_icon,
            size=self.session_settings_btn.sizeHint().height(),
            palette=ORANGE_TRACE,
            parent=vp,
        )
        self.shuffle_button.setToolTip("Shuffle random order")
        shuffle_shadow = QGraphicsDropShadowEffect(self.shuffle_button)
        shuffle_shadow.setBlurRadius(40)
        shuffle_shadow.setOffset(0, 10)
        shuffle_shadow.setColor(ORANGE_TRACE.shadow)
        self.shuffle_button.setGraphicsEffect(shuffle_shadow)
        self.shuffle_button.clicked.connect(self._on_shuffle_clicked)
        self.shuffle_button.raise_()
        self._update_shuffle_floating_visibility()

        # === FLOATING TAG PANEL (overlay on image grid viewport) ===
        self._left_panel_expanded = False
        self._tag_panel_overlay = TagPanelOverlay(
            vp, top_inset=self._grid_viewport_top_inset
        )

        # Build a wrapper widget that holds the entire tag library content.
        self._tag_content_wrapper = QWidget()
        tag_content_layout = QVBoxLayout(self._tag_content_wrapper)
        tag_content_layout.setContentsMargins(0, 0, 0, 0)
        tag_content_layout.setSpacing(10)

        # Title row: "Tags Library" + "Create tag" button
        tags_header_layout = QHBoxLayout()
        tags_header_layout.setContentsMargins(0, 0, 0, 0)
        self._tags_library_title_label = QLabel("Tags Library")
        self._tags_library_title_label.setStyleSheet(
            "font-size: 14px; font-weight: 600; color: #ece8f4; letter-spacing: 0.3px;"
        )
        tags_header_layout.addWidget(self._tags_library_title_label)
        tags_header_layout.addStretch()
        add_tag_btn = QPushButton("+ Create tag")
        add_tag_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(75, 110, 175, 0.85);
                color: #f4f2f8;
                font-size: 12px;
                font-weight: 600;
                padding: 7px 12px;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                min-width: 90px;
            }
            QPushButton:hover { background-color: rgba(93, 123, 192, 0.95); }
            QPushButton:pressed { background-color: rgba(62, 90, 148, 0.95); }
        """)
        add_tag_btn.setToolTip("Add a new tag to the library")
        add_tag_btn.clicked.connect(self._on_add_user_tag_clicked)
        self._add_tag_btn = add_tag_btn
        tags_header_layout.addWidget(add_tag_btn)
        add_shelf_btn = QPushButton("+ Create shelf")
        add_shelf_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.06);
                color: #d8d4e4;
                font-size: 12px;
                font-weight: 600;
                padding: 7px 12px;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                min-width: 90px;
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 0.1); }
            QPushButton:pressed { background-color: rgba(255, 255, 255, 0.14); }
        """)
        add_shelf_btn.setToolTip(
            "Add a titled section (shelf) like Camera-Angle or Miscellaneous"
        )
        add_shelf_btn.clicked.connect(self._on_add_shelf_clicked)
        self._add_shelf_btn = add_shelf_btn
        tags_header_layout.addWidget(add_shelf_btn)
        tag_content_layout.addLayout(tags_header_layout)

        # "Parent to tag..." mode bar
        self._parent_select_bar = QWidget()
        parent_select_layout = QHBoxLayout(self._parent_select_bar)
        parent_select_layout.setContentsMargins(0, 4, 0, 4)
        self._parent_select_label = QLabel("Select parent tag: (none)")
        self._parent_select_label.setStyleSheet("font-size: 11px; color: #ffffff;")
        parent_select_layout.addWidget(self._parent_select_label)
        parent_select_layout.addStretch()
        self._parent_ok_btn = QPushButton("OK")
        self._parent_ok_btn.setEnabled(False)
        self._parent_ok_btn.setFixedWidth(60)
        self._parent_ok_btn.clicked.connect(self._on_parent_select_ok)
        self._parent_cancel_btn = QPushButton("Cancel")
        self._parent_cancel_btn.setFixedWidth(60)
        self._parent_cancel_btn.clicked.connect(self._on_parent_select_cancel)
        parent_select_layout.addWidget(self._parent_ok_btn)
        parent_select_layout.addWidget(self._parent_cancel_btn)
        self._parent_select_bar.setVisible(False)
        tag_content_layout.addWidget(self._parent_select_bar)

        # === NEW: TagLibraryPanel (sections + 3-col grids, no rebuild on expand) ===
        self._tag_library_panel = TagLibraryPanel()
        tag_content_layout.addWidget(self._tag_library_panel, 1)

        # Connect panel signals to MainWindow handlers
        self._tag_library_panel.filter_changed.connect(self._on_panel_filter_changed)
        self._tag_library_panel.tag_delete_requested.connect(self._delete_user_tags)
        self._tag_library_panel.tag_rename_requested.connect(self._on_panel_tag_rename)
        self._tag_library_panel.tag_icon_change_requested.connect(self._on_panel_tag_icon_change)
        self._tag_library_panel.drag_session_started.connect(self._begin_tag_library_drag_session)
        self._tag_library_panel.drag_session_ended.connect(self._end_tag_library_drag_session)

        # Rubber-band selection on the panel's scroll viewport
        self.tags_scroll_area = self._tag_library_panel.get_scroll_area()
        tag_viewport = self.tags_scroll_area.viewport()
        self._tag_library_wheel_filter = TagLibraryWheelFilter(self.tags_scroll_area)
        self.tags_scroll_area.installEventFilter(self._tag_library_wheel_filter)
        tag_viewport.installEventFilter(self._tag_library_wheel_filter)
        try:
            rb_shape = QRubberBand.Shape.Rectangle
        except AttributeError:
            rb_shape = QRubberBand.Rectangle
        self._tag_library_rubber_band = QRubberBand(rb_shape, tag_viewport)
        self._tag_library_rubber_band.setStyleSheet("""
            QRubberBand {
                background-color: rgba(0, 120, 215, 0.2);
                border: 2px solid rgb(0, 120, 215);
                border-radius: 2px;
            }
        """)
        self._tag_library_rubber_band.raise_()
        QApplication.instance().installEventFilter(self)

        # Legacy compat stubs so old call sites compile (will be cleaned up later)
        self.tags_grid_container = self._tag_library_panel
        self._tag_library_panel.setAcceptDrops(True)
        self._tag_grid_drop_filter = TagGridDropFilter(self)
        self._tag_library_panel.installEventFilter(self._tag_grid_drop_filter)

        # Tag library content is filled on first window show (fast empty shell at startup).

        self._tag_panel_overlay.set_content_widget(self._tag_content_wrapper)

        # Trigger button: thin vertical strip at the left edge of the viewport.
        self.tag_filters_floating_btn = QPushButton("Tags\nfilters\n>", vp)
        self.tag_filters_floating_btn.setObjectName("TagFiltersFloatingButton")
        self.tag_filters_floating_btn.setToolTip("Hover to expand tags panel")
        self.tag_filters_floating_btn.setStyleSheet(
            tag_library_floating_button_stylesheet()
        )
        tf_shadow = QGraphicsDropShadowEffect(self.tag_filters_floating_btn)
        tf_shadow.setBlurRadius(12)
        tf_shadow.setOffset(0, 2)
        tf_shadow.setColor(QColor(0, 0, 0, 130))
        self.tag_filters_floating_btn.setGraphicsEffect(tf_shadow)
        self.tag_filters_floating_btn.setFixedWidth(46)
        self.tag_filters_floating_btn.installEventFilter(self)

        # Create AND/OR zones (filtering logic still uses them).
        from gui.tag_widgets import TagDropZone

        self.and_zone = TagDropZone("AND (all required)")
        self.and_zone.tag_dropped.connect(self._on_tag_filter_changed)
        self.and_zone.tags_modified.connect(self._on_tag_filter_changed)
        self.or_zone = TagDropZone("OR (at least one)")
        self.or_zone.tag_dropped.connect(self._on_tag_filter_changed)
        self.or_zone.tags_modified.connect(self._on_tag_filter_changed)
        self.tag_search_input = QLineEdit()
        # Completer is filled when the tag library loads (see _load_tags_into_grid).

        vp.installEventFilter(self)
        self._tag_panel_overlay.panel_did_hide.connect(
            self._position_floating_grid_overlays
        )
        self.image_grid.set_tag_popover_stack_under(self.session_settings_btn)
        QTimer.singleShot(0, self._position_floating_grid_overlays)

        self._image_viewer_window = None

        return middle_panel

    def _toggle_left_sidebar(self) -> None:
        """Toggle the floating tag panel overlay open or closed."""
        if not hasattr(self, "_tag_panel_overlay"):
            return
        if self._tag_panel_overlay.is_panel_visible():
            self._tag_panel_overlay.hide_animated()
            self._left_panel_expanded = False
        else:
            self._tag_panel_overlay.show_animated()
            self._left_panel_expanded = True
        QTimer.singleShot(0, self._position_floating_grid_overlays)

    def _position_floating_grid_overlays(self) -> None:
        """Place floating overlays (session button, tag trigger, tag panel) on image viewport."""
        if not hasattr(self, "image_grid"):
            return
        viewport = self.image_grid.viewport()
        if not viewport:
            return
        margin = 10
        bottom_margin = 4  # closer to viewport bottom (shuffle + start session)
        tag_margin = TagPanelOverlay.VIEWPORT_MARGIN_PX
        top_inset = max(int(getattr(self, "_grid_viewport_top_inset", 0)), tag_margin)
        panel_open = (
            hasattr(self, "_tag_panel_overlay") and self._tag_panel_overlay.isVisible()
        )
        if hasattr(self, "tag_filters_floating_btn"):
            btn = self.tag_filters_floating_btn
            if panel_open:
                btn.hide()
            else:
                btn.show()
                h = max(1, viewport.height() - top_inset - tag_margin)
                btn.setFixedHeight(h)
                btn.move(0, top_inset)
                btn.raise_()
        if hasattr(self, "_tag_panel_overlay"):
            self._tag_panel_overlay.reposition()
        # Start session stays above tag rail, overlay, and tag popover
        session_btn = getattr(self, "session_settings_btn", None)
        shuffle_btn = getattr(self, "shuffle_button", None)
        if session_btn is not None:
            session_hint = session_btn.sizeHint()
            y = max(margin, viewport.height() - session_hint.height() - bottom_margin)
            shuffle_gap = 12
            if shuffle_btn is not None and shuffle_btn.isVisible():
                shuffle_hint = shuffle_btn.sizeHint()
                group_w = shuffle_hint.width() + shuffle_gap + session_hint.width()
                group_x = max(margin, (viewport.width() - group_w) // 2)
                shuffle_btn.setGeometry(
                    group_x, y, shuffle_hint.width(), shuffle_hint.height()
                )
                shuffle_btn.raise_()
                session_btn.setGeometry(
                    group_x + shuffle_hint.width() + shuffle_gap,
                    y,
                    session_hint.width(),
                    session_hint.height(),
                )
            else:
                x = max(margin, (viewport.width() - session_hint.width()) // 2)
                session_btn.setGeometry(
                    x, y, session_hint.width(), session_hint.height()
                )
            session_btn.raise_()

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
        registered = set(
            getattr(self, "_user_tags_config", {}).get("registered_only", [])
        )
        return from_db | registered

    def _get_all_tag_names(self) -> Set[str]:
        """All tag names in the system (default + user). Used to enforce unique names."""
        return self._get_default_tags() | self._get_user_tags()

    def _tag_name_already_used(self, name: str, exclude: Optional[str] = None) -> bool:
        """
        Return True if a tag with the same name already exists (case- and separator-insensitive).
        If exclude is set, that tag is ignored (for rename: current name is allowed).

        Returns:
            True if another tag would conflict with the given name.
        """
        norm = self._normalize_tag_for_match(name)
        if not norm:
            return False
        all_names = self._get_all_tag_names()
        for existing in all_names:
            if exclude is not None and existing == exclude:
                continue
            if self._normalize_tag_for_match(existing) == norm:
                return True
        return False

    def _apply_category_filters(
        self,
        _pre_sorted_images: Optional[List[ImageMetadata]] = None,
        *,
        sync_tags_after: bool = True,
    ) -> None:
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
            images_to_display = self._filter_images_by_category_from_list(
                images_to_display
            )
            # Apply AND/OR filters
            images_to_display = self._apply_and_or_filters(images_to_display)

            shuffle_iteration = self._shuffle_counter
        else:
            # Normal filtering and sorting for other sort modes
            if _pre_sorted_images is not None:
                filtered_images = self._filter_images_by_category(_pre_sorted_images)
            else:
                filtered_images = self._filter_images_by_category()
            filtered_images = self._apply_and_or_filters(filtered_images)
            shuffle_iteration = 0
            images_to_display = self.image_manager.db._sort_images(
                filtered_images, sort_by
            )

        filter_key = (
            frozenset(self._active_categories),
            frozenset(
                (category, frozenset(tags))
                for category, tags in self._active_subtags.items()
            ),
            sort_by,
            shuffle_iteration,  # Include shuffle iteration in filter key
        )
        self.image_grid.load_images_from_list(images_to_display, filter_key)
        self._update_session_images_count(images_to_display)
        # Panel manages its own UI state; no grid rebuild needed here.

        # Store filtered list for session (for course_random mode only)
        if sort_by == "course_random":
            self._filtered_course_random_list = images_to_display.copy()

    def _flush_tag_library_repaint(self) -> None:
        """Paint tag-library UI changes without running deferred grid work."""
        scroll = getattr(self, "tags_scroll_area", None)
        if scroll is not None:
            viewport = scroll.viewport()
            if viewport is not None:
                viewport.repaint()
        overlay = getattr(self, "_tag_panel_overlay", None)
        if overlay is not None and overlay.isVisible():
            overlay.repaint()

    def _schedule_apply_category_filters(
        self, _pre_sorted_images: Optional[List[ImageMetadata]] = None
    ) -> None:
        """
        Defer image-grid filtering to the next event-loop tick.

        Call after ``_sync_tag_grid_state()`` so tag chips repaint first.
        """
        QTimer.singleShot(
            0,
            lambda pre=_pre_sorted_images: self._apply_category_filters(
                pre, sync_tags_after=False
            ),
        )

    def _filter_images_by_category_from_list(
        self, images: List[ImageMetadata]
    ) -> List[ImageMetadata]:
        """
        Filter images from a given list by category/subtag filters (keeps original order).
        Shelf filters: AND shelves require all selected tags; OR shelves require any.
        """
        label_categories_and = shelf_categories_with_filter(
            self._tag_shelf_filter_modes, "and"
        )
        label_categories_or = shelf_categories_with_filter(
            self._tag_shelf_filter_modes, "or"
        )
        constraining_tags_and: Set[str] = set()
        for label_cat in label_categories_and:
            constraining_tags_and.update(
                self._expand_tags_with_descendants(
                    self._active_subtags.get(label_cat, set())
                )
            )
        constraining_tags_or: Set[str] = set()
        for label_cat in label_categories_or:
            constraining_tags_or.update(
                self._expand_tags_with_descendants(
                    self._active_subtags.get(label_cat, set())
                )
            )
        has_label = bool(constraining_tags_and) or bool(constraining_tags_or)
        if not self._active_categories and not has_label and not self._active_subtags:
            return images

        filtered = []
        constraining_and_norm = {
            self._normalize_tag_for_match(t) for t in constraining_tags_and
        }
        constraining_or_norm = {
            self._normalize_tag_for_match(t) for t in constraining_tags_or
        }
        category_filter_data = (
            self._get_active_category_filter_data() if self._active_categories else []
        )

        for metadata in images:
            image_tags_norm = {self._normalize_tag_for_match(t) for t in metadata.tags}

            if not self._active_categories:
                category_match = True
            else:
                # Image must match at least one category: in category AND has all its selected subtags (AND)
                category_match = False
                for allowed_norm, required_groups_norm in category_filter_data:
                    if not (image_tags_norm & allowed_norm):
                        continue
                    group_match = all(
                        bool(image_tags_norm & group) for group in required_groups_norm
                    )
                    if group_match:
                        category_match = True
                        break
            if not category_match:
                continue
            if constraining_and_norm and not constraining_and_norm.issubset(
                image_tags_norm
            ):
                continue
            if constraining_or_norm and not (constraining_or_norm & image_tags_norm):
                continue
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
            1: "import_date_asc",  # Oldest First
            2: "filename_asc",  # Filename A→Z
            3: "filename_desc",  # Filename Z→A
            4: "file_size_asc",  # Lightest First
            5: "file_size_desc",  # Heaviest First
            6: "course_random",  # Session Course Random
        }
        return sort_map.get(self.sort_combo.currentIndex(), "import_date_desc")

    def _on_sort_changed(self, index: int):
        """Handle sort order change."""
        if 0 <= index < len(SORT_OPTIONS):
            self.sort_combo.setToolTip(f"Sort by: {SORT_OPTIONS[index][1]}")
        # Show/hide shuffle button based on selected sort
        is_random_sort = index == 6  # Random is index 6
        self._update_shuffle_floating_visibility()

        # Reset shuffle counter when switching away from random sort
        if not is_random_sort:
            self._shuffle_counter = 0
            self._course_random_images_list = []  # Clear stored course random list
            self._filtered_course_random_list = []  # Clear filtered list

        # If switching to random sort, initialize the global random list if empty
        if is_random_sort and not self._course_random_images_list:
            self._initialize_course_random_list()

        # Persist chosen sort mode for next launch
        settings.set("ui.grid.sort_index", index)
        settings.save()

        # Reapply filters with new sort order
        self._apply_category_filters()

    def _on_shuffle_clicked(self):
        """Handle shuffle button click - regenerate random order for ALL images."""
        # Update global shuffle timestamp for more random variation
        import time
        from core.image_db import _shuffle_timestamp
        import core.image_db as image_db_module

        image_db_module._shuffle_timestamp = int(
            time.time() * 1000000
        )  # Use microseconds

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
            all_images, "course_random", shuffle_iteration=self._shuffle_counter
        )

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
        self.selection_info_label.setText(
            f"Selected: {len(image_ids)} · {total_mb:.2f} MB"
        )

    @staticmethod
    def _slice_images_from_start(
        images: List[Any], start_image_id: Optional[str]
    ) -> List[Any]:
        """Return images from start_image_id to end, preserving original order.

        Args:
            images: Ordered list of image-like objects containing an `id` attribute.
            start_image_id: ID of the first image to keep.

        Returns:
            List[Any]: Sliced list, or the original list when no valid start ID is provided.
        """
        if not start_image_id:
            return images

        for index, image in enumerate(images):
            if getattr(image, "id", None) == start_image_id:
                return images[index:]
        return images

    def _on_start_session_from_grid_image(self, image_id: str) -> None:
        """Open session settings and start a session from the selected grid image."""
        self._on_session_settings_clicked(start_from_image_id=image_id)

    def _on_session_settings_clicked(
        self, start_from_image_id: Optional[str] = None
    ) -> None:
        """Handle Session Settings button click and optionally start from one image."""
        # Get current sort order
        sort_by = self._get_current_sort_order()

        if sort_by == "course_random":
            # Use the EXACT same filtered list as the grid (stored in _filtered_course_random_list)
            if not self._filtered_course_random_list:
                # If not set, get it from grid's current display
                filtered_images = (
                    list(self.image_grid.all_images)
                    if hasattr(self.image_grid, "all_images")
                    else []
                )
                if not filtered_images:
                    # Fallback: regenerate filters
                    if not self._course_random_images_list:
                        self._initialize_course_random_list()
                    filtered_images = self._course_random_images_list
                    filtered_images = self._filter_images_by_category_from_list(
                        filtered_images
                    )
                    filtered_images = self._apply_and_or_filters(filtered_images)
            else:
                # Use the stored filtered list (same as grid)
                filtered_images = self._filtered_course_random_list

            shuffle_iteration = self._shuffle_counter
        else:
            # For other sort modes, get current filtered images
            filtered_images = self._filter_images_by_category()
            filtered_images = self._apply_and_or_filters(filtered_images)
            filtered_images = self.image_manager.db._sort_images(
                filtered_images, sort_by
            )
            shuffle_iteration = 0

        filtered_images = self._slice_images_from_start(
            filtered_images, start_from_image_id
        )
        image_count = len(filtered_images)

        from gui.session_settings_dialog import SessionSettingsDialog

        dialog = SessionSettingsDialog(self.image_manager, image_count, self)
        if dialog.exec_() != QDialog.Accepted or not dialog.session_started:
            return

        settings_dict = dialog.get_session_settings()
        session_type = settings_dict["session_type"]
        window_mode = settings_dict["window_mode"]
        # Use image IDs in the stored order (for course_random) or current order (for others)
        image_ids = [m.id for m in filtered_images]

        course_duration_minutes: Optional[int] = None
        interval_seconds: Optional[int] = None

        if session_type == "Course":
            course_duration_minutes = settings_dict["course_duration_minutes"]
        else:
            # Constant interval now comes from split spinboxes (minutes + tens of seconds).
            interval_seconds = settings_dict.get("interval_seconds", 450)

        if self._slideshow_window is None:
            from gui.slideshow_window import SlideshowWindow

            self._slideshow_window = SlideshowWindow(
                self.session_manager, self.image_manager, parent=self
            )
            self._slideshow_window.session_ended.connect(self._on_session_ended)

        course_config_path = (
            Path(__file__).resolve().parent / "ressources" / "session_configs.json"
        )
        # For course_random mode, use exact order (no reshuffle in session)
        use_exact_order = sort_by == "course_random"
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
                if category == MISCELLANEOUS_SHELF:
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

    def _load_tags_into_grid(self, skip_sync: bool = False) -> None:
        """
        Delegate tag library load to TagLibraryPanel.

        Preserves active filter state across reloads.
        """
        self._user_tags_config = user_tags_config.load_config()
        user_tags_set = self._get_user_tags()

        # Preserve filter state across reload
        restore_cats = set(self._active_categories)
        restore_subtags = {k: set(v) for k, v in self._active_subtags.items()}

        self._tag_library_panel.load(
            user_tags=user_tags_set,
            user_tags_config_data=self._user_tags_config,
            restore_categories=restore_cats,
            restore_subtags=restore_subtags,
        )

        # Sync shelf filter modes from panel
        self._tag_shelf_filter_modes = self._tag_library_panel.get_shelf_filter_modes()

        if not skip_sync:
            self._sync_tag_grid_state()
        self._update_tag_search_completer()

        # Legacy stubs kept for methods that haven't been migrated yet
        panel = self._tag_library_panel
        taxonomy = panel.get_taxonomy()
        self._subcategory_buttons = {}
        self._subcategory_containers = {}
        self._subcategory_tag_order = {}
        self._category_buttons = {}
        self._subtag_to_category = {}
        self._user_tag_display_order = []
        if taxonomy is not None:
            for cat in taxonomy.categories_order:
                self._subcategory_tag_order[cat] = list(taxonomy.subtag_order.get(cat, []))
                for tag in taxonomy.subtag_order.get(cat, []):
                    self._subtag_to_category[tag] = cat
            for cat, sec in panel._category_sections.items():
                self._category_buttons[cat] = sec._category_chip
                self._subcategory_buttons[cat] = dict(sec._grid_host._chips)
                self._subcategory_containers[cat] = sec._grid_host
            for shelf, sec in panel._shelf_sections.items():
                self._subcategory_buttons[shelf] = dict(sec._grid_host._chips)
                self._subcategory_containers[shelf] = sec._grid_host

        # (Legacy layout code removed — TagLibraryPanel now handles all widget construction)

        # Sentinel block: keep old variables accessible for code not yet migrated.
        if False:  # dead code — keeps type-checkers and old call sites from breaking
            subtag_buttons: Dict[str, QPushButton] = {}
            tag_button = None
            tag_name, category_name = "", ""

    def _tag_library_content_width(self) -> int:
        """
        Width available for tag grid content (scroll viewport, not full app window).

        Returns:
            int: Pixel width that must not be exceeded to avoid horizontal scrolling.
        """
        scroll = getattr(self, "tags_scroll_area", None)
        if scroll is not None and scroll.viewport() is not None:
            vp_w = scroll.viewport().width()
            if vp_w > 0:
                return vp_w
        from gui.tag_panel_overlay import TagPanelOverlay
        return (
            TagPanelOverlay.PANEL_WIDTH
            - TAG_LIBRARY_OVERLAY_HORIZONTAL_MARGIN_PX
            - TAG_LIBRARY_VIEWPORT_RIGHT_GUTTER_PX
        )

    def _tag_library_cell_width(self) -> int:
        """Subtag width: 3 columns + gaps inside shelf padding, with small trim."""
        panel = getattr(self, "_tag_library_panel", None)
        if panel is not None:
            return panel._compute_cell_width()
        content_w = self._tag_library_content_width()
        row_w = (
            content_w
            - 2 * TAG_LIBRARY_SHELF_GRID_PADDING_PX
            - TAG_LIBRARY_DROP_ZONE_BORDER_PX
        )
        gaps = TAG_LIBRARY_TAG_GRID_SPACING_PX * (TAG_LIBRARY_TAG_GRID_COLUMNS - 1)
        per_column = (row_w - gaps) // TAG_LIBRARY_TAG_GRID_COLUMNS
        return max(
            TAG_LIBRARY_TAG_CELL_MIN_WIDTH_PX,
            per_column - TAG_LIBRARY_TAG_CELL_WIDTH_TRIM_PX,
        )

    def _tag_library_category_row_width(self) -> int:
        """Main category row (Human, Animal, …) slightly narrower than full content."""
        panel = getattr(self, "_tag_library_panel", None)
        if panel is not None:
            return panel._compute_category_width()
        content_w = self._tag_library_content_width()
        return max(
            TAG_LIBRARY_TAG_CELL_MIN_WIDTH_PX,
            content_w - TAG_LIBRARY_CATEGORY_WIDTH_TRIM_PX,
        )

    def _apply_tag_library_cell_widths(self) -> None:
        """Delegate width propagation to the panel."""
        panel = getattr(self, "_tag_library_panel", None)
        if panel is not None:
            panel._apply_widths()

    def _build_tag_button(
        self,
        tag: str,
        is_user_tag: bool = False,
        *,
        library_subtag_cell: bool = False,
        library_category_row: bool = False,
    ) -> QPushButton:
        """
        Build a unified tag chip for the tag library.

        All library buttons (category rows and subtag cells) use
        ``WrappingDraggableTagButton`` so icon, text, sizing and visual
        states are always identical.

        Args:
            tag: Tag name.
            is_user_tag: If True, tag is user-owned (draggable/renameable).
            library_subtag_cell: True for 3-column grid cells.
            library_category_row: True for full-width category header rows.

        Returns:
            QPushButton: Configured tag button.
        """
        if library_category_row:
            cell_w = self._tag_library_category_row_width()
        elif library_subtag_cell:
            cell_w = self._tag_library_cell_width()
        else:
            cell_w = self._tag_library_cell_width()

        button: QPushButton
        if library_subtag_cell or library_category_row:
            button = WrappingDraggableTagButton(tag, cell_w)
        else:
            button = DraggableTagButton(tag)
            button.setCursor(Qt.PointingHandCursor)

        button.setObjectName("TagGridButton")
        button.setProperty("userTag", is_user_tag)
        button.setProperty("baseLabel", tag)
        if library_category_row:
            button.setProperty("tagGridCategory", True)

        overrides = getattr(self, "_icon_preview_override", {})
        user_config = getattr(self, "_user_tags_config", {})
        icon = find_tag_icon(tag, user_config=user_config, icon_preview_override=overrides)
        if not icon.isNull():
            # Use a large source pixmap so WrappingDraggableTagButton can scale to chip height
            src_px = max(TAG_LIBRARY_CATEGORY_ICON_PX, TAG_LIBRARY_TAG_MIN_HEIGHT_PX)
            button.setIcon(invert_icon(icon, src_px))
            button.setIconSize(QSize(src_px, src_px))

        button.setCheckable(False)
        return button

    @staticmethod
    def _with_expand_icon(label: str, has_children: bool, expanded: bool) -> str:
        """Return label prefixed with expand/collapse icon when relevant."""
        if not has_children:
            return label
        return f"{label} {'▼' if expanded else '▶'}"

    def _get_tag_depth_in_category(
        self,
        tag: str,
        category: str,
        visited: Optional[Set[str]] = None,
    ) -> int:
        """
        Compute hierarchy depth of a tag within its category.
        Root-level subtags are depth 0, their children are depth 1, etc.
        """
        if visited is None:
            visited = set()
        if tag in visited:
            return 0
        visited.add(tag)
        placements = self._user_tags_config.get("placements", {})
        pl = placements.get(tag)
        parent = pl.get("parent_tag") if isinstance(pl, dict) else None
        if not parent:
            return 0
        if self._subtag_to_category.get(parent) != category:
            return 1
        return 1 + self._get_tag_depth_in_category(parent, category, visited)

    def _get_hierarchy_background_color(self, branch_key: str, depth: int) -> QColor:
        """Return a punchy, vivid depth-based color for tag chips."""
        branch_norm = self._normalize_tag_for_match(branch_key)
        if branch_norm == "animal":
            hue = 128
        elif branch_norm == "human":
            hue = 212
        else:
            hue = sum(ord(c) for c in branch_key) % 360
        dark_theme = settings.get("ui.theme", "dark") != "light"
        if dark_theme:
            sat_pct = min(55 + depth * 5, 80)
            light_pct = min(28 + depth * 8, 58)
        else:
            sat_pct = min(50 + depth * 6, 80)
            light_pct = max(80 - depth * 8, 42)
        return QColor.fromHsl(
            hue,
            int(255 * sat_pct / 100),
            int(255 * light_pct / 100),
        )

    @staticmethod
    def _blend_color(base: QColor, tint: QColor, ratio: float) -> QColor:
        """
        Mix base color toward tint by ratio.

        Args:
            base: Source color.
            tint: Target tint color.
            ratio: 0.0 = pure base, 1.0 = pure tint.

        Returns:
            QColor: Blended color (same alpha as base).
        """
        r = int(base.red() + (tint.red() - base.red()) * ratio)
        g = int(base.green() + (tint.green() - base.green()) * ratio)
        b = int(base.blue() + (tint.blue() - base.blue()) * ratio)
        return QColor(max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)), base.alpha())

    @staticmethod
    def _chip_gradient(bg: QColor, *, lighter: int = 108, darker: int = 112, alpha_top: int = 230, alpha_bot: int = 215) -> str:
        """
        Build a vertical qlineargradient CSS value for a tag chip.

        Args:
            bg: Base background color.
            lighter: Factor for the top stop (lighter).
            darker: Factor for the bottom stop (darker).
            alpha_top: Alpha for the top stop.
            alpha_bot: Alpha for the bottom stop.

        Returns:
            str: CSS background value.
        """
        top = bg.lighter(lighter)
        bot = bg.darker(darker)
        top.setAlpha(alpha_top)
        bot.setAlpha(alpha_bot)

        def _rgba(c: QColor) -> str:
            return f"rgba({c.red()},{c.green()},{c.blue()},{c.alpha()})"

        return (
            f"qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            f"stop:0 {_rgba(top)},stop:1 {_rgba(bot)})"
        )

    def _set_hierarchy_button_style(
        self,
        button: QPushButton,
        branch_key: str,
        depth: int,
        active: bool,
        selected_for_drag: bool = False,
    ) -> None:
        """
        Apply unified gradient style + 4 visual states to any tag library button.

        The heavy stylesheet string is generated once per (branch_key, depth) and
        cached on the button.  Subsequent calls only refresh the tagState property
        when the state actually changed, avoiding costly setStyleSheet / unpolish
        / polish calls on every _sync_tag_grid_state sweep.

        States:
            rest       – vivid gradient, subtle outline
            hover      – brighter gradient, lighter border (via :hover QSS)
            selected   – blue-tinted gradient + blue border  (selected_for_drag=True)
            active     – green-tinted gradient + green border (active=True)
        """
        dark_theme = settings.get("ui.theme", "dark") != "light"

        # --- Stylesheet: only rebuild if (branch_key, depth) changed -------------
        style_key = (branch_key, depth)
        if button.property("_styleKey") != str(style_key):
            bg = self._get_hierarchy_background_color(branch_key, depth)
            text = "#f5f5f5" if dark_theme else "#1a1a1a"

            grad_rest = self._chip_gradient(bg, lighter=108, darker=112, alpha_top=220, alpha_bot=200)
            grad_hover = self._chip_gradient(bg, lighter=128, darker=108, alpha_top=240, alpha_bot=225)

            blue_tint = QColor(80, 150, 255)
            bg_sel = self._blend_color(bg, blue_tint, 0.30)
            grad_sel = self._chip_gradient(bg_sel, lighter=115, darker=108, alpha_top=235, alpha_bot=215)
            grad_sel_h = self._chip_gradient(bg_sel, lighter=135, darker=105, alpha_top=245, alpha_bot=230)

            green_tint = QColor(80, 220, 100)
            bg_act = self._blend_color(bg, green_tint, 0.30)
            grad_act = self._chip_gradient(bg_act, lighter=115, darker=108, alpha_top=235, alpha_bot=215)
            grad_act_h = self._chip_gradient(bg_act, lighter=135, darker=105, alpha_top=245, alpha_bot=230)

            border_idle = tag_library_idle_border_css(bg)
            border_hover = f"2px solid {bg.lighter(165).name()}"
            blue_border = "#5aabff" if dark_theme else "#2b6cb0"
            green_border = "#72f572" if dark_theme else "#2fa84f"

            font_px = TAG_LIBRARY_FONT_SUBTAG_PX
            font_css = f"font-size: {font_px}px; font-weight: 600;"
            is_wrapping = isinstance(button, WrappingDraggableTagButton)
            padding = "0px" if is_wrapping else f"{TAG_LIBRARY_TAG_STYLE_V_PADDING_PX}px 4px"

            def _block(selector: str, grad: str, border: str) -> str:
                return (
                    f"{selector} {{ padding: {padding}; color: {text}; {font_css} "
                    f"background: {grad}; border: {border}; border-radius: 5px; }}\n"
                )

            css = (
                _block("QPushButton", grad_rest, border_idle)
                + _block("QPushButton:hover", grad_hover, border_hover)
                + _block('QPushButton[tagState="selected"]', grad_sel, f"2px solid {blue_border}")
                + _block('QPushButton[tagState="selected"]:hover', grad_sel_h, f"2px solid {blue_border}")
                + _block('QPushButton[tagState="active"]', grad_act, f"2px solid {green_border}")
                + _block('QPushButton[tagState="active"]:hover', grad_act_h, f"2px solid {green_border}")
            )
            button.setStyleSheet(css)
            button.setProperty("_styleKey", str(style_key))
            button.setCursor(Qt.PointingHandCursor)

            # Drop shadow: create once per button
            shadow = button.graphicsEffect()
            if not isinstance(shadow, QGraphicsDropShadowEffect):
                shadow = QGraphicsDropShadowEffect(button)
                button.setGraphicsEffect(shadow)
                shadow.setBlurRadius(TAG_LIBRARY_TAG_SHADOW_BLUR_PX)
                shadow.setOffset(0, TAG_LIBRARY_TAG_SHADOW_OFFSET_PX)
                shadow.setColor(QColor(0, 0, 0, TAG_LIBRARY_TAG_SHADOW_ALPHA))

        # --- State property: only re-polish when it actually changes -------------
        new_state = "selected" if selected_for_drag else ("active" if active else "")
        if button.property("tagState") != new_state:
            button.setProperty("tagState", new_state)
            button.style().unpolish(button)
            button.style().polish(button)

    def _on_icon_preview(self, tag: str, icon_filename: Optional[str]) -> None:
        """Live preview: show the chosen icon on the tag button while the icon picker dialog is open."""
        self._icon_preview_override[tag] = icon_filename
        self._update_tag_button_icon(tag)

    def _update_tag_button_icon(self, tag: str) -> None:
        """
        Update the icon of the existing tag button for `tag` without rebuilding the grid.

        Delegates to the panel's chip registry.
        """
        panel = getattr(self, "_tag_library_panel", None)
        if panel is not None:
            panel.update_chip_icon(tag)

    def _on_tag_button_clicked(
        self, tag: str, category_override: Optional[str] = None
    ) -> None:
        """
        Toggle tag in filters from tag buttons.
        When in "Parent to tag..." mode, clicking a tag or category sets it as parent instead.

        Args:
            tag: Tag name to toggle.
            category_override: When set, use this category (for tags that appear in multiple categories, e.g. Weapon).
        """
        if self._parent_select_mode:
            self._on_tag_clicked_in_parent_mode(tag, category_override)
            return
        # Reason: simple click drives filter/expand-collapse only; clear any stale tag-library selection highlight.
        if self._tag_library_selection:
            self._tag_library_selection.clear()
            self._last_selected_tag = None
        # Label categories are not real tags and should never be added to active categories
        if tag in self._category_buttons:
            # Toggle expand/collapse so sub-tags are visible when expanded
            if tag in self._active_categories:
                print(f"[TAG-DEBUG] category_click deactivate requested: {tag}")
                self._deactivate_category(tag)
            else:
                print(f"[TAG-DEBUG] category_click activate requested: {tag}")
                self._active_categories.add(tag)
                self._active_subtags.setdefault(tag, set())
        else:
            category = (
                category_override
                if category_override is not None
                else self._subtag_to_category.get(tag)
            )
            if not category:
                return

            # For label categories, don't add them to active_categories
            # Just manage their sub-tags directly
            if is_tag_shelf(category):
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
                    self._deactivate_subcategory(category, tag)
                else:
                    category_tags.add(tag)
        # Tag library first, image grid on the next event-loop tick.
        affected: Optional[Set[str]] = None
        if tag in self._category_buttons:
            affected = {tag}
        else:
            cat = (
                category_override
                if category_override is not None
                else self._subtag_to_category.get(tag)
            )
            if cat:
                affected = {cat}
        force_rebuild = {tag} if tag in self._category_buttons else None
        self._sync_tag_grid_state(
            categories=affected, force_layout_rebuild=force_rebuild
        )
        self._flush_tag_library_repaint()
        self._schedule_apply_category_filters()

    def _deactivate_category(self, category: str) -> None:
        """
        Deactivate a category and clear all related active sub-tags/filters.

        Args:
            category: Category to deactivate.
        """
        active_subtags_before = {
            key: sorted(values) for key, values in self._active_subtags.items()
        }
        print(
            f"[TAG-DEBUG] deactivate_category(before) category={category} "
            f"active_categories={sorted(self._active_categories)} "
            f"active_subtags={active_subtags_before}"
        )
        self._active_categories.discard(category)
        self._active_subtags.pop(category, None)
        # Reason: force-clear any stale subtag entries that still point to this category.
        for tag in list(self._subtag_to_category.keys()):
            if self._subtag_to_category.get(tag) == category:
                for cat_name, selected_tags in list(self._active_subtags.items()):
                    if tag in selected_tags:
                        selected_tags.discard(tag)
                    if not selected_tags:
                        self._active_subtags.pop(cat_name, None)
        tags_to_remove = set(self._get_category_match_tags(category))
        # Reason: also remove any residual AND/OR tag mapped to this category, even if
        # it is currently hidden or not part of the visible descendants list.
        and_tags = set(self.and_zone.get_tags())
        or_tags = set(self.or_zone.get_tags())
        for tag in and_tags | or_tags:
            if self._subtag_to_category.get(tag) == category:
                tags_to_remove.add(tag)
        for tag in tags_to_remove:
            if tag in and_tags:
                self.and_zone.remove_tag(tag)
            if tag in or_tags:
                self.or_zone.remove_tag(tag)
        active_subtags_after = {
            key: sorted(values) for key, values in self._active_subtags.items()
        }
        print(
            f"[TAG-DEBUG] deactivate_category(after) category={category} "
            f"active_categories={sorted(self._active_categories)} "
            f"active_subtags={active_subtags_after}"
        )

    def _deactivate_subcategory(self, category: str, tag: str) -> None:
        """
        Deactivate a sub-category tag and all its descendant tags/filters.

        Args:
            category: Parent category name.
            tag: Sub-category tag to deactivate.
        """
        category_tags = self._active_subtags.setdefault(category, set())
        descendants = self._get_all_descendants(tag)
        for descendant in descendants:
            category_tags.discard(descendant)
        if not category_tags:
            self._active_subtags.pop(category, None)

        and_tags = set(self.and_zone.get_tags())
        or_tags = set(self.or_zone.get_tags())
        for descendant in descendants:
            if descendant in and_tags:
                self.and_zone.remove_tag(descendant)
            if descendant in or_tags:
                self.or_zone.remove_tag(descendant)

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
        self._sync_tag_grid_state()
        self._flush_tag_library_repaint()
        self._schedule_apply_category_filters()

    def _on_tag_filter_changed(self, tag: str = None) -> None:
        """
        Handle tag filter change from AND/OR zones.

        Args:
            tag: Tag that was added/removed (optional, for tag_dropped signal).
        """
        self._sync_tag_grid_state()
        self._flush_tag_library_repaint()
        self._schedule_apply_category_filters()

    def _clear_all_tag_filters(self) -> None:
        """Clear all tag filters (category, AND, and OR)."""
        self._active_categories.clear()
        self._active_subtags.clear()
        self.and_zone.clear_tags()
        self.or_zone.clear_tags()
        panel = getattr(self, "_tag_library_panel", None)
        if panel is not None:
            panel.clear_filters()
        else:
            self._sync_tag_grid_state()
        self._flush_tag_library_repaint()
        self._schedule_apply_category_filters()

    def _is_in_tag_library(self, widget: QObject) -> bool:
        """Return True if widget is the tag library scroll area or any of its descendants."""
        w = widget
        scroll = getattr(self, "tags_scroll_area", None)
        if not scroll:
            return False
        while w:
            if w == scroll:
                return True
            w = w.parent() if hasattr(w, "parent") else None
        return False

    def _get_tag_library_viewport_pos(
        self, obj: QObject, pos: QPoint
    ) -> Optional[QPoint]:
        """Map a position from obj's coordinates to tag library viewport coordinates."""
        viewport = (
            getattr(self, "tags_scroll_area", None) and self.tags_scroll_area.viewport()
        )
        if not viewport or not obj:
            return None
        if hasattr(obj, "mapToGlobal") and hasattr(viewport, "mapFromGlobal"):
            global_pos = (
                obj.mapToGlobal(pos)
                if hasattr(pos, "x")
                else obj.mapToGlobal(QPoint(pos.x(), pos.y()))
            )
            return viewport.mapFromGlobal(global_pos)
        return None

    def _get_tag_button_for(self, tag_name: str) -> Optional[QWidget]:
        """Return the tag button widget for the given user tag name, or None."""
        panel = getattr(self, "_tag_library_panel", None)
        if panel is not None:
            chip = panel.get_chip(tag_name)
            if chip is not None:
                return chip
        category = self._subtag_to_category.get(tag_name)
        if not category:
            return None
        buttons = self._subcategory_buttons.get(category, {})
        return buttons.get(tag_name)

    def _tag_library_selection_union(self) -> Set[str]:
        """
        Return the combined tag-library multi-select from MainWindow and panel.

        Returns:
            Set[str]: Selected tag names.
        """
        selection = set(self._tag_library_selection)
        panel = getattr(self, "_tag_library_panel", None)
        if panel is not None:
            selection |= set(panel._tag_library_selection)
        return selection

    def _tags_being_dragged(self, primary_tag: str) -> Set[str]:
        """
        Resolve which user tags move together for a grid drag or drop.

        When *primary_tag* is part of the current multi-selection, every
        selected user tag is included; otherwise only *primary_tag* moves.

        Args:
            primary_tag: Tag under the cursor when the drag started.

        Returns:
            Set[str]: User-owned tag names to reparent.
        """
        user_tags = self._get_user_tags()
        if primary_tag not in user_tags:
            return set()
        selection = self._tag_library_selection_union()
        if primary_tag in selection and len(selection) > 1:
            return {t for t in selection if t in user_tags}
        return {primary_tag}

    def _tags_for_apply_drag(self, primary_tag: str) -> Set[str]:
        """
        Resolve tag names dragged onto images (default + user tags).

        Args:
            primary_tag: Tag under the cursor when the drag started.

        Returns:
            Set[str]: Tag names encoded in the drag MIME payload.
        """
        selection = self._tag_library_selection_union()
        if primary_tag in selection and len(selection) > 1:
            return set(selection)
        return {primary_tag}

    def _tags_from_drop_mime(self, mime_data: "QMimeData", primary_tag: str) -> Set[str]:
        """
        Read dragged tag names from drop MIME data.

        Prefers ``TAG_LIBRARY_MULTI_MIME`` when present, otherwise falls back
        to the live selection or the single primary tag.

        Args:
            mime_data: Qt MIME payload from the drop event.
            primary_tag: Primary tag encoded in ``TAG_LIBRARY_MIME``.

        Returns:
            Set[str]: User-owned tag names to reparent.
        """
        user_tags = self._get_user_tags()
        tags: Set[str] = set()
        if mime_data.hasFormat(TAG_LIBRARY_MULTI_MIME):
            raw = mime_data.data(TAG_LIBRARY_MULTI_MIME)
            if raw:
                text = bytes(raw).decode("utf-8")
                tags = {line.strip() for line in text.splitlines() if line.strip()}
        if not tags:
            tags = self._tags_being_dragged(primary_tag)
        return {t for t in tags if t in user_tags}

    def _tag_chip_drag_label(self, button: QWidget) -> str:
        """
        Resolve the tag name encoded when dragging a library chip.

        Args:
            button: Source chip widget.

        Returns:
            str: Canonical tag label for MIME / image assignment.
        """
        key = button.property("tagGridKey")
        if key:
            return str(key)
        base = button.property("baseLabel")
        if base:
            return str(base)
        return str(button.text() if hasattr(button, "text") else "")

    def _tag_chip_allows_reparent(self, button: QWidget) -> bool:
        """
        Return True when a dragged chip may be reparented in the tag grid.

        Category headers and default taxonomy tags only apply to images.

        Args:
            button: Source chip widget.

        Returns:
            bool: True for user-owned subtags.
        """
        if bool(button.property("tagGridCategory")):
            return False
        return bool(button.property("userTag"))

    def _tag_filters_floating_btn_global_rect(self) -> Optional[QRect]:
        """
        Return the Tags-filters rail button bounds in screen coordinates.

        Returns:
            QRect or None if the button is missing or hidden.
        """
        btn = getattr(self, "tag_filters_floating_btn", None)
        if btn is None or not btn.isVisible():
            return None
        return QRect(btn.mapToGlobal(QPoint(0, 0)), btn.size())

    def _begin_tag_library_drag_session(self) -> None:
        """
        Start shared drag helpers: panel fold/reopen poll and tag-library autoscroll.

        Used for every tag-library QDrag (user tags, categories, multi-select).
        """
        self._tag_drag_in_progress = True
        self._start_tag_panel_drag_outside_poll()
        if self._tag_drag_scroll_timer is None:
            self._tag_drag_scroll_timer = QTimer(self)
            self._tag_drag_scroll_timer.timeout.connect(self._on_tag_drag_scroll_tick)
        self._tag_drag_scroll_timer.start(120)

    def _end_tag_library_drag_session(self) -> None:
        """Stop drag helpers after any tag-library QDrag ends."""
        self._tag_drag_in_progress = False
        self._stop_tag_panel_drag_outside_poll()
        self._tag_grid_hover_expand_cancel()
        if self._tag_drag_scroll_timer is not None:
            self._tag_drag_scroll_timer.stop()

    def _start_tag_panel_drag_outside_poll(self) -> None:
        """
        Poll the cursor while a tag-library QDrag runs.

        Qt often omits Leave on the overlay during native DnD (especially on Windows),
        so the deferred leave timer alone can miss a fold when the pointer is already
        outside the panel.
        """
        if not hasattr(self, "_tag_panel_overlay"):
            return
        if self._tag_panel_drag_outside_poll_timer is None:
            self._tag_panel_drag_outside_poll_timer = QTimer(self)
            self._tag_panel_drag_outside_poll_timer.setInterval(35)
            self._tag_panel_drag_outside_poll_timer.timeout.connect(
                self._on_tag_panel_drag_outside_poll_tick
            )
        self._tag_panel_drag_outside_poll_timer.start()

    def _stop_tag_panel_drag_outside_poll(self) -> None:
        """Stop cursor polling after tag drag ends."""
        if self._tag_panel_drag_outside_poll_timer is not None:
            self._tag_panel_drag_outside_poll_timer.stop()

    def _on_tag_panel_drag_outside_poll_tick(self) -> None:
        """
        During a tag-library drag: fold panel over the image grid, reopen on rail/panel hover.

        Keeps polling while the drag runs (even when folded) so hovering the lateral
        Tags-filters button can slide the library back in.
        """
        if not self._tag_drag_in_progress:
            self._stop_tag_panel_drag_outside_poll()
            return
        ov = getattr(self, "_tag_panel_overlay", None)
        if ov is None:
            self._stop_tag_panel_drag_outside_poll()
            return
        if ov.is_dismiss_locked():
            return

        pos = QCursor.pos()
        on_panel = ov.panel_global_rect().contains(pos)
        rail_rect = self._tag_filters_floating_btn_global_rect()
        on_rail = rail_rect is not None and rail_rect.contains(pos)

        if on_panel or on_rail:
            if not ov.is_panel_visible():
                ov.show_animated()
                self._left_panel_expanded = True
                QTimer.singleShot(0, self._position_floating_grid_overlays)
            return

        if ov.is_panel_visible():
            ov.hide_animated()
            self._left_panel_expanded = False

    def _on_tag_drag_scroll_tick(self) -> None:
        """During tag drag: scroll tag library when cursor is near top or bottom edge."""
        if not self._tag_drag_in_progress:
            return
        ov = getattr(self, "_tag_panel_overlay", None)
        if ov is None or not ov.is_panel_visible():
            return
        scroll = getattr(self, "tags_scroll_area", None)
        if not scroll:
            return
        viewport = scroll.viewport()
        vbar = scroll.verticalScrollBar()
        if not viewport or vbar is None:
            return
        margin = 48
        step = 28
        pos = QCursor.pos()
        # Prefer scroll viewport edges; fall back to whole panel when viewport is narrow.
        scroll_rect = QRect(viewport.mapToGlobal(QPoint(0, 0)), viewport.size())
        panel_rect = ov.panel_global_rect()
        zone = scroll_rect if scroll_rect.contains(pos) else (
            panel_rect if panel_rect.contains(pos) else None
        )
        if zone is None:
            return
        if pos.y() < zone.top() + margin:
            vbar.setValue(max(0, vbar.value() - step))
        elif pos.y() > zone.bottom() - margin:
            vbar.setValue(min(vbar.maximum(), vbar.value() + step))

    def _start_tag_button_drag(
        self, button: QWidget, tag_text: str, *, reparent: bool = True
    ) -> None:
        """
        Start a drag from a tag button with the chip pixmap under the cursor.

        User tags may be reparented in the library (``reparent=True``).
        Default tags only apply to images (``reparent=False``).

        Args:
            button: Source chip widget.
            tag_text: Primary dragged tag name.
            reparent: True to allow tag-library reparenting (user tags).
        """
        self._tag_drop_was_on_grid = False
        tags_to_drop = (
            self._tags_being_dragged(tag_text)
            if reparent
            else self._tags_for_apply_drag(tag_text)
        )
        if not tags_to_drop:
            return
        # Composite pixmap: all selected tags stacked (before we remove any button)
        pixmap = None
        hot_spot: Optional[QPoint] = None
        if len(tags_to_drop) > 1:
            tag_list = sorted(tags_to_drop)
            grabs: List[QPixmap] = []
            for t in tag_list:
                btn = self._get_tag_button_for(t)
                if btn and btn.isVisible():
                    g = get_chip_drag_source(btn)
                    if not g.isNull():
                        grabs.append(g)
            if grabs:
                offset = 6
                w = max(p.width() for p in grabs) + (len(grabs) - 1) * offset
                h = max(p.height() for p in grabs) + (len(grabs) - 1) * offset
                composite = QPixmap(w, h)
                composite.fill(Qt.transparent)
                painter = QPainter(composite)
                for i, p in enumerate(grabs):
                    painter.drawPixmap(i * offset, i * offset, p)
                painter.end()
                hot_spot = chip_drag_hot_spot(composite)
                pixmap, hot_spot = drag_pixmap_with_shadow(composite, hot_spot)
        else:
            pixmap, hot_spot = build_chip_drag_pixmap(button)
        if pixmap is None or pixmap.isNull():
            composite = QPixmap(max(120, button.width()), max(28, button.height()))
            composite.fill(Qt.transparent)
            painter = QPainter(composite)
            painter.setPen(Qt.white)
            painter.drawText(composite.rect(), Qt.AlignCenter, tag_text)
            painter.end()
            hot_spot = chip_drag_hot_spot(composite)
            pixmap, hot_spot = drag_pixmap_with_shadow(composite, hot_spot)
        elif hot_spot is None:
            hot_spot = chip_drag_hot_spot(pixmap)

        restore_list: List[Tuple[QWidget, QWidget, Any, int, int, int, int]] = []
        self._drag_ghost_placeholders = []
        if reparent:
            for t in tags_to_drop:
                btn = self._get_tag_button_for(t)
                if not btn or not btn.isVisible():
                    continue
                cont = btn.parentWidget()
                lay = cont.layout() if cont else None
                r, c, rspan, cspan = -1, -1, 1, 1
                if lay and hasattr(lay, "indexOf"):
                    idx = lay.indexOf(btn)
                    if idx >= 0 and hasattr(lay, "getItemPosition"):
                        r, c, rspan, cspan = lay.getItemPosition(idx)
                if lay is not None and r >= 0:
                    ghost = QWidget(cont)
                    ghost.setFixedSize(btn.width(), btn.height())
                    ghost.setStyleSheet(
                        "background: rgba(255,255,255,0.07);"
                        "border: 1px dashed rgba(255,255,255,0.25);"
                        "border-radius: 6px;"
                    )
                    ghost.show()
                    lay.removeWidget(btn)
                    lay.addWidget(ghost, r, c, rspan, cspan)
                    self._drag_ghost_placeholders.append(
                        (ghost, cont, lay, r, c, rspan, cspan)
                    )
                btn.hide()
                restore_list.append((btn, cont, lay, r, c, rspan, cspan))

        drag = QDrag(button)
        mime_data = QMimeData()
        mime_data.setText(tag_text)
        if reparent and button.property("userTag"):
            mime_data.setData(TAG_LIBRARY_MIME, tag_text.encode("utf-8"))
            if len(tags_to_drop) > 1:
                mime_data.setData(
                    TAG_LIBRARY_MULTI_MIME,
                    "\n".join(sorted(tags_to_drop)).encode("utf-8"),
                )
        elif not reparent and len(tags_to_drop) > 1:
            mime_data.setData(
                TAG_LIBRARY_MULTI_MIME,
                "\n".join(sorted(tags_to_drop)).encode("utf-8"),
            )

        drag.setMimeData(mime_data)
        drag.setPixmap(pixmap)
        drag.setHotSpot(apply_drag_cursor_offset(hot_spot, pixmap))
        self._begin_tag_library_drag_session()
        try:
            drag.exec_(Qt.MoveAction)
        finally:
            self._end_tag_library_drag_session()
            # Always remove ghost placeholders
            for ghost, cont, lay, r, c, rspan, cspan in self._drag_ghost_placeholders:
                try:
                    if lay is not None:
                        lay.removeWidget(ghost)
                    ghost.deleteLater()
                except Exception:
                    pass
            self._drag_ghost_placeholders = []
        # Restore user tags to their original place if drop was cancelled
        if reparent and not self._tag_drop_was_on_grid and restore_list:
            try:
                for btn, cont, lay, r, c, rspan, cspan in restore_list:
                    if (
                        cont is not None
                        and lay is not None
                        and r >= 0
                        and btn.parent() is cont
                    ):
                        lay.addWidget(btn, r, c, rspan, cspan)
                        btn.show()
                self._sync_tag_grid_state()
                button.update()
                if restore_list:
                    first_cont = restore_list[0][1]
                    if first_cont is not None:
                        first_cont.updateGeometry()
                        first_cont.update()
                if hasattr(self, "tags_grid_container") and self.tags_grid_container:
                    self.tags_grid_container.update()
                if (
                    hasattr(self, "tags_scroll_area")
                    and self.tags_scroll_area.viewport()
                ):
                    self.tags_scroll_area.viewport().update()
                QApplication.processEvents()
            except Exception:
                pass

    def _get_user_tag_at_viewport_pos(self, viewport_pos: QPoint) -> Optional[str]:
        """Return the user tag name whose button contains viewport_pos, or None."""
        container = getattr(self, "tags_grid_container", None)
        if not container:
            return None
        viewport = self.tags_scroll_area.viewport()
        container_pos = container.mapFrom(viewport, viewport_pos)
        w = container.childAt(container_pos)
        while w:
            if isinstance(w, DraggableTagButton) and w.property("userTag"):
                return w.property("baseLabel") or w.text()
            p = w.mapFrom(container, container_pos)
            next_w = w.childAt(p) if hasattr(w, "childAt") else None
            w = next_w
        return None

    def _get_user_tag_buttons_viewport_rects(self) -> List[Tuple[str, QRect]]:
        """Return list of (tag_name, viewport_QRect) for each visible user tag button."""
        return self._get_subtag_buttons_viewport_rects(user_only=True)

    def _get_subtag_buttons_viewport_rects(
        self, user_only: bool = False
    ) -> List[Tuple[str, QRect]]:
        """
        Return (tag_name, viewport_QRect) for every visible subtag button.

        Args:
            user_only: If True, include only user-owned tags.

        Returns:
            List of (tag, viewport rect) tuples in grid display order.
        """
        panel = getattr(self, "_tag_library_panel", None)
        if panel is not None:
            return panel.get_visible_chip_rects(user_only=user_only)
        viewport = (
            getattr(self, "tags_scroll_area", None) and self.tags_scroll_area.viewport()
        )
        if not viewport:
            return []
        result: List[Tuple[str, QRect]] = []
        for _category, buttons in getattr(self, "_subcategory_buttons", {}).items():
            for tag, btn in buttons.items():
                if user_only and not btn.property("userTag"):
                    continue
                if not btn.isVisible():
                    continue
                top_left_global = btn.mapToGlobal(btn.rect().topLeft())
                viewport_tl = viewport.mapFromGlobal(top_left_global)
                result.append((tag, QRect(viewport_tl, btn.size())))
        return result

    def _get_all_subtags_ordered(self) -> List[str]:
        """Return all currently visible subtag names in top-to-bottom, left-to-right order."""
        rects = self._get_subtag_buttons_viewport_rects(user_only=False)
        rects.sort(key=lambda tr: (tr[1].top(), tr[1].left()))
        return [t for t, _ in rects]

    def _tag_library_ctrl_click(self, tag: str) -> None:
        """Toggle a single tag in the library selection (Ctrl+click)."""
        if tag in self._tag_library_selection:
            self._tag_library_selection.discard(tag)
        else:
            self._tag_library_selection.add(tag)
        self._last_selected_tag = tag
        self._sync_tag_grid_state()

    def _tag_library_shift_click(self, tag: str) -> None:
        """Extend selection from the last clicked tag to ``tag`` (Shift+click)."""
        ordered = self._get_all_subtags_ordered()
        if not ordered:
            return
        anchor = self._last_selected_tag
        if anchor is None or anchor not in ordered:
            self._tag_library_selection.add(tag)
            self._last_selected_tag = tag
            self._sync_tag_grid_state()
            return
        i_anchor = ordered.index(anchor)
        try:
            i_tag = ordered.index(tag)
        except ValueError:
            self._tag_library_selection.add(tag)
            self._last_selected_tag = tag
            self._sync_tag_grid_state()
            return
        lo, hi = min(i_anchor, i_tag), max(i_anchor, i_tag)
        for t in ordered[lo : hi + 1]:
            self._tag_library_selection.add(t)
        self._last_selected_tag = tag
        self._sync_tag_grid_state()

    def _tag_library_finish_selection(
        self, release_viewport_pos: QPoint, modifiers: Qt.KeyboardModifiers
    ) -> None:
        """Apply tag-library selection after modifier+drag rectangle release."""
        start = self._tag_library_selection_start
        if start is None:
            return
        dx = abs(release_viewport_pos.x() - start.x())
        dy = abs(release_viewport_pos.y() - start.y())
        is_drag = (dx > 5) or (dy > 5)
        if is_drag:
            selection_rect = QRect(start, release_viewport_pos).normalized()
            add_to_selection = bool(modifiers & (Qt.ControlModifier | Qt.ShiftModifier))
            if not add_to_selection:
                self._tag_library_selection.clear()
            last_tag = None
            for tag, rect in self._get_subtag_buttons_viewport_rects(user_only=False):
                if selection_rect.intersects(rect):
                    self._tag_library_selection.add(tag)
                    last_tag = tag
            if last_tag:
                self._last_selected_tag = last_tag
        self._tag_library_selection_start = None
        self._tag_library_is_selecting = False
        self._tag_library_drag_start_tag = None
        self._tag_library_drag_start_button = None
        self._sync_tag_grid_state()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Tag library selection: modifier+drag rectangle only."""
        try:
            _enter = QEvent.Type.Enter
            _leave = QEvent.Type.Leave
            _mouse_move = QEvent.Type.MouseMove
        except AttributeError:
            _enter = QEvent.Enter
            _leave = QEvent.Leave
            _mouse_move = QEvent.MouseMove

        # Keep resize cursor feedback reliable in frameless mode, even above child widgets.
        if (
            event.type() == _mouse_move
            and hasattr(event, "pos")
            and isinstance(obj, QWidget)
            and not self.isMaximized()
            and not (event.buttons() & Qt.LeftButton)
        ):
            local_pos = obj.mapTo(self, event.pos()) if obj is not self else event.pos()
            self._update_resize_cursor(local_pos)

        if event.type() == _leave and obj is self:
            self.unsetCursor()

        # Hover over Tags filters trigger: open on Enter only (not every MouseMove —
        # that retriggered reposition and fought the slide animation).
        if (
            hasattr(self, "tag_filters_floating_btn")
            and obj == self.tag_filters_floating_btn
            and event.type() == _enter
            and hasattr(self, "_tag_panel_overlay")
            and not self._tag_panel_overlay.is_panel_visible()
        ):
            self._tag_panel_overlay.show_animated()
            self._left_panel_expanded = True
            QTimer.singleShot(0, self._position_floating_grid_overlays)
            return False

        try:
            _drag_enter = QEvent.Type.DragEnter
            _drag_move = QEvent.Type.DragMove
        except AttributeError:
            _drag_enter = QEvent.DragEnter
            _drag_move = QEvent.DragMove

        if (
            hasattr(self, "image_grid")
            and obj == self.image_grid.viewport()
            and event.type() in (_drag_enter, _drag_move)
        ):
            md = event.mimeData()
            if mime_data_looks_like_tag_library_drag(md):
                ov = getattr(self, "_tag_panel_overlay", None)
                rail_rect = self._tag_filters_floating_btn_global_rect()
                if ov is not None and rail_rect is not None:
                    pos = (
                        event.globalPosition().toPoint()
                        if hasattr(event, "globalPosition")
                        and hasattr(event.globalPosition(), "toPoint")
                        else (
                            self.image_grid.viewport().mapToGlobal(event.pos())
                            if hasattr(event, "pos")
                            else QCursor.pos()
                        )
                    )
                    if rail_rect.contains(pos) and not ov.is_panel_visible():
                        ov.show_animated()
                        self._left_panel_expanded = True
                        QTimer.singleShot(0, self._position_floating_grid_overlays)
            return False

        # Keep floating grid overlays (Tags filters, Start session) anchored on viewport resize.
        if (
            hasattr(self, "image_grid")
            and obj == self.image_grid.viewport()
            and event.type() in (QEvent.Type.Resize, QEvent.Resize)
        ):
            self._position_floating_grid_overlays()
            return False
        try:
            _mouse_press = QEvent.Type.MouseButtonPress
            _mouse_move = QEvent.Type.MouseMove
            _mouse_release = QEvent.Type.MouseButtonRelease
        except AttributeError:
            _mouse_press = QEvent.MouseButtonPress
            _mouse_move = QEvent.MouseMove
            _mouse_release = QEvent.MouseButtonRelease

        if event.type() == _mouse_move and self._tag_library_drag_start_button is not None:
            viewport = (
                getattr(self, "tags_scroll_area", None)
                and self.tags_scroll_area.viewport()
            )
            if viewport and hasattr(event, "globalPos"):
                vp_pos = viewport.mapFromGlobal(event.globalPos())
                if (
                    not self._tag_library_is_selecting
                    and self._tag_library_selection_start is not None
                    and (vp_pos - self._tag_library_selection_start).manhattanLength()
                    >= 10
                ):
                    btn = self._tag_library_drag_start_button
                    tag_text = self._tag_library_drag_start_tag or ""
                    self._tag_library_drag_start_button = None
                    self._tag_library_drag_start_tag = None
                    self._tag_library_selection_start = None
                    if tag_text and btn:
                        self._start_tag_button_drag(
                            btn,
                            tag_text,
                            reparent=self._tag_chip_allows_reparent(btn),
                        )
                        return True

        if event.type() == _mouse_move and self._tag_library_is_selecting:
            viewport = (
                getattr(self, "tags_scroll_area", None)
                and self.tags_scroll_area.viewport()
            )
            if viewport and hasattr(event, "globalPos"):
                vp_pos = viewport.mapFromGlobal(event.globalPos())
                # If drag started on a user tag and moved past threshold, start tag drag (reparent / apply to images)
                if (
                    self._tag_library_drag_start_button is not None
                    and self._tag_library_selection_start is not None
                    and (vp_pos - self._tag_library_selection_start).manhattanLength()
                    >= 10
                ):
                    self._tag_library_rubber_band.hide()
                    self._tag_library_is_selecting = False
                    self._tag_library_selection_start = None
                    btn = self._tag_library_drag_start_button
                    tag_text = self._tag_library_drag_start_tag or ""
                    self._tag_library_drag_start_button = None
                    self._tag_library_drag_start_tag = None
                    if tag_text and btn:
                        self._start_tag_button_drag(
                            btn,
                            tag_text,
                            reparent=self._tag_chip_allows_reparent(btn),
                        )
                    return True
                if self._tag_library_selection_start is not None:
                    self._tag_library_rubber_band.setGeometry(
                        QRect(self._tag_library_selection_start, vp_pos).normalized()
                    )
            return False

        if (
            event.type() == _mouse_release
            and event.button() == Qt.LeftButton
            and self._tag_library_is_selecting
        ):
            viewport = (
                getattr(self, "tags_scroll_area", None)
                and self.tags_scroll_area.viewport()
            )
            if viewport and hasattr(event, "globalPos"):
                vp_pos = viewport.mapFromGlobal(event.globalPos())
                self._tag_library_rubber_band.hide()
                self._tag_library_finish_selection(vp_pos, event.modifiers())
            else:
                self._tag_library_is_selecting = False
                self._tag_library_selection_start = None
            self._tag_library_drag_start_tag = None
            self._tag_library_drag_start_button = None
            return True

        if (
            event.type() == _mouse_press
            and event.button() == Qt.LeftButton
            and self._is_in_tag_library(obj)
        ):
            viewport = self.tags_scroll_area.viewport()
            vp_pos = self._get_tag_library_viewport_pos(obj, event.pos())
            if vp_pos is None:
                return False
            modifiers = event.modifiers()
            has_ctrl = bool(modifiers & Qt.ControlModifier)
            has_shift = bool(modifiers & Qt.ShiftModifier)
            has_modifier = has_ctrl or has_shift

            is_subtag_btn = (
                isinstance(obj, WrappingDraggableTagButton)
                and not bool(obj.property("tagGridCategory"))
            )
            is_category_chip = (
                isinstance(obj, WrappingDraggableTagButton)
                and bool(obj.property("tagGridCategory"))
                and obj.property("tagGridRole") == "category"
            )
            # Tag chips from gui.tag_library.chip — also detect via tagGridRole
            # in case isinstance fails across module reload boundaries.
            tag_grid_role = obj.property("tagGridRole") if hasattr(obj, "property") else None
            is_tag_chip = tag_grid_role in ("tag", "category")
            # "Empty area" = anything in the tag library that isn't a tag chip or scrollbar.
            from qtpy.QtWidgets import QScrollBar as _QScrollBar
            is_interactive_btn = isinstance(obj, DraggableTagButton) or is_tag_chip
            is_scrollbar = isinstance(obj, _QScrollBar)
            is_empty_area = (
                self._is_in_tag_library(obj)
                and not is_interactive_btn
                and not is_scrollbar
            )

            # --- Ctrl / Shift + click on any subtag chip ---
            if has_modifier and is_subtag_btn:
                tag = obj.property("baseLabel") or (obj.text() if hasattr(obj, "text") else "")
                if tag:
                    if has_shift:
                        self._tag_library_shift_click(tag)
                    else:
                        self._tag_library_ctrl_click(tag)
                return True  # consume: don't fire filter toggle

            # --- Simple click without modifier: clear selection unless clicking a selected tag ---
            if not has_modifier and self._tag_library_selection:
                clicked_tag = ""
                if is_subtag_btn:
                    clicked_tag = (
                        obj.property("baseLabel")
                        or (obj.text() if hasattr(obj, "text") else "")
                    )
                if not clicked_tag or clicked_tag not in self._tag_library_selection:
                    self._tag_library_selection.clear()
                    self._last_selected_tag = None
                    self._sync_tag_grid_state()
                # Do NOT consume the event so buttons still fire their click

            # --- Track chip press for drag (user subtag = reparent, else apply to images) ---
            if (is_subtag_btn or is_category_chip) and not has_modifier:
                self._tag_library_drag_start_button = obj
                self._tag_library_drag_start_tag = self._tag_chip_drag_label(obj)
                self._tag_library_selection_start = vp_pos
                drag_tag = self._tag_library_drag_start_tag
                selection = self._tag_library_selection_union()
                if drag_tag in selection and len(selection) > 1:
                    for tag_name in selection:
                        chip_btn = self._get_tag_button_for(tag_name)
                        if chip_btn is not None:
                            prepare_chip_drag_pixmap(chip_btn)
                else:
                    prepare_chip_drag_pixmap(obj)
                return False

            # --- Rubber-band drag from any empty/non-interactive area ---
            if is_empty_area:
                self._tag_library_selection_start = vp_pos
                self._tag_library_is_selecting = True
                self._tag_library_drag_start_tag = None
                self._tag_library_drag_start_button = None
                self._tag_library_rubber_band.setGeometry(QRect(vp_pos, QSize()))
                self._tag_library_rubber_band.show()
                self._tag_library_rubber_band.raise_()
                return True

            # --- Modifier + click on user-tag: start rubber-band (legacy drag-select) ---
            if has_modifier and isinstance(obj, DraggableTagButton) and obj.property("userTag"):
                self._tag_library_selection_start = vp_pos
                self._tag_library_is_selecting = True
                self._tag_library_drag_start_tag = obj.property("baseLabel") or obj.text()
                self._tag_library_drag_start_button = obj
                self._tag_library_rubber_band.setGeometry(QRect(vp_pos, QSize()))
                self._tag_library_rubber_band.show()
                self._tag_library_rubber_band.raise_()
                return True

        return False

    def _on_tag_context_menu_requested(self, tag_text: str) -> None:
        """Show context menu for tag button; only user tags get Rename, Change icon, Parent to tag..."""
        user_tags = self._get_user_tags()
        if tag_text not in user_tags:
            return
        overlay = getattr(self, "_tag_panel_overlay", None)
        if overlay is not None:
            overlay.lock_dismiss(True)
        try:
            menu = QMenu(self)
            rename_action = menu.addAction("Rename...")
            change_icon_action = menu.addAction("Change icon...")
            parent_to_tag_action = menu.addAction("Parent to tag...")
            delete_action = menu.addAction("Delete...")
            action = menu.exec_(QCursor.pos())
            if action == delete_action:
                tags_to_delete = (
                    set(self._tag_library_selection)
                    if tag_text in self._tag_library_selection
                    else {tag_text}
                )
                tags_to_delete = {t for t in tags_to_delete if t in user_tags}
                if tags_to_delete:
                    self._delete_user_tags(tags_to_delete)
                return
            if action == parent_to_tag_action:
                tags_to_parent = (
                    set(self._tag_library_selection)
                    if tag_text in self._tag_library_selection
                    else {tag_text}
                )
                tags_to_parent = {t for t in tags_to_parent if t in user_tags}
                if tags_to_parent:
                    self._enter_parent_select_mode(tags_to_parent)
                return
            if action == change_icon_action:
                cfg = self._user_tags_config
                current = cfg.get("icons", {}).get(tag_text)
                dialog = IconPickerDialog(
                    self,
                    current_icon=current,
                    on_icon_changed=lambda filename: self._on_icon_preview(
                        tag_text, filename
                    ),
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
                if (
                    ok
                    and new_name
                    and new_name.strip()
                    and new_name.strip() != tag_text
                ):
                    new_name = new_name.strip()
                    if self._tag_name_already_used(new_name, exclude=tag_text):
                        QMessageBox.warning(
                            self,
                            "Rename tag",
                            "A tag with this name already exists. Tag names must be unique (case-insensitive).",
                        )
                        return
                    n = self.image_manager.db.rename_tag(tag_text, new_name)
                    cfg = self._user_tags_config
                    placements = cfg.get("placements", {})
                    icons = cfg.get("icons", {})
                    user_tags_config.rename_in_config(
                        placements, icons, tag_text, new_name
                    )
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
        finally:
            if overlay is not None:
                overlay.lock_dismiss(False)

    def _delete_user_tags(self, tags: Set[str]) -> None:
        """
        Remove user-defined tags from images and from the tag library config.

        Args:
            tags: Tag names to delete (non-default user tags only).
        """
        user_tags = self._get_user_tags()
        tags_to_delete = {t for t in tags if t in user_tags}
        if not tags_to_delete:
            return
        label = ", ".join(sorted(tags_to_delete))
        reply = QMessageBox.question(
            self,
            "Delete tags",
            f"Delete tags: {label}?",
            QMessageBox.Ok | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if reply != QMessageBox.Ok:
            return

        self._set_busy_cursor(True)
        progress_bar = self._create_status_progress_bar()
        progress_bar.setFormat(f"Deleting tags: {label}...")
        self.statusBar().showMessage(f"Deleting tags: {label}...")

        worker = TagLibraryDeleteWorker(
            self.image_manager, sorted(tags_to_delete)
        )
        worker.signals.progress.connect(
            lambda cur, tot: self._handle_tag_delete_progress(label, cur, tot),
            Qt.QueuedConnection,
        )
        worker.signals.finished.connect(
            lambda count: self._handle_tag_delete_finished(
                tags_to_delete, count
            ),
            Qt.QueuedConnection,
        )
        worker.signals.error.connect(
            self._handle_tag_delete_error, Qt.QueuedConnection
        )
        self.current_worker = worker
        self.thread_pool.start(worker)

    def _finalize_user_tags_deleted(self, tags_to_delete: Set[str]) -> None:
        """
        Update tag library config and UI after tags were removed from images.

        Args:
            tags_to_delete: Tag names that were deleted.
        """
        cfg = self._user_tags_config
        placements = dict(cfg.get("placements", {}))
        icons = dict(cfg.get("icons", {}))
        registered = [
            t for t in cfg.get("registered_only", []) if t not in tags_to_delete
        ]
        for tag in tags_to_delete:
            placements.pop(tag, None)
            icons.pop(tag, None)
        for tag, placement in list(placements.items()):
            if (
                isinstance(placement, dict)
                and placement.get("parent_tag") in tags_to_delete
            ):
                placements.pop(tag, None)
        user_tags_config.save_config(
            placements,
            icons,
            registered,
            cfg.get("custom_shelves"),
        )
        self._user_tags_config = user_tags_config.load_config()
        self._tag_library_selection -= tags_to_delete
        for tag in tags_to_delete:
            self.and_zone.remove_tag(tag)
            self.or_zone.remove_tag(tag)
            for category, subtags in list(self._active_subtags.items()):
                subtags.discard(tag)
        self._load_tags_into_grid()
        self._update_tag_search_completer()
        self._apply_category_filters()
        self._sync_tag_grid_state()

    def _handle_tag_delete_progress(
        self, label: str, current: int, total: int
    ) -> None:
        """Update status while deleting tags from the library."""
        if total <= 0:
            return
        progress = int(current * 100 / total)
        if self.status_progress_bar is not None:
            self.status_progress_bar.setValue(progress)
            self.status_progress_bar.setFormat(
                f"Deleting tags ({label}): {current}/{total} ({progress}%)"
            )
        if self.dev_mode:
            self.update_dev_progress_bar(progress)
            self.update_dev_progress_label(
                f"Deleting tags: {current}/{total} images scanned"
            )

    def _handle_tag_delete_finished(
        self, tags_to_delete: Set[str], images_updated: int
    ) -> None:
        """Complete tag deletion: config, grid refresh, progress cleanup."""
        try:
            self._finalize_user_tags_deleted(tags_to_delete)
            if self.status_progress_bar is not None:
                self.status_progress_bar.setValue(100)
                self.status_progress_bar.setFormat("Deleting tags: completed")
                self.status_progress_bar.repaint()
            self._cleanup_progress_bars()
            self.statusBar().showMessage("Ready")
            self._set_busy_cursor(False)
            if images_updated:
                QMessageBox.information(
                    self,
                    "Delete tags",
                    f"Removed from {images_updated} image(s).",
                )
        except Exception:
            self._cleanup_progress_bars()
            self.statusBar().showMessage("Ready")
            self._set_busy_cursor(False)

    def _handle_tag_delete_error(self, error_msg: str) -> None:
        """Handle failure while deleting tags from images."""
        self._cleanup_progress_bars()
        self._set_busy_cursor(False)
        self.statusBar().showMessage("Ready")
        self.add_log_message(f"Error while deleting tags: {error_msg}", "ERROR")

    def _set_busy_cursor(self, busy: bool) -> None:
        """
        Show or hide the global wait cursor during long operations.

        Args:
            busy: True to show Qt.WaitCursor, False to restore.
        """
        if busy:
            QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        else:
            QApplication.restoreOverrideCursor()

    def _enter_parent_select_mode(self, tags_to_parent: Set[str]) -> None:
        """Enter 'Parent to tag...' mode: gray given tags, show bar to select parent, OK/Cancel."""
        self._parent_select_mode = True
        self._tags_to_parent = set(tags_to_parent)
        self._parent_select_key = None
        self._parent_select_role = None
        self._parent_select_label.setText("Select parent tag: (none)")
        self._parent_ok_btn.setEnabled(False)
        self._parent_select_bar.setVisible(True)
        self._sync_tag_grid_state()

    def _exit_parent_select_mode(self) -> None:
        """Leave 'Parent to tag...' mode and refresh grid. Clears tag library selection."""
        self._parent_select_mode = False
        self._tags_to_parent = set()
        self._parent_select_key = None
        self._parent_select_role = None
        self._parent_select_bar.setVisible(False)
        self._tag_library_selection = set()
        self._sync_tag_grid_state()

    def _on_tag_clicked_in_parent_mode(
        self, tag: str, category_override: Optional[str] = None
    ) -> None:
        """
        When in parent-select mode: clicking a category sets it as selected parent AND expands it
        so sub-tags are visible; clicking a (sub-)tag sets it as parent AND expands it so its
        children are visible. Categories always expand on click (or on drop).
        """
        if tag in self._tags_to_parent:
            return  # Do not allow selecting a tag we're moving as parent
        if tag in self._category_buttons:
            # Set category as selected parent and expand it so its sub-tags are visible
            self._parent_select_key = tag
            self._parent_select_role = "category"
            self._parent_select_label.setText(
                f"Select parent tag: {self._parent_select_key}"
            )
            self._parent_ok_btn.setEnabled(True)
            self._active_categories.add(tag)
            self._active_subtags.setdefault(tag, set())
            self._sync_tag_grid_state()
            self._flush_tag_library_repaint()
            self._schedule_apply_category_filters()
            return
        # Sub-tag clicked: set as parent and expand so its children (if any) are visible
        self._parent_select_key = tag
        self._parent_select_role = "tag"
        self._parent_select_label.setText(
            f"Select parent tag: {self._parent_select_key}"
        )
        self._parent_ok_btn.setEnabled(True)
        category = (
            category_override
            if category_override is not None
            else self._subtag_to_category.get(tag)
        )
        if category:
            self._active_categories.add(category)
            self._active_subtags.setdefault(category, set()).add(tag)
        self._sync_tag_grid_state()
        self._flush_tag_library_repaint()
        self._schedule_apply_category_filters()

    def _on_parent_select_ok(self) -> None:
        """Apply reparenting: move _tags_to_parent under _parent_select_key, then exit mode.
        Does not clear _active_categories / _active_subtags so expanded categories stay expanded.
        """
        if (
            not self._parent_select_key
            or not self._parent_select_role
            or not self._tags_to_parent
        ):
            return
        cfg = self._user_tags_config
        placements = dict(cfg.get("placements", {}))
        for tag in self._tags_to_parent:
            if self._parent_select_role == "category":
                placements[tag] = {"category": self._parent_select_key}
            else:
                placements[tag] = {"parent_tag": self._parent_select_key}
        user_tags_config.save_config(
            placements,
            cfg.get("icons", {}),
            cfg.get("registered_only"),
        )
        self._user_tags_config = user_tags_config.load_config()
        # Reason: do not clear _active_categories / _active_subtags so tag panel stays expanded
        self._load_tags_into_grid()
        self._exit_parent_select_mode()
        self._sync_tag_grid_state()

    def _on_parent_select_cancel(self) -> None:
        """Cancel parent-select mode without applying."""
        self._exit_parent_select_mode()

    def _get_tag_grid_drop_target_at(self, pos: QPoint) -> Optional[QWidget]:
        """Return the category or tag chip at *pos* in panel coordinates, or None."""
        panel = getattr(self, "_tag_library_panel", None)
        if panel is None:
            return None
        content_pos = panel.map_point_to_content(pos)
        return panel.get_drop_target_at(content_pos)

    def _set_tag_grid_drop_highlight(self, widget: Optional[QWidget]) -> None:
        """Set or clear the drop-target highlight (same look as image grid: dragOver property + style polish)."""
        prev = self._tag_grid_drop_highlight_widget
        if prev is not None:
            prev.setProperty("dragOver", False)
            prev.style().unpolish(prev)
            prev.style().polish(prev)
        self._tag_grid_drop_highlight_widget = widget
        if widget is not None:
            widget.setProperty("dragOver", True)
            widget.style().unpolish(widget)
            widget.style().polish(widget)

    def _on_tag_grid_drag_hover(self, target: Optional[QWidget]) -> None:
        """While dragging over the tag grid: 0.8s hover expand + blink animation on target."""
        if target is None:
            self._tag_grid_hover_expand_cancel()
            return
        role = target.property("tagGridRole") if target else None
        key = target.property("tagGridKey") if target else None
        if not role or not key:
            self._tag_grid_hover_expand_cancel()
            return
        current = (role, key)
        if current == self._tag_grid_hover_target:
            return
        self._tag_grid_hover_expand_cancel()
        self._tag_grid_hover_target = current
        # Start blink animation on the hovered target widget
        self._start_hover_blink(target)
        if self._tag_grid_hover_expand_timer is None:
            self._tag_grid_hover_expand_timer = QTimer(self)
            self._tag_grid_hover_expand_timer.setSingleShot(True)
            self._tag_grid_hover_expand_timer.timeout.connect(
                self._tag_grid_hover_expand_fire
            )
        self._tag_grid_hover_expand_timer.start(800)

    def _start_hover_blink(self, widget: QWidget) -> None:
        """
        Start a blink animation on widget to signal an imminent auto-expand.

        Uses a transparent overlay QFrame that pulses on top of the widget so the
        blink does not interfere with the inline QSS already applied to tag buttons.

        Args:
            widget: The category or tag button being hovered.
        """
        self._stop_hover_blink()
        self._hover_blink_widget = widget
        self._hover_blink_state = False

        # Overlay: sits on top of the widget inside its parent
        overlay = QFrame(widget)
        overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        overlay.setGeometry(widget.rect())
        overlay.setStyleSheet(
            "QFrame { border: 3px solid rgba(255,200,60,0); border-radius: 6px;"
            " background: rgba(255,200,60,0); }"
        )
        overlay.show()
        self._hover_blink_overlay: Optional[QFrame] = overlay  # type: ignore[attr-defined]

        self._hover_blink_timer = QTimer(self)
        self._hover_blink_timer.setInterval(160)
        self._hover_blink_timer.timeout.connect(self._on_hover_blink_tick)
        self._hover_blink_timer.start()

    def _on_hover_blink_tick(self) -> None:
        """Pulse the overlay border/glow between bright and dim."""
        w = self._hover_blink_widget
        overlay = getattr(self, "_hover_blink_overlay", None)
        if w is None or overlay is None or not w.isVisible():
            self._stop_hover_blink()
            return
        self._hover_blink_state = not self._hover_blink_state
        if self._hover_blink_state:
            overlay.setStyleSheet(
                "QFrame { border: 3px solid rgba(255,200,60,220); border-radius: 6px;"
                " background: rgba(255,200,60,35); }"
            )
        else:
            overlay.setStyleSheet(
                "QFrame { border: 3px solid rgba(255,200,60,50); border-radius: 6px;"
                " background: rgba(255,200,60,8); }"
            )
        overlay.setGeometry(w.rect())

    def _stop_hover_blink(self) -> None:
        """Stop the blink animation and destroy the overlay."""
        if self._hover_blink_timer is not None:
            self._hover_blink_timer.stop()
            self._hover_blink_timer = None
        overlay = getattr(self, "_hover_blink_overlay", None)
        if overlay is not None:
            overlay.deleteLater()
            self._hover_blink_overlay = None
        self._hover_blink_widget = None
        self._hover_blink_state = False

    def _tag_grid_hover_expand_cancel(self) -> None:
        """Cancel hover-expand timer and clear target (e.g. on DragLeave or when target changes)."""
        if self._tag_grid_hover_expand_timer is not None:
            self._tag_grid_hover_expand_timer.stop()
            self._tag_grid_hover_expand_timer = None
        self._tag_grid_hover_target = None
        self._stop_hover_blink()

    def _tag_grid_hover_expand_fire(self) -> None:
        """Expand the category or tag that was hovered for 0.5s (so user can see where to drop)."""
        if self._tag_grid_hover_target is None:
            return
        role, key = self._tag_grid_hover_target
        self._tag_grid_hover_target = None
        panel = getattr(self, "_tag_library_panel", None)
        if panel is not None:
            panel.apply_expand_for_drop_target(role, key)
            return
        if role == "category":
            if is_tag_shelf(key):
                self._active_subtags.setdefault(key, set())
            else:
                self._active_categories.add(key)
                self._active_subtags.setdefault(key, set())
        else:
            category = self._subtag_to_category.get(key)
            if category:
                if not is_tag_shelf(category):
                    self._active_categories.add(category)
                self._active_subtags.setdefault(category, set()).add(key)
        self._sync_tag_grid_state()

    def _configure_tag_grid_drop_target(
        self, widget: QWidget, role: str, key: str
    ) -> None:
        """Mark a widget as a tag-library drop target (category row or shelf zone)."""
        widget.setProperty("tagGridRole", role)
        widget.setProperty("tagGridKey", key)

    def _build_shelf_header(self, category: str) -> QLabel:
        """
        Build a shelf section title that accepts tag drops (reparent under this shelf).

        Using QLabel instead of QPushButton so mouse events pass through to the
        viewport for rubber-band selection, while Qt's separate drop-event system
        still routes drops correctly.

        Args:
            category: Shelf name including trailing ':'.

        Returns:
            Styled QLabel acting as a section header and drop target.
        """
        header = QLabel(category)
        header.setObjectName("TagGridButton")
        header.setCursor(Qt.ArrowCursor)
        header.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        header.setFixedWidth(self._tag_library_category_row_width())
        header.setStyleSheet(
            f"QLabel#TagGridButton {{ font-weight: bold; font-size: {TAG_LIBRARY_FONT_SHELF_TITLE_PX}px; "
            "padding: 4px 6px; background-color: transparent; "
            "color: #ffffff; }}"
        )
        # QLabel does not consume mouse events, so clicks propagate normally to the
        # viewport and the eventFilter correctly classifies it as an empty area for
        # rubber-band selection. Drops still work via Qt's separate drop routing.
        self._configure_tag_grid_drop_target(header, "category", category)
        return header

    def _on_tag_grid_drop(self, event: "QDropEvent") -> None:
        """Reposition a user tag when dropped on a category or tag in the grid."""
        self._set_tag_grid_drop_highlight(None)
        self._tag_grid_hover_expand_cancel()
        if not event.mimeData().hasFormat(TAG_LIBRARY_MIME):
            return
        raw = event.mimeData().data(TAG_LIBRARY_MIME)
        dropped_tag = bytes(raw).decode("utf-8") if raw else ""
        if dropped_tag not in self._get_user_tags():
            return
        pos = (
            event.position().toPoint()
            if hasattr(event.position(), "toPoint")
            else event.pos()
        )
        child = self._get_tag_grid_drop_target_at(pos)
        if not child or not child.property("tagGridRole"):
            return
        role = child.property("tagGridRole")
        key = child.property("tagGridKey")
        if dropped_tag == key:
            return
        # Only set after we know the drop is valid (so restore runs when drop on empty area)
        self._tag_drop_was_on_grid = True
        if role == "category":
            placement = {"category": key}
        elif role == "tag":
            placement = {"parent_tag": key}
        else:
            return
        # Reparent all dragged tags (multi-selection or single tag).
        tags_to_reparent = self._tags_from_drop_mime(event.mimeData(), dropped_tag)
        tags_to_reparent.discard(key)
        if not tags_to_reparent:
            return
        cfg = self._user_tags_config
        placements = dict(cfg.get("placements", {}))
        for tag in tags_to_reparent:
            placements[tag] = placement
        user_tags_config.save_config(
            placements,
            cfg.get("icons", {}),
            cfg.get("registered_only"),
        )
        # Preserve expand/filter state so source category stays expanded and active
        saved_categories = set(self._active_categories)
        saved_subtags = {k: set(v) for k, v in self._active_subtags.items()}

        # Defer heavy rebuild to next event loop to avoid lag on drop
        def _do_tag_grid_rebuild() -> None:
            self._user_tags_config = user_tags_config.load_config()
            self._active_categories = saved_categories
            self._active_subtags = saved_subtags
            if role == "category":
                if is_tag_shelf(key):
                    self._active_subtags.setdefault(key, set())
                else:
                    self._active_categories.add(key)
                    self._active_subtags.setdefault(key, set())
            else:
                category = self._subtag_to_category.get(key)
                if category:
                    if not is_tag_shelf(category):
                        self._active_categories.add(category)
                    self._active_subtags.setdefault(category, set()).add(key)
            self._load_tags_into_grid(skip_sync=True)
            self._sync_tag_grid_state()

            # Defer repaint to next event loop tick
            def _force_layout_update() -> None:
                panel = getattr(self, "_tag_library_panel", None)
                if panel is not None:
                    panel._apply_all_states()
                    panel._apply_widths()
                if (
                    hasattr(self, "tags_scroll_area")
                    and self.tags_scroll_area.viewport()
                ):
                    self.tags_scroll_area.viewport().update()

            QTimer.singleShot(0, _force_layout_update)

        QTimer.singleShot(0, _do_tag_grid_rebuild)

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
        if self._tag_name_already_used(tag_name):
            QMessageBox.warning(
                self,
                "Add tag",
                "A tag with this name already exists. Tag names must be unique (case-insensitive).",
            )
            return
        cfg = getattr(self, "_user_tags_config", user_tags_config.load_config())
        self._user_tags_config = cfg
        placements = dict(cfg.get("placements", {}))
        icons = dict(cfg.get("icons", {}))
        registered = list(cfg.get("registered_only", []))
        placements[tag_name] = {"category": MISCELLANEOUS_SHELF}
        if icon_file:
            icons[tag_name] = icon_file
        if tag_name not in registered:
            registered.append(tag_name)
        user_tags_config.save_config(placements, icons, registered)
        self._user_tags_config = user_tags_config.load_config()
        self._load_tags_into_grid()
        self._update_tag_search_completer()
        self._sync_tag_grid_state()

    def _shelf_name_already_used(self, shelf_name: str) -> bool:
        """
        Return True if a category or shelf with the same title already exists.

        Args:
            shelf_name: Raw or normalized shelf title.

        Returns:
            True when the name conflicts with an existing category/shelf/tag.
        """
        norm = self._normalize_tag_for_match(normalize_shelf_name(shelf_name).rstrip(":"))
        if not norm:
            return True
        default_tags_path = Path(__file__).parent / "ressources" / "default_tags.json"
        if default_tags_path.exists():
            categories, _ = load_default_tags_taxonomy(default_tags_path)
            for key in categories:
                if self._normalize_tag_for_match(key.rstrip(":")) == norm:
                    return True
        for shelf in self._user_tags_config.get("custom_shelves", []):
            if not isinstance(shelf, dict):
                continue
            existing = normalize_shelf_name(str(shelf.get("name", "")))
            if self._normalize_tag_for_match(existing.rstrip(":")) == norm:
                return True
        return self._tag_name_already_used(shelf_name.rstrip(":"))

    def _on_add_shelf_clicked(self) -> None:
        """Open dialog to add a user-defined tag library shelf section."""
        dialog = AddShelfDialog(self)
        if dialog.exec_() != QDialog.DialogCode.Accepted:
            return
        raw_name = dialog.get_shelf_name()
        if not raw_name:
            return
        shelf_name = normalize_shelf_name(raw_name)
        if self._shelf_name_already_used(shelf_name):
            QMessageBox.warning(
                self,
                "Create shelf",
                "A category or shelf with this name already exists.",
            )
            return
        cfg = getattr(self, "_user_tags_config", user_tags_config.load_config())
        custom_shelves = list(cfg.get("custom_shelves", []))
        custom_shelves.append(
            {
                "name": shelf_name,
                "filter": dialog.get_filter_mode(),
                "tags": [],
            }
        )
        user_tags_config.save_config(
            dict(cfg.get("placements", {})),
            dict(cfg.get("icons", {})),
            list(cfg.get("registered_only", [])),
            custom_shelves=custom_shelves,
        )
        self._user_tags_config = user_tags_config.load_config()
        self._load_tags_into_grid()
        self._sync_tag_grid_state()

    def _update_available_tags(self) -> None:
        """
        Rebuild the tag library from the database and user tag config.

        Call after imports or other bulk tag changes so new tags appear in the
        library and the search completer stays in sync.
        """
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
            t
            for t, pl in placements.items()
            if isinstance(pl, dict) and pl.get("parent_tag") == tag
        ]

    def _get_all_descendants(
        self, tag: str, visited: Optional[Set[str]] = None
    ) -> Set[str]:
        """
        Return tag plus all tags that are direct or indirect children (parent_tag chain).
        Used so filtering by a category shows images that have the category or any subtag.
        """
        if visited is None:
            visited = set()
        if tag in visited:
            return set()
        visited.add(tag)
        result: Set[str] = {tag}
        for child in self._get_children_of_tag(tag):
            result.update(self._get_all_descendants(child, visited))
        return result

    def _expand_tags_with_descendants(self, tags: Set[str]) -> Set[str]:
        """
        Expand a selected tag set with all nested descendants.

        Args:
            tags: Selected tags.

        Returns:
            Set[str]: Original tags + descendant tags.
        """
        expanded: Set[str] = set()
        for tag in tags:
            expanded.update(self._get_all_descendants(tag))
        return expanded

    def _get_category_match_tags(self, category: str) -> Set[str]:
        """
        Category name plus all tags displayed under it (direct or nested).

        Uses the panel's taxonomy when available; falls back to the legacy
        _subcategory_buttons dict for compatibility.
        """
        panel = getattr(self, "_tag_library_panel", None)
        if panel is not None:
            taxonomy = panel.get_taxonomy()
            if taxonomy is not None:
                return taxonomy.get_category_all_tags(category)
        result: Set[str] = {category}
        for tag in self._subcategory_buttons.get(category, {}):
            result.update(self._get_all_descendants(tag))
        return result

    def _get_active_category_filter_data(self) -> List[Tuple[Set[str], List[Set[str]]]]:
        """
        Precompute per active category: (allowed_tags_norm, required_subtag_groups_norm).
        - allowed: tags that count as "in this category" (category + descendants).
        - required groups: one OR group per selected subtag (selected tag + recursive descendants).
          An image must match at least one tag inside each group.
        Returns list of (allowed_norm, required_groups_norm) for each active category.
        """
        result: List[Tuple[Set[str], List[Set[str]]]] = []
        for category in self._active_categories:
            allowed = self._get_category_match_tags(category)
            allowed_norm = {self._normalize_tag_for_match(t) for t in allowed}
            selected_subtags = self._active_subtags.get(category, set())
            required_groups_norm: List[Set[str]] = []
            for selected_tag in selected_subtags:
                descendants = self._get_all_descendants(selected_tag)
                group_norm = {self._normalize_tag_for_match(t) for t in descendants}
                if group_norm:
                    required_groups_norm.append(group_norm)
            result.append((allowed_norm, required_groups_norm))
        return result

    def _on_panel_filter_changed(self, state: "TagFilterState") -> None:
        """
        Receive filter state from TagLibraryPanel and trigger image grid update.

        The panel owns the UI state; MainWindow only keeps copies for the
        filter logic (which still reads self._active_categories/_active_subtags).

        Args:
            state: Immutable snapshot of the current tag filter.
        """
        self._active_categories = set(state.active_categories)
        self._active_subtags = {k: set(v) for k, v in state.active_subtags.items()}
        self._flush_tag_library_repaint()
        self._schedule_apply_category_filters()

    def _on_panel_tag_rename(self, old_name: str, _placeholder: str) -> None:
        """
        Open rename dialog when TagLibraryPanel requests it.

        Args:
            old_name: Current tag name.
            _placeholder: Unused (panel passes empty string as new_name sentinel).
        """
        from qtpy.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(
            self, "Rename tag", "New name:", text=old_name
        )
        if not (ok and new_name and new_name.strip() and new_name.strip() != old_name):
            return
        new_name = new_name.strip()
        if self._tag_name_already_used(new_name, exclude=old_name):
            from qtpy.QtWidgets import QMessageBox
            QMessageBox.warning(
                self, "Rename tag",
                "A tag with this name already exists."
            )
            return
        self.image_manager.db.rename_tag(old_name, new_name)
        cfg = self._user_tags_config
        placements = dict(cfg.get("placements", {}))
        icons = dict(cfg.get("icons", {}))
        if old_name in placements:
            placements[new_name] = placements.pop(old_name)
        if old_name in icons:
            icons[new_name] = icons.pop(old_name)
        for t, pl in list(placements.items()):
            if isinstance(pl, dict) and pl.get("parent_tag") == old_name:
                placements[t] = {"parent_tag": new_name}
        user_tags_config.save_config(placements, icons, cfg.get("registered_only"))
        self._update_available_tags()

    def _on_panel_tag_icon_change(self, tag: str) -> None:
        """
        Open icon picker dialog when TagLibraryPanel requests it.

        Args:
            tag: Tag name whose icon should be changed.
        """
        cfg = self._user_tags_config
        current = cfg.get("icons", {}).get(tag)
        dialog = IconPickerDialog(
            self,
            current_icon=current,
            on_icon_changed=lambda filename: self._tag_library_panel.update_chip_icon(tag),
        )
        result = dialog.exec_()
        if result == QDialog.DialogCode.Accepted:
            icons = dict(cfg.get("icons", {}))
            chosen = dialog.get_icon_filename()
            if chosen:
                icons[tag] = chosen
            else:
                icons.pop(tag, None)
            user_tags_config.save_config(
                cfg.get("placements", {}), icons, cfg.get("registered_only")
            )
            self._user_tags_config = user_tags_config.load_config()
        self._tag_library_panel.update_chip_icon(tag)

    def _sync_tag_grid_state(
        self,
        categories: Optional[Set[str]] = None,
        force_layout_rebuild: Optional[Set[str]] = None,
    ) -> None:
        """
        Delegate to TagLibraryPanel._apply_all_states().

        The old rebuild logic is no longer used.  Legacy callers throughout
        MainWindow continue to call this method; it now just forwards to the
        panel's lightweight state-sync.

        Args:
            categories: Unused (panel refreshes all sections internally).
            force_layout_rebuild: Unused (no rebuild in new architecture).
        """
        panel = getattr(self, "_tag_library_panel", None)
        if panel is not None:
            panel.sync_filter_state_from(
                self._active_categories,
                self._active_subtags,
                self._tag_library_selection,
            )

    def _sync_tag_grid_state_LEGACY(
        self,
        categories: Optional[Set[str]] = None,
        force_layout_rebuild: Optional[Set[str]] = None,
    ) -> None:
        """Legacy implementation kept for reference — no longer called."""
        if getattr(self, "_tag_drag_in_progress", False):
            return

        max_cols = 3
        placements = self._user_tags_config.get("placements", {})
        scope = categories
        force_layout = force_layout_rebuild or set()

        for category, button in self._category_buttons.items():
            if scope is not None and category not in scope:
                continue
            is_active = category in self._active_categories
            self._set_button_active(button, is_active)
            has_category_children = bool(self._subcategory_buttons.get(category))
            base_label = button.property("baseLabel") or category
            button.setText(
                self._with_expand_icon(base_label, has_category_children, is_active)
            )
            self._set_hierarchy_button_style(
                button=button,
                branch_key=category,
                depth=0,
                active=is_active,
                selected_for_drag=False,
            )

        # Layout rebuild before subtag visibility — setVisible on widgets not in the
        # grid would stack them at (0,0).
        def _category_layout_key(cat: str) -> tuple:
            is_active = cat in self._active_categories
            tag_order = self._subcategory_tag_order.get(cat, [])
            category_subtags = self._active_subtags.get(cat, set())

            def _tag_visible(tag: str) -> bool:
                pl = placements.get(tag)
                parent_tag = pl.get("parent_tag") if isinstance(pl, dict) else None
                if parent_tag is not None:
                    return bool(is_active and parent_tag in category_subtags)
                return bool(is_active)

            visible = frozenset(t for t in tag_order if _tag_visible(t))

            def _has_visible_children(parent: str) -> bool:
                for t in tag_order:
                    if not _tag_visible(t):
                        continue
                    pl = placements.get(t)
                    if isinstance(pl, dict) and pl.get("parent_tag") == parent:
                        return True
                return False

            block_parents = frozenset(
                t
                for t in category_subtags
                if t in visible and _has_visible_children(t)
            )
            return (is_active, visible, block_parents)

        def _build_layout_snapshot() -> Dict[str, tuple]:
            snap: Dict[str, tuple] = {}
            for cat in self._subcategory_tag_order:
                if is_tag_shelf(cat):
                    continue
                snap[cat] = _category_layout_key(cat)
            return snap

        new_snapshot = _build_layout_snapshot()
        old_snapshot: Dict[str, tuple] = getattr(self, "_tag_grid_layout_snapshot", {}) or {}
        changed_categories = []
        for cat in self._subcategory_tag_order:
            if is_tag_shelf(cat):
                continue
            if scope is not None and cat not in scope:
                continue
            if cat in force_layout:
                changed_categories.append(cat)
                continue
            new_key = new_snapshot.get(cat)
            old_key = old_snapshot.get(cat)
            if new_key == old_key:
                continue
            was_active = bool(old_key[0]) if old_key else False
            now_active = bool(new_key[0])
            if was_active != now_active:
                changed_categories.append(cat)
            elif now_active:
                old_visible = old_key[1] if old_key else frozenset()
                old_blocks = old_key[2] if old_key else frozenset()
                if new_key[1] != old_visible or new_key[2] != old_blocks:
                    changed_categories.append(cat)
        if new_snapshot != old_snapshot:
            self._tag_grid_layout_snapshot = new_snapshot

        rebuilt_set = set(changed_categories)

        # Rebuild only categories whose layout structure changed.
        for category in changed_categories:
            container = self._subcategory_containers.get(category)
            if not container:
                continue
            layout = container.layout()
            if not layout:
                continue
            container.setUpdatesEnabled(False)
            while layout.count():
                item = layout.takeAt(0)
                if not item:
                    continue
                widget = item.widget()
                if (
                    widget
                    and isinstance(widget, QFrame)
                    and widget.objectName() == "TagHierarchyFrame"
                ):
                    for child_btn in widget.findChildren(DraggableTagButton):
                        child_btn.setParent(container)
                        child_btn.setVisible(False)
                    widget.deleteLater()
                elif widget is not None:
                    widget.setVisible(False)
            tag_order = self._subcategory_tag_order[category]
            category_subtags = self._active_subtags.get(category, set())
            subtag_buttons = self._subcategory_buttons.get(category, {})
            is_active = category in self._active_categories
            for btn in subtag_buttons.values():
                btn.setVisible(False)

            # Helper: should this tag be visible? (same logic as first loop)
            def _tag_visible(tag: str) -> bool:
                pl = placements.get(tag)
                parent_tag = pl.get("parent_tag") if isinstance(pl, dict) else None
                if parent_tag is not None:
                    return bool(is_active and parent_tag in category_subtags)
                return bool(is_active)

            # Build parent -> ordered children map based on display order.
            ordered_visible_tags = [t for t in tag_order if _tag_visible(t)]
            children_map: Dict[str, List[str]] = {}
            for tag in ordered_visible_tags:
                pl = placements.get(tag)
                parent_tag = pl.get("parent_tag") if isinstance(pl, dict) else None
                if parent_tag:
                    children_map.setdefault(parent_tag, []).append(tag)

            root_tags = [
                t
                for t in ordered_visible_tags
                if not (
                    isinstance(placements.get(t), dict)
                    and placements.get(t).get("parent_tag")
                )
            ]

            def _build_descendants_block(
                parent_tag: str, depth: int
            ) -> Optional[QWidget]:
                children = children_map.get(parent_tag, [])
                if not children:
                    return None
                frame = QFrame()
                frame.setObjectName("TagHierarchyFrame")
                frame.setFrameShape(QFrame.StyledPanel)
                frame.setFocusPolicy(Qt.NoFocus)
                frame.setStyleSheet(
                    "QFrame#TagHierarchyFrame { "
                    f"border: {min(depth, 3)}px solid rgba(255,255,255,0.45); "
                    "border-radius: 6px; "
                    "padding: 0; "
                    "background: transparent; "
                    "}"
                )
                frame_layout = QVBoxLayout(frame)
                frame_layout.setContentsMargins(3, 4, 3, 4)
                frame_layout.setSpacing(6)

                def _new_children_grid() -> QGridLayout:
                    grid = QGridLayout()
                    grid.setContentsMargins(0, 0, 0, 0)
                    grid.setHorizontalSpacing(TAG_LIBRARY_TAG_GRID_SPACING_PX)
                    grid.setVerticalSpacing(6)
                    return grid

                children_grid = _new_children_grid()
                idx_child = 0

                def _flush_children_grid() -> None:
                    nonlocal children_grid, idx_child
                    if idx_child == 0:
                        return
                    frame_layout.addLayout(children_grid)
                    children_grid = _new_children_grid()
                    idx_child = 0

                for child in children:
                    child_btn = subtag_buttons.get(child)
                    if child_btn:
                        row_child, col_child = (
                            idx_child // max_cols,
                            idx_child % max_cols,
                        )
                        children_grid.addWidget(
                            child_btn, row_child, col_child, TAG_LIBRARY_TAG_CELL_ALIGN
                        )
                        child_btn.setVisible(True)
                        idx_child += 1
                    if child in category_subtags:
                        nested = _build_descendants_block(child, depth + 1)
                        if nested is not None:
                            # Reason: show nested grid directly under the clicked child, then continue siblings.
                            _flush_children_grid()
                            frame_layout.addWidget(nested)
                _flush_children_grid()
                return frame

            idx = 0
            for tag in root_tags:
                btn = subtag_buttons.get(tag)
                if not btn:
                    continue
                row, col = idx // max_cols, idx % max_cols
                layout.addWidget(btn, row, col, TAG_LIBRARY_TAG_CELL_ALIGN)
                btn.setVisible(True)
                idx += 1

                if tag in category_subtags:
                    descendants_block = _build_descendants_block(tag, 1)
                    if descendants_block is not None:
                        idx = ((idx + max_cols - 1) // max_cols) * max_cols
                        row_block = idx // max_cols
                        layout.addWidget(descendants_block, row_block, 0, 1, max_cols)
                        idx += max_cols

            container.setMinimumHeight(0)
            container.setVisible(True)
            container.setUpdatesEnabled(True)

        if changed_categories:
            # Invalidate only containers that were rebuilt.
            for category in changed_categories:
                container = self._subcategory_containers.get(category)
                if not container:
                    continue
                lay = container.layout()
                if lay:
                    lay.invalidate()
                    lay.activate()
                container.updateGeometry()
            # Legacy geometry update stubs (no tags_grid_layout in new architecture)
            if hasattr(self, "tags_scroll_area") and self.tags_scroll_area.viewport():
                self.tags_scroll_area.viewport().update()
            QTimer.singleShot(0, self._apply_tag_library_cell_widths)

        for category, subtag_buttons in self._subcategory_buttons.items():
            if is_tag_shelf(category):
                continue
            if scope is not None and category not in scope:
                continue
            is_active = category in self._active_categories
            category_subtags = self._active_subtags.get(category, set())
            for tag, tag_button in subtag_buttons.items():
                if category not in rebuilt_set:
                    pl = placements.get(tag)
                    parent_tag = pl.get("parent_tag") if isinstance(pl, dict) else None
                    if parent_tag is not None:
                        tag_button.setVisible(
                            is_active and parent_tag in category_subtags
                        )
                    else:
                        tag_button.setVisible(is_active)
                is_tag_active = tag in category_subtags
                self._set_button_active(tag_button, is_tag_active)
                has_children = bool(self._get_children_of_tag(tag))
                base_label = tag_button.property("baseLabel") or tag
                tag_button.setText(
                    self._with_expand_icon(base_label, has_children, is_tag_active)
                )
                depth = self._get_tag_depth_in_category(tag, category)
                if getattr(self, "_parent_select_mode", False) and tag in getattr(
                    self, "_tags_to_parent", set()
                ):
                    tag_button.setEnabled(False)
                    tag_button.setStyleSheet(
                        "QPushButton { text-align: left; padding: 2px 4px; opacity: 0.6; background-color: #444; color: #888; }"
                    )
                else:
                    tag_button.setEnabled(True)
                    self._set_hierarchy_button_style(
                        button=tag_button,
                        branch_key=category,
                        depth=depth + 1,
                        active=is_tag_active,
                        selected_for_drag=(
                            tag in getattr(self, "_tag_library_selection", set())
                        ),
                    )

        for label_category in self._subcategory_buttons:
            if not is_tag_shelf(label_category):
                continue
            if scope is not None and label_category not in scope:
                continue
            label_subtags = self._active_subtags.get(label_category, set())
            for tag, tag_button in self._subcategory_buttons[label_category].items():
                pl = placements.get(tag)
                parent_tag = pl.get("parent_tag") if isinstance(pl, dict) else None
                if parent_tag is not None:
                    tag_button.setVisible(parent_tag in label_subtags)
                else:
                    tag_button.setVisible(True)
                is_tag_active = tag in label_subtags
                self._set_button_active(tag_button, is_tag_active)
                has_children = bool(self._get_children_of_tag(tag))
                base_label = tag_button.property("baseLabel") or tag
                tag_button.setText(
                    self._with_expand_icon(base_label, has_children, is_tag_active)
                )
                depth = self._get_tag_depth_in_category(tag, label_category)
                if getattr(self, "_parent_select_mode", False) and tag in getattr(
                    self, "_tags_to_parent", set()
                ):
                    tag_button.setEnabled(False)
                    tag_button.setStyleSheet(
                        "QPushButton { text-align: left; padding: 2px 4px; opacity: 0.6; background-color: #444; color: #888; }"
                    )
                else:
                    tag_button.setEnabled(True)
                    self._set_hierarchy_button_style(
                        button=tag_button,
                        branch_key=label_category,
                        depth=depth + 1,
                        active=is_tag_active,
                        selected_for_drag=(
                            tag in getattr(self, "_tag_library_selection", set())
                        ),
                    )

    @staticmethod
    def _normalize_tag_for_match(tag: str) -> str:
        """
        Normalize tag for case- and separator-insensitive comparison.
        e.g. "Wide-Angle", "wideAngle", "wide angle" all become "wideangle".
        """
        if not tag:
            return ""
        return tag.lower().replace(" ", "").replace("-", "").replace("_", "")

    def _filter_images_by_category(
        self, pre_sorted: Optional[List[ImageMetadata]] = None
    ) -> List:
        """
        Filter images by category (OR) and sub-tags (narrowing by path).
        Miscellaneous = AND (image must have all selected tags).
        Camera-Angle = OR (image must have at least one selected tag, e.g. Hands or Feet).
        Tag matching is case- and separator-insensitive.

        Args:
            pre_sorted: If set, use this list instead of loading/sorting from the DB
                (e.g. background thread already sorted a snapshot for startup).
        """
        sort_by = self._get_current_sort_order()
        if pre_sorted is not None:
            all_images = pre_sorted
        else:
            all_images = self.image_manager.db.list_images(sort_by)

        label_categories_and = shelf_categories_with_filter(
            self._tag_shelf_filter_modes, "and"
        )
        label_categories_or = shelf_categories_with_filter(
            self._tag_shelf_filter_modes, "or"
        )
        constraining_tags_and: Set[str] = set()
        for label_cat in label_categories_and:
            constraining_tags_and.update(
                self._expand_tags_with_descendants(
                    self._active_subtags.get(label_cat, set())
                )
            )
        constraining_tags_or: Set[str] = set()
        for label_cat in label_categories_or:
            constraining_tags_or.update(
                self._expand_tags_with_descendants(
                    self._active_subtags.get(label_cat, set())
                )
            )
        has_active_filters = (
            bool(self._active_categories)
            or bool(constraining_tags_and)
            or bool(constraining_tags_or)
        )
        if not has_active_filters:
            return all_images

        constraining_and_norm = {
            self._normalize_tag_for_match(t) for t in constraining_tags_and
        }
        constraining_or_norm = {
            self._normalize_tag_for_match(t) for t in constraining_tags_or
        }
        category_filter_data = (
            self._get_active_category_filter_data() if self._active_categories else []
        )

        if self._active_categories:
            category_matched = []
            for m in all_images:
                image_tags_norm = {self._normalize_tag_for_match(t) for t in m.tags}
                for allowed_norm, required_groups_norm in category_filter_data:
                    if not (image_tags_norm & allowed_norm):
                        continue
                    group_match = all(
                        bool(image_tags_norm & group) for group in required_groups_norm
                    )
                    if group_match:
                        category_matched.append(m)
                        break
        else:
            category_matched = list(all_images)

        # Apply AND label (Miscellaneous): image must have all selected tags
        if constraining_and_norm:
            category_matched = [
                m
                for m in category_matched
                if constraining_and_norm.issubset(
                    {self._normalize_tag_for_match(t) for t in m.tags}
                )
            ]
        # Apply OR label (Camera-Angle): image must have at least one selected tag
        if constraining_or_norm:
            category_matched = [
                m
                for m in category_matched
                if constraining_or_norm
                & {self._normalize_tag_for_match(t) for t in m.tags}
            ]
        return category_matched

    def _set_button_active(self, button: QPushButton, active: bool) -> None:
        """
        Apply active styling to a tag button via property so QSS applies highlight.
        Only triggers unpolish/polish when the property value actually changes.
        """
        new_val = "true" if active else "false"
        if button.property("tagActive") == new_val:
            return
        button.setProperty("tagActive", new_val)
        button.style().unpolish(button)
        button.style().polish(button)
        button.update()

    # Tree-based tag handling removed in favor of button grid.

    def _setup_dev_tools(self):
        """Set up development tools dock widget."""
        # Create dock widget for dev tools
        self.dev_dock = QDockWidget("Development Log", self)
        self.dev_dock.setAllowedAreas(Qt.BottomDockWidgetArea)
        self.dev_dock.setFeatures(
            QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetFloatable
        )

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
        if hasattr(self, "current_progress_bar"):
            self.current_progress_bar.setValue(progress)

    @Slot(str)
    def update_dev_progress_label(self, text: str):
        """Update dev progress label from any thread."""
        if self.dev_mode and hasattr(self, "dev_progress_label"):
            self.dev_progress_label.setText(text)

    @Slot(int)
    def update_dev_progress_bar(self, progress: int):
        """Update dev progress bar from any thread."""
        if self.dev_mode and hasattr(self, "dev_progress_bar"):
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
        if not hasattr(self, "dev_log"):
            return

        # Format message with timestamp
        from datetime import datetime

        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {level}: {message}"

        # Add color based on level
        color = {"INFO": "#d4d4d4", "WARNING": "#dcdcaa", "ERROR": "#f14c4c"}.get(
            level, "#d4d4d4"
        )

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
                if (
                    path.is_dir()
                    or path.suffix.lower() in ImageManager.SUPPORTED_FORMATS
                ):
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
            if self.dev_mode and hasattr(self, "dev_progress_bar"):
                self.dev_progress_bar.setVisible(False)
                self.dev_progress_bar.setValue(0)
                self.dev_progress_label.setText("No import in progress")
        except Exception as e:
            print(f"Error during cleanup: {e}")

    def _count_images_to_import(
        self, paths: List[Path]
    ) -> Tuple[List[Path], Optional[Path]]:
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
                self, "No Images Found", "No valid images found to import."
            )
            return

        # Detect root directories for the subfolder-as-tags option
        import_root_dirs = [p for p in paths if p.is_dir()]

        # Show import dialog
        from gui.import_dialog import ImportDialog

        dialog = ImportDialog(
            self,
            image_manager=self.image_manager,
            image_paths=image_paths,
            first_image_path=first_image_path,
            import_root_dirs=import_root_dirs if import_root_dirs else None,
        )

        if dialog.exec_() != QDialog.Accepted:
            return

        # Get selected tags
        selected_tags = dialog.get_selected_tags()
        use_subfolder_tags = dialog.get_use_subfolder_tags()
        subfolder_split_separator = dialog.get_subfolder_split_separator()

        # Refresh tag library so any new tags added in the import dialog appear
        self._user_tags_config = user_tags_config.load_config()
        self._load_tags_into_grid()
        self._update_tag_search_completer()
        self._sync_tag_grid_state()

        # Create progress bar in status bar
        progress_bar = self._create_status_progress_bar()

        # Create and configure worker with tags
        worker = ImageImportWorker(
            self.image_manager,
            image_paths,
            selected_tags,
            subfolder_tag_roots=import_root_dirs if use_subfolder_tags else None,
            subfolder_split_separator=subfolder_split_separator,
        )

        # Connect signals with queued connections to ensure thread safety
        worker.signals.progress.connect(
            lambda current, total: self._handle_progress_update(current, total),
            Qt.QueuedConnection,
        )

        worker.signals.log.connect(self.add_log_message, Qt.QueuedConnection)

        # Connect finished signal with explicit slot
        worker.signals.finished.connect(
            self._handle_import_finished, Qt.QueuedConnection
        )

        worker.signals.error.connect(self._handle_import_error, Qt.QueuedConnection)
        worker.signals.image_imported.connect(
            self._on_image_imported, Qt.QueuedConnection
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
                self.status_progress_bar.setFormat(f"Applying tag '{tag}': completed")
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
                self.status_progress_bar.setFormat(f"Removing tag '{tag}': completed")
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
            self.status_progress_bar.setFormat(
                f"Importing: {current}/{total} ({progress}%)"
            )

        # Update dev mode progress
        if self.dev_mode:
            self.update_dev_progress_bar(progress)
            self.update_dev_progress_label(
                f"Importing: {current}/{total} images processed"
            )

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
            if successful > 0:
                # New tags (manual, subfolder, etc.) are on DB rows — rebuild tag library + completer
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
            self, "Import Images", "", f"Images ({formats})"
        )

        if paths:
            self._import_images([Path(p) for p in paths])

    def _on_import_folder(self):
        """Handle folder import action."""
        folder = QFileDialog.getExistingDirectory(self, "Import Folder", "")

        if folder:
            self._import_images([Path(folder)])

    def _setup_menu(self) -> None:
        """
        Build popup menus (no classic menu bar): actions are opened from tool buttons
        next to the logo in the top chrome bar.
        """
        self.menuBar().hide()

        # File menu
        self._file_menu = QMenu(self)
        self._file_menu.setMinimumWidth(220)

        import_action = QAction("Import Images", self)
        import_action.setShortcut("Ctrl+I")
        import_action.triggered.connect(self._on_import_images)
        self._file_menu.addAction(import_action)

        import_folder_action = QAction("Import Folder", self)
        import_folder_action.setShortcut("Ctrl+F")
        import_folder_action.triggered.connect(self._on_import_folder)
        self._file_menu.addAction(import_folder_action)

        self._file_menu.addSeparator()

        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self._show_settings)
        self._file_menu.addAction(settings_action)

        self._file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.close)
        self._file_menu.addAction(exit_action)

        # View menu
        self._view_menu = QMenu(self)

        theme_menu = QMenu("&Theme", self)
        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)
        current_theme = settings.get("ui.theme", "dark")
        for label, key in THEME_OPTIONS:
            action = QAction(label, self)
            action.setCheckable(True)
            action.triggered.connect(
                lambda _=False, theme_key=key: self._set_theme(theme_key)
            )
            if key == current_theme:
                action.setChecked(True)
            theme_group.addAction(action)
            theme_menu.addAction(action)
        self._view_menu.addMenu(theme_menu)

        # Tools menu
        self._tools_menu = QMenu(self)

        dev_mode_action = QAction("Enable &Developer Mode", self)
        dev_mode_action.setCheckable(True)
        dev_mode_action.setChecked(self.dev_mode)
        dev_mode_action.triggered.connect(self._toggle_dev_mode)
        self._tools_menu.addAction(dev_mode_action)

        self.purge_action = QAction("&Purge Image Library...", self)
        self.purge_action.triggered.connect(self._purge_library)
        self.purge_action.setVisible(self.dev_mode)
        self._tools_menu.addAction(self.purge_action)

        reload_tags_action = QAction("&Reload Default Tags", self)
        reload_tags_action.triggered.connect(self.reload_default_tags)
        self._tools_menu.addAction(reload_tags_action)

        # Help menu
        self._help_menu = QMenu(self)

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        self._help_menu.addAction(about_action)

    def _setup_statusbar(self):
        """Set up the status bar."""
        status_bar = self.statusBar()
        status_bar.setMinimumHeight(24)  # Ensure status bar is tall enough
        status_bar.showMessage("Ready")

        # Grid stats on the right (same band as transient status messages / dev log area)
        stats_widget = QWidget()
        stats_layout = QHBoxLayout(stats_widget)
        stats_layout.setContentsMargins(0, 0, 12, 0)
        stats_layout.setSpacing(12)
        self.session_images_count_label = QLabel("Images: 0")
        self.session_images_count_label.setStyleSheet(
            "font-size: 12px; font-weight: bold; color: #ffffff;"
        )
        self.selection_info_label = QLabel("")
        self.selection_info_label.setStyleSheet(
            "font-size: 12px; font-weight: bold; color: #ffffff;"
        )
        stats_layout.addWidget(self.session_images_count_label)
        stats_layout.addWidget(self.selection_info_label)
        status_bar.addPermanentWidget(stats_widget)

    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About SketchBook",
            "SketchBook - A desktop application for timed life drawing sessions.\n\n"
            "Version: 0.1.0",
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
            3000,  # Show for 3 seconds
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
            QMessageBox.No,
        )

        if result == QMessageBox.Yes:
            try:
                # Delete all image files
                from core.user_data import user_data

                image_dir = user_data.get_images_dir()
                if image_dir.exists():
                    for file in image_dir.glob("*"):
                        if (
                            file.is_file()
                            and file.suffix.lower() in ImageManager.SUPPORTED_FORMATS
                        ):
                            file.unlink()

                # Clear metadata database
                self.image_manager.db._images = {}
                self.image_manager.db._save_db()

                QMessageBox.information(
                    self,
                    "Library Purged",
                    "The image library has been successfully purged.",
                )

                self.statusBar().showMessage("Library purged successfully")
                self._apply_category_filters()
            except Exception as e:
                QMessageBox.critical(
                    self, "Purge Error", f"Error purging library: {str(e)}"
                )

    def _on_columns_changed(self, value: int):
        """Handle column slider value changes and persist to user settings."""
        self.columns_count.setText(str(value))
        self.image_grid.set_columns(value)
        settings.set("ui.grid.columns", value)
        settings.save()

    def _on_fit_mode_changed(self, index: int) -> None:
        """
        Handle display-mode combo changes and persist to user settings.

        Args:
            index: Combo-box index matching FitMode enum value.
        """
        mode = FitMode(index)
        self.image_grid.set_fit_mode(mode)
        settings.set("ui.grid.fit_mode", index)
        settings.save()

    def _on_image_clicked(self, image_id: str):
        """Open the image in a large viewer window."""
        if self._image_viewer_window is None:
            from gui.image_viewer_window import ImageViewerWindow

            self._image_viewer_window = ImageViewerWindow(self.image_manager, self)
        if self._image_viewer_window.set_image(image_id):
            self._image_viewer_window.show()
            self._image_viewer_window.raise_()
            self._image_viewer_window.activateWindow()
