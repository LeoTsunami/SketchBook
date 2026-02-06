"""
Tag widget components used by the tag manager.
"""
from pathlib import Path
from typing import Set

from qtpy.QtCore import Qt, Signal, QMimeData, QPoint
from qtpy.QtGui import QDrag, QIcon, QPixmap, QPainter, QImage
from qtpy.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QWidget,
    QVBoxLayout,
)
from gui.icon_utils import find_tag_icon, invert_icon


class DraggableTagChip(QFrame):
    """Widget representing a single tag that can be dragged and removed."""

    removed = Signal(str)  # Emits tag text when removed
    dragged = Signal(str, QPoint)  # Emits tag text and position when dragged

    def __init__(self, text: str, parent=None):
        """
        Initialize the draggable tag chip.

        Args:
            text: Tag text to display
            parent: Parent widget
        """
        super().__init__(parent)
        self.text = text

        # Set object name for QSS styling
        self.setObjectName("DraggableTagChip")

        # Enable mouse tracking for drag detection
        self.setMouseTracking(True)
        self.drag_start_pos = None

        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        app_font = QApplication.instance().font() if QApplication.instance() else self.font()
        self.setFont(app_font)

        # Add icon (if available)
        icon = find_tag_icon(text)
        if not icon.isNull():
            icon_label = QLabel()
            icon_label.setPixmap(invert_icon(icon, 28).pixmap(28, 28))
            icon_label.setStyleSheet("background-color: transparent;")
            layout.addWidget(icon_label)

        # Add text label
        label = QLabel(text)
        label.setStyleSheet("color: inherit;")
        label.setFont(app_font)
        layout.addWidget(label)

        # Add remove button
        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(16, 16)
        remove_btn.setFont(app_font)
        remove_btn.setStyleSheet("color: inherit; background: transparent; border: none;")
        remove_btn.clicked.connect(lambda: self.removed.emit(self.text))
        layout.addWidget(remove_btn)

        # Styles are now handled by global QSS

    def mousePressEvent(self, event):
        """Handle mouse press for drag detection."""
        if event.button() == Qt.LeftButton:
            self.drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move for drag detection."""
        if (
            event.buttons() & Qt.LeftButton
            and self.drag_start_pos is not None
            and (event.pos() - self.drag_start_pos).manhattanLength() >= 10
        ):
            # Start drag
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(self.text)
            drag.setMimeData(mime_data)

            # Create drag pixmap
            pixmap = self.grab()
            drag.setPixmap(pixmap)
            drag.setHotSpot(event.pos())

            # Emit drag signal
            self.dragged.emit(self.text, self.mapToGlobal(event.pos()))

            # Execute drag and check result
            result = drag.exec_(Qt.MoveAction)

            # If drop was not accepted (outside drop zones), remove the tag
            if result == Qt.IgnoreAction:
                self.removed.emit(self.text)

            self.drag_start_pos = None
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        self.drag_start_pos = None
        super().mouseReleaseEvent(event)


class DropScrollArea(QScrollArea):
    """ScrollArea that delegates drop events to its parent TagDropZone."""

    def dragEnterEvent(self, event):
        """Delegate drag enter to parent."""
        parent = self.parent()
        if isinstance(parent, TagDropZone):
            parent.dragEnterEvent(event)
        else:
            super().dragEnterEvent(event)

    def dragLeaveEvent(self, event):
        """Delegate drag leave to parent."""
        parent = self.parent()
        if isinstance(parent, TagDropZone):
            parent.dragLeaveEvent(event)
        else:
            super().dragLeaveEvent(event)

    def dropEvent(self, event):
        """Delegate drop to parent."""
        parent = self.parent()
        if isinstance(parent, TagDropZone):
            parent.dropEvent(event)
        else:
            super().dropEvent(event)


class TagDropZone(QFrame):
    """Zone where tags can be dropped for AND or OR filtering (scrollable, vertical)."""

    tag_dropped = Signal(str)  # Emits tag text when dropped
    tags_modified = Signal()  # Emits when tags are added/removed

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.tags: Set[str] = set()
        self.setAcceptDrops(True)

        # Set object name for QSS styling
        self.setObjectName("TagDropZone")

        # Allow vertical expansion
        size_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        size_policy.setHorizontalStretch(1)
        size_policy.setVerticalStretch(1)
        self.setSizePolicy(size_policy)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)  # Reduced spacing to give more room to tags

        # Title (reduced height)
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setMaximumHeight(18)  # Reduced height for label
        title_label.setStyleSheet("padding: 2px;")  # Minimal padding
        layout.addWidget(title_label)

        # Scrollable tag area (expands to fill available space)
        self.scroll_area = DropScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setAcceptDrops(True)  # Allow drops on scroll area

        # Tag container widget (inside scroll area)
        self.tag_container = QWidget()
        self.tag_layout = QVBoxLayout(self.tag_container)
        self.tag_layout.setContentsMargins(2, 2, 2, 2)
        self.tag_layout.setSpacing(4)
        self.tag_layout.setAlignment(Qt.AlignTop)
        self.tag_layout.addStretch()  # Push tags to top

        self.scroll_area.setWidget(self.tag_container)
        # Add scroll area with stretch to fill available space
        layout.addWidget(self.scroll_area, 1)  # Stretch factor = 1 to expand

        # Styles are now handled by global QSS

    def dragEnterEvent(self, event):
        """Handle drag enter event."""
        if event.mimeData().hasText():
            event.acceptProposedAction()
            # Add a property to indicate drag state for QSS styling
            self.setProperty("dragOver", True)
            self.style().unpolish(self)
            self.style().polish(self)
            # Also update scroll area visual state
            self.scroll_area.setProperty("dragOver", True)
            self.scroll_area.style().unpolish(self.scroll_area)
            self.scroll_area.style().polish(self.scroll_area)

    def dragLeaveEvent(self, event):
        """Handle drag leave event."""
        # Remove drag state property
        self.setProperty("dragOver", False)
        self.style().unpolish(self)
        self.style().polish(self)
        # Also update scroll area visual state
        self.scroll_area.setProperty("dragOver", False)
        self.scroll_area.style().unpolish(self.scroll_area)
        self.scroll_area.style().polish(self.scroll_area)

    def dropEvent(self, event):
        """Handle drop event."""
        tag_text = event.mimeData().text()
        if tag_text and tag_text not in self.tags:
            self.add_tag(tag_text)
            self.tag_dropped.emit(tag_text)
        # Remove drag state property
        self.setProperty("dragOver", False)
        self.style().unpolish(self)
        self.style().polish(self)
        # Also update scroll area visual state
        self.scroll_area.setProperty("dragOver", False)
        self.scroll_area.style().unpolish(self.scroll_area)
        self.scroll_area.style().polish(self.scroll_area)

    def add_tag(self, tag: str):
        """Add a tag to this zone."""
        if tag not in self.tags:
            self.tags.add(tag)
            chip = DraggableTagChip(tag, self.tag_container)
            chip.removed.connect(self._on_chip_removed)
            chip.dragged.connect(self._on_tag_dragged)
            # Insert before the stretch at the end
            self.tag_layout.insertWidget(self.tag_layout.count() - 1, chip)
            self.tags_modified.emit()

    def _on_chip_removed(self, tag: str):
        self.remove_tag(tag)
        # Notifier le parent (AdvancedTagManager) de mettre à jour les filtres
        parent = self.parent()
        if hasattr(parent, "_emit_filters_changed"):
            parent._emit_filters_changed()

    def remove_tag(self, tag: str):
        """Remove a tag from this zone."""
        if tag in self.tags:
            self.tags.remove(tag)
            # Remove the chip widget
            for i in range(self.tag_layout.count()):
                widget = self.tag_layout.itemAt(i).widget()
                if isinstance(widget, DraggableTagChip) and widget.text == tag:
                    widget.deleteLater()
                    break
            self.tags_modified.emit()

    def _on_tag_dragged(self, tag: str, pos: QPoint):
        """Handle tag drag from this zone."""
        # Remove from this zone when dragged
        self.remove_tag(tag)

    def get_tags(self) -> Set[str]:
        """Get all tags in this zone."""
        return self.tags.copy()

    def clear_tags(self):
        """Clear all tags from this zone."""
        self.tags.clear()
        # Remove all chip widgets (but keep the stretch at the end)
        while self.tag_layout.count() > 1:  # Keep the stretch (last item)
            item = self.tag_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
