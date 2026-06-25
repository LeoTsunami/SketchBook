"""
Icon utility functions for SketchBook GUI.
Centralized icon handling to avoid code duplication.
"""
from pathlib import Path
from typing import Optional, Dict

from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QIcon, QPixmap, QImage
from qtpy.QtWidgets import QComboBox, QStyle, QStyleOptionComboBox, QStylePainter

_ICONS_DIR = Path(__file__).parent / "ressources" / "icones"


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


def load_white_icon(filename: str, size: int = 18) -> QIcon:
    """
    Load a monochrome PNG from ``gui/ressources/icones`` and render it in white.

    Args:
        filename: Icon file name (e.g. ``shuffle.png``).
        size: Icon size in pixels.

    Returns:
        White-tinted icon, or an empty icon if the file is missing.
    """
    icon_path = _ICONS_DIR / filename
    if not icon_path.exists():
        return QIcon()
    return invert_icon(QIcon(str(icon_path)), size)


class IconLeadingComboBox(QComboBox):
    """Combo box that shows a fixed icon when closed; item labels appear in the popup."""

    def __init__(self, leading_icon: QIcon, parent=None) -> None:
        """
        Initialize the combo box.

        Args:
            leading_icon: Icon displayed in the collapsed control.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._leading_icon = leading_icon
        self.setIconSize(QSize(16, 16))

    def paintEvent(self, event) -> None:
        """Paint the combo chrome and leading icon without the current item text."""
        painter = QStylePainter(self)
        option = QStyleOptionComboBox()
        self.initStyleOption(option)
        option.currentText = ""
        option.iconSize = QSize(0, 0)
        painter.drawComplexControl(QStyle.CC_ComboBox, option)

        if self._leading_icon.isNull():
            return

        icon_size = self.iconSize()
        arrow_width = 18
        inner = self.rect().adjusted(4, 0, -(arrow_width + 2), 0)
        x = inner.x() + max(0, (inner.width() - icon_size.width()) // 2)
        y = inner.y() + max(0, (inner.height() - icon_size.height()) // 2)
        self._leading_icon.paint(
            painter, x, y, icon_size.width(), icon_size.height(), Qt.AlignCenter
        )
