"""
Tag management component with search and filtering capabilities.
"""
from typing import List, Set
from qtpy.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLineEdit,
    QCompleter,
    QLabel,
    QPushButton,
    QFrame
)
from qtpy.QtCore import Qt, Signal, QStringListModel
from qtpy.QtGui import QFont, QFontMetrics

class TagChip(QFrame):
    """Widget representing a single tag that can be removed."""
    
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
        
        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(4)
        
        # Add text label
        label = QLabel(text)
        layout.addWidget(label)
        
        # Add remove button
        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(16, 16)
        remove_btn.clicked.connect(lambda: self.removed.emit(self.text))
        layout.addWidget(remove_btn)
        
        # Apply theme-aware styles
        self._apply_theme()
    
    def _apply_theme(self):
        """Apply theme-aware styles to components."""
        from core.settings import settings
        
        if settings.get("ui.theme") == "dark":
            # Dark theme
            self.setStyleSheet("""
                TagChip {
                    background-color: #3c3f41;
                    border-radius: 10px;
                }
                QLabel {
                    color: #ffffff;
                }
                QPushButton {
                    background-color: transparent;
                    border: none;
                    color: #999999;
                    font-weight: bold;
                }
                QPushButton:hover {
                    color: #ffffff;
                }
            """)
        else:
            # Light theme
            self.setStyleSheet("""
                TagChip {
                    background-color: #e0e0e0;
                    border-radius: 10px;
                }
                QLabel {
                    color: #000000;
                }
                QPushButton {
                    background-color: transparent;
                    border: none;
                    color: #666666;
                    font-weight: bold;
                }
                QPushButton:hover {
                    color: #000000;
                }
            """)

class TagManager(QWidget):
    """Widget for managing image tags with search and filtering."""
    
    tags_changed = Signal(list)  # Emits list of active tags when changed
    
    def __init__(self, parent=None):
        """
        Initialize the tag manager.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Initialize state
        self.all_tags: Set[str] = set()
        self.active_tags: Set[str] = set()
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Create search bar
        search_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search or add tags...")
        self.search_input.returnPressed.connect(self._on_search_return)
        search_layout.addWidget(self.search_input)
        
        # Add clear button
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self.clear_tags)
        search_layout.addWidget(clear_btn)
        
        layout.addLayout(search_layout)
        
        # Create tag flow area
        self.tag_area = QWidget()
        self.tag_layout = QHBoxLayout(self.tag_area)
        self.tag_layout.setContentsMargins(0, 0, 0, 0)
        self.tag_layout.setSpacing(4)
        self.tag_layout.setAlignment(Qt.AlignLeft)
        layout.addWidget(self.tag_area)
        
        # Set up completer
        self.completer = QCompleter()
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchContains)
        self.search_input.setCompleter(self.completer)
        
        # Apply theme-aware styles
        self._apply_theme()
    
    def _apply_theme(self):
        """Apply theme-aware styles to components."""
        from core.settings import settings
        
        if settings.get("ui.theme") == "dark":
            # Dark theme
            self.setStyleSheet("""
                QLineEdit {
                    background-color: #3c3f41;
                    color: #ffffff;
                    border: 1px solid #4d4d4d;
                    border-radius: 4px;
                    padding: 4px;
                }
                QLineEdit:focus {
                    border: 1px solid #5d5d5d;
                }
                QPushButton {
                    background-color: #3c3f41;
                    color: #ffffff;
                    border: 1px solid #4d4d4d;
                    border-radius: 4px;
                    padding: 4px 8px;
                }
                QPushButton:hover {
                    background-color: #4b6eaf;
                }
                QPushButton:pressed {
                    background-color: #3d5a8c;
                }
            """)
        else:
            # Light theme
            self.setStyleSheet("""
                QLineEdit {
                    background-color: #ffffff;
                    color: #000000;
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                    padding: 4px;
                }
                QLineEdit:focus {
                    border: 1px solid #0078d7;
                }
                QPushButton {
                    background-color: #f0f0f0;
                    color: #000000;
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                    padding: 4px 8px;
                }
                QPushButton:hover {
                    background-color: #e5e5e5;
                }
                QPushButton:pressed {
                    background-color: #d0d0d0;
                }
            """)
    
    def set_available_tags(self, tags: List[str]):
        """
        Set the list of available tags for autocompletion.
        
        Args:
            tags: List of available tags
        """
        self.all_tags = set(tags)
        model = QStringListModel(sorted(self.all_tags))
        self.completer.setModel(model)
    
    def _on_search_return(self):
        """Handle return/enter key in search input."""
        tag = self.search_input.text().strip()
        if tag:
            self.add_tag(tag)
            self.search_input.clear()
    
    def add_tag(self, tag: str):
        """
        Add a tag to the active set.
        
        Args:
            tag: Tag to add
        """
        if tag not in self.active_tags:
            self.active_tags.add(tag)
            chip = TagChip(tag, self)
            chip.removed.connect(self.remove_tag)
            self.tag_layout.addWidget(chip)
            self.tags_changed.emit(sorted(self.active_tags))
    
    def remove_tag(self, tag: str):
        """
        Remove a tag from the active set.
        
        Args:
            tag: Tag to remove
        """
        if tag in self.active_tags:
            self.active_tags.remove(tag)
            
            # Remove the chip widget
            for i in range(self.tag_layout.count()):
                widget = self.tag_layout.itemAt(i).widget()
                if isinstance(widget, TagChip) and widget.text == tag:
                    widget.deleteLater()
                    break
            
            self.tags_changed.emit(sorted(self.active_tags))
    
    def clear_tags(self):
        """Remove all active tags."""
        self.active_tags.clear()
        
        # Remove all chip widgets
        while self.tag_layout.count():
            widget = self.tag_layout.takeAt(0).widget()
            if widget:
                widget.deleteLater()
        
        self.tags_changed.emit([])
    
    def get_active_tags(self) -> List[str]:
        """
        Get the list of currently active tags.
        
        Returns:
            List of active tags
        """
        return sorted(self.active_tags) 