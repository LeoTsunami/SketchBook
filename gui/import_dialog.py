"""
Dialog for selecting tags before importing images.
"""
from pathlib import Path
from typing import List, Set, Dict, Optional
from qtpy.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QWidget,
    QGridLayout,
    QFrame,
    QSizePolicy,
)
from qtpy.QtCore import Qt, QSize
from qtpy.QtGui import QPixmap, QIcon, QImage
from PIL import Image
from core.image_manager import ImageManager


class ImportDialog(QDialog):
    """Dialog for selecting tags before importing images."""
    
    def __init__(self, parent=None, image_manager: ImageManager = None, image_paths: List[Path] = None, first_image_path: Optional[Path] = None):
        """
        Initialize the import dialog.
        
        Args:
            parent: Parent widget
            image_manager: ImageManager instance
            image_paths: List of image paths that will be imported
            first_image_path: Path to the first image for preview
        """
        super().__init__(parent)
        self.setWindowTitle("Import Images")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        
        # Apply global stylesheet (inherited from parent application)
        # The dialog will automatically inherit the global QSS applied to QApplication
        
        self.image_manager = image_manager
        self.image_paths = image_paths or []
        self.first_image_path = first_image_path
        self.selected_tags: Set[str] = set()
        
        # Tag buttons storage
        self._category_buttons: Dict[str, QPushButton] = {}
        self._subcategory_buttons: Dict[str, Dict[str, QPushButton]] = {}
        self._user_tag_buttons: Dict[str, QPushButton] = {}
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header message
        header_label = QLabel(f"You're about to import {len(self.image_paths)} image{'s' if len(self.image_paths) != 1 else ''}.")
        header_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px 0px;")
        layout.addWidget(header_label)
        
        subtitle_label = QLabel("Choose associated tags in the library")
        subtitle_label.setStyleSheet("font-size: 12px; color: #888; padding-bottom: 10px;")
        layout.addWidget(subtitle_label)
        
        # Main content area with splitter-like layout
        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)
        
        # Left side: Image preview
        preview_panel = QWidget()
        preview_layout = QVBoxLayout(preview_panel)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        
        preview_label = QLabel("Preview")
        preview_label.setStyleSheet("font-size: 12px; font-weight: bold; padding-bottom: 5px;")
        preview_layout.addWidget(preview_label)
        
        self.preview_label = QLabel()
        self.preview_label.setMinimumSize(200, 200)
        self.preview_label.setMaximumSize(300, 300)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("""
            QLabel {
                background-color: #2d2d2d;
                border: 1px solid #4d4d4d;
                border-radius: 4px;
            }
        """)
        self._load_preview_image()
        preview_layout.addWidget(self.preview_label)
        preview_layout.addStretch()
        
        content_layout.addWidget(preview_panel)
        
        # Right side: Tags library
        tags_panel = QWidget()
        tags_layout = QVBoxLayout(tags_panel)
        tags_layout.setContentsMargins(0, 0, 0, 0)
        
        tags_title = QLabel("Tags Library")
        tags_title.setStyleSheet("font-size: 12px; font-weight: bold; padding-bottom: 5px;")
        tags_layout.addWidget(tags_title)
        
        # Scrollable tags grid
        self.tags_scroll_area = QScrollArea()
        self.tags_scroll_area.setWidgetResizable(True)
        self.tags_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tags_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tags_scroll_area.setFrameShape(QFrame.NoFrame)
        
        self.tags_container = QWidget()
        self.tags_grid_layout = QGridLayout(self.tags_container)
        self.tags_grid_layout.setContentsMargins(0, 0, 0, 0)
        self.tags_grid_layout.setSpacing(10)
        self.tags_grid_layout.setAlignment(Qt.AlignTop)
        
        self._load_tags_into_grid()
        
        self.tags_scroll_area.setWidget(self.tags_container)
        tags_layout.addWidget(self.tags_scroll_area)
        
        content_layout.addWidget(tags_panel, 2)  # Give tags panel more space
        
        layout.addLayout(content_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        import_button = QPushButton("Import")
        import_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        import_button.clicked.connect(self.accept)
        
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(import_button)
        
        layout.addLayout(button_layout)
    
    def _load_preview_image(self):
        """Load and display the first image preview."""
        if not self.first_image_path or not self.first_image_path.exists():
            self.preview_label.setText("No preview available")
            return
        
        try:
            # Load image with PIL
            with Image.open(self.first_image_path) as img:
                # Convert to RGB if necessary
                if img.mode != "RGB":
                    img = img.convert("RGB")
                
                # Resize to fit preview (max 300x300)
                max_size = 300
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                # Convert PIL Image to QPixmap
                img_bytes = img.tobytes("raw", "RGB")
                q_image = QImage(img_bytes, img.width, img.height, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(q_image)
                
                self.preview_label.setPixmap(pixmap)
        except Exception as e:
            self.preview_label.setText(f"Preview error:\n{str(e)}")
    
    def _load_tags_into_grid(self):
        """Load tags from JSON into the tags grid."""
        # Load default tags from JSON
        default_tags_path = Path(__file__).parent / "ressources" / "default_tags.json"
        
        if default_tags_path.exists():
            try:
                import json
                with open(default_tags_path, "r", encoding="utf-8") as f:
                    default_tags = json.load(f)
                
                def collect_subtags(data, collected: List[str]) -> None:
                    """Recursively collect subtags from nested structures."""
                    if isinstance(data, list):
                        for item in data:
                            collect_subtags(item, collected)
                    elif isinstance(data, dict):
                        for key, value in data.items():
                            collected.append(key)
                            collect_subtags(value, collected)
                    elif isinstance(data, str):
                        collected.append(data)
                
                # Process each category
                categories_list = list(default_tags.items())
                max_cols = 3
                max_tags_per_row = 3
                
                # First pass: calculate rows
                category_row_counts: List[int] = []
                for category, tags in categories_list:
                    subtags: List[str] = []
                    collect_subtags(tags, subtags)
                    unique_subtags = list(dict.fromkeys(subtags))
                    subtag_rows = max(1, (len(unique_subtags) + max_tags_per_row - 1) // max_tags_per_row) if unique_subtags else 0
                    num_rows = 1 + subtag_rows
                    category_row_counts.append(num_rows)
                
                # Calculate starting rows
                current_row = 0
                category_start_rows: List[int] = []
                for num_rows in category_row_counts:
                    category_start_rows.append(current_row)
                    current_row += num_rows + 1
                
                # Second pass: create UI
                for category_idx, (category, tags) in enumerate(categories_list):
                    row = category_start_rows[category_idx]
                    num_rows = category_row_counts[category_idx]
                    
                    is_label_category = category in ["Miscellaneous:", "Camera-Angle:"]
                    
                    # Collect subtags first
                    subtags: List[str] = []
                    collect_subtags(tags, subtags)
                    unique_subtags = list(dict.fromkeys(subtags))
                    
                    # Create subtag buttons
                    subtag_buttons: Dict[str, QPushButton] = {}
                    for idx, tag in enumerate(unique_subtags):
                        tag_button = self._build_tag_button(tag)
                        tag_button.setCheckable(True)
                        tag_button.clicked.connect(lambda _, name=tag: self._on_tag_button_clicked(name))
                        tag_row = row + 1 + (idx // max_tags_per_row)
                        tag_col = idx % max_tags_per_row
                        self.tags_grid_layout.addWidget(tag_button, tag_row, tag_col)
                        subtag_buttons[tag] = tag_button
                        # Initially visible only for label categories
                        tag_button.setVisible(is_label_category)
                    
                    self._subcategory_buttons[category] = subtag_buttons
                    
                    # Category button/label
                    if is_label_category:
                        category_label = QLabel(category)
                        category_label.setStyleSheet("font-weight: bold; font-size: 12px; padding: 4px; background-color: transparent;")
                        category_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                        self.tags_grid_layout.addWidget(category_label, row, 0, 1, max_cols)
                    else:
                        category_button = self._build_tag_button(category)
                        category_button.setCheckable(True)
                        category_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
                        category_button.clicked.connect(lambda _, name=category: self._on_tag_button_clicked(name))
                        self.tags_grid_layout.addWidget(category_button, row, 0, 1, max_cols)
                        self._category_buttons[category] = category_button
                    
                    # Separator
                    if category_idx < len(categories_list) - 1:
                        separator = QFrame()
                        separator.setFrameShape(QFrame.Shape.HLine)
                        separator.setFrameShadow(QFrame.Shadow.Sunken)
                        separator.setStyleSheet("QFrame { color: #666; }")
                        separator_row = row + num_rows
                        self.tags_grid_layout.addWidget(separator, separator_row, 0, 1, max_cols)
                
                # Add spacer
                max_row = 0
                for i in range(self.tags_grid_layout.count()):
                    item = self.tags_grid_layout.itemAt(i)
                    if item:
                        row, col, row_span, col_span = self.tags_grid_layout.getItemPosition(i)
                        max_row = max(max_row, row + row_span - 1)
                if max_row >= 0:
                    self.tags_grid_layout.setRowStretch(max_row + 1, 1)
            
            except Exception as e:
                print(f"Error loading default tags: {str(e)}")
        
        # Load user tags
        if self.image_manager:
            all_tags = set()
            for metadata in self.image_manager.db.list_images():
                all_tags.update(metadata.tags)
            default_tags_set = self._get_default_tags()
            user_tags = sorted(all_tags - default_tags_set)
            
            if user_tags:
                # Add separator
                separator = QFrame()
                separator.setFrameShape(QFrame.Shape.HLine)
                separator.setFrameShadow(QFrame.Shadow.Sunken)
                separator.setStyleSheet("QFrame { color: #666; }")
                current_row = self.tags_grid_layout.rowCount()
                self.tags_grid_layout.addWidget(separator, current_row, 0, 1, 3)
                
                # Add user tags
                user_label = QLabel("User Tags")
                user_label.setStyleSheet("font-weight: bold; font-size: 12px; padding: 4px;")
                self.tags_grid_layout.addWidget(user_label, current_row + 1, 0, 1, 3)
                
                for idx, tag in enumerate(user_tags):
                    tag_row = current_row + 2 + (idx // max_cols)
                    tag_col = idx % max_cols
                    tag_button = self._build_tag_button(tag)
                    tag_button.setCheckable(True)
                    tag_button.clicked.connect(lambda _, name=tag: self._on_tag_button_clicked(name))
                    self.tags_grid_layout.addWidget(tag_button, tag_row, tag_col)
                    self._user_tag_buttons[tag] = tag_button
    
    def _get_default_tags(self) -> Set[str]:
        """Get default tags from JSON."""
        default_tags_path = Path(__file__).parent / "ressources" / "default_tags.json"
        
        if not default_tags_path.exists():
            return set()
        
        try:
            import json
            with open(default_tags_path, "r", encoding="utf-8") as f:
                default_tags_data = json.load(f)
        except Exception:
            return set()
        
        tag_set: Set[str] = set()
        
        def extract_tags(data) -> None:
            if isinstance(data, list):
                for item in data:
                    extract_tags(item)
            elif isinstance(data, dict):
                for key, value in data.items():
                    tag_set.add(key)
                    extract_tags(value)
            elif isinstance(data, str):
                tag_set.add(data)
        
        extract_tags(default_tags_data)
        return tag_set
    
    def _find_tag_icon(self, tag: str) -> QIcon:
        """Find tag icon."""
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
    
    def _invert_icon(self, icon: QIcon) -> QIcon:
        """Invert icon colors."""
        if icon.isNull():
            return icon
        pixmap = icon.pixmap(QSize(28, 28))
        image = pixmap.toImage()
        image.invertPixels(QImage.InvertRgb)
        return QIcon(QPixmap.fromImage(image))
    
    def _build_tag_button(self, tag: str) -> QPushButton:
        """Build a tag button with icon."""
        button = QPushButton(tag)
        icon = self._find_tag_icon(tag)
        if not icon.isNull():
            button.setIcon(self._invert_icon(icon))
            button.setIconSize(QSize(28, 28))
        button.setStyleSheet("QPushButton { text-align: left; padding: 2px 4px; }")
        return button
    
    def _on_tag_button_clicked(self, tag: str):
        """Handle tag button click - toggle selection."""
        button = self._get_tag_button(tag)
        if not button:
            return
        
        if tag in self.selected_tags:
            self.selected_tags.remove(tag)
            button.setChecked(False)
            self._update_button_style(button, False)
        else:
            self.selected_tags.add(tag)
            button.setChecked(True)
            self._update_button_style(button, True)
            # Show subtags if it's a category
            if tag in self._category_buttons:
                self._show_category_subtags(tag)
    
    def _update_button_style(self, button: QPushButton, checked: bool):
        """Update button style based on checked state."""
        base_style = "QPushButton { text-align: left; padding: 2px 4px; }"
        if checked:
            button.setStyleSheet(
                base_style + " QPushButton { background-color: #8ec5ff; }"
            )
        else:
            button.setStyleSheet(base_style)
    
    def _get_tag_button(self, tag: str) -> Optional[QPushButton]:
        """Get tag button by tag name."""
        # Check category buttons
        if tag in self._category_buttons:
            return self._category_buttons[tag]
        
        # Check subcategory buttons
        for buttons in self._subcategory_buttons.values():
            if tag in buttons:
                return buttons[tag]
        
        # Check user tag buttons
        if tag in self._user_tag_buttons:
            return self._user_tag_buttons[tag]
        
        return None
    
    def _show_category_subtags(self, category: str):
        """Show subtags for a category."""
        if category in self._subcategory_buttons:
            for tag_button in self._subcategory_buttons[category].values():
                tag_button.setVisible(True)
    
    def get_selected_tags(self) -> Set[str]:
        """
        Get selected tags.
        
        Returns:
            Set of selected tag names
        """
        return self.selected_tags.copy()
