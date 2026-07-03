"""
Compact colour picker popup for tag library shelves.

A small frameless grid of curated swatches shown near the cursor, with a
"Custom…" fallback to the full ``QColorDialog`` for fine control.
"""
from __future__ import annotations

from typing import Optional

from qtpy.QtCore import Qt, QPoint
from qtpy.QtGui import QColor, QCursor
from qtpy.QtWidgets import (
    QColorDialog,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# Curated jewel-tone palette matching the app's dark UI aesthetic.
_SWATCHES = [
    "#7c4dff", "#5c6bc0", "#42a5f5", "#26c6da",
    "#26a69a", "#66bb6a", "#9ccc65", "#d4e157",
    "#ffca28", "#ffa726", "#ff7043", "#ec407a",
    "#ab47bc", "#8d6e63", "#78909c", "#ef5350",
]

_COLUMNS = 4
_SWATCH_PX = 30


class ShelfColorPopup(QDialog):
    """
    Minimal swatch-grid colour picker.

    Args:
        current: Currently selected colour, highlighted if it matches a swatch.
        parent: Parent widget for modality.
    """

    def __init__(self, current: Optional[QColor] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._selected: Optional[str] = None
        self.setWindowFlags(Qt.Popup)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setObjectName("ShelfColorPopup")
        self.setStyleSheet(
            "QDialog#ShelfColorPopup {"
            " background: #241a2c;"
            " border: 1px solid rgba(255,255,255,0.14);"
            " border-radius: 10px;"
            "}"
            " QPushButton#ShelfColorCustom {"
            " color: #d8d2e8; background: rgba(255,255,255,0.06);"
            " border: 1px solid rgba(255,255,255,0.12); border-radius: 6px;"
            " padding: 5px; font-size: 11px; font-weight: 600;"
            "}"
            " QPushButton#ShelfColorCustom:hover { background: rgba(255,255,255,0.12); }"
        )

        current_hex = current.name().lower() if current is not None and current.isValid() else None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(8)

        grid = QGridLayout()
        grid.setSpacing(6)
        for idx, hex_color in enumerate(_SWATCHES):
            btn = QPushButton()
            btn.setFixedSize(_SWATCH_PX, _SWATCH_PX)
            btn.setCursor(Qt.PointingHandCursor)
            selected = current_hex == hex_color.lower()
            border = (
                "2px solid #ffffff" if selected else "1px solid rgba(0,0,0,0.35)"
            )
            btn.setStyleSheet(
                f"QPushButton {{ background: {hex_color}; border: {border};"
                f" border-radius: 6px; }}"
                f"QPushButton:hover {{ border: 2px solid #ffffff; }}"
            )
            btn.clicked.connect(lambda _=False, c=hex_color: self._choose(c))
            grid.addWidget(btn, idx // _COLUMNS, idx % _COLUMNS)
        outer.addLayout(grid)

        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        custom_btn = QPushButton("Custom…")
        custom_btn.setObjectName("ShelfColorCustom")
        custom_btn.setCursor(Qt.PointingHandCursor)
        custom_btn.clicked.connect(self._open_custom)
        footer.addWidget(custom_btn)
        outer.addLayout(footer)

    def _choose(self, hex_color: str) -> None:
        """Record the picked colour and close the popup."""
        self._selected = hex_color
        self.accept()

    def _open_custom(self) -> None:
        """Fall back to the full colour dialog for fine control."""
        initial = QColor(self._selected) if self._selected else QColor("#7c4dff")
        chosen = QColorDialog.getColor(initial, self, "Custom colour")
        if chosen.isValid():
            self._selected = chosen.name()
            self.accept()

    def selected_color(self) -> Optional[str]:
        """Return the chosen hex colour, or None if cancelled."""
        return self._selected


def pick_shelf_color(
    current: Optional[QColor] = None,
    parent: Optional[QWidget] = None,
    at: Optional[QPoint] = None,
) -> Optional[str]:
    """
    Show the compact shelf colour popup and return the chosen hex colour.

    Args:
        current: Currently selected colour (highlighted if in the palette).
        parent: Parent widget for the popup.
        at: Global position to anchor the popup (defaults to cursor).

    Returns:
        str | None: Chosen hex colour, or None if cancelled.
    """
    popup = ShelfColorPopup(current, parent)
    anchor = at if at is not None else QCursor.pos()
    popup.move(anchor)
    if popup.exec_() == QDialog.DialogCode.Accepted:
        return popup.selected_color()
    return None
