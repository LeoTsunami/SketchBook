"""
Icon utility functions for SketchBook GUI.
Centralized icon handling to avoid code duplication.
"""
from pathlib import Path
from typing import Optional, Dict
from qtpy.QtGui import QIcon, QPixmap, QImage
from qtpy.QtCore import QSize


def find_tag_icon(tag: str, user_config: Optional[Dict] = None, icon_preview_override: Optional[Dict[str, Optional[str]]] = None) -> QIcon:
    """
    Resolve a tag icon based on the tag name, with optional user config overrides.

    Args:
        tag: Tag name.
        user_config: Optional user tags config dict with 'icons' key mapping tag names to icon filenames.
        icon_preview_override: Optional dict for live preview while "Change icon" dialog is open.

    Returns:
        QIcon: Icon for the tag or an empty icon if not found.
    """
    icons_dir = Path(__file__).parent / "ressources" / "icones" / "tags"
    if not icons_dir.exists():
        return QIcon()

    # Live preview override (highest priority)
    if icon_preview_override and tag in icon_preview_override:
        preview = icon_preview_override[tag]
        if preview is None:
            return QIcon()
        icon_path = icons_dir / preview
        if icon_path.exists():
            return QIcon(str(icon_path))
        return QIcon()

    # User config override
    if user_config:
        config_icons = user_config.get("icons", {})
        if tag in config_icons:
            icon_file = icons_dir / config_icons[tag]
            if icon_file.exists():
                return QIcon(str(icon_file))

    # Default: match by tag name
    tag_lower = tag.lower()
    file_map = {path.stem.lower(): path for path in icons_dir.glob("*.png")}
    if tag_lower in file_map:
        return QIcon(str(file_map[tag_lower]))

    # Fallback mappings
    fallback_map = {
        "hands": "hand",
        "feet": "foot",
        "objects": "object",
    }
    fallback = fallback_map.get(tag_lower)
    if fallback and fallback in file_map:
        return QIcon(str(file_map[fallback]))

    return QIcon()


def invert_icon(icon: QIcon, size: int = 24) -> QIcon:
    """
    Invert icon colors for better visibility.

    Args:
        icon: Original icon.
        size: Icon size in pixels (default: 24).

    Returns:
        QIcon: New icon with inverted colors, or original if inversion fails.
    """
    if icon.isNull():
        return icon
    
    pixmap = icon.pixmap(QSize(size, size))
    if pixmap.isNull():
        return icon
    
    image = pixmap.toImage()
    if image.isNull():
        return icon
    
    image.invertPixels(QImage.InvertRgb)
    return QIcon(QPixmap.fromImage(image))
