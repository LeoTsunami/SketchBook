"""
Image thumbnail widget for displaying individual images in the grid.
"""
import sys
from pathlib import Path
from qtpy.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QWidget,
    QGraphicsView,
    QGraphicsScene
)
from qtpy.QtCore import Qt, Signal, QTimer
from qtpy.QtGui import QPixmap
from core.settings import settings


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
        self.setObjectName("ImageThumbnail")
        self.setFrameStyle(QFrame.NoFrame)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.selected = False
        self.setProperty("selected", False)
        
        # Disable mouse events on thumbnails to let ImageGrid handle all selection
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        
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
        
        # Store original pixmap for resizing
        self.original_pixmap = None
        self.pixmap_item = None
    
    def _apply_theme(self):
        pass  # Désormais géré par le QSS global
    
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
            
            # Ensure proper centering by centering the view on the scene
            self.graphics_view.centerOn(self.pixmap_item)
            
            # Schedule another fit after a short delay to ensure proper scaling
            QTimer.singleShot(50, lambda: self._ensure_proper_centering())
            
        except Exception as e:
            self.set_error(str(e))
    
    def _ensure_proper_centering(self):
        """Ensure the image is properly centered in the view."""
        if not self.scene or not self.pixmap_item:
            return
            
        # Fit the view to show the entire image
        self.graphics_view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        
        # Center the view on the pixmap item
        self.graphics_view.centerOn(self.pixmap_item)
    
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
            # Fit the view to show the entire image
            self.graphics_view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
            
            # Ensure proper centering after resize
            self.graphics_view.centerOn(self.pixmap_item)
    
    def set_selected(self, selected: bool):
        """Set the selection state of the thumbnail."""
        if self.selected != selected:
            self.selected = selected
            self.setProperty("selected", selected)
            self.style().unpolish(self)
            self.style().polish(self)
    
    def _update_style(self):
        pass  # Désormais géré par le QSS global 