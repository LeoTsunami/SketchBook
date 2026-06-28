"""
TagGridHost – 3-column flow grid of tag chips, pre-built once at load time.

Layout follows the legacy ``_sync_tag_grid_state`` index algorithm:

* Tags flow left-to-right, 3 per row.
* When an expandable tag is active, a full-width ``TagHierarchyFrame`` is
  inserted on the next row and tags that followed are pushed down.
* Chips and frames are repositioned in a single ``QGridLayout`` — never
  destroyed on expand/collapse.
"""
from __future__ import annotations

from typing import Dict, List, Literal, Optional, Set, Tuple, Union

from qtpy.QtCore import Qt, QRect
from qtpy.QtWidgets import (
    QFrame,
    QGridLayout,
    QSizePolicy,
    QWidget,
)

from gui.tag_library.constants import (
    TAG_LIBRARY_TAG_GRID_COLUMNS,
    TAG_LIBRARY_TAG_GRID_SPACING_PX,
    TAG_LIBRARY_TAG_CELL_ALIGN,
    TAG_LIBRARY_SHELF_GRID_PADDING_PX,
)
from gui.tag_library.chip import (
    WrappingDraggableTagButton,
    apply_chip_style,
)
from gui.tag_library.state import TagLibraryTaxonomy


COLS = TAG_LIBRARY_TAG_GRID_COLUMNS

ColTag = Tuple[int, str]
LayoutLine = Union[
    Tuple[Literal["row"], List[ColTag]],
    Tuple[Literal["frame"], str],
]


class TagGridHost(QWidget):
    """
    Flowing 3-column grid for one level of tags inside a category or shelf.

    Args:
        category: Category / shelf name.
        taxonomy: Full library taxonomy.
        chips: Shared dict tag → chip widget for this category.
        root_tags: Ordered tags at this hierarchy level.
        branch_key: Hue branch key for chip colours.
        depth_offset: Nesting depth (0 = direct subtags of category).
        shelf_padding: Extra padding for shelf drop zones.
    """

    def __init__(
        self,
        category: str,
        taxonomy: TagLibraryTaxonomy,
        chips: Dict[str, WrappingDraggableTagButton],
        root_tags: List[str],
        branch_key: str,
        depth_offset: int = 0,
        shelf_padding: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._category = category
        self._taxonomy = taxonomy
        self._chips = chips
        self._branch_key = branch_key
        self._depth_offset = depth_offset
        self._root_tags = list(root_tags)
        self._local_tags: Set[str] = set()
        self._cell_width = 0
        self._last_active_subtags: Set[str] = set()
        self._cached_lines: Optional[List[LayoutLine]] = None
        self._child_frames: Dict[str, QFrame] = {}
        self._child_grids: Dict[str, "TagGridHost"] = {}

        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self.setMinimumHeight(0)

        padding = TAG_LIBRARY_SHELF_GRID_PADDING_PX if shelf_padding else 0
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(padding, padding, padding, padding)
        self._grid.setHorizontalSpacing(TAG_LIBRARY_TAG_GRID_SPACING_PX)
        self._grid.setVerticalSpacing(6)
        for col in range(COLS):
            self._grid.setColumnStretch(col, 1)

        for tag in self._root_tags:
            if tag in self._chips and self._taxonomy.has_children(tag):
                self._ensure_child_frame(tag)

        self._relayout(set())

    @staticmethod
    def _chip_is_alive(chip: Optional[WrappingDraggableTagButton]) -> bool:
        """
        Return True when the Qt C++ backing object for *chip* still exists.

        Args:
            chip: Chip widget to probe.

        Returns:
            bool: False after the underlying QObject was destroyed.
        """
        if chip is None:
            return False
        try:
            chip.objectName()
            return True
        except RuntimeError:
            return False

    def _park_widget(self, widget: QWidget) -> None:
        """
        Remove *widget* from the grid while keeping it alive off-layout.

        Args:
            widget: Chip or hierarchy frame to stash on this host.
        """
        widget.setParent(self)
        widget.hide()

    def _clear_grid(self) -> None:
        """Detach every item from the grid without destroying chips or frames."""
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget() if item else None
            if widget is not None:
                self._park_widget(widget)

    # ------------------------------------------------------------------
    # Layout computation (legacy idx algorithm)
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_layout_lines(
        root_tags: List[str],
        taxonomy: TagLibraryTaxonomy,
        active_subtags: Set[str],
    ) -> List[LayoutLine]:
        """
        Compute row / frame sequence using the legacy virtual-index algorithm.

        When a tag with children is active, the next row is reserved for its
        hierarchy frame and following tags are pushed down by one row.

        Args:
            root_tags: Tags at this hierarchy level in display order.
            taxonomy: Library taxonomy.
            active_subtags: Currently expanded parent tags.

        Returns:
            Ordered list of layout lines (chip rows and frames).
        """
        row_buckets: Dict[int, List[Tuple[int, str]]] = {}
        frame_rows: Dict[int, str] = {}
        idx = 0

        for tag in root_tags:
            row, col = divmod(idx, COLS)
            row_buckets.setdefault(row, []).append((col, tag))
            idx += 1

            if taxonomy.has_children(tag) and tag in active_subtags:
                aligned_idx = ((idx + COLS - 1) // COLS) * COLS
                block_row = aligned_idx // COLS
                frame_rows[block_row] = tag
                idx = aligned_idx + COLS

        all_rows = sorted(set(row_buckets) | set(frame_rows))
        lines: List[LayoutLine] = []
        for row_num in all_rows:
            if row_num in row_buckets:
                cols = sorted(row_buckets[row_num], key=lambda x: x[0])
                lines.append(("row", cols))
            if row_num in frame_rows:
                lines.append(("frame", frame_rows[row_num]))
        return lines

    def _apply_column_widths(self) -> None:
        """Sync grid column minimum widths with the current cell width."""
        if self._cell_width <= 0:
            return
        for col in range(COLS):
            self._grid.setColumnMinimumWidth(col, self._cell_width)

    def _relayout(self, active_subtags: Set[str]) -> None:
        """
        Reposition chips and frames in the grid for the current expand state.

        Args:
            active_subtags: Expanded parent tags at this category level.
        """
        lines = self._compute_layout_lines(
            self._root_tags, self._taxonomy, active_subtags
        )
        if lines == self._cached_lines:
            return

        self._last_active_subtags = set(active_subtags)
        self._cached_lines = list(lines)
        self._clear_grid()
        self._local_tags = set()

        grid_row = 0
        for kind, payload in lines:
            if kind == "row":
                for col, tag in payload:
                    if col < 0 or col >= COLS:
                        continue
                    chip = self._chips.get(tag)
                    if chip is None or not self._chip_is_alive(chip):
                        continue
                    self._local_tags.add(tag)
                    chip.setParent(self)
                    chip.show()
                    self._grid.addWidget(chip, grid_row, col, TAG_LIBRARY_TAG_CELL_ALIGN)
                grid_row += 1
            else:
                parent_tag = payload
                frame = self._ensure_child_frame(parent_tag)
                expanded = parent_tag in active_subtags
                frame.setParent(self)
                frame.setVisible(expanded)
                if expanded:
                    frame.show()
                self._grid.addWidget(frame, grid_row, 0, 1, COLS)
                grid_row += 1
                child_grid = self._child_grids.get(parent_tag)
                if child_grid is not None:
                    child_grid._relayout(active_subtags)

        self._apply_column_widths()
        self._grid.invalidate()
        self.updateGeometry()

    def _ensure_child_frame(self, parent_tag: str) -> QFrame:
        """
        Return (and create if needed) the hierarchy frame for *parent_tag*.

        Args:
            parent_tag: Parent tag name.

        Returns:
            QFrame wrapping the nested TagGridHost.
        """
        existing = self._child_frames.get(parent_tag)
        if existing is not None:
            return existing

        children = self._taxonomy.get_children(parent_tag)
        child_root_tags = [
            t for t in children if self._taxonomy.get_parent(t) == parent_tag
        ]
        frame, child_grid = self._make_hierarchy_frame(parent_tag, child_root_tags)
        self._child_frames[parent_tag] = frame
        self._child_grids[parent_tag] = child_grid
        return frame

    def _make_hierarchy_frame(
        self, parent_tag: str, child_root_tags: List[str]
    ) -> tuple[QFrame, "TagGridHost"]:
        """
        Build a bordered frame containing a nested child grid.

        Args:
            parent_tag: Parent tag name (determines border depth).
            child_root_tags: Direct children to display inside the frame.

        Returns:
            tuple: (frame, child TagGridHost).
        """
        frame = QFrame(self)
        frame.setObjectName("TagHierarchyFrame")
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setFocusPolicy(Qt.NoFocus)
        frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        frame.setStyleSheet(
            "QFrame#TagHierarchyFrame { "
            "border: 1px solid rgba(255,255,255,0.14); "
            "border-radius: 10px; "
            "padding: 0; "
            "background: rgba(0, 0, 0, 0.1); "
            "}"
        )
        frame_layout = QGridLayout(frame)
        frame_layout.setContentsMargins(3, 4, 3, 4)
        frame_layout.setHorizontalSpacing(TAG_LIBRARY_TAG_GRID_SPACING_PX)
        frame_layout.setVerticalSpacing(6)

        child_grid = TagGridHost(
            category=self._category,
            taxonomy=self._taxonomy,
            chips=self._chips,
            root_tags=child_root_tags,
            branch_key=self._branch_key,
            depth_offset=self._depth_offset + 1,
            shelf_padding=False,
            parent=frame,
        )
        child_grid.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        frame_layout.addWidget(child_grid, 0, 0, 1, COLS)
        frame.setVisible(False)
        return frame, child_grid

    def _tag_depth(self, tag: str, visited: Optional[Set[str]] = None) -> int:
        """
        Return visual nesting depth of *tag* within the category.

        Args:
            tag: Tag name.
            visited: Cycle guard.

        Returns:
            int: 0 for root subtags, 1+ for nested.
        """
        parent = self._taxonomy.get_parent(tag)
        if not parent:
            return 0
        if visited is None:
            visited = set()
        if tag in visited:
            return 0
        visited.add(tag)
        return 1 + self._tag_depth(parent, visited)

    # ------------------------------------------------------------------
    # State update
    # ------------------------------------------------------------------

    def apply_active_subtags(self, active_subtags: Set[str]) -> None:
        """
        Re-layout this grid for the current expand/collapse state.

        Args:
            active_subtags: Active subtag names for this category.
        """
        self._relayout(active_subtags)

    def invalidate_layout_cache(self) -> None:
        """
        Force the next ``apply_active_subtags`` call to reposition widgets.

        Called after a full panel reload when chip instances are replaced.
        """
        self._cached_lines = None
        for child_grid in self._child_grids.values():
            child_grid.invalidate_layout_cache()

    def update_chip_states(
        self,
        active_subtags: Set[str],
        selection: Set[str],
        parent_select_mode: bool,
        tags_to_parent: Set[str],
    ) -> None:
        """
        Refresh chip visuals for tags owned by this grid tree.

        Args:
            active_subtags: Active filter tags.
            selection: Tags selected for multi-drag.
            parent_select_mode: Reparent mode active.
            tags_to_parent: Tags being reparented (grayed out).
        """
        for tag in self._local_tags:
            chip = self._chips.get(tag)
            if chip is None or not self._chip_is_alive(chip):
                continue
            is_active = tag in active_subtags
            in_selection = tag in selection
            depth = self._depth_offset + 1 + self._tag_depth(tag)
            apply_chip_style(
                chip,
                branch_key=self._branch_key,
                depth=depth,
                active=is_active,
                selected_for_drag=in_selection,
            )
            has_children = self._taxonomy.has_children(tag)
            expanded = is_active and has_children
            base_label = chip.property("baseLabel") or ""
            label = _with_expand_icon(base_label, has_children, expanded)
            if chip.text() != label:
                chip.setText(label)

            if parent_select_mode and tag in tags_to_parent:
                chip.setEnabled(False)
                chip.setStyleSheet(
                    "QPushButton { text-align: left; padding: 2px 4px; "
                    "opacity: 0.6; background-color: #444; color: #888; }"
                )
            else:
                chip.setEnabled(True)

        for child_grid in self._child_grids.values():
            child_grid.update_chip_states(
                active_subtags, selection, parent_select_mode, tags_to_parent
            )

    # ------------------------------------------------------------------
    # Width propagation
    # ------------------------------------------------------------------

    def apply_cell_width(self, cell_w: int) -> None:
        """
        Set chip width for every tag in this grid tree.

        Args:
            cell_w: Pixel width per column.
        """
        if cell_w <= 0:
            return
        self._cell_width = cell_w
        for tag in self._root_tags:
            chip = self._chips.get(tag)
            if chip is not None and self._chip_is_alive(chip):
                chip.set_cell_width(cell_w)
        for child_grid in self._child_grids.values():
            child_grid.apply_cell_width(cell_w)
        self._apply_column_widths()

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def get_chip(self, tag: str) -> Optional[WrappingDraggableTagButton]:
        """
        Return the chip for *tag* if it belongs to this category.

        Args:
            tag: Tag name.

        Returns:
            Chip widget or None.
        """
        if tag in self._chips:
            return self._chips.get(tag)
        for child_grid in self._child_grids.values():
            found = child_grid.get_chip(tag)
            if found is not None:
                return found
        return None

    def visible_chip_rects(
        self, viewport_widget: QWidget
    ) -> List[tuple[str, QRect]]:
        """
        Return (tag, viewport rect) for visible chips in this grid tree.

        Args:
            viewport_widget: Coordinate space for returned rects.

        Returns:
            List of (tag_name, QRect).
        """
        result: List[tuple[str, QRect]] = []
        for tag in self._local_tags:
            chip = self._chips.get(tag)
            if chip is None or chip.isHidden():
                continue
            tl = chip.mapToGlobal(chip.rect().topLeft())
            vp_tl = viewport_widget.mapFromGlobal(tl)
            result.append((tag, QRect(vp_tl, chip.size())))
        for child_grid in self._child_grids.values():
            result.extend(child_grid.visible_chip_rects(viewport_widget))
        return result


def _with_expand_icon(label: str, has_children: bool, expanded: bool) -> str:
    """
    Return *label* with a ▼ / ▶ suffix when the tag has children.

    Args:
        label: Display name.
        has_children: Whether nested tags exist.
        expanded: Whether children are currently shown.

    Returns:
        str: Decorated label.
    """
    if not has_children:
        return label
    return f"{label} {'▼' if expanded else '▶'}"
