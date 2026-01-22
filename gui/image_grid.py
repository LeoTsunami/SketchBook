"""
Image grid component for displaying image thumbnails in a scrollable grid layout.
"""
from pathlib import Path
from typing import List, Optional, Dict, Set
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
    QDialog,
    QLineEdit,
    QPushButton,
    QMessageBox
)
from qtpy.QtCore import Qt, QSize, Signal, QTimer, QThreadPool, QRect, QPoint
from qtpy.QtGui import QPixmap, QImage, QResizeEvent
from core.image_manager import ImageManager
from core.image_db import ImageMetadata
from gui.image_loader_worker import ImageLoaderWorker
from gui.image_thumbnail import ImageThumbnail
from qtpy.QtWidgets import QCompleter

def load_stylesheet(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

class AddTagDialog(QDialog):
    """Dialog for adding tags to selected images."""
    
    def __init__(self, parent=None, existing_tags=None):
        super().__init__(parent)
        self.setWindowTitle("Add Tags")
        self.existing_tags = existing_tags or []
        self.selected_tags = []
        
        layout = QVBoxLayout(self)
        
        # Tag input with autocomplete
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("Enter tags (comma separated)")
        layout.addWidget(self.tag_input)
        
        # Add completer
        completer = QCompleter(self.existing_tags)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.tag_input.setCompleter(completer)
        
        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("Add")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
    
    def get_tags(self):
        """Return the entered tags as a list."""
        return [tag.strip() for tag in self.tag_input.text().split(",") if tag.strip()]

class ImageGrid(QScrollArea):
    """Scrollable grid of image thumbnails."""
    
    image_clicked = Signal(str)  # Emits image ID when clicked
    selection_changed = Signal(list)  # Emits list of selected image IDs
    session_images_selected = Signal(list)  # Emits list of image IDs for drawing session
    BASE_BATCH_SIZE = 20
    MIN_ROWS_LOADED = 5
    MIN_THUMBNAIL_HEIGHT = 150
    MIN_WINDOW_WIDTH = 800
    ASPECT_RATIO = 1.2
    
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
        
        # Set up thread pool for image loading
        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(4)  # Limit concurrent image loads
        
        # Set up unified timer for all layout updates with shorter interval
        self.layout_timer = QTimer(self)
        self.layout_timer.setSingleShot(True)
        self.layout_timer.setInterval(50)  # Reduced to 50ms for more responsiveness
        self.layout_timer.timeout.connect(self._update_layout)
        
        # Set up separate timer for checking visible thumbnails
        self.visibility_timer = QTimer(self)
        self.visibility_timer.setSingleShot(True)
        self.visibility_timer.setInterval(50)
        self.visibility_timer.timeout.connect(self._check_visible_thumbnails)
        
        # Connect scroll bar
        self.verticalScrollBar().valueChanged.connect(self._on_scroll)
        
        self.row_heights = {}  # Store optimal height for each row
        
        self.is_layout_locked = False  # Add lock to prevent concurrent layout updates
        self.pending_column_change = None  # Store pending column change
        
        # Create context menu
        self.context_menu = QMenu(self)
        self.add_tags_action = self.context_menu.addAction("Add Tags...")
        self.delete_action = self.context_menu.addAction("Delete from Library")
        self.use_for_session_action = self.context_menu.addAction("Use for Drawing Session")
        
        # Connect actions
        self.add_tags_action.triggered.connect(self._add_tags_to_selection)
        self.delete_action.triggered.connect(self._delete_selected)
        self.use_for_session_action.triggered.connect(self._use_for_session)
    
    def _apply_theme(self):
        from core.settings import settings
        theme = settings.get("ui.theme")
        self._update_thumbnail_theme(theme)
    
    def _update_thumbnail_theme(self, theme: str):
        pass  # Le style des thumbnails est désormais géré uniquement par QSS global
    
    def _on_scroll(self, value):
        """Handle scroll events."""
        # Check visible thumbnails
        self._check_visible_thumbnails()
        
        # Check if we need to load more thumbnails
        viewport_bottom = value + self.viewport().height()
        content_bottom = self.content.height()
        
        # Increased preload margin to 1000px
        if content_bottom - viewport_bottom < 1000 and self.loaded_count < len(self.all_images):
            self._load_next_batch()
    
    def _update_layout(self):
        """Handle all layout updates in one place."""
        if not self.thumbnails:
            return
        
        # First calculate row heights
        self._calculate_row_heights()
        
        # Then perform layout
        self._do_relayout()
        
        # Finally check for visible thumbnails that need loading
        self._check_visible_thumbnails()
    
    def set_columns(self, columns: int):
        """Set the number of columns in the grid."""
        if self.columns == columns:
            return
            
        self.columns = columns
        self.needs_relayout = True
        
        # Clear cache to force proper image reloading
        self.pixmap_cache.clear()
        
        # Trigger layout update
        self.layout_timer.start()
        
        # Load more images if needed
        if self.loaded_count < len(self.all_images):
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
        # Stop any pending relayout
        self.layout_timer.stop()
        
        # Clear loading state
        self.loading_images.clear()
        
        # Clear thumbnails
        for thumbnail in self.thumbnails.values():
            self.grid.removeWidget(thumbnail)
            thumbnail.deleteLater()
        self.thumbnails.clear()
        
        # Clear cache if filter changed
        self.pixmap_cache.clear()
        
        self.loaded_count = 0
        self.all_images.clear()
    
    def load_images(self, filter_tags: Optional[List[str]] = None):
        """
        Load and display images, optionally filtered by tags.
        
        Args:
            filter_tags: Optional list of tags to filter images by
        """
        # Clear if filter changed
        if self.current_filter != filter_tags:
            self.clear()
        
        # Store filter
        self.current_filter = filter_tags
        
        # Get all matching images
        self.all_images = self.image_manager.db.search_images(filter_tags)
        
        # Create initial batch of thumbnails
        self._load_next_batch()
        
        # Trigger initial layout update
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
            
            # Create thumbnail
            thumbnail = ImageThumbnail(metadata.id, metadata.original_filename, self)
            
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
    
    def _check_visible_thumbnails(self):
        """Check which thumbnails are visible and load their images."""
        viewport_rect = QRect(
            self.horizontalScrollBar().value(),
            self.verticalScrollBar().value(),
            self.viewport().width(),
            self.viewport().height()
        )
        
        # Increased margin to preload more images
        margin = 500
        viewport_rect.adjust(-margin, -margin, margin, margin)
        
        # Track which thumbnails need loading
        to_load = set()
        
        # Check all thumbnails in or near the viewport
        for image_id, thumbnail in self.thumbnails.items():
            if viewport_rect.intersects(self._get_widget_geometry(thumbnail)):
                if image_id not in self.loading_images and image_id not in self.pixmap_cache:
                    to_load.add(image_id)
        
        # Load all needed thumbnails
        for image_id in to_load:
            self._load_thumbnail_image(image_id)
    
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
        """Load image for a thumbnail asynchronously."""
        if image_id not in self.thumbnails:
            return
            
        if image_id in self.loading_images:
            return
            
        if image_id in self.pixmap_cache:
            thumbnail = self.thumbnails[image_id]
            thumbnail.set_image(self.pixmap_cache[image_id])
            return
            
        # Find metadata
        metadata = next((m for m in self.all_images if m.id == image_id), None)
        if not metadata:
            return
            
        # Mark as loading
        self.loading_images.add(image_id)
            
        # Get actual thumbnail size for proper scaling
        # Use the graphics_view size which is the actual image display area
        thumbnail = self.thumbnails[image_id]
        target_width = thumbnail.graphics_view.width()
        target_height = thumbnail.graphics_view.height()
        
        # Ensure minimum size for quality
        if target_width <= 0:
            target_width = thumbnail.width() - 8
        if target_height <= 0:
            target_height = thumbnail.height() - 8
        
        # Create and start worker with actual thumbnail dimensions
        image_path = self.image_manager.image_dir / metadata.path
        worker = ImageLoaderWorker(image_id, image_path, (target_width, target_height))
        
        worker.signals.finished.connect(self._on_image_loaded)
        worker.signals.error.connect(self._on_image_error)
        
        self.thread_pool.start(worker)
    
    def _on_image_loaded(self, image_id: str, pixmaps: tuple):
        """Handle loaded image."""
        self.loading_images.discard(image_id)
        
        if image_id not in self.thumbnails:
            return
            
        thumbnail = self.thumbnails[image_id]
        fast_pixmap, high_quality_pixmap = pixmaps
        
        # Cache the high quality pixmap
        self.pixmap_cache[image_id] = high_quality_pixmap
        
        # Set the image
        thumbnail.set_image(high_quality_pixmap)
    
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
            self.selection_start = event.pos()
            self.is_selecting = True

            # Convert viewport coordinates to content coordinates
            content_pos = self.content.mapFrom(self, event.pos())
            
            # Check if clicked on a thumbnail
            child = self.content.childAt(content_pos)
            if isinstance(child, ImageThumbnail):
                # Store the clicked thumbnail for later processing
                self.clicked_on_thumbnail = child.image_id
                self.clicked_position = event.pos()
            else:
                self.clicked_on_thumbnail = None
                if not (event.modifiers() & (Qt.ShiftModifier | Qt.ControlModifier)):
                    # Clear selection if clicking empty space without modifiers
                    self.selected_images.clear()
                    self._update_selection()
            
            # Always show rubber band for drag selection
            # Position the rubber band correctly in viewport coordinates
            self.rubber_band.setGeometry(QRect(event.pos(), QSize()))
            self.rubber_band.show()
            self.rubber_band.raise_()  # Ensure it's on top
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if self.is_selecting:
            # Update rubber band geometry with proper coordinates
            selection_rect = QRect(self.selection_start, event.pos()).normalized()
            self.rubber_band.setGeometry(selection_rect)
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.is_selecting:
            self.is_selecting = False
            self.rubber_band.hide()
            
            # Check if this was a single click (no drag)
            if hasattr(self, 'clicked_position') and self.clicked_position == event.pos():
                # Single click - handle thumbnail selection
                if hasattr(self, 'clicked_on_thumbnail') and self.clicked_on_thumbnail:
                    if event.modifiers() == Qt.ShiftModifier:
                        # Add to selection
                        self.selected_images.add(self.clicked_on_thumbnail)
                    elif event.modifiers() == Qt.ControlModifier:
                        # Toggle selection
                        if self.clicked_on_thumbnail in self.selected_images:
                            self.selected_images.remove(self.clicked_on_thumbnail)
                        else:
                            self.selected_images.add(self.clicked_on_thumbnail)
                    else:
                        # New selection
                        self.selected_images = {self.clicked_on_thumbnail}
                    
                    self._update_selection()
                    # Emit clicked signal for single click
                    self.image_clicked.emit(self.clicked_on_thumbnail)
            else:
                # Drag selection - get thumbnails in selection rectangle
                selection_rect = QRect(self.selection_start, event.pos()).normalized()
                for i in range(self.grid.count()):
                    widget = self.grid.itemAt(i).widget()
                    if isinstance(widget, ImageThumbnail):
                        # Convert widget position to viewport coordinates for proper intersection test
                        widget_rect = QRect(widget.mapTo(self, QPoint(0, 0)), widget.size())
                        if selection_rect.intersects(widget_rect):
                            if event.modifiers() == Qt.ControlModifier:
                                # Ctrl + drag always removes from selection
                                self.selected_images.discard(widget.image_id)
                            else:
                                # Normal drag adds to selection
                                self.selected_images.add(widget.image_id)
                
                self._update_selection()
            
            # Clean up
            if hasattr(self, 'clicked_on_thumbnail'):
                delattr(self, 'clicked_on_thumbnail')
            if hasattr(self, 'clicked_position'):
                delattr(self, 'clicked_position')
        
        super().mouseReleaseEvent(event)
    
    def _update_selection(self):
        """Update visual selection state of all thumbnails."""
        for i in range(self.grid.count()):
            widget = self.grid.itemAt(i).widget()
            if isinstance(widget, ImageThumbnail):
                widget.set_selected(widget.image_id in self.selected_images)
        self.selection_changed.emit(list(self.selected_images))

    def contextMenuEvent(self, event):
        """Show context menu."""
        if self.selected_images:  # Only show if there are selected images
            self.context_menu.popup(event.globalPos())
    
    def _add_tags_to_selection(self):
        """Open dialog to add tags to selected images."""
        dialog = AddTagDialog(self, self.image_manager.get_all_tags())
        if dialog.exec_() == QDialog.Accepted:
            new_tags = dialog.get_tags()
            if new_tags:
                for image_id in self.selected_images:
                    self.image_manager.add_tags(image_id, new_tags)
    
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
    
    def _use_for_session(self):
        """Emit signal with selected images for drawing session."""
        self.session_images_selected.emit(list(self.selected_images))

    def load_images_with_advanced_filter(self, filters: dict):
        """
        Load and display images with advanced AND/OR filtering.
        
        Args:
            filters: Dictionary with "and" and "or" sets of tags
        """
        # Extract filter sets
        and_tags = filters.get("and", set())
        or_tags = filters.get("or", set())
        
        # Clear if filter changed
        current_filter_key = (frozenset(and_tags), frozenset(or_tags))
        if self.current_filter != current_filter_key:
            self.clear()
        
        # Store filter
        self.current_filter = current_filter_key
        
        # Get all matching images
        self.all_images = self.image_manager.search_images_advanced(and_tags, or_tags)
        
        # Create initial batch of thumbnails
        self._load_next_batch()
        
        # Trigger initial layout update
        self.layout_timer.start() 