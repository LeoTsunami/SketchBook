"""
Image grid component for displaying image thumbnails in a scrollable grid layout.
"""

from pathlib import Path
from typing import Callable, List, Optional, Dict, Set, Tuple
from collections import deque
from qtpy.QtWidgets import (
    QWidget,
    QScrollArea,
    QGridLayout,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QScrollBar,
    QGraphicsView,
    QGraphicsScene,
    QRubberBand,
    QMenu,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QApplication,
    QSizePolicy,
)
from qtpy.QtCore import (
    Qt,
    QSize,
    Signal,
    QTimer,
    QThreadPool,
    QRect,
    QPoint,
    QUrl,
    QElapsedTimer,
)
from qtpy.QtGui import (
    QColor,
    QPixmap,
    QImage,
    QResizeEvent,
    QIcon,
    QDragEnterEvent,
    QDropEvent,
)
from core.image_manager import ImageManager
from core.image_db import ImageMetadata
from gui.image_loader_worker import ImageLoaderWorker
from gui.image_rotate_worker import RotateImageWorker
from gui.tag_apply_worker import TagApplyWorker
from gui.image_thumbnail import ImageThumbnail, TagChip
from gui.thumbnail_fitting import FitMode
from gui.scroll_preview_overlay import ScrollPreviewOverlay
from gui.tag_hover_popover import TagHoverPopover
from qtpy.QtWidgets import QCompleter
import json


class ImageGrid(QScrollArea):
    """Scrollable grid of image thumbnails."""

    image_clicked = Signal(str)  # Emits image ID when clicked (single click)
    image_double_clicked = Signal(
        str
    )  # Emits image ID when double-clicked (open viewer)
    selection_changed = Signal(list)  # Emits list of selected image IDs
    start_session_from_image_requested = Signal(
        str
    )  # Emits selected image ID (must be exactly one)
    grid_needs_refresh = (
        Signal()
    )  # Emits when DB changed (delete, etc.) so main window can reload
    tag_remove_progress = Signal(str, int, int)  # tag, current, total
    tag_remove_finished = Signal(str, list, int)  # tag, image_ids, total
    tag_remove_error = Signal(str)  # error message
    BASE_BATCH_SIZE = (
        10  # Reason: smaller batches = less lag per batch, load more often
    )
    MIN_ROWS_LOADED = 3
    MIN_THUMBNAIL_HEIGHT = 150
    MIN_WINDOW_WIDTH = 800
    ASPECT_RATIO = 1.2
    VIRTUALIZATION_THRESHOLD = 400
    VIRTUALIZED_POOL_EXTRA_ROWS = (
        10  # Rows above/below viewport so more images load ahead
    )
    SCROLL_PREVIEW_LOAD_CHECK_MS = 150
    SCROLL_IDLE_MS = 120
    USER_IDLE_MS = 600
    VIEWPORT_BUFFER_ROWS = 3
    SCROLL_PREVIEW_ROW_OFFSET = 1
    GRID_EXTENDED_ROWS = 5
    IDLE_REFRESH_INTERVAL_MS = 120
    IDLE_MAX_LOADS_PER_TICK = 4
    EXTRACT_VICINITY_COUNT = 30
    EXTRACT_STEP_FACTOR = 2
    EXTRACT_LOAD_SIZE = 240
    EXTRACT_PRELOAD_PER_TICK = 4
    EXTRACT_PRELOAD_PER_TICK_SCROLL = 3
    EXTRACT_PRELOAD_PER_TICK_PREVIEW = 8
    PHASE_GRID_CORE = 1
    PHASE_EXTRACT_VICINITY = 2
    PHASE_GRID_EXTENDED = 3
    PHASE_EXTRACT_BALANCED = 4
    RESIZE_COARSE_INTERVAL_MS = 16
    RESIZE_FINALIZE_MS = 140

    def __init__(self, image_manager: ImageManager, parent=None):
        """
        Initialize the image grid.

        Args:
            image_manager: Instance of ImageManager for accessing images
            parent: Parent widget
        """
        super().__init__(parent)
        self.image_manager = image_manager
        self.selected_images = set()  # Store selected image IDs
        self.selection_start = None  # For drag selection
        self.is_selecting = False
        self.last_selected_image = None  # Store last selected image for range selection
        self.active_image_id = None  # Image whose tags are currently visible

        # Create widget to hold the grid
        self.content = QWidget()
        self.setWidget(self.content)
        self.setWidgetResizable(True)

        # Create grid layout
        self.grid = QGridLayout(self.content)
        self.grid.setSpacing(8)
        self.grid.setContentsMargins(8, 8, 8, 8)

        # Enable mouse tracking for drag selection
        self.setMouseTracking(True)
        self.content.setMouseTracking(True)

        # Create selection rubber band
        self.rubber_band = QRubberBand(QRubberBand.Rectangle, self.viewport())
        self.rubber_band.setStyleSheet("""
            QRubberBand {
                background-color: rgba(0, 120, 215, 0.2);
                border: 2px solid rgb(0, 120, 215);
                border-radius: 2px;
            }
        """)
        # Ensure rubber band is always on top
        self.rubber_band.raise_()

        # Scroll preview overlay: shown while viewport thumbnails are still loading
        self._scroll_preview = ScrollPreviewOverlay(self.viewport())
        self._scroll_preview.raise_()
        # Tag hover popover: floating panel below hovered thumbnail, shows full tag names
        self._tag_popover = TagHoverPopover(self.viewport())
        self._tag_popover.raise_()
        self._scroll_preview_load_check_timer = QTimer(self)
        self._scroll_preview_load_check_timer.setInterval(
            self.SCROLL_PREVIEW_LOAD_CHECK_MS
        )
        self._scroll_preview_load_check_timer.timeout.connect(
            self._on_scroll_preview_load_check
        )
        self._scroll_idle_timer = QTimer(self)
        self._scroll_idle_timer.setSingleShot(True)
        self._scroll_idle_timer.setInterval(self.SCROLL_IDLE_MS)
        self._scroll_idle_timer.timeout.connect(self._on_scroll_idle)
        self._scroll_preview_frame_key: Optional[Tuple[int, int]] = None
        # Extract strip for scroll preview: indices into all_images (1 every N), preloaded in background
        self._extract_indices: List[int] = []
        self._image_id_to_extract_index: Dict[str, int] = {}
        self._extract_pixmaps: Dict[int, QPixmap] = {}  # extract list index -> pixmap
        self._extract_balanced_pending: List[int] = []
        self._extract_vicinity_pending: List[int] = []
        self._extract_vicinity_slot_set: Set[int] = set()
        self._extract_loading: Set[str] = set()
        self._extract_preload_timer = QTimer(self)
        self._extract_preload_timer.setSingleShot(False)
        self._extract_preload_timer.setInterval(40)
        self._extract_preload_timer.timeout.connect(self._process_extract_preload)
        self._user_idle_timer = QTimer(self)
        self._user_idle_timer.setSingleShot(True)
        self._user_idle_timer.setInterval(self.USER_IDLE_MS)
        self._user_idle_timer.timeout.connect(self._on_user_idle)
        self._idle_refresh_timer = QTimer(self)
        self._idle_refresh_timer.setInterval(self.IDLE_REFRESH_INTERVAL_MS)
        self._idle_refresh_timer.timeout.connect(self._on_idle_refresh_tick)
        self._bg_idle_mode = False

        # Import drop: file/folder drops on grid (or forwarded from thumbnail) trigger this callback
        self._import_drop_callback: Optional[Callable[[List[QUrl]], None]] = None
        self._tag_color_resolver: Optional[Callable[[str], QColor]] = None
        self.setAcceptDrops(True)

        # Apply theme-aware styles
        self._apply_theme()
        self.content.setObjectName("content")

        # Initialize state
        self.thumbnails: Dict[str, ImageThumbnail] = {}
        self.current_filter = None
        self.all_images: List[ImageMetadata] = []
        # Reason: O(1) lookup by image_id instead of O(n) linear scans in load/display paths.
        self._image_id_to_index: Dict[str, int] = {}
        self.loaded_count = 0
        self.loading_images: Set[str] = set()  # Track images being loaded
        self._load_failed_images: Set[str] = set()
        self.pixmap_cache: Dict[str, QPixmap] = {}  # Cache loaded pixmaps
        self.columns = 4  # Default number of columns
        self.needs_relayout = False  # Flag to track if relayout is needed
        self.max_thumbnail_height = 300  # Default maximum height
        self.sort_by = "import_date_desc"  # Default sort: most recent first
        self._fit_mode: FitMode = FitMode.FIT_ALL

        # Set up thread pool for main image loading (thumbnails in the grid)
        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(8)

        # Separate pool for scroll-preview extracts; runs in parallel with grid loads.
        self.extract_thread_pool = QThreadPool(self)
        self.extract_thread_pool.setMaxThreadCount(4)

        # Set up unified timer for all layout updates with shorter interval
        self.layout_timer = QTimer(self)
        self.layout_timer.setSingleShot(True)
        self.layout_timer.setInterval(50)  # Reduced to 50ms for more responsiveness
        self.layout_timer.timeout.connect(self._update_layout)

        # Set up separate timer for checking visible thumbnails (debounce scroll)
        self.visibility_timer = QTimer(self)
        self.visibility_timer.setSingleShot(True)
        self.visibility_timer.setInterval(
            40
        )  # Faster reaction on scroll; fires shortly after last scroll event
        self.visibility_timer.timeout.connect(self._check_visible_thumbnails)

        # Tiered pixmap load queues (priority: viewport core > extract head > idle extra > extract tail)
        self._tier0_queue: deque = deque()
        self._tier3_queue: deque = deque()
        self.load_ticker_timer = QTimer(self)
        self.load_ticker_timer.setSingleShot(False)
        self.load_ticker_timer.setInterval(
            15
        )  # Reason: faster ticks = images appear sooner
        self.load_ticker_timer.timeout.connect(self._process_pending_loads)
        self.MAX_LOADS_PER_TICK = 16
        self.PENDING_QUEUE_MAX = 300

        # Connect scroll bar (valueChanged is enough; we debounce with visibility_timer)
        self.verticalScrollBar().valueChanged.connect(self._on_scroll)

        self.row_heights = {}  # Store optimal height for each row

        # Virtualized mode: fixed pool of thumbnails reused for visible range only
        self.thumbnail_pool: List[ImageThumbnail] = []
        self._virtualized_content_height = (
            0  # Content height when virtualized (total_rows * row_height)
        )

        self.is_layout_locked = False  # Add lock to prevent concurrent layout updates
        self.pending_column_change = None  # Store pending column change

        # Interactive window resize: fast (pixelated) fits during drag; smooth fit at end.
        self._resize_interactive = False
        self._coarse_throttle_timer = QElapsedTimer()
        self._coarse_throttle_started = False
        self._coarse_debounce_timer = QTimer(self)
        self._coarse_debounce_timer.setSingleShot(True)
        self._coarse_debounce_timer.timeout.connect(self._on_resize_coarse_debounce)
        self.resize_finalize_timer = QTimer(self)
        self.resize_finalize_timer.setSingleShot(True)
        self.resize_finalize_timer.setInterval(self.RESIZE_FINALIZE_MS)
        self.resize_finalize_timer.timeout.connect(self._on_resize_finalize)

        # Create context menu
        self.context_menu = QMenu(self)
        self.rotate_cw_action = self.context_menu.addAction("Rotate 90° clockwise")
        self.rotate_cw_action.triggered.connect(self._rotate_selected_clockwise)
        self.rotate_ccw_action = self.context_menu.addAction(
            "Rotate 90° counterclockwise"
        )
        self.rotate_ccw_action.triggered.connect(self._rotate_selected_counterclockwise)
        self.context_menu.addSeparator()
        self.start_session_from_image_action = self.context_menu.addAction(
            "Start session from this image"
        )
        self.start_session_from_image_action.triggered.connect(
            self._start_session_from_selected_image
        )
        self.context_menu.addSeparator()
        self.delete_action = self.context_menu.addAction("Delete from Library")
        self.delete_action.triggered.connect(self._delete_selected)

    def _apply_theme(self):
        from core.settings import settings

        theme = settings.get("ui.theme")
        self._update_thumbnail_theme(theme)

    def _update_thumbnail_theme(self, theme: str):
        pass  # Le style des thumbnails est désormais géré uniquement par QSS global

    def _rebuild_image_id_index(self) -> None:
        """Rebuild the O(1) image-id-to-index mapping after any change to ``all_images``."""
        self._image_id_to_index = {m.id: i for i, m in enumerate(self.all_images)}

    def _schedule_idle_resume(self) -> None:
        """Pause low-priority grid preloads until the next idle window."""
        self._bg_idle_mode = False
        self._idle_refresh_timer.stop()
        self._tier3_queue.clear()
        self._user_idle_timer.start()

    def _has_extract_pending(self) -> bool:
        """Return True if any scroll-preview extract slot is still queued."""
        return bool(self._extract_vicinity_pending or self._extract_balanced_pending)

    def _is_scrolling(self) -> bool:
        """Return True while scroll events are still arriving (idle timer running)."""
        return self._scroll_idle_timer.isActive()

    def _pause_background_work_for_scroll(self) -> None:
        """Stop background timers so scroll stays on the main thread."""
        self.load_ticker_timer.stop()
        self._scroll_preview_load_check_timer.stop()
        if not self._extract_vicinity_pending:
            self._extract_preload_timer.stop()

    def _ensure_extract_preload_running(self) -> None:
        """Keep extract loads active (scroll preview depends on them)."""
        if self._is_scrolling():
            if not self._extract_vicinity_pending:
                return
        elif not self._has_extract_pending():
            return
        if not self._extract_preload_timer.isActive():
            self._extract_preload_timer.start()

    def _ensure_load_ticker_running(self) -> None:
        """Start the grid load ticker when a grid phase has work."""
        if self._is_scrolling():
            return
        if self._current_post_scroll_load_phase() in (
            self.PHASE_GRID_CORE,
            self.PHASE_GRID_EXTENDED,
        ):
            self.load_ticker_timer.start()

    def _note_user_activity(self) -> None:
        """Pause idle background preloads while the user interacts with the grid."""
        self._schedule_idle_resume()

    def _on_user_idle(self) -> None:
        """Resume low-priority preloads after a short quiet period."""
        if self._is_scrolling():
            self._user_idle_timer.start()
            return
        self._bg_idle_mode = True
        self._merge_into_load_queue(self._tier3_queue, self._grid_extended_load_order())
        self._rebuild_extract_balanced_pending()
        self._ensure_extract_preload_running()
        self._ensure_load_ticker_running()
        self._idle_refresh_timer.start()

    def _on_idle_refresh_tick(self) -> None:
        """Top up extended-grid and balanced-extract loads during sustained inactivity."""
        if not self._bg_idle_mode or self._is_scrolling():
            return
        self._merge_into_load_queue(self._tier3_queue, self._grid_extended_load_order())
        self._rebuild_extract_balanced_pending()
        self._ensure_load_ticker_running()

    def _viewport_row_range(self, extra_rows: int) -> tuple[int, int]:
        """
        Return the first/last visible row in the viewport, expanded by *extra_rows*.

        Args:
            extra_rows: Rows to include above and below the visible band.

        Returns:
            Tuple ``(first_row, last_row)`` inclusive, clamped to the grid.
        """
        if not self.all_images:
            return (0, 0)
        scroll_y = self.verticalScrollBar().value()
        viewport_h = self.viewport().height()
        spacing = self.grid.spacing()
        margins = self.grid.contentsMargins()
        mt = margins.top()
        _, row_height = self._calculate_optimal_dimensions()
        row_h = row_height + spacing
        if row_h <= 0:
            return (0, 0)
        total_rows = (len(self.all_images) + self.columns - 1) // self.columns
        adj_top = max(0, scroll_y - mt)
        adj_bottom = scroll_y + viewport_h - mt
        core_first = max(0, adj_top // row_h)
        core_last = min(total_rows - 1, adj_bottom // row_h)
        first_row = max(0, core_first - extra_rows)
        last_row = min(total_rows - 1, core_last + extra_rows)
        return first_row, last_row

    def _viewport_image_index_range(self, extra_rows: int) -> tuple[int, int]:
        """
        Return ``[start, end)`` image indices around the viewport.

        Args:
            extra_rows: Rows to include above and below the visible band.

        Returns:
            Half-open index range into ``all_images``.
        """
        first_row, last_row = self._viewport_row_range(extra_rows)
        start_index = first_row * self.columns
        end_index = min(len(self.all_images), (last_row + 1) * self.columns)
        return start_index, end_index

    def _vicinity_load_order(
        self, start: int, end: int, buffer_rows: int
    ) -> List[str]:
        """
        Build a load order that prioritises the viewport, then expands up/down.

        Args:
            start: First image index (inclusive).
            end: End image index (exclusive).
            buffer_rows: Rows to include above and below the visible band.

        Returns:
            Image ids to load, closest to the viewport first.
        """
        if start >= end or not self.all_images:
            return []
        core_first, core_last = self._viewport_row_range(0)
        min_row = start // self.columns
        max_row = min(
            (len(self.all_images) - 1) // self.columns, (end - 1) // self.columns
        )
        ordered_ids: List[str] = []
        seen: Set[str] = set()

        def append_row(row: int) -> None:
            if row < min_row or row > max_row:
                return
            row_start = row * self.columns
            row_end = min(len(self.all_images), row_start + self.columns)
            for idx in range(max(start, row_start), min(end, row_end)):
                image_id = self.all_images[idx].id
                if image_id in seen:
                    continue
                if image_id in self.loading_images or image_id in self.pixmap_cache:
                    continue
                seen.add(image_id)
                ordered_ids.append(image_id)

        for row in range(core_first, core_last + 1):
            append_row(row)
        for offset in range(1, buffer_rows + 1):
            append_row(core_first - offset)
            append_row(core_last + offset)
        return ordered_ids

    def _viewport_core_load_order(self) -> List[str]:
        """Priority 1: viewport plus ``VIEWPORT_BUFFER_ROWS`` above and below."""
        start, end = self._viewport_image_index_range(self.VIEWPORT_BUFFER_ROWS)
        return self._vicinity_load_order(start, end, self.VIEWPORT_BUFFER_ROWS)

    def _grid_extended_load_order(self) -> List[str]:
        """Phase 3: ``GRID_EXTENDED_ROWS`` beyond the viewport core buffer."""
        if not self.all_images:
            return []
        core_first, core_last = self._viewport_row_range(0)
        total_rows = (len(self.all_images) + self.columns - 1) // self.columns
        outer_start, outer_end = self._viewport_image_index_range(
            self.VIEWPORT_BUFFER_ROWS + self.GRID_EXTENDED_ROWS
        )
        min_row = outer_start // self.columns
        max_row = min(total_rows - 1, (outer_end - 1) // self.columns)
        ordered_ids: List[str] = []
        seen: Set[str] = set()

        def append_row(row: int) -> None:
            if row < min_row or row > max_row:
                return
            row_start = row * self.columns
            row_end = min(len(self.all_images), row_start + self.columns)
            for idx in range(row_start, row_end):
                image_id = self.all_images[idx].id
                if image_id in seen:
                    continue
                if image_id in self.loading_images or image_id in self.pixmap_cache:
                    continue
                seen.add(image_id)
                ordered_ids.append(image_id)

        for offset in range(
            self.VIEWPORT_BUFFER_ROWS + 1,
            self.VIEWPORT_BUFFER_ROWS + self.GRID_EXTENDED_ROWS + 1,
        ):
            append_row(core_first - offset)
            append_row(core_last + offset)
        return ordered_ids

    def _idle_extra_load_order(self) -> List[str]:
        """Backward-compatible alias for the extended grid band."""
        return self._grid_extended_load_order()

    def _merge_into_load_queue(
        self, queue: deque, image_ids: List[str], *, front: bool = False
    ) -> None:
        """Append image ids to a load queue, skipping duplicates and in-flight loads."""
        existing = set(queue)
        for image_id in image_ids:
            if image_id in existing:
                continue
            if image_id in self.loading_images or image_id in self.pixmap_cache:
                continue
            if front:
                queue.appendleft(image_id)
            else:
                queue.append(image_id)
            existing.add(image_id)

    def _pop_next_load_id(self, queue: deque) -> Optional[str]:
        """Pop the next loadable image id from a tier queue."""
        while queue:
            image_id = queue.popleft()
            if image_id in self.loading_images or image_id in self.pixmap_cache:
                continue
            return image_id
        return None

    def _refresh_tier0_queue(self) -> None:
        """Rebuild phase-1 viewport loads from the current scroll position."""
        if not self.all_images:
            self._tier0_queue.clear()
            return
        order = self._viewport_core_load_order()
        if self._is_virtualized():
            order = [image_id for image_id in order if image_id in self.thumbnails]
        self._tier0_queue.clear()
        self._merge_into_load_queue(self._tier0_queue, order)

    def _band_image_ids_need_work(self, image_ids: List[str]) -> bool:
        """Return True when any image in the band still lacks a displayed pixmap."""
        for image_id in image_ids:
            if image_id in self._load_failed_images:
                continue
            if image_id not in self.pixmap_cache:
                return True
            thumb = self.thumbnails.get(image_id)
            if thumb is not None and thumb.pixmap_item is None:
                return True
            if not self._is_virtualized() and thumb is None:
                return True
        return False

    def _extract_slots_need_work(self, extract_slots: List[int]) -> bool:
        """Return True when any extract slot in the list is not yet available."""
        for extract_i in extract_slots:
            if extract_i in self._extract_pixmaps:
                continue
            if extract_i >= len(self._extract_indices):
                continue
            meta = self.all_images[self._extract_indices[extract_i]]
            if meta.id in self._extract_loading:
                return True
            return True
        return False

    def _planned_vicinity_extract_indices(self) -> List[int]:
        """Phase-2 extract slots: ``EXTRACT_VICINITY_COUNT`` nearest the scroll target."""
        if not self._extract_indices:
            return []
        target_i = self._scroll_preview_target_extract_index()
        order = self._build_extract_vicinity_order(
            target_i,
            len(self._extract_indices),
            self.EXTRACT_VICINITY_COUNT,
        )
        return order[: self.EXTRACT_VICINITY_COUNT]

    def _current_post_scroll_load_phase(self) -> int:
        """
        Return the active step in the post-scroll load sequence (1..4), or 5 when done.

        Sequence:
            1. Viewport + ``VIEWPORT_BUFFER_ROWS``
            2. ``EXTRACT_VICINITY_COUNT`` nearest preview extracts
            3. ``GRID_EXTENDED_ROWS`` beyond the core buffer
            4. Remaining preview extracts (balanced / dyadic order)
        """
        core_ids = self._viewport_core_load_order()
        if self._is_virtualized():
            core_ids = [i for i in core_ids if i in self.thumbnails]
        if self._tier0_queue or self._band_image_ids_need_work(core_ids):
            return self.PHASE_GRID_CORE
        vicinity_slots = list(self._extract_vicinity_slot_set)
        if self._extract_vicinity_pending or self._extract_slots_need_work(
            vicinity_slots
        ):
            return self.PHASE_EXTRACT_VICINITY
        extended_ids = self._grid_extended_load_order()
        if self._is_virtualized():
            extended_ids = [i for i in extended_ids if i in self.thumbnails]
        if self._tier3_queue or self._band_image_ids_need_work(extended_ids):
            return self.PHASE_GRID_EXTENDED
        if self._extract_balanced_pending or self._extract_slots_need_work(
            self._extract_balanced_pending
        ):
            return self.PHASE_EXTRACT_BALANCED
        return 5

    def _rebuild_extract_balanced_pending(self) -> None:
        """Phase 4: hierarchical strip order excluding phase-2 vicinity slots."""
        if not self._extract_indices:
            self._extract_balanced_pending.clear()
            return
        full_order = self._build_balanced_extract_order(len(self._extract_indices))
        skip = set(self._extract_vicinity_slot_set)
        balanced: List[int] = []
        for extract_i in full_order:
            if extract_i in skip or extract_i in self._extract_pixmaps:
                continue
            if extract_i in self._extract_vicinity_pending:
                continue
            balanced.append(extract_i)
        self._extract_balanced_pending = balanced

    def _rebuild_post_scroll_load_plan(self) -> None:
        """Rebuild all four post-scroll load queues for the current scroll position."""
        if not self.all_images:
            return
        self._refresh_tier0_queue()
        self._tier3_queue.clear()
        extended = self._grid_extended_load_order()
        if self._is_virtualized():
            extended = [i for i in extended if i in self.thumbnails]
        self._merge_into_load_queue(self._tier3_queue, extended)
        self._queue_extracts_near_scroll(max_count=self.EXTRACT_VICINITY_COUNT)
        self._rebuild_extract_balanced_pending()

    def _ensure_thumbnail_widgets_near_viewport(self) -> None:
        """Create thumbnail widgets up to the extended preload horizon (non-virtualized)."""
        if self._is_virtualized() or not self.all_images:
            return
        _, end_index = self._viewport_image_index_range(
            self.VIEWPORT_BUFFER_ROWS + self.GRID_EXTENDED_ROWS
        )
        while self.loaded_count < end_index and self.loaded_count < len(self.all_images):
            self._load_next_batch()

    def _viewport_has_unloaded_images(self) -> bool:
        """
        Return True when any image index in the visible viewport lacks a pixmap.

        Uses index/cache state so detection works before virtualized widgets are
        reassigned on scroll (no debounce wait).

        Returns:
            bool: True if at least one viewport image still needs loading.
        """
        if not self.all_images:
            return False
        start, end = self._viewport_image_index_range(0)
        for idx in range(start, end):
            image_id = self.all_images[idx].id
            if image_id in self._load_failed_images:
                continue
            if image_id not in self.pixmap_cache:
                return True
            thumb = self.thumbnails.get(image_id)
            if thumb is not None and thumb.pixmap_item is None:
                return True
            if not self._is_virtualized() and thumb is None:
                return True
        return False

    def _apply_pixmap_to_thumbnail(self, image_id: str, pixmap) -> None:
        """Paint a loaded pixmap on its thumbnail when not scrolling."""
        if self._is_scrolling():
            return
        thumb = self.thumbnails.get(image_id)
        if thumb and thumb.image_id == image_id:
            thumb.set_image(pixmap)

    def _update_scroll_preview_during_scroll(self) -> None:
        """Keep preview position and image aligned with scroll while the grid loads."""
        if not self.all_images or not self._viewport_has_unloaded_images():
            return
        self._queue_extracts_near_scroll(max_count=self.EXTRACT_VICINITY_COUNT)
        self._ensure_extract_preload_running()
        if not self._scroll_preview.isVisible():
            self._show_scroll_preview(
                self.verticalScrollBar().value(), immediate=True
            )
        else:
            self._update_scroll_preview_position()
            self._update_scroll_preview_image()

    def _sync_scroll_preview_with_viewport_loads(self) -> None:
        """Show preview while the viewport is waiting on pixmaps; hide when ready."""
        if not self.all_images:
            return
        if self._viewport_has_unloaded_images():
            self._queue_extracts_near_scroll()
            self._ensure_extract_preload_running()
            immediate = self._is_scrolling()
            if not self._scroll_preview.isVisible():
                self._show_scroll_preview(
                    self.verticalScrollBar().value(), immediate=immediate
                )
            else:
                self._update_scroll_preview_position()
                self._update_scroll_preview_image()
            if not self._scroll_preview_load_check_timer.isActive():
                self._scroll_preview_load_check_timer.start()
        elif self._scroll_preview.isVisible() and not self._is_scrolling():
            self._on_scroll_preview_load_check()

    def _maybe_extend_non_virtualized_grid(self) -> None:
        """Create more thumbnail widgets when nearing the bottom (non-virtualized)."""
        if self._is_virtualized() or not self.all_images:
            return
        viewport_bottom = (
            self.verticalScrollBar().value() + self.viewport().height()
        )
        content_bottom = self.content.height()
        if (
            content_bottom - viewport_bottom < 1200
            and self.loaded_count < len(self.all_images)
        ):
            self._load_next_batch()

    def _on_scroll_idle(self) -> None:
        """After scroll stops: relayout visible cells, resume loads, sync preview."""
        self._check_visible_thumbnails()
        self._maybe_extend_non_virtualized_grid()

    def _on_scroll_preview_load_check(self) -> None:
        """Poll while preview is open; hide once viewport is ready and scroll has stopped."""
        if not self._scroll_preview.isVisible():
            self._scroll_preview_load_check_timer.stop()
            return
        self._update_scroll_preview_position()
        if self._viewport_has_unloaded_images():
            self._update_scroll_preview_image()
            return
        if self._is_scrolling():
            return
        self._scroll_preview_load_check_timer.stop()
        self._hide_scroll_preview()

    def _on_scroll(self, value):
        """Handle scroll events; defer heavy work until scrolling stops."""
        self._schedule_idle_resume()
        self._pause_background_work_for_scroll()
        self._scroll_idle_timer.start()
        self._update_scroll_preview_during_scroll()
        self._tag_popover.refresh_position()

    def _viewport_top_image_index(self) -> int:
        """
        Index in ``all_images`` for the first cell on the topmost visible row.

        Returns:
            Clamped image index (0 .. len-1).
        """
        if not self.all_images:
            return 0
        first_row, _ = self._viewport_row_range(0)
        return min(first_row * self.columns, len(self.all_images) - 1)

    def _scroll_preview_target_image_index(self) -> int:
        """
        Image index shown in the scroll preview (viewport top + row offset).

        Returns:
            Clamped image index (0 .. len-1).
        """
        if not self.all_images:
            return 0
        first_row, _ = self._viewport_row_range(0)
        total_rows = (len(self.all_images) + self.columns - 1) // self.columns
        target_row = min(first_row + self.SCROLL_PREVIEW_ROW_OFFSET, total_rows - 1)
        return min(target_row * self.columns, len(self.all_images) - 1)

    def _scroll_preview_target_extract_index(self) -> int:
        """
        Extract-strip index closest to the scroll-preview target row.

        Returns:
            Index into ``_extract_indices``.
        """
        if not self._extract_indices:
            return 0
        target_img = self._scroll_preview_target_image_index()
        return min(
            range(len(self._extract_indices)),
            key=lambda i: abs(self._extract_indices[i] - target_img),
        )

    def _nearest_extract_pixmap(self, target_extract_i: int) -> Optional[QPixmap]:
        """
        Return the loaded extract pixmap closest to the target strip index.

        Args:
            target_extract_i: Desired extract index for the current scroll ratio.

        Returns:
            Nearest available pixmap, or None if the strip cache is empty.
        """
        if not self._extract_pixmaps:
            return None
        nearest_i = min(
            self._extract_pixmaps.keys(),
            key=lambda i: abs(i - target_extract_i),
        )
        pixmap = self._extract_pixmaps[nearest_i]
        if pixmap is None or pixmap.isNull():
            return None
        return pixmap

    def _nearest_grid_pixmap_for_scroll(self) -> Optional[QPixmap]:
        """
        Fallback: nearest already-loaded grid thumbnail to the scroll target.

        Returns:
            QPixmap from the main grid cache, or None.
        """
        if not self.pixmap_cache:
            return None
        target_img_idx = self._scroll_preview_target_image_index()
        best_pixmap: Optional[QPixmap] = None
        best_dist: Optional[int] = None
        for image_id, pixmap in self.pixmap_cache.items():
            if pixmap is None or pixmap.isNull():
                continue
            img_idx = self._image_id_to_index.get(image_id)
            if img_idx is None:
                continue
            dist = abs(img_idx - target_img_idx)
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best_pixmap = pixmap
        return best_pixmap

    def _resolve_scroll_preview_frame(self) -> Tuple[Optional[QPixmap], int, int]:
        """
        Pick the best preview pixmap for the current scroll position.

        Returns:
            Tuple of (pixmap, target_extract_index, source_extract_index).
            ``source_extract_index`` is -1 for grid fallback when no extract strip exists.
        """
        target_i = (
            self._scroll_preview_target_extract_index()
            if self._extract_indices
            else 0
        )
        if not self._extract_indices:
            return self._nearest_grid_pixmap_for_scroll(), target_i, -1
        exact = self._extract_pixmaps.get(target_i)
        if exact is not None and not exact.isNull():
            return exact, target_i, target_i
        if self._extract_pixmaps:
            nearest_i = min(
                self._extract_pixmaps.keys(),
                key=lambda i: abs(i - target_i),
            )
            pixmap = self._extract_pixmaps[nearest_i]
            if pixmap is not None and not pixmap.isNull():
                return pixmap, target_i, nearest_i
        return self._nearest_grid_pixmap_for_scroll(), target_i, -1

    def _scroll_preview_pixmap_for_current_scroll(self) -> Optional[QPixmap]:
        """
        Return the best available preview image for the current scroll position.

        Prefers the exact extract slot, then the nearest loaded extract, then the
        nearest visible grid thumbnail.

        Returns:
            QPixmap when any candidate is loaded, else None.
        """
        pixmap, _, _ = self._resolve_scroll_preview_frame()
        return pixmap

    def _prioritize_extract_for_scroll(self) -> None:
        """Queue extract slots around the current scroll position (highest priority)."""
        self._queue_extracts_near_scroll()

    @staticmethod
    def _build_extract_vicinity_order(
        target_i: int, count: int, radius: int
    ) -> List[int]:
        """
        Build extract-slot order: target first, then expanding ±1, ±2, …

        Args:
            target_i: Center extract index for the current scroll position.
            count: Total number of extract slots.
            radius: How many slots to include on each side of the target.

        Returns:
            Ordered extract indices to preload.
        """
        if count <= 0:
            return []
        target_i = max(0, min(count - 1, target_i))
        order: List[int] = [target_i]
        seen: Set[int] = {target_i}
        for delta in range(1, radius + 1):
            for candidate in (target_i + delta, target_i - delta):
                if 0 <= candidate < count and candidate not in seen:
                    seen.add(candidate)
                    order.append(candidate)
        return order

    def _detach_extract_from_pending(self, extract_i: int) -> None:
        """Remove an extract slot from the balanced queue (vicinity owns it)."""
        try:
            self._extract_balanced_pending.remove(extract_i)
        except ValueError:
            pass

    def _queue_extracts_near_scroll(self, max_count: Optional[int] = None) -> None:
        """Fill phase-2 vicinity queue with extracts closest to the viewport."""
        if not self._extract_indices:
            return
        limit = max_count if max_count is not None else self.EXTRACT_VICINITY_COUNT
        target_i = self._scroll_preview_target_extract_index()
        order = self._build_extract_vicinity_order(
            target_i, len(self._extract_indices), limit
        )[:limit]
        self._extract_vicinity_slot_set = set(order)
        vicinity: List[int] = []
        for extract_i in order:
            if extract_i in self._extract_pixmaps:
                continue
            self._detach_extract_from_pending(extract_i)
            vicinity.append(extract_i)
        if not vicinity:
            self._extract_vicinity_pending.clear()
            return
        seen = set(vicinity)
        tail = [i for i in self._extract_vicinity_pending if i not in seen]
        self._extract_vicinity_pending = vicinity + tail

    def _update_scroll_preview_position(self) -> None:
        """Update overlay position to follow the scrollbar thumb."""
        v = self.verticalScrollBar()
        self._scroll_preview.update_geometry_from_scroll(
            self.viewport().width(),
            self.viewport().height(),
            v.value(),
            v.maximum(),
        )

    def _rebuild_extract_indices(self) -> None:
        """Build list of indices for the extract strip (1 every N images) and start preloading."""
        self._extract_preload_timer.stop()
        self._extract_loading.clear()
        self._extract_pixmaps.clear()
        self._extract_indices.clear()
        self._image_id_to_extract_index.clear()
        if not self.all_images:
            self._extract_balanced_pending.clear()
            self._extract_vicinity_pending.clear()
            self._extract_vicinity_slot_set.clear()
            return
        step = max(1, self.EXTRACT_STEP_FACTOR * self.columns)
        idx = 0
        while idx < len(self.all_images):
            self._extract_indices.append(idx)
            self._image_id_to_extract_index[self.all_images[idx].id] = (
                len(self._extract_indices) - 1
            )
            idx += step
        self._extract_balanced_pending = self._build_balanced_extract_order(
            len(self._extract_indices)
        )
        self._extract_vicinity_pending.clear()
        self._extract_vicinity_slot_set.clear()
        if self._has_extract_pending():
            self._extract_preload_timer.start()

    @staticmethod
    def _build_balanced_extract_order(count: int) -> List[int]:
        """Return indices [0..count-1] in a hierarchical Debut/Fin/Milieu, quarts, 1/8, 1/16... order.

        Idée:
        - Charger d'abord les bornes (début/fin) et le milieu,
        - Puis, récursivement, les milieux de chaque segment [début, milieu], [milieu, fin], etc.

        Cela donne une vue globale très vite (haut/bas/milieu), puis on raffine par quarts, huitièmes, etc.
        """
        if count <= 0:
            return []
        if count == 1:
            return [0]

        max_idx = count - 1
        seen: Set[int] = set()
        order: List[int] = []

        def add(idx: int) -> None:
            i = max(0, min(max_idx, idx))
            if i not in seen:
                seen.add(i)
                order.append(i)

        # 1) Début, fin, milieu global
        add(0)
        add(max_idx)
        add(max_idx // 2)

        # 2) Parcours hiérarchique des segments pour ajouter les milieux (quarts, huitièmes, etc.)
        segments: List[Tuple[int, int]] = [(0, max_idx // 2), (max_idx // 2, max_idx)]

        while len(seen) < count and segments:
            next_segments: List[Tuple[int, int]] = []
            for start, end in segments:
                if end - start <= 1:
                    continue
                mid = (start + end) // 2
                add(mid)
                # Sous-segments à raffiner ensuite
                next_segments.append((start, mid))
                next_segments.append((mid, end))
            segments = next_segments

        # Si jamais il reste des trous (cas bornes bizarres), on complète linéairement.
        for i in range(count):
            if i not in seen:
                order.append(i)

        return order

    def _process_extract_preload(self) -> None:
        """Start extract loads following the post-scroll phase sequence."""
        scrolling = self._is_scrolling()
        if scrolling:
            per_tick = self.EXTRACT_PRELOAD_PER_TICK_SCROLL
            pending = self._extract_vicinity_pending
        else:
            phase = self._current_post_scroll_load_phase()
            if phase == self.PHASE_EXTRACT_VICINITY:
                pending = self._extract_vicinity_pending
            elif phase == self.PHASE_EXTRACT_BALANCED:
                pending = self._extract_balanced_pending
            else:
                return
            per_tick = (
                self.EXTRACT_PRELOAD_PER_TICK_PREVIEW
                if self._scroll_preview.isVisible()
                else self.EXTRACT_PRELOAD_PER_TICK
            )
        for _ in range(per_tick):
            if not self.all_images:
                break
            extract_i = self._pop_from_extract_pending(pending)
            if extract_i is None:
                self._extract_preload_timer.stop()
                break
            meta = self.all_images[self._extract_indices[extract_i]]
            self._extract_loading.add(meta.id)
            path = self.image_manager.image_dir / meta.path
            worker = ImageLoaderWorker(
                meta.id,
                path,
                (self.EXTRACT_LOAD_SIZE, self.EXTRACT_LOAD_SIZE),
                self._fit_mode,
                emit_fast=False,
            )
            worker.signals.finished.connect(self._on_image_loaded)
            worker.signals.error.connect(self._on_image_error)
            self.extract_thread_pool.start(worker)
        if not scrolling and self._current_post_scroll_load_phase() in (
            self.PHASE_EXTRACT_VICINITY,
            self.PHASE_EXTRACT_BALANCED,
        ):
            self._extract_preload_timer.start()
        elif not self._has_extract_pending():
            self._extract_preload_timer.stop()

    def _pop_from_extract_pending(self, pending: List[int]) -> Optional[int]:
        """Pop the next valid extract index from a pending list."""
        while pending:
            extract_i = pending.pop(0)
            if extract_i >= len(self._extract_indices):
                continue
            img_idx = self._extract_indices[extract_i]
            if img_idx >= len(self.all_images):
                continue
            meta = self.all_images[img_idx]
            if extract_i in self._extract_pixmaps or meta.id in self._extract_loading:
                continue
            return extract_i
        return None

    def _update_scroll_preview_image(self) -> None:
        """Update overlay image to match the current scroll position."""
        if not self._scroll_preview.isVisible():
            return
        pixmap, target_i, source_i = self._resolve_scroll_preview_frame()
        if pixmap is None:
            return
        frame_key = (target_i, source_i)
        if frame_key == self._scroll_preview_frame_key:
            return
        self._scroll_preview_frame_key = frame_key
        self._scroll_preview.set_image(pixmap, fast=self._is_scrolling())

    def _show_scroll_preview(self, scroll_value: int, *, immediate: bool = False) -> None:
        """Show the scroll preview overlay (nearest loaded image when possible)."""
        self._scroll_preview_frame_key = None
        self._update_scroll_preview_position()
        pixmap, target_i, source_i = self._resolve_scroll_preview_frame()
        if pixmap is not None:
            self._scroll_preview_frame_key = (target_i, source_i)
            self._scroll_preview.set_image(
                pixmap, fast=immediate or self._is_scrolling()
            )
        if immediate:
            self._scroll_preview.show_immediate()
        else:
            self._scroll_preview.show_animated()
        self._scroll_preview.raise_()

    def _hide_scroll_preview(self) -> None:
        """Hide the scroll preview overlay once viewport thumbnails are ready."""
        self._scroll_preview_frame_key = None
        self._scroll_preview.hide_animated()
        self._ensure_load_ticker_running()

    def _is_virtualized(self) -> bool:
        """True when we have too many images and use a fixed pool of widgets."""
        return len(self.all_images) > self.VIRTUALIZATION_THRESHOLD

    def _required_virtualized_pool_size(self) -> int:
        """
        Number of thumbnail widgets needed to cover the viewport plus buffer rows.

        Reason: Row height shrinks when columns increase (narrower cells), so more rows
        fit on screen; the pool must grow or the bottom of the viewport stays empty.

        Returns:
            int: Pool size (never greater than ``len(self.all_images)``).
        """
        if not self.all_images:
            return 0
        thumbnail_width, row_height = self._calculate_optimal_dimensions()
        spacing = self.grid.spacing()
        viewport_h = self.viewport().height()
        rows_visible = max(1, (viewport_h + spacing) // (row_height + spacing))
        pool_rows = rows_visible + 2 * self.VIRTUALIZED_POOL_EXTRA_ROWS
        pool_size = min(pool_rows * self.columns, len(self.all_images))
        pool_size = max(pool_size, min(self.columns * 2, len(self.all_images)))
        return pool_size

    def _ensure_virtualized_pool(self) -> None:
        """Create or grow the thumbnail pool so it always fits the visible index range."""
        pool_size = self._required_virtualized_pool_size()
        if pool_size <= 0:
            return
        thumbnail_width, row_height = self._calculate_optimal_dimensions()
        while len(self.thumbnail_pool) < pool_size:
            meta = self.all_images[0] if self.all_images else None
            if not meta:
                return
            thumb = ImageThumbnail(
                meta.id,
                meta.original_filename,
                self.content,
                self.image_manager,
                remove_tag_callback=self._remove_tag_from_selection,
                get_selected_images_callback=lambda: self.selected_images,
                show_tag_popover_callback=self._show_tag_popover,
                import_drop_callback=self._import_drop_callback,
                tag_drop_flash_callback=self._flash_tag_drop,
            )
            thumb._fit_mode = self._fit_mode
            thumb.apply_outer_geometry(thumbnail_width, row_height)
            thumb.clicked.connect(self.image_clicked.emit)
            self.thumbnail_pool.append(thumb)

    def _update_virtualized_view(self) -> None:
        """In virtualized mode: set content height and assign pool to visible indices.

        Optimised to skip redundant geometry calls and reuse thumbnails that
        already display the correct image (avoids scene-clear + re-set on every scroll).
        """
        if not self._is_virtualized() or not self.all_images:
            return
        # Reason: leftover grid cells from a previous non-virtualized load would paint
        # on top of absolute-positioned pool widgets (non-interactive ghost fragments).
        self._drain_thumbnail_grid_layout()
        self._ensure_virtualized_pool()
        thumbnail_width, row_height = self._calculate_optimal_dimensions()
        layout_key = (thumbnail_width, row_height)
        if getattr(self, "_layout_cell_size", None) != layout_key:
            self._layout_cell_size = layout_key
            self.pixmap_cache.clear()
        spacing = self.grid.spacing()
        margins = self.grid.contentsMargins()
        total_images = len(self.all_images)
        total_rows = (total_images + self.columns - 1) // self.columns
        content_height = (
            total_rows * (row_height + spacing)
            - spacing
            + margins.top()
            + margins.bottom()
        )
        if self._virtualized_content_height != content_height:
            self._virtualized_content_height = content_height
            self.content.setMinimumHeight(content_height)
            self.content.setFixedHeight(content_height)
        scroll_y = self.verticalScrollBar().value()
        viewport_h = self.viewport().height()
        row_h = row_height + spacing
        mt = margins.top()
        adj_top = scroll_y - mt
        adj_bottom = scroll_y + viewport_h - mt
        first_row = max(0, adj_top // row_h - self.VIRTUALIZED_POOL_EXTRA_ROWS)
        last_row = min(
            total_rows - 1,
            adj_bottom // row_h + self.VIRTUALIZED_POOL_EXTRA_ROWS,
        )
        start_index = first_row * self.columns
        end_index = min(total_images, (last_row + 1) * self.columns)

        inner_w, inner_h = ImageThumbnail.content_dimensions(
            thumbnail_width, row_height
        )

        self.thumbnails.clear()
        for i, thumb in enumerate(self.thumbnail_pool):
            idx = start_index + i
            if idx >= end_index:
                if thumb.isVisible():
                    thumb.clear_pixmap()
                    thumb.hide()
                continue

            meta = self.all_images[idx]
            same_image = thumb.image_id == meta.id

            if not same_image:
                thumb.assign_metadata(meta)
                if meta.id in self.pixmap_cache:
                    thumb.set_image(self.pixmap_cache[meta.id])
            elif meta.id in self.pixmap_cache and thumb.pixmap_item is None:
                thumb.set_image(self.pixmap_cache[meta.id])

            thumb.set_selected(meta.id in self.selected_images)

            # Reason: only push geometry when it actually changed to avoid
            # cascading relayout and repaint on every scroll tick.
            if thumb.width() != thumbnail_width or thumb.height() != row_height:
                thumb.apply_outer_geometry(thumbnail_width, row_height)
            elif (
                thumb.graphics_view.width() != inner_w
                or thumb.graphics_view.height() != inner_h
            ):
                thumb.image_container.setFixedSize(inner_w, inner_h)
                thumb.graphics_view.setFixedSize(inner_w, inner_h)

            row, col = idx // self.columns, idx % self.columns
            x = margins.left() + col * (thumbnail_width + spacing)
            y = mt + row * row_h
            thumb.setGeometry(x, y, thumbnail_width, row_height)
            if not thumb.isVisible():
                thumb.show()
            self.thumbnails[meta.id] = thumb

        # Keep pixmap cache bounded (Reason: 20k images = avoid OOM)
        if len(self.pixmap_cache) > 400:
            visible_ids = {self.all_images[i].id for i in range(start_index, end_index)}
            for pid in list(self.pixmap_cache.keys()):
                if pid not in visible_ids and pid not in self.loading_images:
                    self.pixmap_cache.pop(pid, None)
                    if len(self.pixmap_cache) <= 400:
                        break

    def _reset_content_height_for_layout(self) -> None:
        """
        Reset content height constraints so the grid layout controls height.
        Call when switching to non-virtualized mode (e.g. after filtering to few images);
        otherwise content can stay at setFixedHeight(0) from clear() and nothing is visible.
        """
        self.content.setMinimumHeight(0)
        self.content.setMaximumHeight(
            16777215
        )  # QWIDGETSIZE_MAX: allow layout to size content

    def _update_layout(self):
        """Handle all layout updates in one place."""
        if self._is_virtualized():
            self._update_virtualized_view()
            return
        for thumb in self.thumbnail_pool:
            thumb.hide()
        if not self.thumbnails:
            return
        self._reset_content_height_for_layout()
        if not self._resize_interactive:
            self._calculate_row_heights()
        self._do_relayout()
        if not self._resize_interactive:
            self._check_visible_thumbnails()

    def _schedule_window_resize_relayout(self) -> None:
        """
        Throttle grid relayout during live window resize and schedule a final sharp refit.

        Coarse passes use ImageGrid._resize_interactive so thumbnails use fast scaling;
        after RESIZE_FINALIZE_MS without width changes, apply smooth scaling to all visible cells.
        """
        self.resize_finalize_timer.stop()
        self.resize_finalize_timer.start(self.RESIZE_FINALIZE_MS)

        if not self._coarse_throttle_started:
            self._coarse_throttle_timer.start()
            self._coarse_throttle_started = True
            self._run_interactive_layout()
            return

        elapsed = self._coarse_throttle_timer.elapsed()
        if elapsed >= self.RESIZE_COARSE_INTERVAL_MS:
            self._coarse_throttle_timer.restart()
            self._run_interactive_layout()
            self._coarse_debounce_timer.stop()
        elif not self._coarse_debounce_timer.isActive():
            delay = max(1, self.RESIZE_COARSE_INTERVAL_MS - int(elapsed))
            self._coarse_debounce_timer.start(delay)

    def _on_resize_coarse_debounce(self) -> None:
        """Run one throttled coarse layout after the debounce delay."""
        self._coarse_throttle_timer.restart()
        self._run_interactive_layout()

    def _set_fast_resize_flag(self, active: bool) -> None:
        """Set ``_fast_resize_active`` on all live thumbnails (pool + dict)."""
        for thumb in self.thumbnail_pool:
            thumb._fast_resize_active = active
        for thumb in self.thumbnails.values():
            thumb._fast_resize_active = active

    def _run_interactive_layout(self) -> None:
        """Run a full layout pass with fast (coarse) thumbnail scaling."""
        self._resize_interactive = True
        self._set_fast_resize_flag(True)
        try:
            self._update_layout()
        finally:
            self._resize_interactive = False

    def _on_resize_finalize(self) -> None:
        """End of window resize: stop throttling state and apply smooth pixmap fitting."""
        self._coarse_debounce_timer.stop()
        self._coarse_throttle_started = False
        self._set_fast_resize_flag(False)
        self._apply_full_quality_fit_all_thumbnails()

    def _apply_full_quality_fit_all_thumbnails(self) -> None:
        """Restore SmoothTransformation + full-quality fit on every loaded thumbnail."""
        seen: Set[ImageThumbnail] = set()
        for thumb in list(self.thumbnails.values()):
            if thumb in seen:
                continue
            seen.add(thumb)
            thumb.apply_full_quality_fit()
        for thumb in self.thumbnail_pool:
            if thumb.isVisible():
                thumb.apply_full_quality_fit()

    def set_fit_mode(self, mode: FitMode) -> None:
        """
        Change the image display strategy for every thumbnail.

        Args:
            mode: New display mode (FitMode enum value).
        """
        if self._fit_mode == mode:
            return
        self._fit_mode = mode
        for thumb in self.thumbnails.values():
            thumb.set_fit_mode(mode)
        for thumb in self.thumbnail_pool:
            thumb.set_fit_mode(mode)

    def set_columns(self, columns: int):
        """Set the number of columns in the grid."""
        if self.columns == columns:
            return

        self.columns = columns
        self.needs_relayout = True
        self.pixmap_cache.clear()
        self._rebuild_extract_indices()
        self.layout_timer.start()
        if not self._is_virtualized() and self.loaded_count < len(self.all_images):
            self._load_next_batch()

    def set_import_drop_callback(
        self, callback: Optional[Callable[[List[QUrl]], None]]
    ) -> None:
        """Set callback for file/folder drops (on grid or forwarded from thumbnail). Used for import."""
        self._import_drop_callback = callback

    def set_tag_color_resolver(
        self, resolver: Optional[Callable[[str], QColor]]
    ) -> None:
        """
        Set a callback that maps a tag label to its library accent colour.

        Args:
            resolver: Callable returning a QColor for the given tag text.
        """
        self._tag_color_resolver = resolver

    def _tag_drop_flash_targets(
        self, image_ids: List[str]
    ) -> List[ImageThumbnail]:
        """
        Return thumbnails that will receive drop feedback (visible in the viewport).

        Args:
            image_ids: Images tagged by the drop.

        Returns:
            Thumbnails currently shown inside the scroll viewport.
        """
        targets: List[ImageThumbnail] = []
        viewport = self.viewport()
        viewport_rect = viewport.rect()
        for image_id in image_ids:
            thumb = self.thumbnails.get(image_id)
            if thumb is None or not thumb.isVisible():
                continue
            top_left = thumb.mapTo(viewport, QPoint(0, 0))
            if viewport_rect.intersects(QRect(top_left, thumb.size())):
                targets.append(thumb)
        return targets

    def _flash_tag_drop(
        self,
        image_ids: List[str],
        tag: str,
        primary_image_id: Optional[str] = None,
    ) -> None:
        """
        Play a colour flash on every selected thumbnail visible in the viewport.

        Single-image drops use a smooth opacity pulse; multi-image drops use a
        lightweight instant tint to stay responsive.

        Args:
            image_ids: Image IDs that received the tag.
            tag: Tag label (used to resolve colour).
            primary_image_id: Drop target id (reserved; flash uses all viewport hits).
        """
        from gui.tag_drop_overlay import play_tag_drop_flash

        if self._tag_color_resolver is not None:
            color = self._tag_color_resolver(tag)
        else:
            color = QColor(140, 100, 220)

        targets = self._tag_drop_flash_targets(image_ids)
        if not targets:
            return

        animated = len(targets) == 1
        for thumb in targets:
            play_tag_drop_flash(
                thumb.image_container,
                color,
                animated=animated,
            )

    def refresh_visible_tags_for_images(self, image_ids: List[str]) -> None:
        """
        Refresh tag chips only when the active image is among the updated set.

        Args:
            image_ids: Image IDs whose tags may have changed.
        """
        if not self.active_image_id or self.active_image_id not in image_ids:
            return
        thumb = self.thumbnails.get(self.active_image_id)
        if thumb is not None:
            thumb.refresh_tags()

    def _calculate_row_heights(self):
        """Calculate optimal height for each row based on actual image dimensions."""
        if not self.thumbnails:
            return

        # Calculate available width for thumbnails
        spacing = self.grid.spacing()
        margins = self.grid.contentsMargins()
        available_width = self.viewport().width() - margins.left() - margins.right()
        thumbnail_width = (
            available_width - (self.columns - 1) * spacing
        ) // self.columns

        # First, calculate the natural height for each image at the given width
        image_heights = {}
        for image_id in self.thumbnails.keys():
            if image_id in self.pixmap_cache:
                pixmap = self.pixmap_cache[image_id]
                # Calculate height while maintaining aspect ratio
                natural_height = (thumbnail_width * pixmap.height()) / pixmap.width()
                image_heights[image_id] = natural_height

        # Group images by row and find the maximum height for each row
        self.row_heights = {}
        current_row = 0
        for idx, metadata in enumerate(self.all_images):
            if idx >= self.loaded_count:
                break

            row = idx // self.columns
            if row != current_row:
                current_row = row

            if metadata.id in image_heights:
                if row not in self.row_heights:
                    self.row_heights[row] = 0
                self.row_heights[row] = max(
                    self.row_heights[row], image_heights[metadata.id]
                )

        # Ensure minimum height for rows without loaded images
        for row in self.row_heights:
            self.row_heights[row] = max(200, int(self.row_heights[row]))

    def _calculate_optimal_dimensions(self):
        """Calculate optimal thumbnail dimensions based on available space."""
        spacing = self.grid.spacing()
        margins = self.grid.contentsMargins()
        available_width = max(
            self.viewport().width() - margins.left() - margins.right(),
            self.MIN_WINDOW_WIDTH - margins.left() - margins.right(),
        )

        # Calculate thumbnail width based on available space and columns
        thumbnail_width = (
            available_width - (self.columns - 1) * spacing
        ) // self.columns

        # Calculate height using our desired aspect ratio
        optimal_height = int(thumbnail_width * self.ASPECT_RATIO)

        # Ensure minimum height
        thumbnail_height = max(optimal_height, self.MIN_THUMBNAIL_HEIGHT)

        return thumbnail_width, thumbnail_height

    def _do_relayout(self):
        """Perform the actual grid layout (in-place updates; avoids full grid clear on resize)."""
        if not self.thumbnails:
            return

        thumbnail_width, thumbnail_height = self._calculate_optimal_dimensions()
        layout_key = (thumbnail_width, thumbnail_height)
        if getattr(self, "_layout_cell_size", None) != layout_key:
            self._layout_cell_size = layout_key
            self.pixmap_cache.clear()

        for idx, metadata in enumerate(self.all_images):
            if idx >= self.loaded_count:
                break
            if metadata.id not in self.thumbnails:
                continue

            thumbnail = self.thumbnails[metadata.id]
            row = idx // self.columns
            col = idx % self.columns

            cell_item = self.grid.itemAtPosition(row, col)
            cell_w = cell_item.widget() if cell_item is not None else None
            if cell_w is not None and cell_w is not thumbnail:
                self.grid.removeWidget(cell_w)

            cell_item = self.grid.itemAtPosition(row, col)
            cell_w = cell_item.widget() if cell_item is not None else None
            if cell_w is not thumbnail:
                self.grid.addWidget(thumbnail, row, col)

            thumbnail.apply_outer_geometry(thumbnail_width, thumbnail_height)
            thumbnail.show()

    def _drain_thumbnail_grid_layout(self) -> None:
        """
        Remove every widget from ``self.grid`` and schedule deletion.

        Virtualized thumbnails are parented to ``content`` with absolute geometry only;
        they never use this layout. Non-virtualized thumbnails are placed in the grid.
        When switching between modes, ``clear()`` used to skip this step if
        ``thumbnail_pool`` was non-empty, leaving orphan cells that painted as ghost images.

        Returns:
            None
        """
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def clear(self):
        """Remove all thumbnails from the grid."""
        self.layout_timer.stop()
        self.resize_finalize_timer.stop()
        self._coarse_debounce_timer.stop()
        self._coarse_throttle_started = False
        self.visibility_timer.stop()
        self.load_ticker_timer.stop()
        self._scroll_preview_load_check_timer.stop()
        self._scroll_idle_timer.stop()
        self._user_idle_timer.stop()
        self._scroll_preview.hide_immediate()
        self._tag_popover.hide_popover()
        self._extract_preload_timer.stop()
        self._idle_refresh_timer.stop()
        self._bg_idle_mode = False
        self._extract_indices.clear()
        self._image_id_to_extract_index.clear()
        self._extract_pixmaps.clear()
        self._extract_balanced_pending.clear()
        self._extract_vicinity_pending.clear()
        self._extract_vicinity_slot_set.clear()
        self._extract_loading.clear()
        self._tier0_queue.clear()
        self._tier3_queue.clear()
        self.loading_images.clear()
        self._load_failed_images.clear()
        # Reason: always drain the layout so virtual ↔ non-virtual transitions never
        # leave stale QGridLayout cells (visible as non-interactive fragments in gutters).
        self._drain_thumbnail_grid_layout()

        if self.thumbnail_pool:
            self.thumbnails.clear()
            self.pixmap_cache.clear()
            for thumb in self.thumbnail_pool:
                thumb.clear_pixmap()
                thumb.hide()
            self.loaded_count = 0
            self.all_images.clear()
            self._image_id_to_index.clear()
            self.content.setMinimumHeight(0)
            self.content.setFixedHeight(0)
            return

        self.thumbnails.clear()
        self.pixmap_cache.clear()
        self.loaded_count = 0
        self.all_images.clear()
        self._image_id_to_index.clear()

    def load_images(
        self, filter_tags: Optional[List[str]] = None, sort_by: str = "import_date_desc"
    ):
        """
        Load and display images, optionally filtered by tags.

        Args:
            filter_tags: Optional list of tags to filter images by
            sort_by: Sort order (see ImageDatabase.list_images for options)
        """
        # Clear if filter or sort changed
        filter_key = (filter_tags, sort_by)
        if self.current_filter != filter_key:
            self.clear()

        # Store filter and sort
        self.current_filter = filter_key
        self.sort_by = sort_by

        # Use advanced search for consistency (convert list to set for AND logic)
        if filter_tags:
            self.all_images = self.image_manager.db.search_images_advanced(
                and_tags=set(filter_tags), or_tags=None, sort_by=sort_by
            )
        else:
            self.all_images = self.image_manager.db.list_images(sort_by)
        self._rebuild_image_id_index()
        self._rebuild_extract_indices()
        if not self._is_virtualized():
            self._load_next_batch()
        self.layout_timer.start()
        self._user_idle_timer.start()

    def _calculate_batch_size(self) -> int:
        """Calculate the batch size based on current number of columns."""
        # Calculate proportional batch size
        column_factor = self.columns / 4  # Base proportion on 4 columns
        base_rows = max(
            self.MIN_ROWS_LOADED, self.BASE_BATCH_SIZE // 4
        )  # Ensure minimum rows
        batch_size = int(base_rows * self.columns * column_factor)
        return batch_size

    def _load_next_batch(self):
        """Load the next batch of thumbnails."""
        if self.loaded_count >= len(self.all_images):
            return

        # Calculate batch size based on current columns
        batch_size = self._calculate_batch_size()

        # Get optimal dimensions
        thumbnail_width, thumbnail_height = self._calculate_optimal_dimensions()

        # Load next batch
        end_idx = min(self.loaded_count + batch_size, len(self.all_images))
        for idx in range(self.loaded_count, end_idx):
            metadata = self.all_images[idx]

            # Calculate grid position
            row = idx // self.columns
            col = idx % self.columns

            # Create thumbnail with callback to remove tags from selected images
            thumbnail = ImageThumbnail(
                metadata.id,
                metadata.original_filename,
                self.content,
                self.image_manager,
                remove_tag_callback=self._remove_tag_from_selection,
                get_selected_images_callback=lambda: self.selected_images,
                show_tag_popover_callback=self._show_tag_popover,
                import_drop_callback=self._import_drop_callback,
                tag_drop_flash_callback=self._flash_tag_drop,
            )
            thumbnail._fit_mode = self._fit_mode

            thumbnail.apply_outer_geometry(thumbnail_width, thumbnail_height)

            self.grid.addWidget(thumbnail, row, col)
            self.thumbnails[metadata.id] = thumbnail
            thumbnail.clicked.connect(self.image_clicked.emit)

        self.loaded_count = end_idx

        # Trigger layout update
        self.layout_timer.start()

    def prepend_image(self, metadata: ImageMetadata) -> None:
        """
        Add a single image at the top of the grid without full refresh.
        Used when a new image is imported so it appears immediately at the top.
        """
        self.all_images.insert(0, metadata)
        self._rebuild_image_id_index()
        if self._is_virtualized():
            self.layout_timer.start()
            self.visibility_timer.start()
            return
        thumbnail_width, thumbnail_height = self._calculate_optimal_dimensions()
        thumbnail = ImageThumbnail(
            metadata.id,
            metadata.original_filename,
            self.content,
            self.image_manager,
            remove_tag_callback=self._remove_tag_from_selection,
            get_selected_images_callback=lambda: self.selected_images,
            show_tag_popover_callback=self._show_tag_popover,
            import_drop_callback=self._import_drop_callback,
            tag_drop_flash_callback=self._flash_tag_drop,
        )
        thumbnail._fit_mode = self._fit_mode
        thumbnail.apply_outer_geometry(thumbnail_width, thumbnail_height)
        self.thumbnails[metadata.id] = thumbnail
        thumbnail.clicked.connect(self.image_clicked.emit)
        self.loaded_count += 1
        old_widgets: List[QWidget] = []
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                old_widgets.append(item.widget())
        self.grid.addWidget(thumbnail, 0, 0)
        for i, w in enumerate(old_widgets):
            row = (i + 1) // self.columns
            col = (i + 1) % self.columns
            self.grid.addWidget(w, row, col)
        self.layout_timer.start()
        self.visibility_timer.start()

    def _check_visible_thumbnails(self):
        """Compute which thumbnails are visible and enqueue their pixmap loads (or update virtualized view)."""
        if self._is_scrolling():
            return
        if self._is_virtualized():
            self._update_virtualized_view()
        else:
            self._ensure_thumbnail_widgets_near_viewport()
        self._rebuild_post_scroll_load_plan()
        self._ensure_load_ticker_running()
        self._ensure_extract_preload_running()
        self._sync_scroll_preview_with_viewport_loads()

    def _process_pending_loads(self):
        """Process grid loads for the active post-scroll phase (core, then extended)."""
        if self._is_scrolling():
            return
        phase = self._current_post_scroll_load_phase()
        if phase == self.PHASE_GRID_CORE:
            queue = self._tier0_queue
            per_tick = self.MAX_LOADS_PER_TICK
        elif phase == self.PHASE_GRID_EXTENDED:
            queue = self._tier3_queue
            per_tick = self.IDLE_MAX_LOADS_PER_TICK
        else:
            self.load_ticker_timer.stop()
            return
        for _ in range(per_tick):
            image_id = self._pop_next_load_id(queue)
            if image_id is None:
                break
            self._load_thumbnail_image(image_id)
        if self._current_post_scroll_load_phase() in (
            self.PHASE_GRID_CORE,
            self.PHASE_GRID_EXTENDED,
        ):
            self.load_ticker_timer.start()
        else:
            self.load_ticker_timer.stop()

    def _is_thumbnail_visible(self, thumbnail: QWidget) -> bool:
        """Check if a thumbnail is in or near the viewport."""
        if not thumbnail.isVisible():
            return False

        viewport_rect = QRect(
            self.horizontalScrollBar().value(),
            self.verticalScrollBar().value(),
            self.viewport().width(),
            self.viewport().height(),
        )

        # Add margin for preloading
        margin = 500
        viewport_rect.adjust(-margin, -margin, margin, margin)

        return viewport_rect.intersects(self._get_widget_geometry(thumbnail))

    def _get_widget_geometry(self, widget: QWidget) -> QRect:
        """Get the global geometry of a widget relative to the scroll area."""
        return QRect(widget.mapTo(self.content, widget.rect().topLeft()), widget.size())

    def _load_thumbnail_image(self, image_id: str):
        """Load image for a thumbnail asynchronously. When virtualized, may load for cache only (thumbnail not visible)."""
        if self._is_scrolling():
            return
        if image_id in self.loading_images:
            return
        idx = self._image_id_to_index.get(image_id)
        if idx is None or idx >= len(self.all_images):
            return
        metadata = self.all_images[idx]
        if image_id in self.pixmap_cache:
            if image_id in self.thumbnails:
                self.thumbnails[image_id].set_image(self.pixmap_cache[image_id])
            return
        self.loading_images.add(image_id)
        if image_id in self.thumbnails:
            thumbnail = self.thumbnails[image_id]
            fallback_w, fallback_h = ImageThumbnail.content_dimensions(
                thumbnail.width(), thumbnail.height()
            )
            target_width = thumbnail.graphics_view.width() or fallback_w
            target_height = thumbnail.graphics_view.height() or fallback_h
        else:
            thumbnail_width, thumbnail_height = self._calculate_optimal_dimensions()
            target_width, target_height = ImageThumbnail.content_dimensions(
                thumbnail_width, thumbnail_height
            )
        image_path = self.image_manager.image_dir / metadata.path
        worker = ImageLoaderWorker(
            image_id,
            image_path,
            (target_width, target_height),
            self._fit_mode,
        )

        worker.signals.fast_ready.connect(self._on_image_fast_ready)
        worker.signals.finished.connect(self._on_image_loaded)
        worker.signals.error.connect(self._on_image_error)

        self.thread_pool.start(worker)

    def _on_image_fast_ready(self, image_id: str, pixmap):
        """Show fast-scaled pixmap immediately for visual feedback while HQ loads.

        Only applied when the thumbnail has no image yet (avoids downgrading
        a previously cached HQ pixmap).
        """
        if image_id not in self._image_id_to_index:
            return
        if image_id in self.pixmap_cache:
            return
        thumb = self.thumbnails.get(image_id)
        if thumb and thumb.image_id == image_id and thumb.pixmap_item is None:
            self._apply_pixmap_to_thumbnail(image_id, pixmap)
        if not self._is_scrolling():
            self._sync_scroll_preview_with_viewport_loads()

    def _on_image_loaded(self, image_id: str, pixmap):
        """Handle loaded HQ image and update cache + display."""
        self.loading_images.discard(image_id)
        self._extract_loading.discard(image_id)
        if image_id not in self._image_id_to_index:
            return
        if image_id in self._image_id_to_extract_index:
            extract_i = self._image_id_to_extract_index[image_id]
            self._extract_pixmaps[extract_i] = pixmap
            self.pixmap_cache[image_id] = pixmap
            self._apply_pixmap_to_thumbnail(image_id, pixmap)
            self._scroll_preview_frame_key = None
            if self._scroll_preview.isVisible():
                self._update_scroll_preview_image()
            if not self._is_scrolling():
                self._ensure_load_ticker_running()
                self._ensure_extract_preload_running()
                self._sync_scroll_preview_with_viewport_loads()
            return
        self.pixmap_cache[image_id] = pixmap
        self._apply_pixmap_to_thumbnail(image_id, pixmap)
        if not self._is_scrolling():
            self._ensure_load_ticker_running()
            self._ensure_extract_preload_running()
            self._sync_scroll_preview_with_viewport_loads()

    def _on_image_error(self, image_id: str, error_msg: str):
        """Handle image loading error."""
        self.loading_images.discard(image_id)
        self._extract_loading.discard(image_id)
        self._load_failed_images.add(image_id)
        if image_id in self.thumbnails and not self._is_scrolling():
            self.thumbnails[image_id].set_error(error_msg)
        if not self._is_scrolling():
            self._sync_scroll_preview_with_viewport_loads()

    def resizeEvent(self, event):
        """Handle resize events to adjust grid layout."""
        super().resizeEvent(event)
        self._update_scroll_preview_position()
        self._tag_popover.refresh_position()
        if event.size().width() != event.oldSize().width():
            self.needs_relayout = True
            self._schedule_window_resize_relayout()

    def _calculate_thumbnail_size(self):
        """Calculate the width and height for thumbnails."""
        # Calculate width based on viewport
        spacing = self.grid.spacing()
        margins = self.grid.contentsMargins()
        available_width = self.viewport().width() - margins.left() - margins.right()
        thumbnail_width = (
            available_width - (self.columns - 1) * spacing
        ) // self.columns

        # Calculate maximum height needed based on loaded images
        max_height = 0
        for image_id, thumbnail in self.thumbnails.items():
            if image_id in self.pixmap_cache:
                pixmap = self.pixmap_cache[image_id]
                scaled_height = (thumbnail_width * pixmap.height()) / pixmap.width()
                max_height = max(max_height, scaled_height)

        # Use either calculated height or default if no images loaded
        self.max_thumbnail_height = int(max_height) if max_height > 0 else 300

        return thumbnail_width, self.max_thumbnail_height

    def mousePressEvent(self, event):

        self._note_user_activity()
        if event.button() == Qt.LeftButton:
            # Convert viewport coordinates to content coordinates
            content_pos = self.content.mapFrom(self, event.pos())

            # Check if clicked on a tag chip - if so, don't handle selection
            clicked_widget = self.content.childAt(content_pos)
            if clicked_widget:
                # Walk up the widget hierarchy to find if we clicked on a TagChip
                widget = clicked_widget
                depth = 0
                while widget and depth < 10:  # Limit depth to avoid infinite loops
                    # Check if widget is a TagChip or has TagChip in its hierarchy
                    if isinstance(widget, TagChip) or widget.objectName() == "TagChip":
                        # Clicked on a tag chip, let it handle the event
                        super().mousePressEvent(event)
                        return
                    # Check if widget is inside a tags container
                    if (
                        hasattr(widget, "objectName")
                        and widget.objectName() == "TagsContainer"
                    ):
                        # Clicked inside tags container, let child widgets handle it
                        super().mousePressEvent(event)
                        return
                    # Check if widget has "RemoveButton" in objectName
                    if (
                        hasattr(widget, "objectName")
                        and widget.objectName()
                        and "RemoveButton" in widget.objectName()
                    ):
                        super().mousePressEvent(event)
                        return
                    widget = widget.parent()
                    depth += 1

            self.clicked_position = event.pos()
            self.selection_start = event.pos()
            self.is_selecting = True

            # Check if clicked on a thumbnail by checking all thumbnails
            clicked_thumbnail = None
            for thumbnail in self.thumbnails.values():
                # Convert thumbnail position to content coordinates
                thumbnail_global_pos = thumbnail.mapTo(self.content, QPoint(0, 0))
                thumbnail_rect = QRect(thumbnail_global_pos, thumbnail.size())
                if thumbnail_rect.contains(content_pos):
                    clicked_thumbnail = thumbnail
                    break

            if clicked_thumbnail:
                # Store the clicked thumbnail for later processing
                self.clicked_on_thumbnail = clicked_thumbnail.image_id
                self._log_debug(f"Clicked on thumbnail: {self.clicked_on_thumbnail}")
            else:
                self.clicked_on_thumbnail = None
                if not (event.modifiers() & (Qt.ShiftModifier | Qt.ControlModifier)):
                    # Clear selection if clicking empty space without modifiers
                    self.selected_images.clear()
                    self.last_selected_image = None
                    self._update_selection()

            # Always show rubber band for drag selection
            # Position the rubber band correctly in viewport coordinates
            self.rubber_band.setGeometry(QRect(event.pos(), QSize()))
            self.rubber_band.show()
            self.rubber_band.raise_()  # Ensure it's on top

        super().mousePressEvent(event)

    def _log_debug(self, message: str) -> None:
        """Log debug message to developer log if available."""
        parent = self.parent()
        while parent:
            if hasattr(parent, "add_log_message"):
                parent.add_log_message(message, "INFO")
                return
            parent = parent.parent()
        # No global print fallback in normal mode

    def mouseDoubleClickEvent(self, event):
        """Open viewer on double-click on a thumbnail."""
        if event.button() != Qt.LeftButton:
            super().mouseDoubleClickEvent(event)
            return
        content_pos = self.content.mapFrom(self, event.pos())
        for thumbnail in self.thumbnails.values():
            thumbnail_global_pos = thumbnail.mapTo(self.content, QPoint(0, 0))
            thumbnail_rect = QRect(thumbnail_global_pos, thumbnail.size())
            if thumbnail_rect.contains(content_pos):
                self.image_double_clicked.emit(thumbnail.image_id)
                event.accept()
                return
        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event):
        self._note_user_activity()
        if self.is_selecting:
            # Update rubber band geometry with proper coordinates
            selection_rect = QRect(self.selection_start, event.pos()).normalized()
            self.rubber_band.setGeometry(selection_rect)
        super().mouseMoveEvent(event)

    def wheelEvent(self, event):
        """Let wheel events reach the scroll area (preload is not paused on scroll)."""
        super().wheelEvent(event)

    def mouseReleaseEvent(self, event):
        self._log_debug("Mouse release event")
        if event.button() == Qt.LeftButton and self.is_selecting:
            self._log_debug("Left button released")
            self.is_selecting = False
            self.rubber_band.hide()

            # Check if this was a single click (no drag)
            if (
                hasattr(self, "clicked_position")
                and self.clicked_position == event.pos()
            ):
                self._log_debug("Single click detected")
                # Single click - handle thumbnail selection
                if hasattr(self, "clicked_on_thumbnail") and self.clicked_on_thumbnail:
                    self._log_debug("Clicked on thumbnail detected")
                    if event.modifiers() == Qt.ShiftModifier:
                        # Range selection: select all images between last selected and clicked
                        self._log_debug("Shift+click detected")
                        self._log_debug(
                            f"last_selected_image: {self.last_selected_image}"
                        )
                        self._log_debug(
                            f"clicked_on_thumbnail: {self.clicked_on_thumbnail}"
                        )
                        self._log_debug(f"all_images count: {len(self.all_images)}")

                        if self.last_selected_image:
                            # Find indices of last selected and clicked images
                            start_idx = None
                            end_idx = None

                            # Find start index
                            self._log_debug(
                                f"Searching for start image: {self.last_selected_image}"
                            )
                            for i, img in enumerate(self.all_images):
                                if img.id == self.last_selected_image:
                                    start_idx = i
                                    self._log_debug(
                                        f"Found start at index: {start_idx}"
                                    )
                                    break

                            # Find end index
                            self._log_debug(
                                f"Searching for end image: {self.clicked_on_thumbnail}"
                            )
                            for i, img in enumerate(self.all_images):
                                if img.id == self.clicked_on_thumbnail:
                                    end_idx = i
                                    self._log_debug(f"Found end at index: {end_idx}")
                                    break

                            self._log_debug(
                                f"start_idx: {start_idx}, end_idx: {end_idx}"
                            )

                            # If both indices found, select range
                            if start_idx is not None and end_idx is not None:
                                start_idx, end_idx = min(start_idx, end_idx), max(
                                    start_idx, end_idx
                                )
                                self._log_debug(
                                    f"Selecting range from {start_idx} to {end_idx} (inclusive)"
                                )
                                selected_count = 0
                                for i in range(start_idx, end_idx + 1):
                                    if i < len(self.all_images):
                                        self.selected_images.add(self.all_images[i].id)
                                        selected_count += 1
                                self._log_debug(f"Selected {selected_count} images")
                            elif start_idx is not None:
                                # Only start found, select from start to end of list
                                self._log_debug(
                                    f"Only start found, selecting from {start_idx} to end"
                                )
                                for i in range(start_idx, len(self.all_images)):
                                    self.selected_images.add(self.all_images[i].id)
                            elif end_idx is not None:
                                # Only end found, select from start of list to end
                                self._log_debug(
                                    f"Only end found, selecting from start to {end_idx}"
                                )
                                for i in range(end_idx + 1):
                                    self.selected_images.add(self.all_images[i].id)
                            else:
                                # Neither found, just add clicked image
                                self._log_debug(
                                    f"Neither image found, just adding clicked image"
                                )
                                self.selected_images.add(self.clicked_on_thumbnail)
                        else:
                            # No previous selection, just add clicked image
                            self._log_debug(
                                f"No previous selection, just adding clicked image"
                            )
                            self.selected_images.add(self.clicked_on_thumbnail)
                        self.last_selected_image = self.clicked_on_thumbnail
                        self._log_debug(
                            f"Updated last_selected_image to: {self.last_selected_image}"
                        )
                        self._log_debug(
                            f"Total selected images: {len(self.selected_images)}"
                        )
                    elif event.modifiers() == Qt.ControlModifier:
                        # Toggle selection
                        if self.clicked_on_thumbnail in self.selected_images:
                            self.selected_images.remove(self.clicked_on_thumbnail)
                        else:
                            self.selected_images.add(self.clicked_on_thumbnail)
                        self.last_selected_image = self.clicked_on_thumbnail
                    else:
                        # New selection
                        self.selected_images = {self.clicked_on_thumbnail}
                        self.last_selected_image = self.clicked_on_thumbnail

                    self._update_selection()
                    # Emit clicked signal for single click
                    self.image_clicked.emit(self.clicked_on_thumbnail)
            else:
                # Drag selection - get thumbnails in selection rectangle
                selection_rect = QRect(self.selection_start, event.pos()).normalized()
                last_dragged_image = None
                if not event.modifiers():
                    self.selected_images.clear()
                widgets_to_check = (
                    list(self.thumbnail_pool)
                    if self.thumbnail_pool
                    else [
                        self.grid.itemAt(i).widget()
                        for i in range(self.grid.count())
                        if self.grid.itemAt(i) and self.grid.itemAt(i).widget()
                    ]
                )
                for widget in widgets_to_check:
                    if not isinstance(widget, ImageThumbnail) or not widget.isVisible():
                        continue
                    widget_rect = QRect(widget.mapTo(self, QPoint(0, 0)), widget.size())
                    if selection_rect.intersects(widget_rect):
                        if event.modifiers() == Qt.ControlModifier:
                            self.selected_images.discard(widget.image_id)
                        else:
                            self.selected_images.add(widget.image_id)
                            last_dragged_image = widget.image_id

                # Update last selected image for range selection
                if last_dragged_image:
                    self.last_selected_image = last_dragged_image

                self._update_selection()

            # Clean up
            if hasattr(self, "clicked_on_thumbnail"):
                delattr(self, "clicked_on_thumbnail")
            if hasattr(self, "clicked_position"):
                delattr(self, "clicked_position")

            # Ensure active image (tags) follows the current click/selection
            # so that when we select an image under the cursor, its tags appear
            if self.last_selected_image:
                self.set_active_image(self.last_selected_image)

        super().mouseReleaseEvent(event)

    def _update_selection(self):
        """Update visual selection state of all thumbnails (borders only)."""
        if self.thumbnail_pool:
            for thumb in self.thumbnail_pool:
                if thumb.isVisible():
                    thumb.set_selected(thumb.image_id in self.selected_images)
        else:
            for i in range(self.grid.count()):
                widget = self.grid.itemAt(i).widget()
                if isinstance(widget, ImageThumbnail):
                    widget.set_selected(widget.image_id in self.selected_images)
        # If active image is no longer selected, hide its tags
        if self.active_image_id and self.active_image_id not in self.selected_images:
            self.set_active_image(None)

        self.selection_changed.emit(list(self.selected_images))

    def set_active_image(self, image_id: str | None) -> None:
        """
        Set the image whose tags are currently visible, based on hover.

        Only this image will display its TagChips to keep UI performant.
        """
        # Tags doivent être affichés uniquement pour les images sélectionnées
        if image_id is not None and image_id not in self.selected_images:
            # Si on survole une image non sélectionnée, on efface l'image active
            image_id = None

        if image_id == self.active_image_id:
            return

        # Hide tags on previous active image and hide floating popover
        if self.active_image_id and self.active_image_id in self.thumbnails:
            self.thumbnails[self.active_image_id].set_tags_visible(False)
        self._tag_popover.hide_popover()

        self.active_image_id = image_id

        # Show tags on new active image (thumbnails dict holds visible pool in virtualized mode)
        if self.active_image_id and self.active_image_id in self.thumbnails:
            self.thumbnails[self.active_image_id].set_tags_visible(True)
        else:
            self._tag_popover.hide_popover()

    def set_tag_popover_stack_under(self, widget: QWidget) -> None:
        """Stack the tag chip popover below ``widget`` (e.g. Start session button)."""
        self._tag_popover.set_stack_under_widget(widget)

    def _show_tag_popover(
        self, thumbnail: ImageThumbnail, image_id: str, tags: Set[str]
    ) -> None:
        """Show the floating tag popover below the given thumbnail with full tag names."""
        self._tag_popover.show_below(
            thumbnail,
            self.viewport(),
            tags,
            image_id,
            remove_tag_callback=self._remove_tag_from_selection,
        )

    def contextMenuEvent(self, event):
        """Show context menu."""
        if self.selected_images:  # Only show if there are selected images
            has_single_selection = len(self.selected_images) == 1
            self.start_session_from_image_action.setEnabled(has_single_selection)
            self.start_session_from_image_action.setVisible(has_single_selection)
            self.context_menu.popup(event.globalPos())

    def _start_session_from_selected_image(self) -> None:
        """Emit a request to start a session from the currently selected image."""
        if len(self.selected_images) != 1:
            return
        selected_image_id = next(iter(self.selected_images))
        self.start_session_from_image_requested.emit(selected_image_id)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Accept file/folder drops so they are handled as import (not as tag on thumbnail)."""
        md = event.mimeData()
        if md.hasUrls() and self._import_drop_callback:
            event.acceptProposedAction()
            return
        if md.hasFormat("application/x-sketchbook-tag-library-multi") or (
            md.hasText() and md.text().strip()
        ):
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:
        """Keep tag drops accepted over empty grid areas between thumbnails."""
        md = event.mimeData()
        if md.hasUrls() and self._import_drop_callback:
            event.acceptProposedAction()
            return
        if md.hasFormat("application/x-sketchbook-tag-library-multi") or (
            md.hasText() and md.text().strip()
        ):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        """Handle file/folder drop on empty grid area: forward to import."""
        if event.mimeData().hasUrls() and self._import_drop_callback:
            self._import_drop_callback(event.mimeData().urls())
            event.acceptProposedAction()

    def _rotate_selected_clockwise(self):
        """Rotate selected images 90° clockwise and refresh thumbnails."""
        self._rotate_selected(clockwise=True)

    def _rotate_selected_counterclockwise(self):
        """Rotate selected images 90° counterclockwise and refresh thumbnails."""
        self._rotate_selected(clockwise=False)

    def _rotate_selected(self, clockwise: bool) -> None:
        """
        Rotate all selected images by 90° in background threads; refresh display when each completes.

        Args:
            clockwise: If True, rotate 90° clockwise; if False, rotate 90° counterclockwise.
        """
        if not self.selected_images:
            return
        for image_id in list(self.selected_images):
            metadata = self.image_manager.get_image_metadata(image_id)
            if not metadata:
                continue
            path = self.image_manager.image_dir / metadata.path
            fmt = (metadata.format or "jpg").upper()
            worker = RotateImageWorker(
                image_id, path, clockwise, fmt, self.image_manager
            )
            worker.signals.finished.connect(self._on_rotate_finished)
            worker.signals.error.connect(self._on_rotate_error)
            self.thread_pool.start(worker)

    def _on_rotate_finished(self, image_id: str, success: bool, w: int, h: int) -> None:
        """Update metadata and UI after a rotation completes (main thread)."""
        if not success:
            return
        self.image_manager.update_image_metadata(image_id, width=w, height=h)
        self.pixmap_cache.pop(image_id, None)
        if image_id in self.thumbnails:
            self.thumbnails[image_id].clear_pixmap()
        meta = self.image_manager.get_image_metadata(image_id)
        if meta:
            idx = self._image_id_to_index.get(image_id)
            if idx is not None and idx < len(self.all_images):
                self.all_images[idx] = meta
        self._check_visible_thumbnails()
        self.layout_timer.start()

    def _on_rotate_error(self, image_id: str, error_msg: str) -> None:
        """Log rotation error (main thread)."""
        print(f"Rotate failed for {image_id}: {error_msg}")

    def _delete_selected(self):
        """Delete selected images after confirmation."""
        count = len(self.selected_images)
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Confirm Deletion")
        msg.setText(
            f"Are you sure you want to delete {count} image{'s' if count > 1 else ''}?"
        )
        msg.setInformativeText("This action cannot be undone.")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)

        if msg.exec_() == QMessageBox.Yes:
            for image_id in self.selected_images:
                self.image_manager.delete_image(image_id)
            self.selected_images.clear()
            self._update_selection()
            self.grid_needs_refresh.emit()

    def _remove_tag_from_selection(self, tag: str):
        """
        Remove a tag from all selected images using the same background worker as tag assignment.

        Args:
            tag: Tag to remove from selected images
        """
        if not self.selected_images:
            return

        image_ids = list(self.selected_images)
        worker = TagApplyWorker(
            self.image_manager,
            image_ids,
            tag,
            operation="remove",
        )

        worker.signals.progress.connect(
            lambda cur, tot: self.tag_remove_progress.emit(tag, cur, tot),
            Qt.QueuedConnection,
        )
        worker.signals.finished.connect(
            lambda total: self._on_remove_tag_finished(tag, image_ids, total),
            Qt.QueuedConnection,
        )
        worker.signals.error.connect(
            self._on_remove_tag_error,
            Qt.QueuedConnection,
        )

        self.thread_pool.start(worker)

    def _on_remove_tag_finished(
        self, tag: str, image_ids: List[str], total: int
    ) -> None:
        """Refresh thumbnails after tag removal when tag UI is visible."""
        self.refresh_visible_tags_for_images(image_ids)
        self.tag_remove_finished.emit(tag, image_ids, total)

    def _on_remove_tag_error(self, error_msg: str) -> None:
        """Handle tag removal error (main thread)."""
        self.tag_remove_error.emit(error_msg)

    def _add_tag_to_images(self, tag: str, image_ids: List[str]):
        """
        Add a tag to multiple images and refresh their display.

        Args:
            tag: Tag to add
            image_ids: List of image IDs to add the tag to
        """
        self.image_manager.add_tags_to_images(image_ids, tag)
        self.refresh_visible_tags_for_images(image_ids)

    def load_images_with_advanced_filter(
        self, filters: dict, sort_by: str = "import_date_desc"
    ):
        """
        Load and display images with advanced AND/OR filtering.

        Args:
            filters: Dictionary with "and" and "or" sets of tags
            sort_by: Sort order (see ImageDatabase.list_images for options)
        """
        # Extract filter sets
        and_tags = filters.get("and", set())
        or_tags = filters.get("or", set())

        # Clear if filter or sort changed
        current_filter_key = (frozenset(and_tags), frozenset(or_tags), sort_by)
        if self.current_filter != current_filter_key:
            self.clear()

        # Store filter and sort
        self.current_filter = current_filter_key
        self.sort_by = sort_by

        self.all_images = self.image_manager.search_images_advanced(
            and_tags, or_tags, sort_by
        )
        self._rebuild_image_id_index()
        self._rebuild_extract_indices()
        if not self._is_virtualized():
            self._load_next_batch()
        self.layout_timer.start()

    def load_images_from_list(self, images: List[ImageMetadata], filter_key) -> None:
        """
        Load and display a provided list of images.

        Args:
            images: List of image metadata to display.
            filter_key: Key used to detect filter changes.
        """
        new_ids = set(m.id for m in images)
        list_changed = len(images) != len(self.all_images) or (
            self.all_images and new_ids != set(m.id for m in self.all_images)
        )
        if list_changed or self.current_filter != filter_key:
            self.clear()
            self.verticalScrollBar().setValue(0)
            self.horizontalScrollBar().setValue(0)
            self.grid.update()
            self.content.update()
            self.viewport().update()
            QApplication.processEvents()

        self.current_filter = filter_key
        self.all_images = list(images)
        self._rebuild_image_id_index()
        self._rebuild_extract_indices()
        if self._is_virtualized():
            self._update_virtualized_view()
        else:
            self._load_next_batch()
        self.layout_timer.start()
        self.visibility_timer.start()
        self._user_idle_timer.start()
        self.grid.update()
        self.content.update()
        self.viewport().update()
