"""
Image thumbnail widget for displaying individual images in the grid.
"""
import sys
from pathlib import Path
from typing import Optional
from qtpy.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QWidget,
    QGraphicsView,
    QGraphicsScene,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QApplication,
    QSizePolicy
)
from qtpy.QtCore import Qt, Signal, QTimer
from qtpy.QtGui import QPixmap, QIcon, QImage, QCursor, QDragEnterEvent, QDropEvent, QFontMetrics
from core.settings import settings


def _find_tag_icon(tag: str) -> QIcon:
    """
    Resolve a tag icon based on the tag name.

    Args:
        tag: Tag name.

    Returns:
        QIcon: Icon for the tag or an empty icon if not found.
    """
    icons_dir = Path(__file__).parent / "ressources" / "icones" / "tags"
    if not icons_dir.exists():
        return QIcon()

    tag_lower = tag.lower()
    file_map = {path.stem.lower(): path for path in icons_dir.glob("*.png")}
    if tag_lower in file_map:
        return QIcon(str(file_map[tag_lower]))

    fallback_map = {
        "hands": "hand",
        "feet": "foot",
        "objects": "object",
    }
    fallback = fallback_map.get(tag_lower)
    if fallback and fallback in file_map:
        return QIcon(str(file_map[fallback]))

    return QIcon()


def _invert_icon(icon: QIcon, size: int = 20) -> QIcon:
    """
    Invert icon colors for better visibility.

    Args:
        icon: Original icon.
        size: Icon size.

    Returns:
        QIcon: Inverted icon.
    """
    if icon.isNull():
        return icon
    pixmap = icon.pixmap(size, size)
    image = pixmap.toImage()
    image.invertPixels(QImage.InvertRgb)
    return QIcon(QPixmap.fromImage(image))


class TagChip(QFrame):
    """Widget representing a single tag chip for thumbnail display."""
    
    removed = Signal(str)  # Emits tag text when removed
    
    def __init__(self, text: str, parent=None):
        """
        Initialize the tag chip.

        Args:
            text: Tag text to display
            parent: Parent widget
        """
        super().__init__(parent)
        self.text = text
        self.setObjectName("TagChip")
        # CRITICAL: Force enable mouse events - override parent's transparent setting
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        
        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 3, 5, 3)
        layout.setSpacing(6)

        app_font = QApplication.instance().font() if QApplication.instance() else self.font()
        # Use larger font for tags
        larger_font = app_font
        larger_font.setPointSize(max(9, app_font.pointSize() + 1))
        self.setFont(larger_font)

        # Add icon (if available) - preserve visibility with minimum size
        icon = _find_tag_icon(text)
        self.has_icon = not icon.isNull()
        if self.has_icon:
            icon_label = QLabel()
            # Use 20x20 pixmap, allow slight reduction if space is very limited
            icon_label.setPixmap(_invert_icon(icon, 20).pixmap(20, 20))
            icon_label.setStyleSheet("background-color: transparent;")
            icon_label.setMinimumSize(16, 16)  # Minimum size to keep icon visible
            icon_label.setMaximumSize(20, 20)  # Maximum size
            icon_label.setScaledContents(True)  # Allow pixmap to scale down if needed
            layout.addWidget(icon_label)

        # Add text label - allow it to shrink and elide when space is limited
        self.text_label = QLabel(text)
        self.text_label.setStyleSheet("color: #ffffff; font-size: 11px;")
        self.text_label.setFont(larger_font)
        # Allow text to shrink and elide (crop) when space is limited
        self.text_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.text_label.setMinimumWidth(0)  # Allow label to shrink to minimum
        layout.addWidget(self.text_label, 1)  # Give text label stretch factor to take available space

        # Add remove button - fixed size to preserve visibility
        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(18, 18)  # Fixed size - always visible
        remove_btn.setFont(larger_font)
        remove_btn.setStyleSheet("color: #ffffff; background: transparent; border: none; font-weight: bold; font-size: 14px;")
        remove_btn.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        remove_btn.setCursor(QCursor(Qt.PointingHandCursor))
        remove_btn.setFocusPolicy(Qt.StrongFocus)  # Ensure button can receive focus
        remove_btn.setObjectName(f"RemoveButton_{text}")
        
        remove_btn.clicked.connect(lambda: self.removed.emit(text))
        
        layout.addWidget(remove_btn)
        
        # Update elided text after layout is calculated
        QTimer.singleShot(0, self._update_elided_text)
    
    def resizeEvent(self, event):
        """Update elided text when chip is resized."""
        super().resizeEvent(event)
        self._update_elided_text()
    
    def _update_elided_text(self):
        """Update the text label with elided text based on available width."""
        if not hasattr(self, 'text_label') or not self.text_label:
            return
        
        # Calculate available width for text label
        # Account for margins, spacing, icon, and remove button
        margins = self.layout().contentsMargins()
        spacing = self.layout().spacing()
        
        # Estimate space taken by icon (if present) and remove button
        icon_width = 20 if hasattr(self, 'has_icon') and self.has_icon else 0
        remove_btn_width = 18
        available_width = self.width() - margins.left() - margins.right() - icon_width - remove_btn_width - (spacing * 2)
        
        if available_width <= 0:
            self.text_label.setText("")
            return
        
        # Use QFontMetrics to calculate elided text
        font_metrics = QFontMetrics(self.text_label.font())
        elided_text = font_metrics.elidedText(self.text, Qt.ElideRight, available_width)
        self.text_label.setText(elided_text)


class ImageThumbnail(QFrame):
    """Widget representing a single image thumbnail."""
    
    clicked = Signal(str)  # Emits image ID when clicked
    tag_removed = Signal(str, str)  # Emits (image_id, tag) when a tag is removed
    
    def __init__(self, image_id: str, label: str, parent=None, image_manager=None, remove_tag_callback=None, get_selected_images_callback=None):
        """
        Initialize the thumbnail widget.
        
        Args:
            image_id: Unique identifier of the image
            label: Text to display under the image (not used anymore)
            parent: Parent widget
            image_manager: ImageManager instance for accessing tags
            remove_tag_callback: Optional callback function(tag: str) to remove tag from selected images
            get_selected_images_callback: Optional callback function() -> Set[str] to get selected image IDs
        """
        super().__init__(parent)
        self.image_id = image_id
        self.image_manager = image_manager
        self.remove_tag_callback = remove_tag_callback
        self.get_selected_images_callback = get_selected_images_callback
        self.setObjectName("ImageThumbnail")
        self.setFrameStyle(QFrame.NoFrame)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.selected = False
        self.setProperty("selected", False)
        
        # Enable drag and drop for tags
        self.setAcceptDrops(True)
        
        # Don't disable mouse events on the entire thumbnail - only on image parts
        # We'll handle clicks manually to distinguish image clicks from tag clicks
        # self.setAttribute(Qt.WA_TransparentForMouseEvents, True)  # REMOVED - causes issues with tag clicks
        
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
        # Make graphics view transparent to mouse events so ImageGrid can handle selection
        self.graphics_view.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(Qt.transparent)
        self.graphics_view.setScene(self.scene)
        
        # Create image container that maintains aspect ratio
        self.image_container = QWidget()
        self.image_container.setMinimumHeight(100)  # Minimum height to prevent collapse
        self.image_container.setStyleSheet("background: transparent;")
        # Make image container transparent to mouse events so ImageGrid can handle selection
        self.image_container.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        
        # Create container layout
        container_layout = QVBoxLayout(self.image_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(self.graphics_view)
        
        layout.addWidget(self.image_container, 1)  # Give image container stretch factor
        
        # Create tags container (initially hidden)
        self.tags_container = QWidget()
        self.tags_container.setObjectName("TagsContainer")
        # CRITICAL: Force enable mouse events - set True then False to override parent
        self.tags_container.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.tags_container.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.tags_container.hide()  # Hidden by default
        self.tags_layout = QGridLayout(self.tags_container)
        self.tags_layout.setContentsMargins(2, 2, 2, 2)
        self.tags_layout.setSpacing(4)
        self.tags_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        
        layout.addWidget(self.tags_container)
        
        # Store original pixmap for resizing
        self.original_pixmap = None
        self.pixmap_item = None
        self.tag_chips = {}  # Store tag chips by tag name
    
    def _apply_theme(self):
        pass  # Désormais géré par le QSS global
    
    def set_image(self, pixmap: QPixmap):
        """Set the image pixmap."""
        if not self.scene:
            return
            
        try:
            # Store original pixmap (the pixmap is already scaled to correct size by worker)
            self.original_pixmap = pixmap
            
            # Clear previous pixmap item
            if self.pixmap_item:
                self.scene.removeItem(self.pixmap_item)
            
            # Use the pixmap directly - it's already scaled to the correct size by ImageLoaderWorker
            # No need to resize again, which would cause pixelation
            self.pixmap_item = self.scene.addPixmap(pixmap)
            
            # Set scene rect to match pixmap size
            self.scene.setSceneRect(self.pixmap_item.boundingRect())
            
            # Center the view
            self.graphics_view.setAlignment(Qt.AlignCenter)
            
            # Center the view on the pixmap item (no fitInView to avoid pixelation)
            self.graphics_view.centerOn(self.pixmap_item)
            
            # Reset transform to ensure no scaling artifacts
            self.graphics_view.resetTransform()
            
        except Exception as e:
            self.set_error(str(e))
    
    def _ensure_proper_centering(self):
        """Ensure the image is properly centered in the view."""
        if not self.scene or not self.pixmap_item:
            return
        
        # Just center the view - no need to rescale as pixmap is already correct size
        self.graphics_view.centerOn(self.pixmap_item)
        self.graphics_view.resetTransform()
    
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
    
    def eventFilter(self, obj, event):
        """Filter events to ensure tag chips can receive mouse events."""
        # Let tag chips and their children handle their own events
        if isinstance(obj, TagChip) or obj.parent() == self.tags_container:
            return False  # Don't filter, let the widget handle it
        return super().eventFilter(obj, event)
    
    def mousePressEvent(self, event):
        """Handle mouse press events - forward to ImageGrid if not on tags."""
        # Check if click is on tags container or any tag chip
        click_pos = event.pos()

        if self.tags_container.isVisible():
            tags_rect = self.tags_container.geometry()
            if tags_rect.contains(click_pos):
                # Click is on tags area - let child widgets handle it
                super().mousePressEvent(event)
                return

        # Click is not on tags - let parent (ImageGrid) handle selection
        event.ignore()  # Let the event propagate
    
    def resizeEvent(self, event):
        """Handle resize events to adjust image scaling and re-layout tags."""
        super().resizeEvent(event)
        
        # Just center the view - the image will be reloaded at new size if needed
        if self.scene and self.pixmap_item:
            self.graphics_view.centerOn(self.pixmap_item)
            self.graphics_view.resetTransform()
        
        # Re-layout tags if thumbnail size changed
        if self.tag_chips:
            self._relayout_tags()
    
    def set_selected(self, selected: bool):
        """Set the selection state of the thumbnail (border only)."""
        if self.selected != selected:
            self.selected = selected
            self.setProperty("selected", selected)
            self.style().unpolish(self)
            self.style().polish(self)

    def set_tags_visible(self, visible: bool) -> None:
        """
        Control whether tags are visible for this thumbnail.

        Tags are now decoupled from simple selection: only the 'active'
        image (gérée par ImageGrid) doit afficher ses tags pour éviter
        de surcharger l'UI quand beaucoup d'images sont sélectionnées.
        """
        if visible:
            self._load_and_display_tags()
        else:
            self._hide_tags()

    def refresh_tags(self):
        """Refresh tags display (used after external tag updates)."""
        # Tags ne sont rafraîchis que si le conteneur est visible
        if self.tags_container.isVisible():
            self._load_and_display_tags()
    
    def _load_and_display_tags(self):
        """Load and display tags for this image."""
        if not self.image_manager:
            return
        
        # Get image metadata
        metadata = self.image_manager.get_image_metadata(self.image_id)
        if not metadata:
            return
        
        # Clear existing tags
        self._clear_tags()
        
        # Add tags
        for tag in sorted(metadata.tags):
            self._add_tag_chip(tag)
        
        # Show tags container if there are tags
        if self.tag_chips:
            self.tags_container.show()
            self.tags_container.raise_()  # Ensure tags container is on top
            # Ensure all chips are on top
            for chip in self.tag_chips.values():
                chip.raise_()
        else:
            self.tags_container.hide()
    
    def _hide_tags(self):
        """Hide the tags container."""
        self.tags_container.hide()
    
    def _clear_tags(self):
        """Clear all tag chips."""
        for chip in self.tag_chips.values():
            chip.deleteLater()
        self.tag_chips.clear()
    
    def _relayout_tags(self):
        """Re-layout all tag chips in the grid."""
        # Remove all chips from layout
        while self.tags_layout.count():
            item = self.tags_layout.takeAt(0)
            if item.widget():
                self.tags_layout.removeWidget(item.widget())
        
        # Re-add all chips with proper positions
        # Calculate max chips per row based on available width
        # Each chip is roughly 80-100px wide now (larger), account for margins and spacing
        available_width = max(self.width() - 20, 100)  # Account for margins
        max_per_row = max(2, available_width // 90)  # Estimate based on available width (larger chips)
        for idx, (tag, chip) in enumerate(sorted(self.tag_chips.items())):
            row = idx // max_per_row
            col = idx % max_per_row
            self.tags_layout.addWidget(chip, row, col)
    
    def _enable_mouse_events_recursive(self, widget: QWidget):
        """Recursively enable mouse events on widget and all its children."""
        # Force disable by setting True then False
        widget.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        widget.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        for child in widget.findChildren(QWidget):
            child.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            child.setAttribute(Qt.WA_TransparentForMouseEvents, False)
    
    def _add_tag_chip(self, tag: str):
        """Add a tag chip to the tags container."""
        if tag in self.tag_chips:
            return
        
        chip = TagChip(tag, self.tags_container)
        chip.removed.connect(self._on_tag_removed)
        # Enable mouse events on chip and all its children recursively
        self._enable_mouse_events_recursive(chip)
        chip.raise_()  # Ensure chip is on top
        
        # Calculate position in grid (wrap automatically)
        num_chips = len(self.tag_chips)
        # Estimate max chips per row based on thumbnail width
        # Each chip is roughly 80-100px wide now (larger), so we can fit about 2-3 per row for typical thumbnails
        # We'll use a simple calculation: row = num_chips // max_per_row, col = num_chips % max_per_row
        available_width = max(self.width() - 20, 100)  # Account for margins
        max_per_row = max(2, available_width // 90)  # Estimate based on available width (larger chips)
        row = num_chips // max_per_row
        col = num_chips % max_per_row
        
        self.tags_layout.addWidget(chip, row, col)
        self.tag_chips[tag] = chip
        
        # CRITICAL: Force disable WA_TransparentForMouseEvents AFTER adding to layout
        # We need to do this multiple times and ensure it's really disabled
        self.tags_container.setAttribute(Qt.WA_TransparentForMouseEvents, True)  # Set to True first
        self.tags_container.setAttribute(Qt.WA_TransparentForMouseEvents, False)  # Then False to force update
        chip.setAttribute(Qt.WA_TransparentForMouseEvents, True)  # Set to True first
        chip.setAttribute(Qt.WA_TransparentForMouseEvents, False)  # Then False to force update
        
        # Enable mouse events on all children recursively
        self._enable_mouse_events_recursive(chip)
        
        self.tags_container.raise_()
        chip.raise_()
        
        # Install event filter to ensure mouse events reach chips
        chip.installEventFilter(self)
        for child in chip.findChildren(QWidget):
            child.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            child.installEventFilter(self)
        
        # Debug info removed
    
    def _on_tag_removed(self, tag: str):
        """Handle tag removal from chip."""
        if not self.image_manager:
            return
        
        # If callback is provided, use it to remove tag from all selected images
        if self.remove_tag_callback:
            self.remove_tag_callback(tag)
            return
        
        # Otherwise, remove tag only from this image (fallback behavior)
        # Get current tags
        metadata = self.image_manager.get_image_metadata(self.image_id)
        if not metadata:
            return
        
        # Remove tag from set
        new_tags = metadata.tags.copy()
        new_tags.discard(tag)
        
        # Update metadata
        self.image_manager.update_image_metadata(self.image_id, tags=new_tags)
        
        # Remove chip from UI and re-layout remaining chips
        if tag in self.tag_chips:
            chip = self.tag_chips.pop(tag)
            chip.deleteLater()
            # Re-layout remaining chips
            self._relayout_tags()
        
        # Hide tags container if no tags left
        if not self.tag_chips:
            self.tags_container.hide()
        
        # Emit signal for parent to handle if needed
        self.tag_removed.emit(self.image_id, tag)

    def _update_style(self):
        pass  # Désormais géré par le QSS global

    def enterEvent(self, event):
        """When mouse enters, ask parent grid to show this image's tags."""
        parent = self.parent()
        while parent:
            if hasattr(parent, "set_active_image"):
                parent.set_active_image(self.image_id)
                break
            parent = parent.parent()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """When mouse leaves, let grid decide if tags should change."""
        # On ne force pas ici la désactivation des tags pour éviter les
        # effets de flicker si d'autres logiques décident de l'image active.
        super().leaveEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event for tag drops."""
        if event.mimeData().hasText():
            # Check if it's a tag being dragged (from tag library)
            tag_text = event.mimeData().text()
            # Accept if it looks like a tag (not empty, reasonable length)
            if tag_text and len(tag_text.strip()) > 0:
                event.acceptProposedAction()
                # Add visual feedback
                self.setProperty("dragOver", True)
                self.style().unpolish(self)
                self.style().polish(self)
            else:
                event.ignore()
        else:
            event.ignore()
    
    def dragLeaveEvent(self, event):
        """Handle drag leave event."""
        # Remove visual feedback
        self.setProperty("dragOver", False)
        self.style().unpolish(self)
        self.style().polish(self)
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop event for tag drops."""
        if not event.mimeData().hasText():
            event.ignore()
            return

        tag_text = event.mimeData().text().strip()
        if not tag_text:
            event.ignore()
            return

        # Get selected images
        selected_images = set()
        if self.get_selected_images_callback:
            selected_images = self.get_selected_images_callback()

        # Determine which images to tag
        images_to_tag: list[str] = []

        if not selected_images:
            # No selection: tag only the image where we dropped
            images_to_tag = [self.image_id]
        elif len(selected_images) > 1 and self.image_id in selected_images:
            # Multiple images selected and drop on one of them: tag all selected
            images_to_tag = list(selected_images)
        elif len(selected_images) == 1 and self.image_id in selected_images:
            # Single image selected and drop on it: tag only that image
            images_to_tag = [self.image_id]
        else:
            # Drop on non-selected image while others are selected: tag only the dropped image
            images_to_tag = [self.image_id]

        # Delegate heavy work to MainWindow via async worker
        parent = self.parent()
        while parent:
            # MainWindow has apply_tag_to_images_async
            if hasattr(parent, "apply_tag_to_images_async"):
                parent.apply_tag_to_images_async(tag_text, images_to_tag)
                break
            parent = parent.parent()

        # Remove visual feedback
        self.setProperty("dragOver", False)
        self.style().unpolish(self)
        self.style().polish(self)

        event.acceptProposedAction()