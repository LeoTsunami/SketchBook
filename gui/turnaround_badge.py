"""
Turnaround badge overlay (white icon + drop shadow) for grid, viewer, and session.
"""

from __future__ import annotations

from qtpy.QtCore import Qt
from qtpy.QtGui import QColor, QFont, QPixmap
from qtpy.QtWidgets import (
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QWidget,
)

from gui.icon_utils import find_tag_icon, tint_icon


class TurnaroundBadgeOverlay(QLabel):
    """Floating turnaround icon badge; parent should be the host widget."""

    BADGE_ICON_GRID = 36
    BADGE_BOX_GRID = 44
    BADGE_ICON_LARGE = 44
    BADGE_BOX_LARGE = 52
    BADGE_MARGIN = 10

    def __init__(self, parent: QWidget, *, large: bool = False) -> None:
        """
        Initialize the badge overlay.

        Args:
            parent: Host widget (thumbnail, graphics view, overlay container).
            large: Use larger sizing for viewer and session.
        """
        super().__init__(parent)
        self._icon_px = self.BADGE_ICON_LARGE if large else self.BADGE_ICON_GRID
        box = self.BADGE_BOX_LARGE if large else self.BADGE_BOX_GRID
        self.setObjectName("TurnaroundBadge")
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(box, box)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(
            "QLabel#TurnaroundBadge { background: transparent; border: none; }"
        )
        badge_pm = build_turnaround_badge_pixmap(self._icon_px)
        if not badge_pm.isNull():
            self.setPixmap(badge_pm)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(14 if large else 12)
        shadow.setOffset(0, 1)
        shadow.setColor(QColor(0, 0, 0, 210))
        self.setGraphicsEffect(shadow)
        self.hide()

    def reposition(self, host: QWidget | None = None) -> None:
        """
        Place the badge in the bottom-right corner of its parent (or host).

        Args:
            host: Optional widget whose size defines placement; defaults to parent.
        """
        target = host or self.parentWidget()
        if target is None:
            return
        margin = self.BADGE_MARGIN
        x = max(0, target.width() - self.width() - margin)
        y = max(0, target.height() - self.height() - margin)
        self.move(x, y)
        self.raise_()

    def set_visible_for_turnaround(self, visible: bool) -> None:
        """
        Show or hide the badge.

        Args:
            visible: Whether the current context is a turnaround.
        """
        if visible:
            self.reposition()
            self.show()
            self.raise_()
        else:
            self.hide()


class TurnaroundViewerHintOverlay(QWidget):
    """
    Bottom-centered turnaround hint for viewer and session (icon + drag hint text).
    """

    HINT_TEXT = "Click and drag to turn around"
    ICON_PX = TurnaroundBadgeOverlay.BADGE_ICON_LARGE
    BOTTOM_MARGIN = 24

    def __init__(self, parent: QWidget) -> None:
        """
        Initialize the viewer hint strip.

        Args:
            parent: Host widget (typically the graphics view).
        """
        super().__init__(parent)
        self.setObjectName("TurnaroundViewerHint")
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 12, 8)
        layout.setSpacing(10)

        self._icon_label = QLabel()
        self._icon_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        badge_pm = build_turnaround_badge_pixmap(self.ICON_PX)
        if not badge_pm.isNull():
            self._icon_label.setPixmap(badge_pm)
            self._icon_label.setFixedSize(badge_pm.size())
        icon_shadow = QGraphicsDropShadowEffect(self._icon_label)
        icon_shadow.setBlurRadius(12)
        icon_shadow.setOffset(0, 1)
        icon_shadow.setColor(QColor(0, 0, 0, 200))
        self._icon_label.setGraphicsEffect(icon_shadow)

        self._hint_label = QLabel(self.HINT_TEXT)
        self._hint_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self._hint_label.setFont(font)
        self._hint_label.setStyleSheet("color: #ffffff;")
        hint_shadow = QGraphicsDropShadowEffect(self._hint_label)
        hint_shadow.setBlurRadius(10)
        hint_shadow.setOffset(0, 1)
        hint_shadow.setColor(QColor(0, 0, 0, 180))
        self._hint_label.setGraphicsEffect(hint_shadow)

        layout.addWidget(self._icon_label)
        layout.addWidget(self._hint_label)
        self.adjustSize()
        self.hide()

    def reposition(
        self, host: QWidget | None = None, *, bottom_offset_y: int = 0
    ) -> None:
        """
        Place the hint strip centered along the bottom edge of the host.

        Args:
            host: Optional widget whose size defines placement; defaults to parent.
            bottom_offset_y: Extra lift from the bottom (e.g. above session controls).
        """
        self.adjustSize()
        target = host or self.parentWidget()
        if target is None:
            return
        x = max(0, (target.width() - self.width()) // 2)
        y = max(
            0,
            target.height() - self.height() - self.BOTTOM_MARGIN - bottom_offset_y,
        )
        self.move(x, y)
        self.raise_()

    def set_visible_for_turnaround(self, visible: bool) -> None:
        """
        Show or hide the viewer hint.

        Args:
            visible: Whether the current image is a turnaround.
        """
        if visible:
            self.reposition()
            self.show()
            self.raise_()
        else:
            self.hide()


def build_turnaround_badge_pixmap(size: int = TurnaroundBadgeOverlay.BADGE_ICON_GRID) -> QPixmap:
    """
    Build a white turnaround badge pixmap from the tag icon asset.

    Args:
        size: Icon size in pixels.

    Returns:
        QPixmap: White-tinted icon, or null pixmap if missing.
    """
    raw = find_tag_icon("Turnaround")
    if raw.isNull():
        return QPixmap()
    tinted = tint_icon(raw, QColor(255, 255, 255), size)
    return tinted.pixmap(size, size)
