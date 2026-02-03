"""
Image grid component for displaying image thumbnails in a scrollable grid layout.
"""
from pathlib import Path
from typing import List, Optional, Dict, Set
from collections import deque
from qtpy.QtWidgets import (
    QWidget,
    QScrollArea,
    QGridLayout,
    QLabel,
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
    QSizePolicy
)
from qtpy.QtCore import Qt, QSize, Signal, QTimer, QThreadPool, QRect, QPoint
from qtpy.QtGui import QPixmap, QImage, QResizeEvent, QIcon
from core.image_manager import ImageManager
from core.image_db import ImageMetadata
from gui.image_loader_worker import ImageLoaderWorker
from gui.image_rotate_worker import RotateImageWorker
from gui.tag_apply_worker import TagApplyWorker
from gui.image_thumbnail import ImageThumbnail, TagChip
from qtpy.QtWidgets import QCompleter
import json

def load_stylesheet(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

class ImageGrid(QScrollArea):
    """Scrollable grid of image thumbnails."""
    
    image_clicked = Signal(str)  # Emits image ID when clicked (single click)
    image_double_clicked = Signal(str)  # Emits image ID when double-clicked (open viewer)
    selection_changed = Signal(list)  # Emits list of selected image IDs
    grid_needs_refresh = Signal()  # Emits when DB changed (delete, etc.) so main window can reload
    tag_remove_progress = Signal(str, int, int)  # tag, current, total
    tag_remove_finished = Signal(str, list, int)  # tag, image_ids, total
    tag_remove_error = Signal(str)  # error message
    BASE_BATCH_SIZE = 10  # Reason: smaller batches = less lag per batch, load more often
    MIN_ROWS_LOADED = 2
    MIN_THUMBNAIL_HEIGHT = 150
    MIN_WINDOW_WIDTH = 800
    ASPECT_RATIO = 1.2
    # Virtualization: above this count we use a fixed pool of widgets (smooth scroll with 20k+ images)
    VIRTUALIZATION_THRESHOLD = 400
    VIRTUALIZED_POOL_EXTRA_ROWS = 3  # Rows above/below viewport to render
    
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
        
        # Apply theme-aware styles
        self._apply_theme()
        self.content.setObjectName("content")
        
        # Initialize state
        self.thumbnails: Dict[str, ImageThumbnail] = {}
        self.current_filter = None
        self.all_images: List[ImageMetadata] = []
        self.loaded_count = 0
        self.loading_images: Set[str] = set()  # Track images being loaded
        self.pixmap_cache: Dict[str, QPixmap] = {}  # Cache loaded pixmaps
        self.columns = 4  # Default number of columns
        self.needs_relayout = False  # Flag to track if relayout is needed
        self.max_thumbnail_height = 300  # Default maximum height
        self.sort_by = "import_date_desc"  # Default sort: most recent first
        
        # Set up thread pool for image loading
        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(4)  # Limit concurrent image loads
        
        # Set up unified timer for all layout updates with shorter interval
        self.layout_timer = QTimer(self)
        self.layout_timer.setSingleShot(True)
        self.layout_timer.setInterval(50)  # Reduced to 50ms for more responsiveness
        self.layout_timer.timeout.connect(self._update_layout)
        
        # Set up separate timer for checking visible thumbnails (debounce scroll)
        self.visibility_timer = QTimer(self)
        self.visibility_timer.setSingleShot(True)
        self.visibility_timer.setInterval(50)  # Reason: short debounce so images appear quickly
        self.visibility_timer.timeout.connect(self._check_visible_thumbnails)

        # Pending pixmap loads: only process a few per tick to avoid main-thread lag
        self.pending_load_queue: deque = deque()
        self.load_ticker_timer = QTimer(self)
        self.load_ticker_timer.setSingleShot(False)
        self.load_ticker_timer.setInterval(40)  # Reason: faster ticks so pixmaps show up sooner
        self.load_ticker_timer.timeout.connect(self._process_pending_loads)
        self.MAX_LOADS_PER_TICK = 3  # Reason: balance between responsiveness and main-thread load
        self.PENDING_QUEUE_MAX = 60  # Cap queue to avoid loading too many off-screen items
        
        # Connect scroll bar
        self.verticalScrollBar().valueChanged.connect(self._on_scroll)
        
        self.row_heights = {}  # Store optimal height for each row

        # Virtualized mode: fixed pool of thumbnails reused for visible range only
        self.thumbnail_pool: List[ImageThumbnail] = []
        self._virtualized_content_height = 0  # Content height when virtualized (total_rows * row_height)
        
        self.is_layout_locked = False  # Add lock to prevent concurrent layout updates
        self.pending_column_change = None  # Store pending column change
        
        # Create context menu
        self.context_menu = QMenu(self)
        self.rotate_cw_action = self.context_menu.addAction("Rotate 90° clockwise")
        self.rotate_cw_action.triggered.connect(self._rotate_selected_clockwise)
        self.rotate_ccw_action = self.context_menu.addAction("Rotate 90° counterclockwise")
        self.rotate_ccw_action.triggered.connect(self._rotate_selected_counterclockwise)
        self.context_menu.addSeparator()
        self.delete_action = self.context_menu.addAction("Delete from Library")
        self.delete_action.triggered.connect(self._delete_selected)
    
    def _apply_theme(self):
        from core.settings import settings
        theme = settings.get("ui.theme")
        self._update_thumbnail_theme(theme)
    
    def _update_thumbnail_theme(self, theme: str):
        pass  # Le style des thumbnails est désormais géré uniquement par QSS global
    
    def _on_scroll(self, value):
        """Handle scroll events. Visibility check is debounced via visibility_timer."""
        # Debounce: only schedule visibility check; avoids running on every scroll tick
        self.visibility_timer.start()

        # Check if we need to load more thumbnail widgets (infinite scroll); larger margin = request sooner
        viewport_bottom = value + self.viewport().height()
        content_bottom = self.content.height()
        if not self._is_virtualized() and content_bottom - viewport_bottom < 1200 and self.loaded_count < len(self.all_images):
            self._load_next_batch()

    def _is_virtualized(self) -> bool:
        """True when we have too many images and use a fixed pool of widgets."""
        return len(self.all_images) > self.VIRTUALIZATION_THRESHOLD

    def _ensure_virtualized_pool(self) -> None:
        """Create the thumbnail pool once when in virtualized mode."""
        if self.thumbnail_pool:
            return
        thumbnail_width, row_height = self._calculate_optimal_dimensions()
        spacing = self.grid.spacing()
        margins = self.grid.contentsMargins()
        viewport_h = self.viewport().height()
        # Pool size = enough rows to fill viewport + extra above/below
        rows_visible = max(1, (viewport_h + spacing) // (row_height + spacing))
        pool_rows = rows_visible + 2 * self.VIRTUALIZED_POOL_EXTRA_ROWS
        pool_size = min(pool_rows * self.columns, len(self.all_images) or 1)
        pool_size = max(pool_size, self.columns * 2)
        for _ in range(pool_size):
            meta = self.all_images[0] if self.all_images else None
            if not meta:
                continue
            thumb = ImageThumbnail(
                meta.id,
                meta.original_filename,
                self.content,
                self.image_manager,
                remove_tag_callback=self._remove_tag_from_selection,
                get_selected_images_callback=lambda: self.selected_images,
            )
            thumb.setFixedWidth(thumbnail_width)
            thumb.setFixedHeight(row_height)
            thumb.image_container.setFixedSize(thumbnail_width - 4, row_height - 4)
            thumb.graphics_view.setFixedSize(thumbnail_width - 4, row_height - 4)
            thumb.clicked.connect(self.image_clicked.emit)
            self.thumbnail_pool.append(thumb)

    def _update_virtualized_view(self) -> None:
        """In virtualized mode: set content height and assign pool to visible indices."""
        if not self._is_virtualized() or not self.all_images:
            return
        self._ensure_virtualized_pool()
        thumbnail_width, row_height = self._calculate_optimal_dimensions()
        spacing = self.grid.spacing()
        margins = self.grid.contentsMargins()
        total_images = len(self.all_images)
        total_rows = (total_images + self.columns - 1) // self.columns
        content_height = total_rows * (row_height + spacing) - spacing + margins.top() + margins.bottom()
        self._virtualized_content_height = content_height
        self.content.setMinimumHeight(content_height)
        self.content.setFixedHeight(content_height)
        scroll_y = self.verticalScrollBar().value()
        viewport_h = self.viewport().height()
        row_h = row_height + spacing
        first_row = max(0, scroll_y // row_h - self.VIRTUALIZED_POOL_EXTRA_ROWS)
        last_row = min(total_rows - 1, (scroll_y + viewport_h) // row_h + self.VIRTUALIZED_POOL_EXTRA_ROWS)
        start_index = first_row * self.columns
        end_index = min(total_images, (last_row + 1) * self.columns)
        # Assign pool widgets to indices [start_index, end_index)
        self.thumbnails.clear()
        for i, thumb in enumerate(self.thumbnail_pool):
            idx = start_index + i
            if idx >= end_index:
                thumb.hide()
                continue
            meta = self.all_images[idx]
            thumb.assign_metadata(meta)
            if meta.id in self.pixmap_cache:
                thumb.set_image(self.pixmap_cache[meta.id])
            thumb.set_selected(meta.id in self.selected_images)
            thumb.setFixedWidth(thumbnail_width)
            thumb.setFixedHeight(row_height)
            thumb.image_container.setFixedSize(thumbnail_width - 4, row_height - 4)
            thumb.graphics_view.setFixedSize(thumbnail_width - 4, row_height - 4)
            row, col = idx // self.columns, idx % self.columns
            x = margins.left() + col * (thumbnail_width + spacing)
            y = margins.top() + row * (row_height + spacing)
            thumb.setGeometry(x, y, thumbnail_width, row_height)
            thumb.show()
            self.thumbnails[meta.id] = thumb
        # Enqueue pixmap loads for visible items
        self.pending_load_queue.clear()
        for idx in range(start_index, end_index):
            if idx >= len(self.all_images):
                break
            image_id = self.all_images[idx].id
            if image_id not in self.loading_images and image_id not in self.pixmap_cache:
                self.pending_load_queue.append(image_id)
        if self.pending_load_queue:
            self.load_ticker_timer.start()
        # Keep pixmap cache bounded: evict off-screen entries when over limit (Reason: 20k images = avoid OOM)
        visible_ids = {self.all_images[i].id for i in range(start_index, end_index)}
        max_cache = 400
        if len(self.pixmap_cache) > max_cache:
            for pid in list(self.pixmap_cache.keys()):
                if pid not in visible_ids and pid not in self.loading_images:
                    self.pixmap_cache.pop(pid, None)
                    if len(self.pixmap_cache) <= max_cache:
                        break

    def _update_layout(self):
        """Handle all layout updates in one place."""
        if self._is_virtualized():
            self._update_virtualized_view()
            return
        for thumb in self.thumbnail_pool:
            thumb.hide()
        if not self.thumbnails:
            return
        self._calculate_row_heights()
        self._do_relayout()
        self._check_visible_thumbnails()
    
    def set_columns(self, columns: int):
        """Set the number of columns in the grid."""
        if self.columns == columns:
            return
            
        self.columns = columns
        self.needs_relayout = True
        
        # Clear cache to force proper image reloading
        self.pixmap_cache.clear()
        
        self.layout_timer.start()
        if not self._is_virtualized() and self.loaded_count < len(self.all_images):
            self._load_next_batch()

    def _calculate_row_heights(self):
        """Calculate optimal height for each row based on actual image dimensions."""
        if not self.thumbnails:
            return
            
        # Calculate available width for thumbnails
        spacing = self.grid.spacing()
        margins = self.grid.contentsMargins()
        available_width = self.viewport().width() - margins.left() - margins.right()
        thumbnail_width = (available_width - (self.columns - 1) * spacing) // self.columns
        
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
                self.row_heights[row] = max(self.row_heights[row], image_heights[metadata.id])
        
        # Ensure minimum height for rows without loaded images
        for row in self.row_heights:
            self.row_heights[row] = max(200, int(self.row_heights[row]))

    def _calculate_optimal_dimensions(self):
        """Calculate optimal thumbnail dimensions based on available space."""
        spacing = self.grid.spacing()
        margins = self.grid.contentsMargins()
        available_width = max(self.viewport().width() - margins.left() - margins.right(),
                            self.MIN_WINDOW_WIDTH - margins.left() - margins.right())
        
        # Calculate thumbnail width based on available space and columns
        thumbnail_width = (available_width - (self.columns - 1) * spacing) // self.columns
        
        # Calculate height using our desired aspect ratio
        optimal_height = int(thumbnail_width * self.ASPECT_RATIO)
        
        # Ensure minimum height
        thumbnail_height = max(optimal_height, self.MIN_THUMBNAIL_HEIGHT)
        
        return thumbnail_width, thumbnail_height

    def _do_relayout(self):
        """Perform the actual grid layout."""
        if not self.thumbnails:
            return
        
        # Get optimal dimensions
        thumbnail_width, thumbnail_height = self._calculate_optimal_dimensions()
        
        # Clear the grid
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().hide()
        
        # Re-add all thumbnails with proper sizes
        for idx, metadata in enumerate(self.all_images):
            if idx >= self.loaded_count:
                break
                
            row = idx // self.columns
            col = idx % self.columns
            
            if metadata.id in self.thumbnails:
                thumbnail = self.thumbnails[metadata.id]
                
                # Set sizes
                thumbnail.setFixedWidth(thumbnail_width)
                thumbnail.setFixedHeight(thumbnail_height)
                thumbnail.image_container.setFixedSize(thumbnail_width - 4, thumbnail_height - 4)
                thumbnail.graphics_view.setFixedSize(thumbnail_width - 4, thumbnail_height - 4)
                
                # Add to grid
                self.grid.addWidget(thumbnail, row, col)
                thumbnail.show()
                
                # Update image scaling (handled by resizeEvent in thumbnail)
                # No need to call fitInView as it causes pixelation

    def clear(self):
        """Remove all thumbnails from the grid."""
        self.layout_timer.stop()
        self.visibility_timer.stop()
        self.load_ticker_timer.stop()
        self.pending_load_queue.clear()
        self.loading_images.clear()
        if self.thumbnail_pool:
            self.thumbnails.clear()
            self.pixmap_cache.clear()
            for thumb in self.thumbnail_pool:
                thumb.hide()
            self.loaded_count = 0
            self.all_images.clear()
            self.content.setMinimumHeight(0)
            self.content.setFixedHeight(0)
            return
        for thumbnail in self.thumbnails.values():
            self.grid.removeWidget(thumbnail)
            thumbnail.deleteLater()
        self.thumbnails.clear()
        self.pixmap_cache.clear()
        self.loaded_count = 0
        self.all_images.clear()
    
    def load_images(self, filter_tags: Optional[List[str]] = None, sort_by: str = "import_date_desc"):
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
        
        self.all_images = self.image_manager.db.search_images(filter_tags, sort_by)
        if not self._is_virtualized():
            self._load_next_batch()
        self.layout_timer.start()
    
    def _calculate_batch_size(self) -> int:
        """Calculate the batch size based on current number of columns."""
        # Calculate proportional batch size
        column_factor = self.columns / 4  # Base proportion on 4 columns
        base_rows = max(self.MIN_ROWS_LOADED, self.BASE_BATCH_SIZE // 4)  # Ensure minimum rows
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
                self, 
                self.image_manager,
                remove_tag_callback=self._remove_tag_from_selection,
                get_selected_images_callback=lambda: self.selected_images
            )
            
            # Set initial size
            thumbnail.setFixedWidth(thumbnail_width)
            thumbnail.setFixedHeight(thumbnail_height)
            thumbnail.image_container.setFixedSize(thumbnail_width - 4, thumbnail_height - 4)
            thumbnail.graphics_view.setFixedSize(thumbnail_width - 4, thumbnail_height - 4)
            
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
        )
        thumbnail.setFixedWidth(thumbnail_width)
        thumbnail.setFixedHeight(thumbnail_height)
        thumbnail.image_container.setFixedSize(thumbnail_width - 4, thumbnail_height - 4)
        thumbnail.graphics_view.setFixedSize(thumbnail_width - 4, thumbnail_height - 4)
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
        if self._is_virtualized():
            self._update_virtualized_view()
            return
        viewport_rect = QRect(
            self.horizontalScrollBar().value(),
            self.verticalScrollBar().value(),
            self.viewport().width(),
            self.viewport().height()
        )
        margin = 400  # Preload a bit above/below viewport
        viewport_rect.adjust(-margin, -margin, margin, margin)

        to_load: List[str] = []
        for image_id, thumbnail in self.thumbnails.items():
            if not viewport_rect.intersects(self._get_widget_geometry(thumbnail)):
                continue
            if image_id in self.loading_images or image_id in self.pixmap_cache:
                continue
            to_load.append(image_id)

        # Replace queue with currently visible items (prioritize what user sees)
        self.pending_load_queue.clear()
        for image_id in to_load[: self.PENDING_QUEUE_MAX]:
            self.pending_load_queue.append(image_id)

        if self.pending_load_queue:
            self.load_ticker_timer.start()

    def _process_pending_loads(self):
        """Process a few pending pixmap loads per tick to avoid main-thread lag."""
        for _ in range(self.MAX_LOADS_PER_TICK):
            if not self.pending_load_queue:
                self.load_ticker_timer.stop()
                return
            image_id = self.pending_load_queue.popleft()
            # Re-check: might already be loading or cached (e.g. from another batch)
            if image_id in self.loading_images or image_id in self.pixmap_cache:
                continue
            self._load_thumbnail_image(image_id)
        if not self.pending_load_queue:
            self.load_ticker_timer.stop()
    
    def _is_thumbnail_visible(self, thumbnail: QWidget) -> bool:
        """Check if a thumbnail is in or near the viewport."""
        if not thumbnail.isVisible():
            return False
            
        viewport_rect = QRect(
            self.horizontalScrollBar().value(),
            self.verticalScrollBar().value(),
            self.viewport().width(),
            self.viewport().height()
        )
        
        # Add margin for preloading
        margin = 500
        viewport_rect.adjust(-margin, -margin, margin, margin)
        
        return viewport_rect.intersects(self._get_widget_geometry(thumbnail))

    def _get_widget_geometry(self, widget: QWidget) -> QRect:
        """Get the global geometry of a widget relative to the scroll area."""
        return QRect(
            widget.mapTo(self.content, widget.rect().topLeft()),
            widget.size()
        )
    
    def _load_thumbnail_image(self, image_id: str):
        """Load image for a thumbnail asynchronously. When virtualized, may load for cache only (thumbnail not visible)."""
        if image_id in self.loading_images:
            return
        if image_id in self.pixmap_cache:
            if image_id in self.thumbnails:
                self.thumbnails[image_id].set_image(self.pixmap_cache[image_id])
            return
        metadata = next((m for m in self.all_images if m.id == image_id), None)
        if not metadata:
            return
        self.loading_images.add(image_id)
        if image_id in self.thumbnails:
            thumbnail = self.thumbnails[image_id]
            target_width = thumbnail.graphics_view.width() or (thumbnail.width() - 8)
            target_height = thumbnail.graphics_view.height() or (thumbnail.height() - 8)
        else:
            thumbnail_width, thumbnail_height = self._calculate_optimal_dimensions()
            target_width = thumbnail_width - 4
            target_height = thumbnail_height - 4
        
        # Create and start worker with actual thumbnail dimensions
        image_path = self.image_manager.image_dir / metadata.path
        worker = ImageLoaderWorker(image_id, image_path, (target_width, target_height))
        
        worker.signals.finished.connect(self._on_image_loaded)
        worker.signals.error.connect(self._on_image_error)
        
        self.thread_pool.start(worker)
    
    def _on_image_loaded(self, image_id: str, pixmaps: tuple):
        """Handle loaded image. Always cache; set_image only if thumbnail still shows this image (virtualized may have recycled it)."""
        self.loading_images.discard(image_id)
        fast_pixmap, high_quality_pixmap = pixmaps
        self.pixmap_cache[image_id] = high_quality_pixmap
        if image_id in self.thumbnails:
            self.thumbnails[image_id].set_image(high_quality_pixmap)
    
    def _on_image_error(self, image_id: str, error_msg: str):
        """Handle image loading error."""
        self.loading_images.discard(image_id)
        if image_id in self.thumbnails:
            self.thumbnails[image_id].set_error(error_msg)
    
    def resizeEvent(self, event):
        """Handle resize events to adjust grid layout."""
        super().resizeEvent(event)
        
        # Only trigger relayout if width changed
        if event.size().width() != event.oldSize().width():
            self.needs_relayout = True
            self.layout_timer.start()
    
    def _calculate_thumbnail_size(self):
        """Calculate the width and height for thumbnails."""
        # Calculate width based on viewport
        spacing = self.grid.spacing()
        margins = self.grid.contentsMargins()
        available_width = self.viewport().width() - margins.left() - margins.right()
        thumbnail_width = (available_width - (self.columns - 1) * spacing) // self.columns
        
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
                    if hasattr(widget, 'objectName') and widget.objectName() == "TagsContainer":
                        # Clicked inside tags container, let child widgets handle it
                        super().mousePressEvent(event)
                        return
                    # Check if widget has "RemoveButton" in objectName
                    if hasattr(widget, 'objectName') and widget.objectName() and "RemoveButton" in widget.objectName():
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
            if hasattr(parent, 'add_log_message'):
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
        if self.is_selecting:
            # Update rubber band geometry with proper coordinates
            selection_rect = QRect(self.selection_start, event.pos()).normalized()
            self.rubber_band.setGeometry(selection_rect)
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        self._log_debug("Mouse release event")
        if event.button() == Qt.LeftButton and self.is_selecting:
            self._log_debug("Left button released")
            self.is_selecting = False
            self.rubber_band.hide()
            
            # Check if this was a single click (no drag)
            if hasattr(self, 'clicked_position') and self.clicked_position == event.pos():
                self._log_debug("Single click detected")
                # Single click - handle thumbnail selection
                if hasattr(self, 'clicked_on_thumbnail') and self.clicked_on_thumbnail:
                    self._log_debug("Clicked on thumbnail detected")
                    if event.modifiers() == Qt.ShiftModifier:
                        # Range selection: select all images between last selected and clicked
                        self._log_debug("Shift+click detected")
                        self._log_debug(f"last_selected_image: {self.last_selected_image}")
                        self._log_debug(f"clicked_on_thumbnail: {self.clicked_on_thumbnail}")
                        self._log_debug(f"all_images count: {len(self.all_images)}")
                        
                        if self.last_selected_image:
                            # Find indices of last selected and clicked images
                            start_idx = None
                            end_idx = None
                            
                            # Find start index
                            self._log_debug(f"Searching for start image: {self.last_selected_image}")
                            for i, img in enumerate(self.all_images):
                                if img.id == self.last_selected_image:
                                    start_idx = i
                                    self._log_debug(f"Found start at index: {start_idx}")
                                    break
                            
                            # Find end index
                            self._log_debug(f"Searching for end image: {self.clicked_on_thumbnail}")
                            for i, img in enumerate(self.all_images):
                                if img.id == self.clicked_on_thumbnail:
                                    end_idx = i
                                    self._log_debug(f"Found end at index: {end_idx}")
                                    break
                            
                            self._log_debug(f"start_idx: {start_idx}, end_idx: {end_idx}")
                            
                            # If both indices found, select range
                            if start_idx is not None and end_idx is not None:
                                start_idx, end_idx = min(start_idx, end_idx), max(start_idx, end_idx)
                                self._log_debug(f"Selecting range from {start_idx} to {end_idx} (inclusive)")
                                selected_count = 0
                                for i in range(start_idx, end_idx + 1):
                                    if i < len(self.all_images):
                                        self.selected_images.add(self.all_images[i].id)
                                        selected_count += 1
                                self._log_debug(f"Selected {selected_count} images")
                            elif start_idx is not None:
                                # Only start found, select from start to end of list
                                self._log_debug(f"Only start found, selecting from {start_idx} to end")
                                for i in range(start_idx, len(self.all_images)):
                                    self.selected_images.add(self.all_images[i].id)
                            elif end_idx is not None:
                                # Only end found, select from start of list to end
                                self._log_debug(f"Only end found, selecting from start to {end_idx}")
                                for i in range(end_idx + 1):
                                    self.selected_images.add(self.all_images[i].id)
                            else:
                                # Neither found, just add clicked image
                                self._log_debug(f"Neither image found, just adding clicked image")
                                self.selected_images.add(self.clicked_on_thumbnail)
                        else:
                            # No previous selection, just add clicked image
                            self._log_debug(f"No previous selection, just adding clicked image")
                            self.selected_images.add(self.clicked_on_thumbnail)
                        self.last_selected_image = self.clicked_on_thumbnail
                        self._log_debug(f"Updated last_selected_image to: {self.last_selected_image}")
                        self._log_debug(f"Total selected images: {len(self.selected_images)}")
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
                widgets_to_check = list(self.thumbnail_pool) if self.thumbnail_pool else [
                    self.grid.itemAt(i).widget() for i in range(self.grid.count())
                    if self.grid.itemAt(i) and self.grid.itemAt(i).widget()
                ]
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
            if hasattr(self, 'clicked_on_thumbnail'):
                delattr(self, 'clicked_on_thumbnail')
            if hasattr(self, 'clicked_position'):
                delattr(self, 'clicked_position')
            
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

        # Hide tags on previous active image
        if self.active_image_id and self.active_image_id in self.thumbnails:
            self.thumbnails[self.active_image_id].set_tags_visible(False)

        self.active_image_id = image_id

        # Show tags on new active image (thumbnails dict holds visible pool in virtualized mode)
        if self.active_image_id and self.active_image_id in self.thumbnails:
            self.thumbnails[self.active_image_id].set_tags_visible(True)

    def contextMenuEvent(self, event):
        """Show context menu."""
        if self.selected_images:  # Only show if there are selected images
            self.context_menu.popup(event.globalPos())
    
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
            for i, m in enumerate(self.all_images):
                if m.id == image_id:
                    self.all_images[i] = meta
                    break
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
        msg.setText(f"Are you sure you want to delete {count} image{'s' if count > 1 else ''}?")
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

    def _on_remove_tag_finished(self, tag: str, image_ids: List[str], total: int) -> None:
        """Refresh thumbnails after tag removal completes (main thread)."""
        for image_id in image_ids:
            if image_id in self.thumbnails:
                self.thumbnails[image_id].refresh_tags()
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
        for image_id in image_ids:
            metadata = self.image_manager.get_image_metadata(image_id)
            if metadata:
                new_tags = metadata.tags.copy()
                new_tags.add(tag)
                self.image_manager.update_image_metadata(image_id, tags=new_tags)
        
        # Refresh tags display on affected thumbnails
        for image_id in image_ids:
            if image_id in self.thumbnails:
                self.thumbnails[image_id].refresh_tags()

    def load_images_with_advanced_filter(self, filters: dict, sort_by: str = "import_date_desc"):
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
        
        self.all_images = self.image_manager.search_images_advanced(and_tags, or_tags, sort_by)
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
        list_changed = (
            len(images) != len(self.all_images)
            or (self.all_images and set(m.id for m in images) != set(m.id for m in self.all_images))
        )
        if self.current_filter != filter_key or list_changed:
            self.clear()
            self.grid.update()
            self.content.update()
            QApplication.processEvents()

        self.current_filter = filter_key
        self.all_images = images
        if not self._is_virtualized():
            self._load_next_batch()
        self.layout_timer.start()
        self.visibility_timer.start()
        self.grid.update()
        self.content.update()