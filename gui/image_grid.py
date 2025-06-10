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
    QFrame,
    QScrollBar,
    QGraphicsView,
    QGraphicsScene
)
from qtpy.QtCore import Qt, QSize, Signal, QTimer, QThreadPool, QRect
from qtpy.QtGui import QPixmap, QImage
from core.image_manager import ImageManager
from core.image_db import ImageMetadata
from gui.image_loader_worker import ImageLoaderWorker

class ImageThumbnail(QFrame):
    """Widget representing a single image thumbnail."""
    
    clicked = Signal(str)  # Emits image ID when clicked
    
    def __init__(self, image_id: str, label: str, parent=None):
        """
        Initialize the thumbnail widget.
        
        Args:
            image_id: Unique identifier of the image
            label: Text to display under the image (not used anymore)
            parent: Parent widget
        """
        super().__init__(parent)
        self.image_id = image_id
        self.setFrameStyle(QFrame.Panel | QFrame.Raised)
        self.setLineWidth(1)
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)  # Reduced spacing since we don't have labels anymore
        
        # Create graphics view for better image rendering
        self.graphics_view = QGraphicsView()
        self.graphics_view.setStyleSheet("""
            QGraphicsView {
                background: transparent;
                border: none;
            }
        """)
        self.graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(Qt.transparent)
        self.graphics_view.setScene(self.scene)
        
        # Create image container that maintains aspect ratio
        self.image_container = QWidget()
        self.image_container.setMinimumHeight(100)  # Minimum height to prevent collapse
        self.image_container.setStyleSheet("background: transparent;")
        
        # Create container layout
        container_layout = QVBoxLayout(self.image_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(self.graphics_view)
        
        layout.addWidget(self.image_container, 1)  # Give image container stretch factor
        
        # Style for dark theme
        self.setStyleSheet("""
            ImageThumbnail {
                background-color: #2d2d2d;
                border-radius: 4px;
                border: 1px solid #3d3d3d;
            }
            ImageThumbnail:hover {
                background-color: #353535;
                border: 1px solid #4d4d4d;
            }
        """)
        
        # Store original pixmap for resizing
        self.original_pixmap = None
        self.pixmap_item = None
    
    def set_image(self, pixmap: QPixmap):
        """Set the image pixmap."""
        if not self.scene:
            return
            
        try:
            # Clear previous pixmap item
            if self.pixmap_item:
                self.scene.removeItem(self.pixmap_item)
            
            # Create new pixmap item
            self.pixmap_item = self.scene.addPixmap(pixmap)
            
            # Set scene rect to match pixmap size
            self.scene.setSceneRect(self.pixmap_item.boundingRect())
            
            # Center the view
            self.graphics_view.setAlignment(Qt.AlignCenter)
            
            # Fit the view to show the entire image
            self.graphics_view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
            
            # Schedule another fit after a short delay to ensure proper scaling
            QTimer.singleShot(50, lambda: self.graphics_view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio))
            
        except Exception as e:
            self.set_error(str(e))
    
    def _apply_high_quality_resize(self):
        """Apply high quality resize after the initial fast resize."""
        if not self.original_pixmap or not self.scene:
            return
            
        available_width = self.graphics_view.width()
        
        if available_width <= 0:
            return
            
        # Calculate new height preserving aspect ratio
        image_ratio = self.original_pixmap.width() / self.original_pixmap.height()
        new_height = int(available_width / image_ratio)
        
        scaled_pixmap = self.original_pixmap.scaled(
            available_width,
            new_height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        
        if self.pixmap_item:
            self.pixmap_item.setPixmap(scaled_pixmap)
            self.scene.setSceneRect(self.pixmap_item.boundingRect())
            self.graphics_view.setFixedHeight(new_height)
    
    def set_error(self, error_msg: str):
        """Show error message."""
        if not self.scene:
            return
        # Clear scene
        self.scene.clear()
        # Add error text
        self.scene.addText(f"Error: {error_msg}")
    
    def resizeEvent(self, event):
        """Handle resize events to adjust image scaling."""
        super().resizeEvent(event)
        
        if self.scene and self.pixmap_item:
            self.graphics_view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
    
    def mousePressEvent(self, event):
        """Handle mouse click events."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.image_id)
        super().mousePressEvent(event)

class ImageGrid(QScrollArea):
    """Scrollable grid of image thumbnails."""
    
    image_clicked = Signal(str)  # Emits image ID when an image is clicked
    LOAD_BATCH_SIZE = 20  # Number of images to load in each batch
    
    def __init__(self, image_manager: ImageManager, parent=None):
        """
        Initialize the image grid.
        
        Args:
            image_manager: Instance of ImageManager for accessing images
            parent: Parent widget
        """
        super().__init__(parent)
        self.image_manager = image_manager
        
        # Create widget to hold the grid
        self.content = QWidget()
        self.setWidget(self.content)
        self.setWidgetResizable(True)
        
        # Create grid layout
        self.grid = QGridLayout(self.content)
        self.grid.setSpacing(8)
        self.grid.setContentsMargins(8, 8, 8, 8)
        
        # Set dark theme styles
        self.setStyleSheet("""
            QScrollArea {
                background-color: #1e1e1e;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 12px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #4d4d4d;
                min-height: 20px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #5d5d5d;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background-color: #2d2d2d;
            }
            QWidget#content {
                background-color: #1e1e1e;
            }
        """)
        self.content.setObjectName("content")
        
        # Initialize state
        self.thumbnails: Dict[str, ImageThumbnail] = {}  # image_id -> thumbnail
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
        self.layout_timer.start()
    
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

    def _do_relayout(self):
        """Perform the actual grid layout."""
        if not self.thumbnails:
            return
        
        # Calculate thumbnail width
        spacing = self.grid.spacing()
        margins = self.grid.contentsMargins()
        available_width = self.viewport().width() - margins.left() - margins.right()
        thumbnail_width = (available_width - (self.columns - 1) * spacing) // self.columns
        
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
                row_height = self.row_heights.get(row, 200)
                
                # Set sizes
                thumbnail.setFixedWidth(thumbnail_width)
                thumbnail.setFixedHeight(row_height)
                thumbnail.image_container.setFixedSize(thumbnail_width - 8, row_height - 8)
                thumbnail.graphics_view.setFixedSize(thumbnail_width - 8, row_height - 8)
                
                # Add to grid
                self.grid.addWidget(thumbnail, row, col)
                thumbnail.show()
                
                # Update image scaling
                if thumbnail.scene and thumbnail.pixmap_item:
                    thumbnail.graphics_view.fitInView(thumbnail.scene.sceneRect(), Qt.KeepAspectRatio)

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
    
    def _load_next_batch(self):
        """Load the next batch of thumbnails."""
        if self.loaded_count >= len(self.all_images):
            return
        
        # Load next batch
        end_idx = min(self.loaded_count + self.LOAD_BATCH_SIZE, len(self.all_images))
        for idx in range(self.loaded_count, end_idx):
            metadata = self.all_images[idx]
            
            # Calculate grid position
            row = idx // self.columns
            col = idx % self.columns
            
            # Create thumbnail
            thumbnail = ImageThumbnail(metadata.id, metadata.original_filename, self)
            
            # Set initial size based on row height if available
            if row in self.row_heights:
                thumbnail.setFixedHeight(self.row_heights[row])
            
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
        thumbnail = self.thumbnails[image_id]
        target_width = thumbnail.width() - 8  # Account for margins
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