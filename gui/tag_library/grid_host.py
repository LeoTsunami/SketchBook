"""
TagGridHost – 3-column flow grid of tag chips, pre-built once at load time.

Layout mirrors the legacy ``_sync_tag_grid_state`` behaviour:

* Tags flow left-to-right in rows of 3.
* When a tag with children is expanded, a ``TagHierarchyFrame`` (bordered
  block) is inserted on the next row below the parent's row, containing a
  nested ``TagGridHost`` for its children.
* Expand/collapse is ``setVisible()`` on the frame only — no layout rebuild.

Anatomy (root tags [Terrestrial*, Insect, Bird, …]):

    Row 0: [Terrestrial] [Insect] [Bird]
    Row 1: ┌─ TagHierarchyFrame (Terrestrial children, hidden until active) ─┐
           │  [Felin] [Aquatic] […]                                         │
           └──────────────────────────────────────────────────────────────────┘
    Row 2: [Monkey] [Horse] [Elephant]
    …
"""
from __future__ import annotations

from typing import Dict, List, Optional, Set

from qtpy.QtCore import Qt, QRect
from qtpy.QtWidgets import (
    QFrame,
    QGridLayout,
    QSizePolicy,
    QVBoxLayout,
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
        self._local_tags: Set[str] = set()
        # parent_tag → bordered frame wrapping the child TagGridHost
        self._child_frames: Dict[str, QFrame] = {}
        self._child_grids: Dict[str, "TagGridHost"] = {}

        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self.setMinimumHeight(0)

        padding = TAG_LIBRARY_SHELF_GRID_PADDING_PX if shelf_padding else 0
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(padding, padding, padding, padding)
        self._layout.setSpacing(6)

        self._build(root_tags)

    # ------------------------------------------------------------------
    # Build (called once)
    # ------------------------------------------------------------------

    def _build(self, root_tags: List[str]) -> None:
        """
        Lay out *root_tags* in rows of 3 with optional hierarchy frames.

        Args:
            root_tags: Tags to place at this level.
        """
        row_widget: Optional[QWidget] = None
        row_layout: Optional[QGridLayout] = None
        col = 0

        def _flush_row() -> None:
            nonlocal row_widget, row_layout, col
            if row_widget is not None:
                self._layout.addWidget(row_widget)
            row_widget = None
            row_layout = None
            col = 0

        def _ensure_row() -> QGridLayout:
            nonlocal row_widget, row_layout
            if row_layout is None:
                row_widget = QWidget(self)
                row_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
                row_layout = QGridLayout(row_widget)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setHorizontalSpacing(TAG_LIBRARY_TAG_GRID_SPACING_PX)
                row_layout.setVerticalSpacing(0)
            return row_layout

        for tag in root_tags:
            chip = self._chips.get(tag)
            if chip is None:
                continue

            self._local_tags.add(tag)
            grid = _ensure_row()
            grid.addWidget(chip, 0, col, TAG_LIBRARY_TAG_CELL_ALIGN)
            col += 1

            if col >= COLS:
                _flush_row()

            if not self._taxonomy.has_children(tag):
                continue

            # Close the current chip row, then add a full-width hierarchy block.
            _flush_row()

            children = self._taxonomy.get_children(tag)
            child_root_tags = [
                t for t in children if self._taxonomy.get_parent(t) == tag
            ]
            frame, child_grid = self._make_hierarchy_frame(tag, child_root_tags)
            self._layout.addWidget(frame)
            self._child_frames[tag] = frame
            self._child_grids[tag] = child_grid

        _flush_row()

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
        depth = self._depth_offset + 2
        frame = QFrame(self)
        frame.setObjectName("TagHierarchyFrame")
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setFocusPolicy(Qt.NoFocus)
        frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        frame.setStyleSheet(
            "QFrame#TagHierarchyFrame { "
            f"border: {min(depth, 3)}px solid rgba(255,255,255,0.45); "
            "border-radius: 6px; "
            "padding: 0; "
            "background: transparent; "
            "}"
        )
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(3, 4, 3, 4)
        frame_layout.setSpacing(6)

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
        frame_layout.addWidget(child_grid)
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
    # State update (no layout rebuild)
    # ------------------------------------------------------------------

    def apply_active_subtags(self, active_subtags: Set[str]) -> None:
        """
        Show / hide hierarchy frames for expanded parent tags.

        Args:
            active_subtags: Active subtag names for this category.
        """
        for tag, frame in self._child_frames.items():
            should_show = tag in active_subtags
            if frame.isHidden() == should_show:
                frame.setVisible(should_show)
            child_grid = self._child_grids.get(tag)
            if should_show and child_grid is not None:
                child_grid.apply_active_subtags(active_subtags)

    def update_chip_states(
        self,
        active_subtags: Set[str],
        selection: Set[str],
        parent_select_mode: bool,
        tags_to_parent: Set[str],
    ) -> None:
        """
        Refresh chip visuals for tags owned by this grid level.

        Args:
            active_subtags: Active filter tags.
            selection: Tags selected for multi-drag.
            parent_select_mode: Reparent mode active.
            tags_to_parent: Tags being reparented (grayed out).
        """
        for tag in self._local_tags:
            chip = self._chips.get(tag)
            if chip is None:
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
        Set chip width for every tag placed in this grid and descendants.

        Args:
            cell_w: Pixel width per column.
        """
        for tag in self._local_tags:
            chip = self._chips.get(tag)
            if chip is not None:
                chip.set_cell_width(cell_w)
        for child_grid in self._child_grids.values():
            child_grid.apply_cell_width(cell_w)

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
        if tag in self._local_tags:
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
