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
    QCheckBox,
    QButtonGroup,
    QRadioButton,
)
from qtpy.QtCore import Qt, QSize, QPoint, QEvent, QObject
from qtpy.QtGui import QPixmap, QIcon, QImage, QDrag, QPainter
from qtpy.QtCore import QMimeData
from PIL import Image
from core.image_manager import ImageManager
from core import user_tags_config
from gui.icon_utils import find_tag_icon, invert_icon
from gui.tag_shelves import (
    MISCELLANEOUS_SHELF,
    is_tag_shelf,
    load_default_tags_taxonomy,
    parse_category_tags,
)

# MIME type for drag from tag library (reparent in grid); must match main window
TAG_LIBRARY_MIME = "application/x-sketchbook-tag-library"


class DraggableTagLibraryButton(QPushButton):
    """Tag button that can be dragged onto category/tag in the grid to reparent (same as main tag library)."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self._drag_start_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (
            event.buttons() & Qt.LeftButton
            and self._drag_start_pos is not None
            and (event.pos() - self._drag_start_pos).manhattanLength() >= 10
        ):
            tag_text = self.text()
            if not tag_text:
                return
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(tag_text)
            mime_data.setData(TAG_LIBRARY_MIME, tag_text.encode("utf-8"))
            drag.setMimeData(mime_data)
            pixmap = QPixmap(120, 28)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setPen(Qt.white)
            painter.drawText(pixmap.rect(), Qt.AlignCenter, tag_text)
            painter.end()
            drag.setPixmap(pixmap)
            drag.exec_(Qt.MoveAction)
            return
        super().mouseMoveEvent(event)


class ImportTagGridDropFilter(QObject):
    """Event filter to accept tag drag/drop on the import dialog tag grid (reparent user tags)."""

    def __init__(self, dialog: "ImportDialog"):
        super().__init__(dialog)
        self._dialog = dialog

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj != self._dialog.tags_container:
            return False
        try:
            _drag_enter = QEvent.Type.DragEnter
            _drag_move = QEvent.Type.DragMove
            _drag_leave = QEvent.Type.DragLeave
            _drop_type = QEvent.Type.Drop
        except AttributeError:
            _drag_enter = QEvent.DragEnter
            _drag_move = QEvent.DragMove
            _drag_leave = QEvent.DragLeave
            _drop_type = QEvent.Drop
        if event.type() == _drag_enter:
            if event.mimeData().hasFormat(TAG_LIBRARY_MIME):
                event.acceptProposedAction()
            return True
        if event.type() == _drag_move:
            if event.mimeData().hasFormat(TAG_LIBRARY_MIME):
                event.acceptProposedAction()
                pos = (
                    event.position().toPoint()
                    if hasattr(event, "position")
                    and hasattr(event.position(), "toPoint")
                    else event.pos()
                )
                target = self._dialog._get_import_drop_target_at(pos)
                self._dialog._set_import_drop_highlight(target)
            return True
        if event.type() == _drag_leave:
            self._dialog._set_import_drop_highlight(None)
            return False
        if event.type() == _drop_type:
            self._dialog._on_import_grid_drop(event)
            return True
        return False


class ImportDialog(QDialog):
    """Dialog for selecting tags before importing images."""

    def __init__(
        self,
        parent=None,
        image_manager: ImageManager = None,
        image_paths: List[Path] = None,
        first_image_path: Optional[Path] = None,
        import_root_dirs: Optional[List[Path]] = None,
    ):
        """
        Initialize the import dialog.

        Args:
            parent: Parent widget
            image_manager: ImageManager instance
            image_paths: List of image paths that will be imported
            first_image_path: Path to the first image for preview
            import_root_dirs: Root directories of the import (enables subfolder-as-tags option)
        """
        super().__init__(parent)
        self.setWindowTitle("Import Images")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)

        self.image_manager = image_manager
        self.image_paths = image_paths or []
        self.first_image_path = first_image_path
        self.import_root_dirs = import_root_dirs or []
        self.selected_tags: Set[str] = set()

        # Tag buttons storage (same structure as main window tag library)
        self._category_buttons: Dict[str, QPushButton] = {}
        self._subcategory_buttons: Dict[str, Dict[str, QPushButton]] = {}
        self._subcategory_containers: Dict[str, QWidget] = {}
        self._subcategory_tag_order: Dict[str, List[str]] = {}
        self._subtag_to_category: Dict[str, str] = {}
        self._user_tag_buttons: Dict[str, QPushButton] = {}
        self._user_tags_config: Dict[str, Any] = {}
        self._tags_added_during_session: Set[str] = set()
        self._added_row_buttons: Dict[str, QPushButton] = {}
        self._import_drop_highlight_widget: Optional[QWidget] = None

        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header message
        header_label = QLabel(
            f"You're about to import {len(self.image_paths)} image{'s' if len(self.image_paths) != 1 else ''}."
        )
        header_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; padding: 10px 0px;"
        )
        layout.addWidget(header_label)

        subtitle_label = QLabel("Choose associated tags in the library")
        subtitle_label.setStyleSheet(
            "font-size: 12px; color: #888; padding-bottom: 10px;"
        )
        layout.addWidget(subtitle_label)

        # Subfolder-as-tags option (only when importing from a directory)
        self._subfolder_tags_checkbox = QCheckBox("Use subfolder names as tags")
        self._subfolder_tags_checkbox.setToolTip(
            "Automatically tag each image with the name of its parent subfolder(s)."
        )
        self._subfolder_tags_checkbox.setStyleSheet("font-size: 12px; padding: 4px 0;")
        if self.import_root_dirs:
            layout.addWidget(self._subfolder_tags_checkbox)
            self._subfolder_options_widget = QWidget()
            sub_opts = QVBoxLayout(self._subfolder_options_widget)
            sub_opts.setContentsMargins(24, 0, 0, 0)
            sub_opts.setSpacing(6)
            self._subfolder_split_checkbox = QCheckBox(
                "Split each folder name into several tags using:"
            )
            self._subfolder_split_checkbox.setStyleSheet(
                "font-size: 12px; color: #aaa;"
            )
            self._subfolder_split_checkbox.setToolTip(
                "Each path segment (folder name) is split on the chosen character; "
                "each piece becomes one tag (capitalized)."
            )
            self._subfolder_split_checkbox.toggled.connect(
                self._on_subfolder_split_toggled
            )
            sub_opts.addWidget(self._subfolder_split_checkbox)
            sep_row = QHBoxLayout()
            sep_row.setSpacing(10)
            sep_label = QLabel("Separator:")
            sep_label.setStyleSheet("font-size: 12px; color: #888;")
            sep_row.addWidget(sep_label)
            self._subfolder_sep_group = QButtonGroup(self)
            sep_specs = [
                ("- (hyphen)", "-"),
                ("_ (underscore)", "_"),
                ("Space", " "),
                (". (dot)", "."),
            ]
            for i, (label, value) in enumerate(sep_specs):
                rb = QRadioButton(label)
                rb.setProperty("sep_value", value)
                rb.setStyleSheet("font-size: 12px;")
                self._subfolder_sep_group.addButton(rb, i)
                sep_row.addWidget(rb)
            sep_row.addStretch()
            self._subfolder_sep_group.button(1).setChecked(True)
            sub_opts.addLayout(sep_row)
            layout.addWidget(self._subfolder_options_widget)
            self._subfolder_options_widget.hide()
            self._subfolder_tags_checkbox.toggled.connect(
                self._on_subfolder_main_toggled
            )
            self._on_subfolder_split_toggled(False)

        # Main content area with splitter-like layout
        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)

        # Left side: Image preview
        preview_panel = QWidget()
        preview_layout = QVBoxLayout(preview_panel)
        preview_layout.setContentsMargins(0, 0, 0, 0)

        preview_label = QLabel("Preview")
        preview_label.setStyleSheet(
            "font-size: 12px; font-weight: bold; padding-bottom: 5px;"
        )
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
        tags_title.setStyleSheet(
            "font-size: 12px; font-weight: bold; padding-bottom: 5px;"
        )
        tags_layout.addWidget(tags_title)

        # Add user tag (Miscellaneous) - for this import only; can later be moved to default categories
        add_user_tag_row = QHBoxLayout()
        add_user_tag_row.setSpacing(8)
        add_user_tag_label = QLabel("Add user tag (Miscellaneous):")
        add_user_tag_label.setStyleSheet("font-size: 11px; color: #888;")
        self._add_user_tag_input = QLineEdit()
        self._add_user_tag_input.setPlaceholderText(
            "Type a tag name and press Add or Enter"
        )
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
        self.tags_container.installEventFilter(ImportTagGridDropFilter(self))
        tags_layout.addWidget(self.tags_scroll_area)

        content_layout.addWidget(tags_panel, 2)  # Give tags panel more space

        layout.addLayout(content_layout)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)

        import_button = QPushButton("Import")
        import_button.clicked.connect(self._on_import_clicked)
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

        button_layout.addWidget(cancel_button)
        button_layout.addWidget(import_button)

        layout.addLayout(button_layout)

    def _on_subfolder_main_toggled(self, checked: bool) -> None:
        """
        Show or hide split/separator options when 'Use subfolder names as tags' toggles.

        Args:
            checked: New state of the subfolder-as-tags checkbox.
        """
        w = getattr(self, "_subfolder_options_widget", None)
        if w is not None:
            w.setVisible(bool(checked))

    def _on_subfolder_split_toggled(self, checked: bool) -> None:
        """
        Enable separator radio buttons only when split is enabled.

        Args:
            checked: New state of the split checkbox.
        """
        group = getattr(self, "_subfolder_sep_group", None)
        if group is None:
            return
        for btn in group.buttons():
            btn.setEnabled(bool(checked))

    def _build_subtags_for_category(
        self,
        category: str,
        default_subtags: List[str],
        user_tags: List[str],
        placements: Dict[str, Any],
    ) -> List[str]:
        """Build ordered subtag list; default tags ignore user placement overrides."""
        from gui.tag_shelves import build_subtags_for_category

        return build_subtags_for_category(
            category,
            default_subtags,
            user_tags,
            placements,
            self._get_default_tags(),
        )

    def _get_children_of_tag(self, tag: str) -> List[str]:
        """Return list of tags whose placement has parent_tag = tag (sub-category children)."""
        placements = self._user_tags_config.get("placements", {})
        return [
            t
            for t, pl in placements.items()
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
            dict.fromkeys(
                user_tags_list + self._user_tags_config.get("registered_only", [])
            )
        )

        default_tags_path = Path(__file__).parent / "ressources" / "default_tags.json"
        if not default_tags_path.exists():
            return
        try:
            import json

            default_tags, _shelf_modes = load_default_tags_taxonomy(default_tags_path)

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
            for category_idx, (category, tags_value) in enumerate(categories_list):
                is_label_category = is_tag_shelf(category)
                tags_data, _ = parse_category_tags(tags_value)
                default_st: List[str] = []
                collect_subtags(tags_data, default_st)
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
                    tag_button = self._build_tag_button(tag, is_user_tag=False)
                    tag_button.setCheckable(True)
                    tag_button.clicked.connect(
                        lambda _=False, name=tag: self._on_tag_button_clicked(name)
                    )
                    tag_button.setProperty("tagGridRole", "tag")
                    tag_button.setProperty("tagGridKey", tag)
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
                    category_button = self._build_tag_button(
                        category, is_user_tag=False
                    )
                    category_button.setCheckable(True)
                    category_button.setSizePolicy(
                        QSizePolicy.Preferred, QSizePolicy.Maximum
                    )
                    category_button.clicked.connect(
                        lambda _=False, name=category: self._on_tag_button_clicked(name)
                    )
                    category_button.setProperty("tagGridRole", "category")
                    category_button.setProperty("tagGridKey", category)
                    self.tags_grid_layout.addWidget(
                        category_button, row, 0, 1, max_cols
                    )
                    self._category_buttons[category] = category_button

                current_row = row + 2
                if category_idx < len(categories_list) - 1:
                    separator = QFrame()
                    separator.setFrameShape(QFrame.Shape.HLine)
                    separator.setFrameShadow(QFrame.Shadow.Sunken)
                    separator.setStyleSheet("QFrame { color: #666; }")
                    self.tags_grid_layout.addWidget(
                        separator, current_row, 0, 1, max_cols
                    )
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
                user_label.setStyleSheet(
                    "font-weight: bold; font-size: 12px; padding: 4px;"
                )
                self.tags_grid_layout.addWidget(user_label, current_row + 1, 0, 1, 3)

                for idx, tag in enumerate(user_tags):
                    tag_row = current_row + 2 + (idx // max_cols)
                    tag_col = idx % max_cols
                    tag_button = self._build_tag_button(tag, is_user_tag=True)
                    tag_button.setCheckable(True)
                    tag_button.clicked.connect(
                        lambda _, name=tag: self._on_tag_button_clicked(name)
                    )
                    self.tags_grid_layout.addWidget(tag_button, tag_row, tag_col)
                    self._user_tag_buttons[tag] = tag_button

    def _get_default_tags(self) -> Set[str]:
        """Get default tags from JSON."""
        default_tags_path = Path(__file__).parent / "ressources" / "default_tags.json"
        if not default_tags_path.exists():
            return set()
        try:
            categories, _ = load_default_tags_taxonomy(default_tags_path)
        except (OSError, ValueError):
            return set()

        tag_set: Set[str] = set()

        def extract_tags(data: Any) -> None:
            if isinstance(data, list):
                for item in data:
                    extract_tags(item)
            elif isinstance(data, dict):
                for key, value in data.items():
                    tag_set.add(key)
                    extract_tags(value)
            elif isinstance(data, str):
                tag_set.add(data)

        for category, value in categories.items():
            if not is_tag_shelf(category):
                tag_set.add(category)
            tags_data, _ = parse_category_tags(value)
            extract_tags(tags_data)
        return tag_set

    def _build_tag_button(self, tag: str, is_user_tag: bool = False) -> QPushButton:
        """Build a tag button with icon. If is_user_tag, use draggable button for reparenting in grid."""
        if is_user_tag:
            button = DraggableTagLibraryButton(tag)
            button.setProperty("userTag", True)
        else:
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
        self._tags_added_during_session.add(tag)
        tag_button = self._build_tag_button(tag, is_user_tag=True)
        tag_button.setCheckable(True)
        tag_button.setChecked(True)
        tag_button.clicked.connect(
            lambda _, name=tag: self._on_tag_button_clicked(name)
        )
        self._user_tag_buttons[tag] = tag_button
        self._added_row_buttons[tag] = tag_button
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

    def _get_import_drop_target_at(self, pos: QPoint) -> Optional[QWidget]:
        """Return the category or tag button (widget with tagGridRole) at pos in container coords."""
        container = getattr(self, "tags_container", None)
        if not container:
            return None
        w = container.childAt(pos)
        while w and w != container:
            if w.property("tagGridRole"):
                return w
            local = w.mapFrom(container, pos)
            next_w = w.childAt(local) if hasattr(w, "childAt") else None
            w = next_w
        return None

    def _set_import_drop_highlight(self, widget: Optional[QWidget]) -> None:
        """Set or clear the drop-target highlight."""
        prev = self._import_drop_highlight_widget
        if prev is not None:
            prev.setProperty("dragOver", False)
            prev.style().unpolish(prev)
            prev.style().polish(prev)
        self._import_drop_highlight_widget = widget
        if widget is not None:
            widget.setProperty("dragOver", True)
            widget.style().unpolish(widget)
            widget.style().polish(widget)

    def _on_import_grid_drop(self, event) -> None:
        """Reposition a user tag when dropped on a category or tag in the import grid."""
        self._set_import_drop_highlight(None)
        if not event.mimeData().hasFormat(TAG_LIBRARY_MIME):
            return
        raw = event.mimeData().data(TAG_LIBRARY_MIME)
        dropped_tag = bytes(raw).decode("utf-8") if raw else ""
        pos = (
            event.position().toPoint()
            if hasattr(event, "position") and hasattr(event.position(), "toPoint")
            else event.pos()
        )
        child = self._get_import_drop_target_at(pos)
        if not child or not child.property("tagGridRole"):
            return
        role = child.property("tagGridRole")
        key = child.property("tagGridKey")
        if dropped_tag == key:
            return
        cfg = self._user_tags_config
        placements = dict(cfg.get("placements", {}))
        if role == "category":
            placements[dropped_tag] = {"category": key}
        else:
            placements[dropped_tag] = {"parent_tag": key}
        ro = list(cfg.get("registered_only", []))
        if dropped_tag not in ro:
            ro.append(dropped_tag)
        user_tags_config.save_config(placements, cfg.get("icons", {}), ro)
        self._user_tags_config = user_tags_config.load_config()
        self._load_tags_into_grid()
        self._sync_import_subtags_visibility()
        if dropped_tag in self._added_row_buttons:
            btn = self._added_row_buttons.pop(dropped_tag)
            self._added_user_tags_layout.removeWidget(btn)
            btn.deleteLater()

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
        placements = self._user_tags_config.get("placements", {})
        for category in self._subcategory_tag_order:
            container = self._subcategory_containers.get(category)
            if not container:
                continue
            is_label = is_tag_shelf(category)
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
                after = tag_order[idx_t + 1 :]
                children = [
                    c
                    for c in self._get_children_of_tag(expanded_parent)
                    if c in tag_order
                ]
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

    def _on_import_clicked(self) -> None:
        """Persist tags added during this session to config, then close with Accept."""
        if self._tags_added_during_session:
            cfg = self._user_tags_config
            placements = dict(cfg.get("placements", {}))
            ro = list(cfg.get("registered_only", []))
            for tag in self._tags_added_during_session:
                if tag not in placements:
                    placements[tag] = {"category": MISCELLANEOUS_SHELF}
                if tag not in ro:
                    ro.append(tag)
            user_tags_config.save_config(placements, cfg.get("icons", {}), ro)
        self.accept()

    def get_selected_tags(self) -> Set[str]:
        """
        Get selected tags.

        Returns:
            Set of selected tag names
        """
        return self.selected_tags.copy()

    def get_use_subfolder_tags(self) -> bool:
        """
        Whether the user wants subfolder names applied as tags.

        Returns:
            True if the checkbox is checked and root dirs are available.
        """
        return bool(self.import_root_dirs and self._subfolder_tags_checkbox.isChecked())

    def get_subfolder_split_separator(self) -> Optional[str]:
        """
        Separator used to split each folder name into several tags.

        Returns:
            One of ``-``, ``_``, `` `` (space), or ``.`` when split is enabled;
            ``None`` when split is off or subfolder tags are off.
        """
        if not self.get_use_subfolder_tags():
            return None
        if not getattr(self, "_subfolder_split_checkbox", None):
            return None
        if not self._subfolder_split_checkbox.isChecked():
            return None
        group = getattr(self, "_subfolder_sep_group", None)
        if group is None:
            return None
        btn = group.checkedButton()
        if btn is None:
            return None
        val = btn.property("sep_value")
        allowed = frozenset({"-", "_", " ", "."})
        if val not in allowed:
            return None
        return str(val)
