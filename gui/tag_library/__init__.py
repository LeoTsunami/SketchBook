"""
gui.tag_library – modular tag library panel.

Public API surface:
    TagLibraryPanel  – drop-in replacement for the tag grid in MainWindow.
    TagLibraryTaxonomy – immutable description of the tag tree.
    TagFilterState   – filter snapshot emitted by TagLibraryPanel.filter_changed.
    DraggableTagButton / WrappingDraggableTagButton – chip widget classes.
    apply_chip_style – style helper (reused by MainWindow for compatibility).
    mime_data_looks_like_tag_library_drag – MIME helper.
    TAG_LIBRARY_MIME / TAG_LIBRARY_MULTI_MIME – MIME type constants.
"""

from gui.tag_library.constants import (
    TAG_LIBRARY_MIME,
    TAG_LIBRARY_MULTI_MIME,
    mime_data_looks_like_tag_library_drag,
)
from gui.tag_library.chip import (
    DraggableTagButton,
    WrappingDraggableTagButton,
    apply_chip_style,
    build_chip_drag_pixmap,
    prepare_chip_drag_pixmap,
    chip_drag_hot_spot,
    apply_drag_cursor_offset,
    drag_pixmap_with_shadow,
    grab_chip_for_drag,
    get_chip_drag_source,
    get_hierarchy_background_color,
    blend_color,
)
from gui.tag_library.theme import chip_palette
from gui.tag_library.state import TagLibraryTaxonomy, TagFilterState
from gui.tag_library.panel import TagLibraryPanel

__all__ = [
    "TAG_LIBRARY_MIME",
    "TAG_LIBRARY_MULTI_MIME",
    "mime_data_looks_like_tag_library_drag",
    "DraggableTagButton",
    "WrappingDraggableTagButton",
    "apply_chip_style",
    "drag_pixmap_with_shadow",
    "grab_chip_for_drag",
    "get_chip_drag_source",
    "build_chip_drag_pixmap",
    "prepare_chip_drag_pixmap",
    "chip_drag_hot_spot",
    "apply_drag_cursor_offset",
    "get_hierarchy_background_color",
    "blend_color",
    "chip_palette",
    "TagLibraryTaxonomy",
    "TagFilterState",
    "TagLibraryPanel",
]
