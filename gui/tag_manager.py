"""
Tag management component with advanced AND/OR filtering and drag & drop capabilities.
"""
from typing import List, Set, Dict, Optional
from qtpy.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLineEdit,
    QCompleter,
    QLabel,
    QPushButton,
    QGroupBox,
    QGridLayout
)
from qtpy.QtCore import Qt, Signal, QStringListModel, QPropertyAnimation, QTimer
from qtpy.QtGui import QFont, QFontMetrics, QPixmap, QPainter, QColor

from gui.tag_widgets import TagDropZone

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
        self.search_input.setPlaceholderText("Search tags")
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self.search_input.returnPressed.connect(self._on_search_return)
        search_layout.addWidget(self.search_input)
        self._search_base_style = self.search_input.styleSheet()
        self._invalid_tag_animation: Optional[QPropertyAnimation] = None
        
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
        
        # Filter zones (horizontal, expand to fill available space)
        zones_layout = QHBoxLayout()
        zones_layout.setSpacing(8)
        
        # AND zone
        self.and_zone = TagDropZone("AND (all required)")
        self.and_zone.tag_dropped.connect(self._on_filter_changed)
        self.and_zone.tags_modified.connect(self._on_tags_modified)
        zones_layout.addWidget(self.and_zone, 1)  # Stretch factor = 1 to expand
        
        # OR zone
        self.or_zone = TagDropZone("OR (at least one)")
        self.or_zone.tag_dropped.connect(self._on_filter_changed)
        self.or_zone.tags_modified.connect(self._on_tags_modified)
        zones_layout.addWidget(self.or_zone, 1)  # Stretch factor = 1 to expand
        
        # Add zones layout with stretch to fill available space
        layout.addLayout(zones_layout, 1)  # Stretch factor = 1 to expand
        
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

    def _resolve_tag(self, text: str) -> Optional[str]:
        """
        Resolve a tag by case-insensitive match.

        Args:
            text: Tag text to resolve.

        Returns:
            Optional[str]: Matching tag with original casing if found.
        """
        if not text:
            return None
        text_lower = text.lower()
        for tag in self.all_tags:
            if tag.lower() == text_lower:
                return tag
        return None

    def _trigger_invalid_tag_feedback(self) -> None:
        """
        Animate the search bar and highlight it in red for invalid tags.
        """
        if self._invalid_tag_animation is not None:
            self._invalid_tag_animation.stop()

        base_style = self._search_base_style or ""
        self.search_input.setStyleSheet(f"{base_style} border: 1px solid #e04f4f;")

        start_pos = self.search_input.pos()
        animation = QPropertyAnimation(self.search_input, b"pos", self)
        animation.setDuration(300)
        animation.setKeyValueAt(0.0, start_pos)
        animation.setKeyValueAt(0.15, start_pos + QPoint(-6, 0))
        animation.setKeyValueAt(0.3, start_pos + QPoint(6, 0))
        animation.setKeyValueAt(0.45, start_pos + QPoint(-4, 0))
        animation.setKeyValueAt(0.6, start_pos + QPoint(4, 0))
        animation.setKeyValueAt(0.75, start_pos + QPoint(-2, 0))
        animation.setKeyValueAt(1.0, start_pos)
        animation.start()
        self._invalid_tag_animation = animation

        QTimer.singleShot(300, lambda: self.search_input.setStyleSheet(base_style))

    def _on_search_return(self):
        """
        Handle Enter key for tag search input.
        """
        text = self.search_input.text().strip()
        suggestion = self._find_suggestion(text)
        if suggestion and suggestion != text:
            # Complète automatiquement
            self.search_input.setText(suggestion)
            self.suggestion_label.hide()
            self.add_tag_to_and(suggestion)
            self.search_input.clear()
        elif text:
            resolved_tag = self._resolve_tag(text)
            if resolved_tag is None:
                self._trigger_invalid_tag_feedback()
                return
            self.add_tag_to_and(resolved_tag)
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

    def toggle_tag(self, tag: str) -> None:
        """
        Toggle a tag in the filters.

        Args:
            tag: Tag to toggle in the AND or OR zone.
        """
        if tag in self.and_zone.get_tags():
            self.and_zone.remove_tag(tag)
            self._emit_filters_changed()
            return
        if tag in self.or_zone.get_tags():
            self.or_zone.remove_tag(tag)
            self._emit_filters_changed()
            return
        self.add_tag_to_and(tag)
    
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