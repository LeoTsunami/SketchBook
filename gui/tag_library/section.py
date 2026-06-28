"""
CategorySection  – collapsible section with a header chip + 3-col tag grid.
ShelfSection     – always-expanded section with a label header + 3-col tag grid.

Both are standalone QWidget subclasses.  The panel stacks them in a QVBoxLayout.
Expand/collapse is done entirely with setVisible() on the TagGridHost; the grid
widget tree is never rebuilt after initial construction.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional, Set

from qtpy.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from qtpy.QtCore import Qt, Signal

from gui.tag_library.constants import (
    TAG_LIBRARY_FONT_CATEGORY_PX,
    TAG_LIBRARY_FONT_SHELF_TITLE_PX,
    TAG_LIBRARY_TAG_CELL_ALIGN,
    TAG_LIBRARY_CATEGORY_MIN_HEIGHT_PX,
    TAG_LIBRARY_SHELF_GRID_PADDING_PX,
    TAG_LIBRARY_CATEGORY_ICON_PX,
    TAG_LIBRARY_TAG_ICON_PX,
)
from gui.tag_library.chip import (
    WrappingDraggableTagButton,
    apply_chip_style,
    get_hierarchy_background_color,
)
from gui.tag_library.grid_host import TagGridHost, _with_expand_icon
from gui.tag_library.state import TagLibraryTaxonomy


# ---------------------------------------------------------------------------
# CategorySection
# ---------------------------------------------------------------------------

class CategorySection(QWidget):
    """
    One collapsible section for a non-shelf category (Animal, Human, …).

    Composed of:
    - A full-width ``WrappingDraggableTagButton`` header chip (clickable).
    - A ``TagGridHost`` with all subtags in a 3-col grid (hidden when collapsed).

    Signals:
        header_clicked: Emitted when the header chip is clicked.
        chip_clicked: Emitted with tag name when a subtag chip is clicked.
        chip_context_menu: Emitted with tag name when right-click on a chip.
        chip_drag_started: Emitted when a DnD drag begins.
        chip_drag_ended: Emitted when a DnD drag ends.
    """

    header_clicked = Signal(str)           # category name
    chip_clicked = Signal(str, str)        # (tag_name, category_name)
    chip_context_menu = Signal(str)        # tag_name
    chip_drag_started = Signal()
    chip_drag_ended = Signal()

    def __init__(
        self,
        category: str,
        taxonomy: TagLibraryTaxonomy,
        chips: Dict[str, WrappingDraggableTagButton],
        root_tags: List[str],
        category_chip: WrappingDraggableTagButton,
        parent: Optional[QWidget] = None,
    ) -> None:
        """
        Args:
            category: Category name.
            taxonomy: Full library taxonomy.
            chips: Dict tag → chip widget (all subtags of this category).
            root_tags: Ordered root-level subtags for this category.
            category_chip: Pre-built chip for the category header row.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._category = category
        self._taxonomy = taxonomy
        self._category_chip = category_chip

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Header chip
        category_chip.setProperty("tagGridRole", "category")
        category_chip.setProperty("tagGridKey", category)
        category_chip.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        category_chip.clicked.connect(lambda: self.header_clicked.emit(category))
        category_chip.drag_session_started.connect(self.chip_drag_started)
        category_chip.drag_session_ended.connect(self.chip_drag_ended)
        layout.addWidget(category_chip, 0, Qt.AlignHCenter)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        # Subtag grid (built once, initially hidden)
        self._grid_host = TagGridHost(
            category=category,
            taxonomy=taxonomy,
            chips=chips,
            root_tags=root_tags,
            branch_key=category,
            depth_offset=0,
            shelf_padding=False,
            parent=self,
        )
        self._grid_host.setVisible(False)
        layout.addWidget(self._grid_host)

        # Wire chip signals
        for tag, chip in chips.items():
            _cat = category
            chip.clicked.connect(
                lambda _=False, t=tag, c=_cat: self.chip_clicked.emit(t, c)
            )
            chip.contextMenuRequested.connect(self.chip_context_menu)
            chip.drag_session_started.connect(self.chip_drag_started)
            chip.drag_session_ended.connect(self.chip_drag_ended)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def category(self) -> str:
        """Category name for this section."""
        return self._category

    @property
    def grid_host(self) -> TagGridHost:
        """Underlying TagGridHost widget."""
        return self._grid_host

    def set_expanded(self, expanded: bool) -> None:
        """
        Show or hide the subtag grid without any layout rebuild.

        Args:
            expanded: True to show subtags, False to collapse.
        """
        self._grid_host.setVisible(expanded)

    def is_expanded(self) -> bool:
        """
        Return whether the subtag grid is currently visible.

        Uses ``not isHidden()`` rather than ``isVisible()`` so the check
        works even before the parent widget is shown (Qt propagates
        visibility only after the top-level window is shown).

        Returns:
            bool: True if expanded.
        """
        return not self._grid_host.isHidden()

    def update_header_chip(
        self, is_active: bool, has_children: bool, cell_w: int
    ) -> None:
        """
        Refresh the category header chip appearance.

        Args:
            is_active: Whether the category filter is active (chip is green).
            has_children: Whether the category has subtags.
            cell_w: Width for the category chip.
        """
        apply_chip_style(
            self._category_chip,
            branch_key=self._category,
            depth=0,
            active=is_active,
            selected_for_drag=False,
        )
        label = _with_expand_icon(
            self._category_chip.property("baseLabel") or self._category,
            has_children,
            self.is_expanded(),
        )
        self._category_chip.setText(label)
        self._category_chip.set_cell_width(cell_w, min_w=cell_w)

    def set_category_chip_width(self, width: int) -> None:
        """
        Set the fixed pixel width of the category header chip.

        Args:
            width: Target chip width (centered in the section).
        """
        self._category_chip.set_cell_width(width, min_w=width)

    def apply_active_subtags(self, active_subtags: Set[str]) -> None:
        """
        Propagate active subtag state to child grids (show/hide child blocks).

        Args:
            active_subtags: Active subtags for this category.
        """
        self._grid_host.apply_active_subtags(active_subtags)

    def update_chip_states(
        self,
        active_subtags: Set[str],
        selection: Set[str],
        parent_select_mode: bool,
        tags_to_parent: Set[str],
    ) -> None:
        """
        Refresh all subtag chip visual states.

        Args:
            active_subtags: Active subtag set for this category.
            selection: Tags in drag selection.
            parent_select_mode: Whether reparent mode is active.
            tags_to_parent: Tags being moved (grayed out).
        """
        self._grid_host.update_chip_states(
            active_subtags, selection, parent_select_mode, tags_to_parent
        )

    def apply_cell_width(self, cell_w: int) -> None:
        """
        Propagate a new cell width to all subtag chips.

        Args:
            cell_w: Pixel width for each chip.
        """
        self._grid_host.apply_cell_width(cell_w)


# ---------------------------------------------------------------------------
# ShelfSection
# ---------------------------------------------------------------------------

class ShelfSection(QWidget):
    """
    Always-expanded shelf section (Camera-Angle, Miscellaneous, user shelves…).

    Uses a ``QLabel`` header so mouse clicks pass through to the viewport for
    rubber-band selection, while drops still route correctly via Qt's drop system.

    Signals:
        chip_clicked: Emitted with (tag_name, shelf_name) on chip click.
        chip_context_menu: Emitted with tag_name on right-click.
        chip_drag_started: Emitted when a DnD drag begins.
        chip_drag_ended: Emitted when a DnD drag ends.
    """

    chip_clicked = Signal(str, str)        # (tag_name, shelf_name)
    chip_context_menu = Signal(str)        # tag_name
    chip_drag_started = Signal()
    chip_drag_ended = Signal()

    def __init__(
        self,
        shelf_name: str,
        taxonomy: TagLibraryTaxonomy,
        chips: Dict[str, WrappingDraggableTagButton],
        root_tags: List[str],
        parent: Optional[QWidget] = None,
    ) -> None:
        """
        Args:
            shelf_name: Shelf title including trailing colon (e.g. "Camera-Angle:").
            taxonomy: Full library taxonomy.
            chips: Dict tag → chip widget for this shelf.
            root_tags: Ordered root-level tags in this shelf.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._shelf_name = shelf_name

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Shelf header label (not a button — passes mouse events to viewport)
        self._header = QLabel(shelf_name)
        self._header.setObjectName("TagGridButton")
        self._header.setCursor(Qt.ArrowCursor)
        self._header.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self._header.setStyleSheet(
            f"QLabel#TagGridButton {{"
            f" font-weight: 600;"
            f" font-size: {TAG_LIBRARY_FONT_SHELF_TITLE_PX}px;"
            f" letter-spacing: 0.4px;"
            f" padding: 6px 4px 4px 4px;"
            f" background-color: transparent;"
            f" color: #c8c2d6;"
            f"}}"
        )
        self._header.setProperty("tagGridRole", "category")
        self._header.setProperty("tagGridKey", shelf_name)
        layout.addWidget(self._header)

        # Drop zone frame + shelf grid
        drop_frame = QFrame()
        drop_frame.setObjectName("TagDropZone")
        drop_frame.setFrameShape(QFrame.NoFrame)
        drop_frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        drop_frame.setMinimumHeight(40)
        drop_frame.setStyleSheet(
            "QFrame#TagDropZone {"
            " border: 1px dashed rgba(255, 255, 255, 0.12);"
            " border-radius: 10px;"
            " background: rgba(0, 0, 0, 0.12);"
            "}"
        )
        drop_frame.setProperty("tagGridRole", "category")
        drop_frame.setProperty("tagGridKey", shelf_name)
        drop_frame_layout = QVBoxLayout(drop_frame)
        drop_frame_layout.setContentsMargins(0, 0, 0, 0)
        drop_frame_layout.setSpacing(0)

        self._grid_host = TagGridHost(
            category=shelf_name,
            taxonomy=taxonomy,
            chips=chips,
            root_tags=root_tags,
            branch_key=shelf_name,
            depth_offset=0,
            shelf_padding=True,
            parent=drop_frame,
        )
        drop_frame_layout.addWidget(self._grid_host)
        layout.addWidget(drop_frame)

        # Wire chip signals
        for tag, chip in chips.items():
            _shelf = shelf_name
            chip.clicked.connect(
                lambda _=False, t=tag, s=_shelf: self.chip_clicked.emit(t, s)
            )
            chip.contextMenuRequested.connect(self.chip_context_menu)
            chip.drag_session_started.connect(self.chip_drag_started)
            chip.drag_session_ended.connect(self.chip_drag_ended)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def shelf_name(self) -> str:
        """Shelf name for this section."""
        return self._shelf_name

    @property
    def grid_host(self) -> TagGridHost:
        """Underlying TagGridHost."""
        return self._grid_host

    def set_header_width(self, width: int) -> None:
        """
        Set the header label width.

        Args:
            width: Pixel width.
        """
        self._header.setFixedWidth(width)

    def update_chip_states(
        self,
        active_subtags: Set[str],
        selection: Set[str],
        parent_select_mode: bool,
        tags_to_parent: Set[str],
    ) -> None:
        """
        Refresh all chip visual states for this shelf.

        Args:
            active_subtags: Active tags in this shelf.
            selection: Tags in drag selection.
            parent_select_mode: Whether reparent mode is active.
            tags_to_parent: Tags being moved (grayed out).
        """
        self._grid_host.update_chip_states(
            active_subtags, selection, parent_select_mode, tags_to_parent
        )

    def apply_cell_width(self, cell_w: int) -> None:
        """
        Propagate a new cell width to all chips in this shelf.

        Args:
            cell_w: Pixel width for each chip.
        """
        self._grid_host.apply_cell_width(cell_w)
