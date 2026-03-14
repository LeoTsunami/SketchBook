"""
Dialog for selecting tags before importing images.
"""
from pathlib import Path
from typing import List, Set, Dict, Optional, Any
from qtpy.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
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
from core import user_tags_config
from gui.icon_utils import find_tag_icon, invert_icon


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
        
        # Tag buttons storage (same structure as main window tag library)
        self._category_buttons: Dict[str, QPushButton] = {}
        self._subcategory_buttons: Dict[str, Dict[str, QPushButton]] = {}
        self._subcategory_containers: Dict[str, QWidget] = {}
        self._subcategory_tag_order: Dict[str, List[str]] = {}
        self._subtag_to_category: Dict[str, str] = {}
        self._user_tag_buttons: Dict[str, QPushButton] = {}
        self._user_tags_config: Dict[str, Any] = {}
        
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
        
        # Add user tag (Miscellaneous) - for this import only; can later be moved to default categories
        add_user_tag_row = QHBoxLayout()
        add_user_tag_row.setSpacing(8)
        add_user_tag_label = QLabel("Add user tag (Miscellaneous):")
        add_user_tag_label.setStyleSheet("font-size: 11px; color: #888;")
        self._add_user_tag_input = QLineEdit()
        self._add_user_tag_input.setPlaceholderText("Type a tag name and press Add or Enter")
        self._add_user_tag_input.setMaximumWidth(280)
        self._add_user_tag_input.returnPressed.connect(self._on_add_user_tag_clicked)
        add_user_tag_btn = QPushButton("Add")
        add_user_tag_btn.clicked.connect(self._on_add_user_tag_clicked)
        add_user_tag_row.addWidget(add_user_tag_label)
        add_user_tag_row.addWidget(self._add_user_tag_input)
        add_user_tag_row.addWidget(add_user_tag_btn)
        add_user_tag_row.addStretch()
        tags_layout.addLayout(add_user_tag_row)
        # Container for dynamically added user tag buttons (for this import)
        self._added_user_tags_widget = QWidget()
        self._added_user_tags_layout = QHBoxLayout(self._added_user_tags_widget)
        self._added_user_tags_layout.setContentsMargins(0, 4, 0, 4)
        self._added_user_tags_layout.setSpacing(6)
        tags_layout.addWidget(self._added_user_tags_widget)
        
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
    
    def _build_subtags_for_category(
        self,
        category: str,
        default_subtags: List[str],
        user_tags: List[str],
        placements: Dict[str, Any],
    ) -> List[str]:
        """
        Build ordered subtag list for a category: default tags + user tags by placement.
        User tags with placement "category" are appended; with "parent_tag" inserted after parent.
        Same logic as main window tag library.
        """
        result = list(dict.fromkeys(default_subtags))
        for ut in user_tags:
            pl = placements.get(ut)
            if pl is None:
                if category == "Miscellaneous:":
                    result.append(ut)
                continue
            if pl.get("category") == category:
                if ut not in result:
                    result.append(ut)
        changed = True
        while changed:
            changed = False
            for ut in user_tags:
                pl = placements.get(ut)
                if pl is None or "parent_tag" not in pl:
                    continue
                parent = pl["parent_tag"]
                if parent in result and ut not in result:
                    idx = result.index(parent) + 1
                    result.insert(idx, ut)
                    changed = True
        return result

    def _get_children_of_tag(self, tag: str) -> List[str]:
        """Return list of tags whose placement has parent_tag = tag (sub-category children)."""
        placements = self._user_tags_config.get("placements", {})
        return [
            t for t, pl in placements.items()
            if isinstance(pl, dict) and pl.get("parent_tag") == tag
        ]

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
        """Load tags from JSON and user config into the grid, same structure as main tag library."""
        max_cols = 3
        max_tags_per_row = 3
        label_categories_set = {"Miscellaneous:", "Camera-Angle:"}

        self._user_tags_config = user_tags_config.load_config()
        placements = self._user_tags_config.get("placements", {})
        user_tags_list: List[str] = []
        if self.image_manager:
            all_tags = set()
            for metadata in self.image_manager.db.list_images():
                all_tags.update(metadata.tags)
            default_set = self._get_default_tags()
            user_tags_list = sorted(all_tags - default_set)
        user_tags_list = list(
            dict.fromkeys(user_tags_list + self._user_tags_config.get("registered_only", []))
        )

        default_tags_path = Path(__file__).parent / "ressources" / "default_tags.json"
        if not default_tags_path.exists():
            return
        try:
            import json
            with open(default_tags_path, "r", encoding="utf-8") as f:
                default_tags = json.load(f)

            def collect_subtags(data, collected: List[str]) -> None:
                if isinstance(data, list):
                    for item in data:
                        collect_subtags(item, collected)
                elif isinstance(data, dict):
                    for key, value in data.items():
                        collected.append(key)
                        collect_subtags(value, collected)
                elif isinstance(data, str):
                    collected.append(data)

            categories_list = list(default_tags.items())
            current_row = 0
            for category_idx, (category, tags) in enumerate(categories_list):
                is_label_category = category in label_categories_set
                default_st: List[str] = []
                collect_subtags(tags, default_st)
                default_st = list(dict.fromkeys(default_st))
                unique_subtags = self._build_subtags_for_category(
                    category, default_st, user_tags_list, placements
                )
                self._subcategory_tag_order[category] = list(unique_subtags)

                row = current_row
                tag_container = QWidget()
                tag_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
                tag_container.setMinimumHeight(0)
                tag_container_layout = QGridLayout(tag_container)
                tag_container_layout.setContentsMargins(0, 0, 0, 0)
                tag_container_layout.setSpacing(10)
                subtag_buttons: Dict[str, QPushButton] = {}
                for tag in unique_subtags:
                    tag_button = self._build_tag_button(tag)
                    tag_button.setCheckable(True)
                    tag_button.clicked.connect(lambda _=False, name=tag: self._on_tag_button_clicked(name))
                    subtag_buttons[tag] = tag_button
                    self._subtag_to_category[tag] = category
                    tag_button.setVisible(is_label_category)

                self.tags_grid_layout.addWidget(tag_container, row + 1, 0, 1, max_cols)
                self._subcategory_containers[category] = tag_container
                self._subcategory_buttons[category] = subtag_buttons

                if is_label_category:
                    category_label = QLabel(category)
                    category_label.setStyleSheet(
                        "font-weight: bold; font-size: 12px; padding: 4px; background-color: transparent;"
                    )
                    category_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    self.tags_grid_layout.addWidget(category_label, row, 0, 1, max_cols)
                else:
                    category_button = self._build_tag_button(category)
                    category_button.setCheckable(True)
                    category_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
                    category_button.clicked.connect(lambda _=False, name=category: self._on_tag_button_clicked(name))
                    self.tags_grid_layout.addWidget(category_button, row, 0, 1, max_cols)
                    self._category_buttons[category] = category_button

                current_row = row + 2
                if category_idx < len(categories_list) - 1:
                    separator = QFrame()
                    separator.setFrameShape(QFrame.Shape.HLine)
                    separator.setFrameShadow(QFrame.Shadow.Sunken)
                    separator.setStyleSheet("QFrame { color: #666; }")
                    self.tags_grid_layout.addWidget(separator, current_row, 0, 1, max_cols)
                    current_row += 1
            max_row = current_row - 1
            if max_row >= 0:
                self.tags_grid_layout.setRowStretch(max_row + 1, 1)
            self._sync_import_subtags_visibility()
        except Exception as e:
            print(f"Error loading default tags: {str(e)}")
        
        # Load user tags (only those not already placed in a category)
        if self.image_manager:
            all_tags = set()
            for metadata in self.image_manager.db.list_images():
                all_tags.update(metadata.tags)
            default_tags_set = self._get_default_tags()
            user_tags = sorted(all_tags - default_tags_set)
            user_tags = [t for t in user_tags if t not in self._subtag_to_category]
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
    
    
    def _build_tag_button(self, tag: str) -> QPushButton:
        """Build a tag button with icon (uses user_tags_config for user tag icons)."""
        button = QPushButton(tag)
        icon = find_tag_icon(tag, user_config=getattr(self, "_user_tags_config", {}))
        if not icon.isNull():
            button.setIcon(invert_icon(icon, 28))
            button.setIconSize(QSize(28, 28))
        button.setStyleSheet("QPushButton { text-align: left; padding: 2px 4px; }")
        return button
    
    def _on_add_user_tag_clicked(self) -> None:
        """Add a new user tag (Miscellaneous) for this import."""
        text = self._add_user_tag_input.text().strip()
        if not text:
            return
        tag = text
        self._add_user_tag_input.clear()
        if tag in self.selected_tags:
            return
        # If tag already exists in grid (e.g. existing user tag), just select it
        if tag in self._user_tag_buttons:
            button = self._user_tag_buttons[tag]
            self.selected_tags.add(tag)
            button.setChecked(True)
            self._update_button_style(button, True)
            return
        self.selected_tags.add(tag)
        tag_button = self._build_tag_button(tag)
        tag_button.setCheckable(True)
        tag_button.setChecked(True)
        tag_button.clicked.connect(lambda _, name=tag: self._on_tag_button_clicked(name))
        self._user_tag_buttons[tag] = tag_button
        self._added_user_tags_layout.addWidget(tag_button)
        self._update_button_style(tag_button, True)

    def _on_tag_button_clicked(self, tag: str):
        """Handle tag button click - toggle selection. Category click expands/collapses subtags."""
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
        # Sync subtag visibility: show subtags only when their category is selected (expanded)
        self._sync_import_subtags_visibility()
    
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
    
    def _sync_import_subtags_visibility(self) -> None:
        """
        Sync subtag visibility and layout with selection. When category is expanded, show only
        top-level tags; tags with a parent_tag (sub-category children) are visible only when
        their parent is selected. Rebuild layout with grouping when a sub-category is expanded.
        """
        max_cols = 3
        label_categories = {"Miscellaneous:", "Camera-Angle:"}
        placements = self._user_tags_config.get("placements", {})
        for category in self._subcategory_tag_order:
            container = self._subcategory_containers.get(category)
            if not container:
                continue
            is_label = category in label_categories
            expanded = is_label or (category in self.selected_tags)
            container.setVisible(expanded)
            if not expanded:
                continue
            tag_order = self._subcategory_tag_order[category]
            subtag_buttons = self._subcategory_buttons.get(category, {})
            # Sub-category children visible only when their parent is selected (like main tag library)
            for tag, btn in subtag_buttons.items():
                pl = placements.get(tag)
                parent_tag = pl.get("parent_tag") if isinstance(pl, dict) else None
                if parent_tag is not None:
                    btn.setVisible(parent_tag in self.selected_tags)
                else:
                    btn.setVisible(True)
            layout = container.layout()
            if not layout:
                continue
            while layout.count():
                layout.takeAt(0)
            category_selected = [t for t in tag_order if t in self.selected_tags]
            expanded_parent = None
            for t in category_selected:
                if self._get_children_of_tag(t):
                    expanded_parent = t
                    break
            if expanded_parent is not None and expanded_parent in tag_order:
                idx_t = tag_order.index(expanded_parent)
                before = tag_order[:idx_t]
                after = tag_order[idx_t + 1:]
                children = [c for c in self._get_children_of_tag(expanded_parent) if c in tag_order]
                rest = [x for x in after if x not in children]
                idx = 0
                for tag in before + [expanded_parent]:
                    btn = subtag_buttons.get(tag)
                    if btn and btn.isVisible():
                        r, c = idx // max_cols, idx % max_cols
                        layout.addWidget(btn, r, c)
                        idx += 1
                idx = ((idx + max_cols - 1) // max_cols) * max_cols
                for tag in children:
                    btn = subtag_buttons.get(tag)
                    if btn and btn.isVisible():
                        r, c = idx // max_cols, idx % max_cols
                        layout.addWidget(btn, r, c)
                        idx += 1
                idx = ((idx + max_cols - 1) // max_cols) * max_cols
                for tag in rest:
                    btn = subtag_buttons.get(tag)
                    if btn and btn.isVisible():
                        r, c = idx // max_cols, idx % max_cols
                        layout.addWidget(btn, r, c)
                        idx += 1
            else:
                idx = 0
                for tag in tag_order:
                    btn = subtag_buttons.get(tag)
                    if btn and btn.isVisible():
                        r, c = idx // max_cols, idx % max_cols
                        layout.addWidget(btn, r, c)
                        idx += 1

    def get_selected_tags(self) -> Set[str]:
        """
        Get selected tags.
        
        Returns:
            Set of selected tag names
        """
        return self.selected_tags.copy()
