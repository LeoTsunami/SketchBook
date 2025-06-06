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
    QScrollBar
)
from qtpy.QtCore import Qt, QSize, Signal, QTimer, QThreadPool, QRect
from qtpy.QtGui import QPixmap, QImage
from core.image_manager import ImageManager
from core.image_db import ImageMetadata
from gui.image_loader_worker import ImageLoaderWorker

class ImageThumbnail(QFrame):
    """Widget representing a single image thumbnail with its label."""
    
    clicked = Signal(str)  # Emits image ID when clicked
    
    def __init__(self, image_id: str, label: str, parent=None):
        """
        Initialize the thumbnail widget.
        
        Args:
            image_id: Unique identifier of the image
            label: Text to display under the image
            parent: Parent widget
        """
        super().__init__(parent)
        self.image_id = image_id
        self.setFrameStyle(QFrame.Panel | QFrame.Raised)
        self.setLineWidth(1)
        
        # Set fixed size for thumbnails
        self.setFixedSize(200, 240)  # Height includes space for label
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Create image container with fixed size
        self.image_container = QWidget()
        self.image_container.setFixedSize(180, 180)
        
        # Create image label with proper size and alignment
        self.image_label = QLabel()
        self.image_label.setMinimumSize(180, 180)
        self.image_label.setMaximumSize(180, 180)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #f8f8f8;
                border: 1px solid #e0e0e0;
                border-radius: 2px;
                color: #999999;
            }
        """)
        
        # Create container layout
        container_layout = QVBoxLayout(self.image_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(self.image_label)
        
        # Set placeholder
        self.image_label.setText("Loading...")
        
        layout.addWidget(self.image_container)
        
        # Create text label
        self.text_label = QLabel(label)
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setWordWrap(True)
        self.text_label.setStyleSheet("""
            QLabel {
                color: #333333;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.text_label)
        
        # Style
        self.setStyleSheet("""
            ImageThumbnail {
                background-color: #ffffff;
                border-radius: 4px;
            }
            ImageThumbnail:hover {
                background-color: #f0f0f0;
            }
        """)
    
    def set_image(self, pixmap: QPixmap):
        """Set the image pixmap."""
        print(f"[DEBUG] Setting image for thumbnail {self.image_id}")
        if not self.image_label:
            print(f"[DEBUG] No image label for thumbnail {self.image_id}")
            return
            
        try:
            # Scale pixmap to fit label while preserving aspect ratio
            scaled_pixmap = pixmap.scaled(
                180, 180,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            print(f"[DEBUG] Scaled pixmap to {scaled_pixmap.width()}x{scaled_pixmap.height()}")
            
            self.image_label.setPixmap(scaled_pixmap)
            self.image_label.setStyleSheet("""
                QLabel {
                    background-color: #f8f8f8;
                    border: 1px solid #e0e0e0;
                    border-radius: 2px;
                }
            """)
            print(f"[DEBUG] Successfully set pixmap for thumbnail {self.image_id}")
        except Exception as e:
            print(f"[DEBUG] Error setting image for thumbnail {self.image_id}: {str(e)}")
            self.set_error(str(e))
    
    def set_error(self, error_msg: str):
        """Show error message."""
        if not self.image_label:
            return
        self.image_label.setText(f"Error: {error_msg}")
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #f8f8f8;
                border: 1px solid #e0e0e0;
                border-radius: 2px;
                color: #ff0000;
            }
        """)
    
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
        
        # Set background color
        self.setStyleSheet("""
            QScrollArea {
                background-color: #f5f5f5;
                border: none;
            }
            QWidget#content {
                background-color: #f5f5f5;
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
        
        # Set up thread pool for image loading
        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(4)  # Limit concurrent image loads
        
        # Set up scroll timer for lazy loading
        self.scroll_timer = QTimer(self)
        self.scroll_timer.setSingleShot(True)
        self.scroll_timer.timeout.connect(self._check_visible_thumbnails)
        
        # Connect scroll bar
        self.verticalScrollBar().valueChanged.connect(self._on_scroll)
    
    def clear(self):
        """Remove all thumbnails from the grid."""
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
    
    def _load_next_batch(self):
        """Load the next batch of thumbnails."""
        if self.loaded_count >= len(self.all_images):
            return
            
        # Calculate grid layout accounting for spacing and margins
        spacing = self.grid.spacing()
        margins = self.grid.contentsMargins()
        available_width = self.width() - margins.left() - margins.right()
        thumbnail_width = 200 + spacing  # Account for spacing between items
        max_cols = max(1, available_width // thumbnail_width)
        
        # Load next batch
        end_idx = min(self.loaded_count + self.LOAD_BATCH_SIZE, len(self.all_images))
        for idx in range(self.loaded_count, end_idx):
            metadata = self.all_images[idx]
            
            # Calculate grid position
            row = idx // max_cols
            col = idx % max_cols
            
            # Create thumbnail
            thumbnail = ImageThumbnail(
                metadata.id,
                metadata.original_filename,
                self
            )
            thumbnail.clicked.connect(self.image_clicked.emit)
            
            # If we have the image in cache, set it immediately
            if metadata.id in self.pixmap_cache:
                thumbnail.set_image(self.pixmap_cache[metadata.id])
            
            self.grid.addWidget(thumbnail, row, col)
            self.thumbnails[metadata.id] = thumbnail
        
        self.loaded_count = end_idx
        
        # Check which thumbnails are visible and load their images
        QTimer.singleShot(50, self._check_visible_thumbnails)
    
    def _on_scroll(self, value):
        """Handle scroll events."""
        # Reset timer on each scroll
        self.scroll_timer.start(100)  # Wait for scrolling to stop
        
        # Check if we need to load more thumbnails
        viewport_bottom = value + self.viewport().height()
        content_bottom = self.content.height()
        
        # If we're near the bottom, load more thumbnails
        if content_bottom - viewport_bottom < 500 and self.loaded_count < len(self.all_images):
            self._load_next_batch()
    
    def _check_visible_thumbnails(self):
        """Check which thumbnails are visible and load their images."""
        viewport_rect = QRect(
            self.horizontalScrollBar().value(),
            self.verticalScrollBar().value(),
            self.viewport().width(),
            self.viewport().height()
        )
        
        # Add some margin to preload images just outside view
        margin = 200
        viewport_rect.adjust(-margin, -margin, margin, margin)
        
        # First, cancel loading of non-visible thumbnails
        for image_id in list(self.loading_images):
            if image_id in self.thumbnails:
                thumbnail = self.thumbnails[image_id]
                if not viewport_rect.intersects(self._get_widget_geometry(thumbnail)):
                    self.loading_images.remove(image_id)
        
        # Then load visible thumbnails
        for image_id, thumbnail in self.thumbnails.items():
            if viewport_rect.intersects(self._get_widget_geometry(thumbnail)):
                self._load_thumbnail_image(image_id)
    
    def _get_widget_geometry(self, widget: QWidget) -> QRect:
        """Get the global geometry of a widget relative to the scroll area."""
        return QRect(
            widget.mapTo(self.content, widget.rect().topLeft()),
            widget.size()
        )
    
    def _load_thumbnail_image(self, image_id: str):
        """Load image for a thumbnail asynchronously."""
        print(f"[DEBUG] Attempting to load thumbnail for image_id: {image_id}")
        
        if image_id not in self.thumbnails:
            print(f"[DEBUG] Image {image_id} not in thumbnails")
            return
            
        if image_id in self.loading_images:
            print(f"[DEBUG] Image {image_id} already loading")
            return
            
        if image_id in self.pixmap_cache:
            print(f"[DEBUG] Image {image_id} found in cache")
            thumbnail = self.thumbnails[image_id]
            thumbnail.set_image(self.pixmap_cache[image_id])
            return
            
        # Find metadata
        metadata = next((m for m in self.all_images if m.id == image_id), None)
        if not metadata:
            print(f"[DEBUG] No metadata found for image {image_id}")
            return
            
        # Mark as loading
        print(f"[DEBUG] Starting to load image {image_id}")
        self.loading_images.add(image_id)
            
        # Create and start worker
        image_path = self.image_manager.image_dir / metadata.path
        print(f"[DEBUG] Image path: {image_path}")
        worker = ImageLoaderWorker(image_id, image_path, (180, 180))
        
        worker.signals.finished.connect(self._on_image_loaded)
        worker.signals.error.connect(self._on_image_error)
        
        print(f"[DEBUG] Starting worker for image {image_id}")
        self.thread_pool.start(worker)
    
    def _on_image_loaded(self, image_id: str, pixmap: QPixmap):
        """Handle loaded image."""
        print(f"[DEBUG] Image loaded callback for {image_id}")
        self.loading_images.discard(image_id)
        
        # Cache the pixmap
        print(f"[DEBUG] Caching pixmap for {image_id}")
        self.pixmap_cache[image_id] = pixmap
        
        # Update thumbnail if it still exists
        if image_id in self.thumbnails:
            print(f"[DEBUG] Updating thumbnail for {image_id}")
            self.thumbnails[image_id].set_image(pixmap)
        else:
            print(f"[DEBUG] No thumbnail found for {image_id}")
    
    def _on_image_error(self, image_id: str, error_msg: str):
        """Handle image loading error."""
        print(f"[DEBUG] Image error for {image_id}: {error_msg}")
        self.loading_images.discard(image_id)
        if image_id in self.thumbnails:
            self.thumbnails[image_id].set_error(error_msg)
    
    def resizeEvent(self, event):
        """Handle resize events to adjust grid layout."""
        super().resizeEvent(event)
        
        # Only reload if we have thumbnails and width changed
        if self.thumbnails and event.size().width() != event.oldSize().width():
            self.load_images(self.current_filter) 