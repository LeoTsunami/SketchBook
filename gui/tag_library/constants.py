"""
Constants, MIME types and small pure helpers for the tag library UI.
"""
from __future__ import annotations

from typing import Any

from qtpy.QtCore import Qt
from qtpy.QtGui import QColor

# ---------------------------------------------------------------------------
# MIME types
# ---------------------------------------------------------------------------
TAG_LIBRARY_MIME = "application/x-sketchbook-tag-library"
TAG_LIBRARY_MULTI_MIME = "application/x-sketchbook-tag-library-multi"

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
TAG_LIBRARY_TAG_GRID_COLUMNS = 3
TAG_LIBRARY_TAG_GRID_SPACING_PX = 14
TAG_LIBRARY_CHIP_SHADOW_BLEED_PX = 14
TAG_LIBRARY_TAG_CELL_WIDTH_TRIM_PX = 8
TAG_LIBRARY_CATEGORY_WIDTH_TRIM_PX = 4
TAG_LIBRARY_CATEGORY_SIDE_INSET_PX = 16
TAG_LIBRARY_SHELF_GRID_PADDING_PX = 4
# QFrame#TagDropZone uses 2px dashed border on each side (style_*.qss).
TAG_LIBRARY_DROP_ZONE_BORDER_PX = 4
TAG_LIBRARY_TAG_CELL_INSET_PX = 1
TAG_LIBRARY_TAG_CELL_ALIGN = Qt.AlignHCenter | Qt.AlignVCenter
TAG_LIBRARY_TAG_BORDER_LIGHTER_PCT = 145
TAG_LIBRARY_TAG_BORDER_WIDTH_PX = 1
TAG_LIBRARY_TAG_STYLE_V_PADDING_PX = 4
TAG_LIBRARY_TAG_MAX_HEIGHT_PX = 110
TAG_LIBRARY_TAG_SHADOW_BLUR_PX = 26
TAG_LIBRARY_TAG_SHADOW_OFFSET_X_PX = 3
TAG_LIBRARY_TAG_SHADOW_OFFSET_Y_PX = 5
TAG_LIBRARY_TAG_SHADOW_ALPHA = 95
TAG_LIBRARY_CATEGORY_SHADOW_BLUR_PX = 32
TAG_LIBRARY_CATEGORY_SHADOW_OFFSET_X_PX = 4
TAG_LIBRARY_CATEGORY_SHADOW_OFFSET_Y_PX = 6
TAG_LIBRARY_CATEGORY_SHADOW_ALPHA = 105
TAG_LIBRARY_DRAG_SHADOW_BLUR_PX = 18
TAG_LIBRARY_DRAG_SHADOW_OFFSET_X_PX = 4
TAG_LIBRARY_DRAG_SHADOW_OFFSET_Y_PX = 9
TAG_LIBRARY_DRAG_SHADOW_ALPHA = 105
TAG_LIBRARY_CHIP_TRACE_DURATION_MS = 2200
TAG_LIBRARY_OVERLAY_HORIZONTAL_MARGIN_PX = 8

# ---------------------------------------------------------------------------
# Scrollbar / viewport
# ---------------------------------------------------------------------------
TAG_LIBRARY_SCROLLBAR_INSET_RIGHT_PX = 0
TAG_LIBRARY_SCROLLBAR_INSET_BOTTOM_PX = 10
TAG_LIBRARY_VIEWPORT_RIGHT_GUTTER_PX = 4
TAG_LIBRARY_GRID_TOP_MARGIN_PX = 4

# ---------------------------------------------------------------------------
# Typography
# ---------------------------------------------------------------------------
TAG_LIBRARY_FONT_SUBTAG_PX = 16
TAG_LIBRARY_FONT_CATEGORY_PX = 20
TAG_LIBRARY_FONT_SHELF_TITLE_PX = 14

# ---------------------------------------------------------------------------
# Icon sizes
# ---------------------------------------------------------------------------
TAG_LIBRARY_TAG_ICON_PX = 26
TAG_LIBRARY_CATEGORY_ICON_PX = 30
TAG_LIBRARY_TAG_ICON_SLOT_PX = 33
TAG_LIBRARY_CATEGORY_ICON_SLOT_PX = 38
TAG_LIBRARY_CHIP_CONTENT_HPAD_PX = 7

# ---------------------------------------------------------------------------
# Minimum widget sizes
# ---------------------------------------------------------------------------
TAG_LIBRARY_TAG_MIN_HEIGHT_PX = 46
TAG_LIBRARY_CATEGORY_MIN_HEIGHT_PX = 52
TAG_LIBRARY_TAG_CHIP_RADIUS_PX = 14
TAG_LIBRARY_CATEGORY_CHIP_RADIUS_PX = 16
TAG_LIBRARY_TAG_CELL_MIN_WIDTH_PX = 48


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

def tag_library_subtle_border_color(bg: QColor) -> str:
    """
    Return an outline color slightly lighter than the tag fill.

    Args:
        bg: Tag background QColor.

    Returns:
        str: CSS color name (e.g. "#4a5b6c").
    """
    return bg.lighter(TAG_LIBRARY_TAG_BORDER_LIGHTER_PCT).name()


def tag_library_idle_border_css(bg: QColor) -> str:
    """
    Build the default (non-active) tag border CSS declaration.

    Args:
        bg: Tag background QColor.

    Returns:
        str: CSS border fragment like ``"2px solid #3a4b5c"``.
    """
    color = tag_library_subtle_border_color(bg)
    w = TAG_LIBRARY_TAG_BORDER_WIDTH_PX
    return f"{w}px solid {color}"


def mime_data_looks_like_tag_library_drag(mime: Any) -> bool:
    """
    Return True if MIME data likely originates from a tag-library drag.

    Args:
        mime: QMimeData instance (or None).

    Returns:
        bool: True when the drag should keep the tag panel open.
    """
    if mime is None:
        return False
    try:
        if mime.hasFormat(TAG_LIBRARY_MIME) or mime.hasFormat(TAG_LIBRARY_MULTI_MIME):
            return True
        return bool(mime.hasText() and mime.text().strip())
    except (AttributeError, TypeError):
        return False
