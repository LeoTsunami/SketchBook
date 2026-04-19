"""
Image thumbnail widget for displaying individual images in the grid.
"""

import sys
from pathlib import Path
from typing import Callable, List, Optional, Set
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
    QSizePolicy,
    QGraphicsDropShadowEffect,
    QGraphicsColorizeEffect,
)
from qtpy.QtCore import Qt, Signal, QTimer, QUrl, QEvent
from qtpy.QtGui import (
    QPainter,
    QPixmap,
    QIcon,
    QImage,
    QCursor,
    QDragEnterEvent,
    QDropEvent,
    QFontMetrics,
    QFont,
    QColor,
)
from core.settings import settings
from gui.icon_utils import find_tag_icon, invert_icon
from gui.thumbnail_fitting import FitMode, fit_pixmap_in_view


class TagChip(QFrame):
    """Widget representing a single tag chip for thumbnail display."""

    removed = Signal(str)  # Emits tag text when removed

    def __init__(self, text: str, parent=None, elide: bool = True):
        """
        Initialize the tag chip.

        Args:
            text: Tag text to display
            parent: Parent widget
            elide: If True, elide text when space is limited; if False, show full text (e.g. in popover).
        """
        super().__init__(parent)
        self.text = text
        self._elide = elide
        self.setObjectName("TagChip")
        # CRITICAL: Force enable mouse events - override parent's transparent setting
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)

        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 3, 5, 3)
        layout.setSpacing(6)

        app_font = (
            QApplication.instance().font() if QApplication.instance() else self.font()
        )
        # Reason: QApplication font may have pointSize() == -1 on some systems; copy and clamp.
        larger_font = QFont(app_font)
        base_point_size = app_font.pointSize()
        if base_point_size <= 0:
            base_point_size = 10
        larger_font.setPointSize(max(9, base_point_size + 1))
        self.setFont(larger_font)

        # Add icon (if available) - preserve visibility with minimum size
        icon = find_tag_icon(text)
        self.has_icon = not icon.isNull()
        if self.has_icon:
            icon_label = QLabel()
            # Use 20x20 pixmap, allow slight reduction if space is very limited
            icon_label.setPixmap(invert_icon(icon, 20).pixmap(20, 20))
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
        layout.addWidget(
            self.text_label, 1
        )  # Give text label stretch factor to take available space

        # Add remove button - fixed size to preserve visibility
        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(18, 18)  # Fixed size - always visible
        remove_btn.setFont(larger_font)
        remove_btn.setStyleSheet(
            "color: #ffffff; background: transparent; border: none; font-weight: bold; font-size: 14px;"
        )
        remove_btn.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        remove_btn.setCursor(QCursor(Qt.PointingHandCursor))
        remove_btn.setFocusPolicy(Qt.StrongFocus)  # Ensure button can receive focus
        remove_btn.setObjectName(f"RemoveButton_{text}")

        remove_btn.clicked.connect(lambda: self.removed.emit(text))

        layout.addWidget(remove_btn)

        if not self._elide:
            self.text_label.setText(text)
        else:
            QTimer.singleShot(0, self._update_elided_text)

    def resizeEvent(self, event):
        """Update elided text when chip is resized (only if elide is enabled)."""
        super().resizeEvent(event)
        if self._elide:
            self._update_elided_text()

    def _update_elided_text(self):
        """Update the text label with elided text based on available width."""
        if not self._elide or not hasattr(self, "text_label") or not self.text_label:
            return

        # Calculate available width for text label
        # Account for margins, spacing, icon, and remove button
        margins = self.layout().contentsMargins()
        spacing = self.layout().spacing()

        # Estimate space taken by icon (if present) and remove button
        icon_width = 20 if hasattr(self, "has_icon") and self.has_icon else 0
        remove_btn_width = 18
        available_width = (
            self.width()
            - margins.left()
            - margins.right()
            - icon_width
            - remove_btn_width
            - (spacing * 2)
        )

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

    def __init__(
        self,
        image_id: str,
        label: str,
        parent=None,
        image_manager=None,
        remove_tag_callback=None,
        get_selected_images_callback=None,
        show_tag_popover_callback: Optional[
            Callable[["ImageThumbnail", str, Set[str]], None]
        ] = None,
        import_drop_callback: Optional[Callable[[List[QUrl]], None]] = None,
    ):
        """
        Initialize the thumbnail widget.

        Args:
            image_id: Unique identifier of the image
            label: Text to display under the image (not used anymore)
            parent: Parent widget
            image_manager: ImageManager instance for accessing tags
            remove_tag_callback: Optional callback function(tag: str) to remove tag from selected images
            get_selected_images_callback: Optional callback function() -> Set[str] to get selected image IDs
            show_tag_popover_callback: If set, tags are shown in a floating popover below the thumbnail
                instead of on the image. Called with (thumbnail_widget, image_id, tags).
            import_drop_callback: If set, file/folder drops (hasUrls) are forwarded here instead of
                being treated as tags. Called with (list of QUrl); grid/main window handles import.
        """
        super().__init__(parent)
        self.image_id = image_id
        self.image_manager = image_manager
        self.remove_tag_callback = remove_tag_callback
        self.get_selected_images_callback = get_selected_images_callback
        self.show_tag_popover_callback = show_tag_popover_callback
        self.import_drop_callback = import_drop_callback
        self.setObjectName("ImageThumbnail")
        self.setFrameStyle(QFrame.NoFrame)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.selected = False
        self._hovered = False
        self.setProperty("selected", False)
        self.setProperty("hovered", False)

        # Enable drag and drop for tags
        self.setAcceptDrops(True)

        # Don't disable mouse events on the entire thumbnail - only on image parts
        # We'll handle clicks manually to distinguish image clicks from tag clicks
        # self.setAttribute(Qt.WA_TransparentForMouseEvents, True)  # REMOVED - causes issues with tag clicks

        # Create layout — no inner margins so the image meets the card border.
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)  # Reduced spacing since we don't have labels anymore

        # Create graphics view for better image rendering
        self.graphics_view = QGraphicsView()
        # Reason: Default QGraphicsView frame adds viewport inset; thumbnails looked
        # off-center and letterboxed until hover; match image_viewer / slideshow.
        self.graphics_view.setFrameShape(QFrame.NoFrame)
        self.graphics_view.setStyleSheet("""
            QGraphicsView {
                background: transparent;
                border: none;
            }
        """)
        self.graphics_view.setRenderHint(QPainter.Antialiasing, True)
        self.graphics_view.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # Reason: FullViewportUpdate ensures the whole viewport repaints when the
        # transform changes; required so stacked QGraphicsEffects (shadow + hover
        # colorize) see a fresh source snapshot after each fit_pixmap_in_view call.
        self.graphics_view.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
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

        # Wrapper so hover colorize is not applied to QGraphicsView itself — Qt
        # graphics effects on QGraphicsView can shift painted content vs. hover.
        self._hover_fx_wrapper = QWidget()
        self._hover_fx_wrapper.setStyleSheet("background: transparent;")
        self._hover_fx_wrapper.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        _hover_wrap_layout = QVBoxLayout(self._hover_fx_wrapper)
        _hover_wrap_layout.setContentsMargins(0, 0, 0, 0)
        _hover_wrap_layout.setSpacing(0)
        _hover_wrap_layout.addWidget(self.graphics_view)

        # Create container layout
        container_layout = QVBoxLayout(self.image_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(self._hover_fx_wrapper)

        # Subtle depth on transparent thumbnails.
        self._shadow_effect = QGraphicsDropShadowEffect(self)
        self._shadow_effect.setBlurRadius(12)
        self._shadow_effect.setOffset(0, 2)
        self._shadow_effect.setColor(QColor(0, 0, 0, 85))
        self.image_container.setGraphicsEffect(None)

        # Hover brightening (white tint at low strength).
        # Reason: the effect MUST start disabled; an active QGraphicsColorizeEffect
        # (even at strength 0) caches the widget sub-tree rendering.  Inside a
        # QScrollArea the cached pixmap is never invalidated by scroll, so every
        # previously-hovered thumbnail's image appears frozen in place.
        self._hover_effect = QGraphicsColorizeEffect(self)
        self._hover_effect.setColor(QColor(255, 255, 255))
        self._hover_effect.setStrength(0.0)
        self._hover_effect.setEnabled(False)
        self._hover_fx_wrapper.setGraphicsEffect(self._hover_effect)

        # Selection outline overlay (drawn above the image content).
        self.selection_overlay = QWidget(self.image_container)
        self.selection_overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.selection_overlay.setStyleSheet(
            "background: transparent; border: 3px solid #5d9dff; border-radius: 6px;"
        )
        self.selection_overlay.hide()

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
        self._fit_mode: FitMode = FitMode.CROP_ALL
        # Reason: set directly by ImageGrid during interactive resize to avoid
        # expensive parent-chain walk (_ancestor_grid_resize_interactive) on every resizeEvent.
        self._fast_resize_active: bool = False
        self._debug_thumb_position = False

        # Reason: must run when the viewport *widget* inside the QGraphicsView
        # actually resizes — not just when the ImageThumbnail frame resizes,
        # which may fire before the viewport has its final geometry.
        # Installed last so all other attributes already exist when the filter fires.
        self.graphics_view.viewport().installEventFilter(self)

    def _debug_position(self, stage: str) -> None:
        """Emit detailed geometry diagnostics for thumbnail/image alignment."""
        if not self._debug_thumb_position or not self.graphics_view:
            return
        if not self.pixmap_item:
            print(
                f"[thumb_debug] id={self.image_id} stage={stage} no_pixmap",
                flush=True,
            )
            return
        try:
            thumb_rect = self.rect()
            container_rect = self.image_container.rect()
            view_rect = self.graphics_view.rect()
            viewport_rect = self.graphics_view.viewport().rect()
            scene_rect = self.scene.sceneRect()
            mapped_center = self.graphics_view.mapFromScene(scene_rect.center())
            viewport_center = viewport_rect.center()
            print(
                (
                    "[thumb_debug] "
                    f"id={self.image_id} stage={stage} "
                    f"thumb={thumb_rect.width()}x{thumb_rect.height()} "
                    f"container={container_rect.width()}x{container_rect.height()} "
                    f"view={view_rect.width()}x{view_rect.height()} "
                    f"viewport={viewport_rect.width()}x{viewport_rect.height()} "
                    f"scene={scene_rect.width():.1f}x{scene_rect.height():.1f} "
                    f"center_delta=({mapped_center.x() - viewport_center.x()},"
                    f"{mapped_center.y() - viewport_center.y()}) "
                    f"transform=(m11={self.graphics_view.transform().m11():.4f},"
                    f"m22={self.graphics_view.transform().m22():.4f})"
                ),
                flush=True,
            )
        except RuntimeError:
            return

    def set_fit_mode(self, mode: FitMode) -> None:
        """
        Change the image display strategy and re-fit immediately.

        Args:
            mode: New display mode.
        """
        if self._fit_mode == mode:
            return
        self._fit_mode = mode
        fit_pixmap_in_view(self.graphics_view, self.scene, self.pixmap_item, mode)

    def _apply_theme(self):
        pass  # Désormais géré par le QSS global

    def set_image(self, pixmap: QPixmap):
        """
        Set the image pixmap and fit it inside the view.

        Args:
            pixmap: The QPixmap to display.
        """
        if not self.scene:
            return

        try:
            self.original_pixmap = pixmap

            if self.pixmap_item:
                self.scene.removeItem(self.pixmap_item)

            self.pixmap_item = self.scene.addPixmap(pixmap)
            self.graphics_view.setAlignment(Qt.AlignCenter)
            self.pixmap_item.setTransformationMode(Qt.SmoothTransformation)
            fit_pixmap_in_view(
                self.graphics_view, self.scene, self.pixmap_item, self._fit_mode
            )
            self._debug_position("set_image_after_fit")

        except Exception as e:
            self.set_error(str(e))

    def _ensure_proper_centering(self):
        """Re-fit the image after any geometry change."""
        fit_pixmap_in_view(
            self.graphics_view, self.scene, self.pixmap_item, self._fit_mode
        )

    def _apply_high_quality_resize(self):
        """Re-fit image in view (kept for backward compatibility)."""
        fit_pixmap_in_view(
            self.graphics_view, self.scene, self.pixmap_item, self._fit_mode
        )

    def _ancestor_grid_resize_interactive(self) -> bool:
        """
        True when an ancestor ImageGrid is applying a coarse (interactive) window resize.

        Returns:
            bool: Whether to prefer fast pixmap scaling for fluid resize.
        """
        w = self.parentWidget()
        depth = 0
        while w is not None and depth < 12:
            if getattr(w, "_resize_interactive", False):
                return True
            w = w.parentWidget()
            depth += 1
        return False

    def apply_full_quality_fit(self) -> None:
        """
        Restore smooth scaling and re-fit after interactive window resize ends.

        Call from ImageGrid when the debounced resize-finalize timer fires.
        """
        if self.pixmap_item:
            self.pixmap_item.setTransformationMode(Qt.SmoothTransformation)
        self.graphics_view.setRenderHint(QPainter.SmoothPixmapTransform, True)
        fit_pixmap_in_view(
            self.graphics_view, self.scene, self.pixmap_item, self._fit_mode
        )
        # Reason: stacked QGraphicsEffects may cache the old render; forcing an
        # update on the outermost effect container ensures the new transform is shown.
        self.image_container.update()
        if self.tag_chips:
            self._relayout_tags()

    def clear_pixmap(self) -> None:
        """Clear the displayed image (e.g. before reloading after rotate)."""
        if self.scene:
            self.scene.clear()
        self.original_pixmap = None
        self.pixmap_item = None

    def assign_metadata(self, metadata) -> None:
        """
        Reassign this thumbnail to display another image (for virtualized grid reuse).

        Args:
            metadata: New image metadata (ImageMetadata) to display.
        """
        self.image_id = metadata.id
        self.clear_pixmap()
        self.set_tags_visible(False)
        self._clear_tags()

    def set_error(self, error_msg: str):
        """Show error message."""
        if not self.scene:
            return
        # Clear scene
        self.scene.clear()
        self.original_pixmap = None
        self.pixmap_item = None
        # Add error text
        self.scene.addText(f"Error: {error_msg}")

    def eventFilter(self, obj, event):
        """Filter events: re-fit on viewport resize; pass-through for tag chips."""
        try:
            if obj is self.graphics_view.viewport() and event.type() == QEvent.Resize:
                if self.pixmap_item:
                    fast = self._fast_resize_active
                    if fast:
                        self.pixmap_item.setTransformationMode(Qt.FastTransformation)
                    fit_pixmap_in_view(
                        self.graphics_view,
                        self.scene,
                        self.pixmap_item,
                        self._fit_mode,
                    )
                    self._debug_position("viewport_resize_after_fit")
                return False
        except (RuntimeError, AttributeError):
            # Reason: during teardown C++ objects may be deleted before Python wrappers.
            return False
        if hasattr(self, "tags_container") and (
            isinstance(obj, TagChip) or obj.parent() == self.tags_container
        ):
            return False
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
        """Handle resize events: re-layout tags (image re-fit is handled by viewport event filter)."""
        super().resizeEvent(event)
        # Keep overlay synced and above image content.
        self.selection_overlay.setGeometry(self.image_container.rect())
        self.selection_overlay.raise_()
        if self.tag_chips and not self._fast_resize_active:
            self._relayout_tags()

    def set_selected(self, selected: bool):
        """Set the selection state of the thumbnail (border only)."""
        if self.selected != selected:
            self.selected = selected
            self.setProperty("selected", selected)
            self.style().unpolish(self)
            self.style().polish(self)
            if selected:
                self.selection_overlay.setStyleSheet(
                    "background: transparent; border: 3px solid #5d9dff; border-radius: 6px;"
                )
                self.selection_overlay.setGeometry(self.image_container.rect())
                self.selection_overlay.show()
                self.selection_overlay.raise_()
            else:
                self.selection_overlay.hide()

    def _set_hovered(self, hovered: bool) -> None:
        """Update hovered visual state (brightness + subtle border accent)."""
        if self._hovered == hovered:
            return
        self._hovered = hovered
        self.setProperty("hovered", hovered)
        # Reason: enable the effect only while hovered; disabling it when idle
        # avoids the stale-cache scroll bug (see __init__ comment).
        if hovered:
            self._hover_effect.setStrength(0.10)
            self._hover_effect.setEnabled(True)
        else:
            self._hover_effect.setEnabled(False)
            self._hover_effect.setStrength(0.0)
        if self.selected:
            border_color = "#8ab9ff" if hovered else "#5d9dff"
            self.selection_overlay.setStyleSheet(
                f"background: transparent; border: 3px solid {border_color}; border-radius: 6px;"
            )
            self.selection_overlay.raise_()
        self.style().unpolish(self)
        self.style().polish(self)
        self._debug_position("hover_on" if hovered else "hover_off")

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
        if self.image_manager:
            self._load_and_display_tags()

    def _load_and_display_tags(self):
        """Load and display tags for this image (on-image container or floating popover)."""
        if not self.image_manager:
            return

        metadata = self.image_manager.get_image_metadata(self.image_id)
        if not metadata:
            return

        tags = metadata.tags
        if not tags:
            if self.show_tag_popover_callback:
                return  # Popover will be hidden by grid
            self._clear_tags()
            self.tags_container.hide()
            return

        # If popover callback is set, show tags in floating popover below thumbnail (full text)
        if self.show_tag_popover_callback:
            self.show_tag_popover_callback(self, self.image_id, tags)
            return

        # Otherwise show tags on the image (elided)
        self._clear_tags()
        for tag in sorted(tags):
            self._add_tag_chip(tag)
        self.tags_container.show()
        self.tags_container.raise_()
        for chip in self.tag_chips.values():
            chip.raise_()

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
        max_per_row = max(
            2, available_width // 90
        )  # Estimate based on available width (larger chips)
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
        max_per_row = max(
            2, available_width // 90
        )  # Estimate based on available width (larger chips)
        row = num_chips // max_per_row
        col = num_chips % max_per_row

        self.tags_layout.addWidget(chip, row, col)
        self.tag_chips[tag] = chip

        # CRITICAL: Force disable WA_TransparentForMouseEvents AFTER adding to layout
        # We need to do this multiple times and ensure it's really disabled
        self.tags_container.setAttribute(
            Qt.WA_TransparentForMouseEvents, True
        )  # Set to True first
        self.tags_container.setAttribute(
            Qt.WA_TransparentForMouseEvents, False
        )  # Then False to force update
        chip.setAttribute(Qt.WA_TransparentForMouseEvents, True)  # Set to True first
        chip.setAttribute(
            Qt.WA_TransparentForMouseEvents, False
        )  # Then False to force update

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
        self._set_hovered(True)
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
        self._set_hovered(False)
        super().leaveEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Accept tag drops (from library) or file/folder drops (forwarded to grid for import)."""
        md = event.mimeData()
        # File/folder drag from OS: hasUrls(); we accept and will forward to import callback
        if md.hasUrls():
            event.acceptProposedAction()
            self.setProperty("dragOver", True)
            self.style().unpolish(self)
            self.style().polish(self)
            return
        # Tag drag from library: hasText() or multi-tag MIME (no URLs)
        if md.hasFormat("application/x-sketchbook-tag-library-multi") or (
            md.hasText() and md.text().strip()
        ):
            event.acceptProposedAction()
            self.setProperty("dragOver", True)
            self.style().unpolish(self)
            self.style().polish(self)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """Handle drag leave event."""
        self.setProperty("dragOver", False)
        self.style().unpolish(self)
        self.style().polish(self)

    def dropEvent(self, event: QDropEvent):
        """Route drop: files/urls -> import callback; text only -> tag the image(s)."""
        md = event.mimeData()

        # File/folder drop: forward to grid/main window for import (do not add paths as tags)
        if md.hasUrls():
            if self.import_drop_callback:
                self.import_drop_callback(md.urls())
                event.acceptProposedAction()
            else:
                event.ignore()
            self.setProperty("dragOver", False)
            self.style().unpolish(self)
            self.style().polish(self)
            return

        # Tag drop (from tag library): multi-tag MIME or hasText(), no URLs
        tag_list: list[str] = []
        if md.hasFormat("application/x-sketchbook-tag-library-multi"):
            raw = md.data("application/x-sketchbook-tag-library-multi")
            if raw:
                tag_list = [
                    t.strip()
                    for t in bytes(raw).decode("utf-8").split("\n")
                    if t.strip()
                ]
        if not tag_list and md.hasText() and md.text().strip():
            tag_list = [md.text().strip()]
        if not tag_list:
            event.ignore()
            self.setProperty("dragOver", False)
            self.style().unpolish(self)
            self.style().polish(self)
            return

        # Get selected images
        selected_images = set()
        if self.get_selected_images_callback:
            selected_images = self.get_selected_images_callback()

        images_to_tag: list[str] = []
        if not selected_images:
            images_to_tag = [self.image_id]
        elif len(selected_images) > 1 and self.image_id in selected_images:
            images_to_tag = list(selected_images)
        elif len(selected_images) == 1 and self.image_id in selected_images:
            images_to_tag = [self.image_id]
        else:
            images_to_tag = [self.image_id]

        parent = self.parent()
        while parent:
            if hasattr(parent, "apply_tag_to_images_async"):
                for tag_text in tag_list:
                    parent.apply_tag_to_images_async(tag_text, images_to_tag)
                break
            parent = parent.parent()

        self.setProperty("dragOver", False)
        self.style().unpolish(self)
        self.style().polish(self)
        event.acceptProposedAction()
