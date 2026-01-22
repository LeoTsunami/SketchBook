"""
Tag management component with advanced AND/OR filtering and drag & drop capabilities.
"""
from typing import List, Set, Dict
from qtpy.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLineEdit,
    QCompleter,
    QLabel,
    QPushButton,
    QFrame,
    QScrollArea,
    QGroupBox,
    QGridLayout
)
from qtpy.QtCore import Qt, Signal, QStringListModel, QMimeData, QPoint
from qtpy.QtGui import QFont, QFontMetrics, QDrag, QPixmap, QPainter, QColor

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
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)
        
        # Add text label
        label = QLabel(text)
        label.setStyleSheet("color: inherit;")
        layout.addWidget(label)
        
        # Add remove button
        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(16, 16)
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
        if (event.buttons() & Qt.LeftButton and 
            self.drag_start_pos is not None and
            (event.pos() - self.drag_start_pos).manhattanLength() >= 10):
            
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

class TagDropZone(QFrame):
    """Zone where tags can be dropped for AND or OR filtering (compact, horizontal)."""
    tag_dropped = Signal(str)  # Emits tag text when dropped
    tags_modified = Signal()   # Emits when tags are added/removed

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.tags: Set[str] = set()
        self.setAcceptDrops(True)
        
        # Set object name for QSS styling
        self.setObjectName("TagDropZone")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        # Title
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Tag area (horizontal, compact)
        self.tag_container = QWidget()
        self.tag_layout = QHBoxLayout(self.tag_container)
        self.tag_layout.setContentsMargins(2, 2, 2, 2)
        self.tag_layout.setSpacing(4)
        self.tag_layout.setAlignment(Qt.AlignLeft)
        layout.addWidget(self.tag_container)

        self.setMaximumHeight(54)  # Compact height
        # Styles are now handled by global QSS
    
    def dragEnterEvent(self, event):
        """Handle drag enter event."""
        if event.mimeData().hasText():
            event.acceptProposedAction()
            # Add a property to indicate drag state for QSS styling
            self.setProperty("dragOver", True)
            self.style().unpolish(self)
            self.style().polish(self)
    
    def dragLeaveEvent(self, event):
        """Handle drag leave event."""
        # Remove drag state property
        self.setProperty("dragOver", False)
        self.style().unpolish(self)
        self.style().polish(self)
    
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
    
    def add_tag(self, tag: str):
        """Add a tag to this zone."""
        if tag not in self.tags:
            self.tags.add(tag)
            chip = DraggableTagChip(tag, self.tag_container)
            chip.removed.connect(self._on_chip_removed)
            chip.dragged.connect(self._on_tag_dragged)
            self.tag_layout.addWidget(chip)
            self.tags_modified.emit()
    
    def _on_chip_removed(self, tag: str):
        self.remove_tag(tag)
        # Notifier le parent (AdvancedTagManager) de mettre à jour les filtres
        parent = self.parent()
        if hasattr(parent, '_emit_filters_changed'):
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
        # Remove all chip widgets
        while self.tag_layout.count():
            item = self.tag_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

class AdvancedTagManager(QWidget):
    """Advanced tag manager with AND/OR filtering and drag & drop."""
    
    filters_changed = Signal(dict)  # Emits {"and": set, "or": set} when filters change
    tags_modified = Signal()  # Relayed to MainWindow
    
    def __init__(self, parent=None):
        """
        Initialize the advanced tag manager.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Initialize state
        self.all_tags: Set[str] = set()
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Search bar
        search_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search or add tags...")
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self.search_input.returnPressed.connect(self._on_search_return)
        search_layout.addWidget(self.search_input)
        
        # Inline suggestion label (superposé au QLineEdit)
        self.suggestion_label = QLabel(self.search_input)
        self.suggestion_label.setStyleSheet("color: #bbbbbb; background: transparent;")
        self.suggestion_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.suggestion_label.move(4, 2)
        self.suggestion_label.hide()
        
        # Add clear button
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self.clear_all_filters)
        search_layout.addWidget(clear_btn)
        
        layout.addLayout(search_layout)
        
        # Filter zones (horizontal, compact)
        zones_layout = QHBoxLayout()
        zones_layout.setSpacing(8)
        
        # AND zone
        self.and_zone = TagDropZone("AND (tous requis)")
        self.and_zone.tag_dropped.connect(self._on_filter_changed)
        self.and_zone.tags_modified.connect(self._on_tags_modified)
        zones_layout.addWidget(self.and_zone)
        
        # OR zone
        self.or_zone = TagDropZone("OR (au moins un)")
        self.or_zone.tag_dropped.connect(self._on_filter_changed)
        self.or_zone.tags_modified.connect(self._on_tags_modified)
        zones_layout.addWidget(self.or_zone)
        
        layout.addLayout(zones_layout)
        
        # Set up completer
        self.completer = QCompleter()
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchContains)
        self.search_input.setCompleter(self.completer)
        
        # Styles are now handled by global QSS
    
    def set_available_tags(self, tags: List[str]):
        """
        Set the list of available tags for autocompletion.
        
        Args:
            tags: List of available tags
        """
        self.all_tags = set(tags)
        self.completer.setModel(QStringListModel(tags))
    
    def _on_search_text_changed(self, text: str):
        """Met à jour la suggestion inline à chaque frappe (alignement parfait, sans espace)."""
        suggestion = self._find_suggestion(text)
        if suggestion and suggestion != text:
            cursor_rect = self.search_input.cursorRect()
            self.suggestion_label.move(cursor_rect.right(), cursor_rect.top())
            self.suggestion_label.setText(suggestion[len(text):])
            self.suggestion_label.setFont(self.search_input.font())
            self.suggestion_label.show()
        else:
            self.suggestion_label.hide()

    def _find_suggestion(self, text: str) -> str:
        """Retourne la suggestion la plus proche (commence par text, insensible à la casse)."""
        if not text:
            return ""
        text_lower = text.lower()
        for tag in sorted(self.all_tags):
            if tag.lower().startswith(text_lower):
                return tag
        return ""

    def _on_search_return(self):
        text = self.search_input.text().strip()
        suggestion = self._find_suggestion(text)
        if suggestion and suggestion != text:
            # Complète automatiquement
            self.search_input.setText(suggestion)
            self.suggestion_label.hide()
            self.add_tag_to_and(suggestion)
            self.search_input.clear()
        elif text:
            self.add_tag_to_and(text)
            self.suggestion_label.hide()
            self.search_input.clear()
    
    def add_tag_to_and(self, tag: str):
        """Add a tag to the AND zone."""
        if tag not in self.all_tags:
            self.all_tags.add(tag)
            tags_list = list(self.all_tags)
            self.completer.setModel(QStringListModel(tags_list))
        self.and_zone.add_tag(tag)
        self._emit_filters_changed()
    
    def _on_filter_changed(self, tag: str):
        """Handle filter changes."""
        self._emit_filters_changed()
    
    def _emit_filters_changed(self):
        """Emit the current filter state."""
        filters = {
            "and": self.and_zone.get_tags(),
            "or": self.or_zone.get_tags()
        }
        self.filters_changed.emit(filters)
    
    def clear_all_filters(self):
        """Clear all filters."""
        self.and_zone.clear_tags()
        self.or_zone.clear_tags()
        self._emit_filters_changed()
    
    def get_filters(self) -> Dict[str, Set[str]]:
        """Get current filters."""
        return {
            "and": self.and_zone.get_tags(),
            "or": self.or_zone.get_tags()
        }

    def _on_tags_modified(self):
        self.tags_modified.emit()

# Alias for backward compatibility
TagManager = AdvancedTagManager 