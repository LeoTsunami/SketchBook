"""
TagLibraryPanel – the full tag library widget.

Replaces the _load_tags_into_grid / _sync_tag_grid_state / _subcategory_*
machinery in MainWindow.  The panel:

  • Builds all CategorySection / ShelfSection widgets once at load time.
  • Handles chip clicks (expand categories, toggle subtag filters) locally
    without any QGridLayout rebuild.
  • Emits ``filter_changed`` so MainWindow can refilter images.
  • Emits action signals (tag_rename_requested, tag_delete_requested, …) so
    MainWindow performs the heavyweight work (DB workers, config saves).

DnD session management (autoscroll, panel fold/reopen) is delegated back to
MainWindow via ``drag_session_started`` / ``drag_session_ended`` signals; the
infrastructure already lives there and uses the panel overlay.
"""
from __future__ import annotations

import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from qtpy.QtCore import Qt, QPoint, QRect, QTimer, Signal
from qtpy.QtGui import QColor, QCursor, QIcon
from qtpy.QtCore import QStringListModel
from qtpy.QtWidgets import (
    QApplication,
    QCompleter,
    QFrame,
    QGridLayout,
    QLabel,
    QMenu,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core import user_tags_config
from core.settings import settings
from gui.icon_utils import find_tag_icon, invert_icon
from gui.tag_shelves import (
    MISCELLANEOUS_SHELF,
    is_tag_shelf,
    load_default_tags_taxonomy,
    merge_custom_shelves,
    parse_category_tags,
)
from gui.tag_library.chip import (
    WrappingDraggableTagButton,
    apply_chip_style,
)
from gui.tag_library.constants import (
    TAG_LIBRARY_CATEGORY_ICON_PX,
    TAG_LIBRARY_CATEGORY_MIN_HEIGHT_PX,
    TAG_LIBRARY_CATEGORY_WIDTH_TRIM_PX,
    TAG_LIBRARY_DROP_ZONE_BORDER_PX,
    TAG_LIBRARY_FONT_CATEGORY_PX,
    TAG_LIBRARY_MIME,
    TAG_LIBRARY_MULTI_MIME,
    TAG_LIBRARY_OVERLAY_HORIZONTAL_MARGIN_PX,
    TAG_LIBRARY_SHELF_GRID_PADDING_PX,
    TAG_LIBRARY_TAG_CELL_MIN_WIDTH_PX,
    TAG_LIBRARY_TAG_GRID_SPACING_PX,
    TAG_LIBRARY_TAG_ICON_PX,
    TAG_LIBRARY_TAG_MIN_HEIGHT_PX,
    TAG_LIBRARY_VIEWPORT_RIGHT_GUTTER_PX,
)
from gui.tag_library.grid_host import TagGridHost, _with_expand_icon
from gui.tag_library.section import CategorySection, ShelfSection
from gui.tag_library.state import TagFilterState, TagLibraryTaxonomy


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _collect_subtags(data: Any, collected: List[str]) -> None:
    """Recursively collect all tag names from the taxonomy data structure."""
    if isinstance(data, list):
        for item in data:
            _collect_subtags(item, collected)
    elif isinstance(data, dict):
        for key, value in data.items():
            collected.append(key)
            _collect_subtags(value, collected)
    elif isinstance(data, str):
        collected.append(data)


def _append_taxonomy_child(
    children_map: Dict[str, List[str]], parent: str, child: str
) -> None:
    """
    Append *child* under *parent* in children_map without duplicates.

    Args:
        children_map: Mutable parent → children list map.
        parent: Parent tag name.
        child: Child tag name.
    """
    children = children_map.setdefault(parent, [])
    if child not in children:
        children.append(child)


def _walk_taxonomy_children(
    data: Any, parent: Optional[str], children_map: Dict[str, List[str]]
) -> None:
    """
    Record parent/child edges from nested default_tags.json values.

    Args:
        data: Category tags value (list, dict, or str).
        parent: Parent tag name, or None at the category root.
        children_map: Map to populate in-place.
    """
    if isinstance(data, list):
        for item in data:
            _walk_taxonomy_children(item, parent, children_map)
    elif isinstance(data, dict):
        for key, value in data.items():
            if parent is not None:
                _append_taxonomy_child(children_map, parent, key)
            _walk_taxonomy_children(value, key, children_map)
    elif isinstance(data, str):
        if parent is not None:
            _append_taxonomy_child(children_map, parent, data)


def _build_subtags_for_category(
    category: str,
    default_subtags: List[str],
    user_tags: List[str],
    placements: Dict[str, Any],
) -> List[str]:
    """
    Build the ordered subtag list for a category.

    Default tags come first; user tags with ``{"category": cat}`` placement are
    appended; user tags with ``{"parent_tag": …}`` are inserted after their
    parent (multiple passes handle chains).

    Args:
        category: Category name.
        default_subtags: Tags from the taxonomy JSON.
        user_tags: All user-owned tags.
        placements: User tag placement config.

    Returns:
        List[str]: Ordered subtag names without duplicates.
    """
    result = list(dict.fromkeys(default_subtags))
    for ut in user_tags:
        pl = placements.get(ut)
        if pl is None:
            if category == MISCELLANEOUS_SHELF:
                result.append(ut)
            continue
        if pl.get("category") == category and ut not in result:
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
                result.insert(result.index(parent) + 1, ut)
                changed = True
    return result


def _normalize_tag(tag: str) -> str:
    """Normalize tag for case- and separator-insensitive match."""
    return tag.lower().replace(" ", "").replace("-", "").replace("_", "")


# ---------------------------------------------------------------------------
# TagLibraryPanel
# ---------------------------------------------------------------------------

class TagLibraryPanel(QWidget):
    """
    Full tag library panel: scroll area containing all category / shelf sections.

    Signals:
        filter_changed: Emitted whenever the active filter changes.
        tag_delete_requested: User requested deletion of one or more tags.
        tag_rename_requested: User requested rename (old_name, new_name).
        tag_icon_change_requested: User requested icon change (tag_name).
        tag_reparent_requested: User chose 'Parent to tag…' (tags, placement).
        shelf_create_requested: User clicked '+ Create shelf' (name, filter_mode).
        tag_create_requested: User clicked '+ Create tag' (name, icon_filename).
        drag_session_started: A chip QDrag has started.
        drag_session_ended: A chip QDrag has ended.
        tag_drop_on_grid: User dropped a tag onto a category/tag target
                           (dropped_tag, role, key).
    """

    filter_changed = Signal(object)                  # TagFilterState
    tag_delete_requested = Signal(object)            # set[str]
    tag_rename_requested = Signal(str, str)          # old_name, new_name
    tag_icon_change_requested = Signal(str)          # tag_name
    tag_reparent_requested = Signal(object, object)  # set[str] tags, dict placement
    shelf_create_requested = Signal(str, str)        # name, filter_mode
    tag_create_requested = Signal(str, str)          # name, icon_filename
    drag_session_started = Signal()
    drag_session_ended = Signal()
    tag_drop_on_grid = Signal(str, str, str)         # dropped_tag, role, key

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # ---- filter state (owned by panel) ----
        self._active_categories: Set[str] = set()
        self._active_subtags: Dict[str, Set[str]] = {}
        self._tag_library_selection: Set[str] = set()
        self._last_selected_tag: Optional[str] = None
        self._tag_drag_in_progress: bool = False

        # ---- parent-select mode ----
        self._parent_select_mode: bool = False
        self._tags_to_parent: Set[str] = set()
        self._parent_select_key: Optional[str] = None
        self._parent_select_role: Optional[str] = None

        # ---- taxonomy + widget refs (built at load time) ----
        self._taxonomy: Optional[TagLibraryTaxonomy] = None
        self._category_sections: Dict[str, CategorySection] = {}
        self._shelf_sections: Dict[str, ShelfSection] = {}
        # All chips indexed by tag name (for icon updates, hit-testing)
        self._all_chips: Dict[str, WrappingDraggableTagButton] = {}
        # Category-header chips
        self._header_chips: Dict[str, WrappingDraggableTagButton] = {}
        # drop-highlight widget
        self._drop_highlight_widget: Optional[QWidget] = None

        # ---- user config (refreshed on each load) ----
        self._user_tags_config: Dict[str, Any] = {}
        self._user_tags: Set[str] = set()
        self._tag_shelf_filter_modes: Dict[str, str] = {}

        # ---- layout ----
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll_area.setFrameShape(QFrame.NoFrame)

        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 6, 0, 0)
        self._content_layout.setSpacing(8)
        self._content_layout.addStretch(1)

        self._scroll_area.setWidget(self._content)
        outer.addWidget(self._scroll_area)

        # Autoscroll during drag
        self._drag_scroll_timer: Optional[QTimer] = None

    # ------------------------------------------------------------------
    # Public API – load / reload
    # ------------------------------------------------------------------

    def load(
        self,
        user_tags: Set[str],
        user_tags_config_data: Dict[str, Any],
        restore_categories: Optional[Set[str]] = None,
        restore_subtags: Optional[Dict[str, Set[str]]] = None,
    ) -> None:
        """
        Build (or rebuild) the entire widget tree from taxonomy + user config.

        Called once at startup and again after structural changes (tag
        reparent, shelf create, tag delete).  Widget tree is fully rebuilt;
        existing filter state can be restored via the ``restore_*`` args.

        Args:
            user_tags: Set of user-owned tag names.
            user_tags_config_data: Loaded user_tags_config dict.
            restore_categories: Active category set to restore after reload.
            restore_subtags: Active subtag dict to restore after reload.
        """
        self._user_tags_config = user_tags_config_data
        self._user_tags = user_tags
        placements = user_tags_config_data.get("placements", {})
        user_tags_list = sorted(user_tags)

        # --- Clear existing sections ---
        self._category_sections.clear()
        self._shelf_sections.clear()
        self._all_chips.clear()
        self._header_chips.clear()

        # Remove all section widgets from the content layout (keep the stretch)
        while self._content_layout.count() > 1:
            item = self._content_layout.takeAt(0)
            w = item.widget() if item else None
            if w:
                w.deleteLater()

        # --- Load taxonomy ---
        default_tags_path = (
            Path(__file__).parent.parent / "ressources" / "default_tags.json"
        )
        if not default_tags_path.exists():
            return

        try:
            taxonomy_raw, self._tag_shelf_filter_modes = load_default_tags_taxonomy(
                default_tags_path
            )
        except Exception:
            traceback.print_exc()
            return

        taxonomy_raw = merge_custom_shelves(
            taxonomy_raw,
            self._tag_shelf_filter_modes,
            user_tags_config_data.get("custom_shelves", []),
        )

        # --- Build TagLibraryTaxonomy ---
        taxonomy = TagLibraryTaxonomy()
        taxonomy.placements = dict(placements)
        taxonomy.user_tags = set(user_tags)
        taxonomy.shelf_filter_modes = dict(self._tag_shelf_filter_modes)

        for category, tags_value in taxonomy_raw.items():
            tags_data, _ = parse_category_tags(tags_value)
            flat: List[str] = []
            _collect_subtags(tags_data, flat)
            flat = list(dict.fromkeys(flat))
            ordered = _build_subtags_for_category(
                category, flat, user_tags_list, placements
            )
            taxonomy.categories_order.append(category)
            taxonomy.subtag_order[category] = ordered
            for tag in ordered:
                taxonomy.subtag_to_category[tag] = category

            # Parent/child edges from nested JSON + user placements
            _walk_taxonomy_children(tags_data, None, taxonomy.children_map)
        for tag, pl in placements.items():
            if isinstance(pl, dict) and "parent_tag" in pl:
                parent = pl["parent_tag"]
                _append_taxonomy_child(taxonomy.children_map, parent, tag)

        self._taxonomy = taxonomy

        # --- Build sections ---
        insert_idx = 0
        for category in taxonomy.categories_order:
            section_w = self._build_section(category, taxonomy, user_tags_list, placements)
            if section_w is not None:
                self._content_layout.insertWidget(insert_idx, section_w)
                insert_idx += 1

                # Separator
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.HLine)
                sep.setFrameShadow(QFrame.Shadow.Sunken)
                sep.setStyleSheet("QFrame { color: #666; }")
                self._content_layout.insertWidget(insert_idx, sep)
                insert_idx += 1

        # --- Restore filter state ---
        if restore_categories is not None:
            self._active_categories = set(restore_categories)
        if restore_subtags is not None:
            self._active_subtags = {k: set(v) for k, v in restore_subtags.items()}

        self._apply_all_states()
        QTimer.singleShot(0, self._apply_widths)

    # ------------------------------------------------------------------
    # Section construction
    # ------------------------------------------------------------------

    def _build_section(
        self,
        category: str,
        taxonomy: TagLibraryTaxonomy,
        user_tags_list: List[str],
        placements: Dict[str, Any],
    ) -> Optional[QWidget]:
        """
        Build one CategorySection or ShelfSection and register chips.

        Args:
            category: Category/shelf name.
            taxonomy: Library taxonomy.
            user_tags_list: Sorted list of user-owned tag names.
            placements: User tag placements.

        Returns:
            The built QWidget section, or None on failure.
        """
        ordered = taxonomy.subtag_order.get(category, [])
        chips: Dict[str, WrappingDraggableTagButton] = {}
        cell_w = self._compute_cell_width()
        cat_w = self._compute_category_width()

        # Build subtag chips
        for tag in ordered:
            chip = WrappingDraggableTagButton(tag, cell_w)
            chip.setObjectName("TagGridButton")
            chip.setProperty("baseLabel", tag)
            chip.setProperty("tagGridRole", "tag")
            chip.setProperty("tagGridKey", tag)
            is_user = tag in self._user_tags
            chip.setProperty("userTag", is_user)
            # Icon
            icon = find_tag_icon(
                tag, user_config=self._user_tags_config, icon_preview_override={}
            )
            if not icon.isNull():
                chip.setIcon(invert_icon(icon, TAG_LIBRARY_TAG_ICON_PX))
                chip.setIconSize(QIcon().actualSize(chip.sizeHint()))
            chips[tag] = chip
            self._all_chips[tag] = chip

        if is_tag_shelf(category):
            # Root tags for a shelf = tags that are NOT children of another tag
            root_tags = [t for t in ordered if taxonomy.get_parent(t) is None]
            section = ShelfSection(
                shelf_name=category,
                taxonomy=taxonomy,
                chips=chips,
                root_tags=root_tags,
            )
            section.chip_clicked.connect(self._on_shelf_chip_clicked)
            section.chip_context_menu.connect(self._on_chip_context_menu)
            section.chip_drag_started.connect(self._on_drag_started)
            section.chip_drag_ended.connect(self._on_drag_ended)
            section.set_header_width(cat_w)
            self._shelf_sections[category] = section
            return section
        else:
            # Build category header chip (full-width)
            header_chip = WrappingDraggableTagButton(category, cat_w)
            header_chip.setObjectName("TagGridButton")
            header_chip.setProperty("baseLabel", category)
            header_chip.setProperty("tagGridRole", "category")
            header_chip.setProperty("tagGridKey", category)
            header_chip.setProperty("tagGridCategory", True)
            header_chip.setProperty("userTag", False)
            cat_icon = find_tag_icon(
                category, user_config=self._user_tags_config, icon_preview_override={}
            )
            if not cat_icon.isNull():
                src_px = max(TAG_LIBRARY_CATEGORY_ICON_PX, TAG_LIBRARY_TAG_MIN_HEIGHT_PX)
                header_chip.setIcon(invert_icon(cat_icon, src_px))
            self._header_chips[category] = header_chip

            root_tags = [t for t in ordered if taxonomy.get_parent(t) is None]
            section = CategorySection(
                category=category,
                taxonomy=taxonomy,
                chips=chips,
                root_tags=root_tags,
                category_chip=header_chip,
            )
            section.header_clicked.connect(self._on_category_header_clicked)
            section.chip_clicked.connect(self._on_subtag_chip_clicked)
            section.chip_context_menu.connect(self._on_chip_context_menu)
            section.chip_drag_started.connect(self._on_drag_started)
            section.chip_drag_ended.connect(self._on_drag_ended)
            self._category_sections[category] = section
            return section

    # ------------------------------------------------------------------
    # Click handlers
    # ------------------------------------------------------------------

    def _on_category_header_clicked(self, category: str) -> None:
        """Toggle category expand / collapse and update filter."""
        if self._parent_select_mode:
            self._on_tag_clicked_in_parent_mode(category)
            return

        if category in self._active_categories:
            # Collapse
            self._active_categories.discard(category)
            self._active_subtags.pop(category, None)
        else:
            # Expand
            self._active_categories.add(category)
            self._active_subtags.setdefault(category, set())

        section = self._category_sections.get(category)
        if section:
            section.set_expanded(category in self._active_categories)
            section.update_header_chip(
                is_active=category in self._active_categories,
                has_children=bool(self._taxonomy and self._taxonomy.subtag_order.get(category)),
                cell_w=self._compute_category_width(),
            )
            active = self._active_subtags.get(category, set())
            section.apply_active_subtags(active)
            section.update_chip_states(
                active, self._tag_library_selection,
                self._parent_select_mode, self._tags_to_parent,
            )
        self._emit_filter()

    def _on_subtag_chip_clicked(self, tag: str, category: str) -> None:
        """Toggle a subtag filter and show/hide its child block."""
        if self._parent_select_mode:
            self._on_tag_clicked_in_parent_mode(tag, category)
            return

        if category not in self._active_categories:
            # Auto-expand the category
            self._active_categories.add(category)
            section = self._category_sections.get(category)
            if section:
                section.set_expanded(True)

        cat_subtags = self._active_subtags.setdefault(category, set())
        if tag in cat_subtags:
            cat_subtags.discard(tag)
        else:
            cat_subtags.add(tag)

        section = self._category_sections.get(category)
        if section:
            section.apply_active_subtags(cat_subtags)
            section.update_chip_states(
                cat_subtags, self._tag_library_selection,
                self._parent_select_mode, self._tags_to_parent,
            )
            section.update_header_chip(
                is_active=True,
                has_children=True,
                cell_w=self._compute_category_width(),
            )
        self._emit_filter()

    def _on_shelf_chip_clicked(self, tag: str, shelf: str) -> None:
        """Toggle a shelf tag filter."""
        if self._parent_select_mode:
            self._on_tag_clicked_in_parent_mode(tag, shelf)
            return

        cat_subtags = self._active_subtags.setdefault(shelf, set())
        if tag in cat_subtags:
            cat_subtags.discard(tag)
        else:
            cat_subtags.add(tag)

        section = self._shelf_sections.get(shelf)
        if section:
            section.update_chip_states(
                cat_subtags, self._tag_library_selection,
                self._parent_select_mode, self._tags_to_parent,
            )
        self._emit_filter()

    # ------------------------------------------------------------------
    # Context menu
    # ------------------------------------------------------------------

    def _on_chip_context_menu(self, tag: str) -> None:
        """Show context menu for a user tag chip."""
        if tag not in self._user_tags:
            return
        overlay = self._get_overlay()
        if overlay is not None:
            overlay.lock_dismiss(True)
        try:
            menu = QMenu(self)
            rename_act = menu.addAction("Rename…")
            icon_act = menu.addAction("Change icon…")
            parent_act = menu.addAction("Parent to tag…")
            delete_act = menu.addAction("Delete…")
            action = menu.exec_(QCursor.pos())

            if action == delete_act:
                tags = (
                    set(self._tag_library_selection)
                    if tag in self._tag_library_selection
                    else {tag}
                )
                tags = {t for t in tags if t in self._user_tags}
                if tags:
                    self.tag_delete_requested.emit(tags)

            elif action == parent_act:
                tags = (
                    set(self._tag_library_selection)
                    if tag in self._tag_library_selection
                    else {tag}
                )
                tags = {t for t in tags if t in self._user_tags}
                if tags:
                    self._enter_parent_select_mode(tags)

            elif action == icon_act:
                self.tag_icon_change_requested.emit(tag)

            elif action == rename_act:
                self.tag_rename_requested.emit(tag, "")  # MainWindow opens dialog

        finally:
            if overlay is not None:
                overlay.lock_dismiss(False)

    # ------------------------------------------------------------------
    # Parent-select mode
    # ------------------------------------------------------------------

    def _enter_parent_select_mode(self, tags: Set[str]) -> None:
        """Gray the given tags and signal that parent selection mode is on."""
        self._parent_select_mode = True
        self._tags_to_parent = set(tags)
        self._apply_all_states()

    def exit_parent_select_mode(self) -> None:
        """Exit parent-select mode and restore normal chip colours."""
        self._parent_select_mode = False
        self._tags_to_parent = set()
        self._tag_library_selection = set()
        self._apply_all_states()

    def _on_tag_clicked_in_parent_mode(
        self, tag: str, category: Optional[str] = None
    ) -> None:
        """Handle a chip click while in parent-select mode (selects the parent)."""
        if tag in self._tags_to_parent:
            return
        self._parent_select_key = tag
        self._parent_select_role = (
            "category" if tag in self._category_sections else "tag"
        )
        # Expand so children are visible
        if self._parent_select_role == "category":
            self._active_categories.add(tag)
            self._active_subtags.setdefault(tag, set())
            sec = self._category_sections.get(tag)
            if sec:
                sec.set_expanded(True)
        elif category:
            self._active_categories.add(category)
            self._active_subtags.setdefault(category, set()).add(tag)
            sec = self._category_sections.get(category)
            if sec:
                sec.set_expanded(True)
                sec.apply_active_subtags(self._active_subtags.get(category, set()))
        self._apply_all_states()
        self._emit_filter()

    # ------------------------------------------------------------------
    # State sync (no rebuild)
    # ------------------------------------------------------------------

    def _apply_all_states(self) -> None:
        """
        Refresh all section/chip visual states without any layout rebuild.

        Called after filter changes, load, parent-select mode toggle.
        """
        if self._taxonomy is None:
            return
        for category, section in self._category_sections.items():
            is_expanded = category in self._active_categories
            # Compare against not-hidden state (isVisible() fails before window is shown)
            if section.is_expanded() != is_expanded:
                section.set_expanded(is_expanded)
            active = self._active_subtags.get(category, set())
            if is_expanded:
                section.apply_active_subtags(active)
            section.update_header_chip(
                is_active=is_expanded,
                has_children=bool(self._taxonomy.subtag_order.get(category)),
                cell_w=self._compute_category_width(),
            )
            section.update_chip_states(
                active, self._tag_library_selection,
                self._parent_select_mode, self._tags_to_parent,
            )
        for shelf, section in self._shelf_sections.items():
            active = self._active_subtags.get(shelf, set())
            section.update_chip_states(
                active, self._tag_library_selection,
                self._parent_select_mode, self._tags_to_parent,
            )

    # ------------------------------------------------------------------
    # Width helpers
    # ------------------------------------------------------------------

    def _compute_cell_width(self) -> int:
        """Compute subtag chip width from current scroll viewport."""
        from gui.tag_panel_overlay import TagPanelOverlay
        vp = self._scroll_area.viewport()
        vp_w = vp.width() if vp and vp.width() > 0 else TagPanelOverlay.PANEL_WIDTH
        row_w = (
            vp_w
            - TAG_LIBRARY_OVERLAY_HORIZONTAL_MARGIN_PX
            - TAG_LIBRARY_VIEWPORT_RIGHT_GUTTER_PX
            - 2 * TAG_LIBRARY_SHELF_GRID_PADDING_PX
            - TAG_LIBRARY_DROP_ZONE_BORDER_PX
        )
        gaps = TAG_LIBRARY_TAG_GRID_SPACING_PX * 2  # 3 cols → 2 gaps
        per_col = (row_w - gaps) // 3
        return max(TAG_LIBRARY_TAG_CELL_MIN_WIDTH_PX, per_col - 6)

    def _compute_category_width(self) -> int:
        """Compute full-width category chip width."""
        from gui.tag_panel_overlay import TagPanelOverlay
        vp = self._scroll_area.viewport()
        vp_w = vp.width() if vp and vp.width() > 0 else TagPanelOverlay.PANEL_WIDTH
        return max(
            TAG_LIBRARY_TAG_CELL_MIN_WIDTH_PX,
            vp_w
            - TAG_LIBRARY_OVERLAY_HORIZONTAL_MARGIN_PX
            - TAG_LIBRARY_VIEWPORT_RIGHT_GUTTER_PX
            - TAG_LIBRARY_CATEGORY_WIDTH_TRIM_PX,
        )

    def _apply_widths(self) -> None:
        """Propagate current viewport-based widths to all chips."""
        cell_w = self._compute_cell_width()
        cat_w = self._compute_category_width()
        for category, chip in self._header_chips.items():
            chip.set_cell_width(cat_w, min_w=cat_w)
            sec = self._category_sections.get(category)
            if sec:
                sec.set_header_width_value(cat_w) if hasattr(sec, "set_header_width_value") else None
                sec.apply_cell_width(cell_w)
        for section in self._shelf_sections.values():
            section.set_header_width(cat_w)
            section.apply_cell_width(cell_w)

    # ------------------------------------------------------------------
    # DnD session
    # ------------------------------------------------------------------

    def _on_drag_started(self) -> None:
        self._tag_drag_in_progress = True
        self.drag_session_started.emit()
        if self._drag_scroll_timer is None:
            self._drag_scroll_timer = QTimer(self)
            self._drag_scroll_timer.timeout.connect(self._on_drag_scroll_tick)
        self._drag_scroll_timer.start(120)

    def _on_drag_ended(self) -> None:
        self._tag_drag_in_progress = False
        self.drag_session_ended.emit()
        if self._drag_scroll_timer is not None:
            self._drag_scroll_timer.stop()

    def _on_drag_scroll_tick(self) -> None:
        """Autoscroll the tag library when cursor is near top/bottom edge."""
        if not self._tag_drag_in_progress:
            return
        scroll = self._scroll_area
        vp = scroll.viewport()
        if not vp:
            return
        cursor_vp = vp.mapFromGlobal(QCursor.pos())
        bar = scroll.verticalScrollBar()
        if not bar:
            return
        margin = 48
        speed = 14
        y = cursor_vp.y()
        h = vp.height()
        if y < margin:
            bar.setValue(bar.value() - speed)
        elif y > h - margin:
            bar.setValue(bar.value() + speed)

    # ------------------------------------------------------------------
    # Filter emission
    # ------------------------------------------------------------------

    def _emit_filter(self) -> None:
        """Build and emit the current filter state."""
        state = TagFilterState.from_mutable(
            self._active_categories, self._active_subtags
        )
        self.filter_changed.emit(state)

    # ------------------------------------------------------------------
    # Public query helpers (for MainWindow compatibility)
    # ------------------------------------------------------------------

    def get_filter_state(self) -> TagFilterState:
        """
        Return the current filter state.

        Returns:
            TagFilterState: Snapshot of active categories and subtags.
        """
        return TagFilterState.from_mutable(
            self._active_categories, self._active_subtags
        )

    def get_active_categories(self) -> Set[str]:
        """Return a copy of the active category set."""
        return set(self._active_categories)

    def get_active_subtags(self) -> Dict[str, Set[str]]:
        """Return a shallow copy of the active subtag dict."""
        return {k: set(v) for k, v in self._active_subtags.items()}

    def get_taxonomy(self) -> Optional[TagLibraryTaxonomy]:
        """Return the current taxonomy (None if not yet loaded)."""
        return self._taxonomy

    def get_shelf_filter_modes(self) -> Dict[str, str]:
        """Return the shelf → filter-mode dict."""
        return dict(self._tag_shelf_filter_modes)

    def clear_filters(self) -> None:
        """Clear all active filters and collapse all categories."""
        self._active_categories.clear()
        self._active_subtags.clear()
        self._apply_all_states()
        self._emit_filter()

    def sync_filter_state_from(
        self,
        active_categories: Set[str],
        active_subtags: Dict[str, Set[str]],
        selection: Optional[Set[str]] = None,
    ) -> None:
        """
        Mirror filter/selection state from MainWindow and refresh the UI.

        Args:
            active_categories: Expanded category filters.
            active_subtags: Active subtags per category.
            selection: Tags selected for multi-drag (optional).
        """
        self._active_categories = set(active_categories)
        self._active_subtags = {k: set(v) for k, v in active_subtags.items()}
        if selection is not None:
            self._tag_library_selection = set(selection)
        self._apply_all_states()

    def map_point_to_content(self, panel_pos: QPoint) -> QPoint:
        """
        Map a point in panel coordinates to the scroll content widget.

        Args:
            panel_pos: Position relative to this panel widget.

        Returns:
            QPoint: Matching position in ``_content`` coordinates.
        """
        viewport = self._scroll_area.viewport()
        vp_pos = viewport.mapFrom(self, panel_pos)
        return self._content.mapFrom(viewport, vp_pos)

    def apply_expand_for_drop_target(self, role: str, key: str) -> None:
        """
        Expand a category or subtag while dragging over it (hover-to-reveal).

        Args:
            role: ``"category"`` or ``"tag"``.
            key: Category or tag name from ``tagGridKey``.
        """
        if self._taxonomy is None:
            return
        if role == "category":
            if is_tag_shelf(key):
                self._active_subtags.setdefault(key, set())
            else:
                self._active_categories.add(key)
                self._active_subtags.setdefault(key, set())
                section = self._category_sections.get(key)
                if section:
                    section.set_expanded(True)
        elif role == "tag":
            category = self._taxonomy.subtag_to_category.get(key)
            if category:
                self._active_categories.add(category)
                self._active_subtags.setdefault(category, set()).add(key)
                section = self._category_sections.get(category)
                if section:
                    section.set_expanded(True)
        self._apply_all_states()
        self._emit_filter()

    def get_chip(self, tag: str) -> Optional[WrappingDraggableTagButton]:
        """
        Return the chip widget for *tag* (subtag or header), or None.

        Args:
            tag: Tag name to look up.

        Returns:
            WrappingDraggableTagButton | None.
        """
        return self._all_chips.get(tag) or self._header_chips.get(tag)

    def update_chip_icon(self, tag: str) -> None:
        """
        Refresh the icon of an existing chip widget (no grid rebuild).

        Args:
            tag: Tag name whose icon should be refreshed.
        """
        chip = self.get_chip(tag)
        if chip is None:
            return
        icon = find_tag_icon(
            tag, user_config=self._user_tags_config, icon_preview_override={}
        )
        if not icon.isNull():
            chip.setIcon(invert_icon(icon, TAG_LIBRARY_TAG_ICON_PX))
        else:
            chip.setIcon(QIcon())

    def set_drop_highlight(self, widget: Optional[QWidget]) -> None:
        """
        Set or clear the drop-target visual highlight.

        Args:
            widget: Widget to highlight, or None to clear.
        """
        prev = self._drop_highlight_widget
        if prev is not None:
            prev.setProperty("dragOver", False)
            prev.style().unpolish(prev)
            prev.style().polish(prev)
        self._drop_highlight_widget = widget
        if widget is not None:
            widget.setProperty("dragOver", True)
            widget.style().unpolish(widget)
            widget.style().polish(widget)

    def get_drop_target_at(self, content_pos: QPoint) -> Optional[QWidget]:
        """
        Return the widget with ``tagGridRole`` at *content_pos* in content coords.

        Args:
            content_pos: Position in the ``_content`` widget's coordinate space.

        Returns:
            QWidget with tagGridRole/tagGridKey properties, or None.
        """
        w = self._content.childAt(content_pos)
        while w and w != self._content:
            if w.property("tagGridRole"):
                return w
            local = w.mapFrom(self._content, content_pos)
            nxt = w.childAt(local) if hasattr(w, "childAt") else None
            w = nxt
        return None

    def get_scroll_area(self) -> QScrollArea:
        """Return the internal QScrollArea (for wheel-filter installation)."""
        return self._scroll_area

    def get_visible_chip_rects(
        self, user_only: bool = False
    ) -> List[Tuple[str, QRect]]:
        """
        Return (tag, viewport-QRect) for every visible subtag chip.

        Args:
            user_only: If True, only include user-owned tags.

        Returns:
            List of (tag_name, QRect) tuples.
        """
        vp = self._scroll_area.viewport()
        if not vp:
            return []
        result: List[Tuple[str, QRect]] = []
        for tag, chip in self._all_chips.items():
            if user_only and not chip.property("userTag"):
                continue
            if not chip.isVisible():
                continue
            tl_global = chip.mapToGlobal(chip.rect().topLeft())
            tl_vp = vp.mapFromGlobal(tl_global)
            result.append((tag, QRect(tl_vp, chip.size())))
        return result

    # ------------------------------------------------------------------
    # Resize
    # ------------------------------------------------------------------

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        QTimer.singleShot(0, self._apply_widths)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_overlay(self):
        """Return the TagPanelOverlay from the parent hierarchy, or None."""
        w = self.parent()
        while w:
            if hasattr(w, "lock_dismiss"):
                return w
            w = w.parent() if hasattr(w, "parent") else None
        return None
