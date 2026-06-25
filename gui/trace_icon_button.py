"""
Small icon button with animated glass trace border (SessionTraceButton style).
"""

from __future__ import annotations

from dataclasses import dataclass

from qtpy.QtCore import QEasingCurve, QRect, QSize, Qt, QVariantAnimation
from qtpy.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QIcon,
    QPainter,
    QPen,
    QPixmap,
)
from qtpy.QtWidgets import QPushButton, QWidget


@dataclass(frozen=True)
class TracePalette:
    """Color scheme for a trace-animated glass button."""

    normal_bg: QColor
    hover_bg: QColor
    pressed_bg: QColor
    base_border: QColor
    trace_lo: QColor
    trace_hi: QColor
    trace_mid: QColor
    shadow: QColor


ORANGE_TRACE = TracePalette(
    normal_bg=QColor(194, 108, 48, 128),
    hover_bg=QColor(230, 132, 58, 158),
    pressed_bg=QColor(168, 88, 36, 168),
    base_border=QColor(255, 214, 170, 130),
    trace_lo=QColor(255, 150, 70, 70),
    trace_hi=QColor(255, 210, 150, 255),
    trace_mid=QColor(245, 128, 52, 90),
    shadow=QColor(255, 140, 48, 150),
)


class TraceIconButton(QPushButton):
    """Compact glass-like icon button with animated border trace."""

    def __init__(
        self,
        icon: QIcon,
        size: int = 28,
        palette: TracePalette = ORANGE_TRACE,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._palette = palette
        self._trace_progress = 0.0
        self._icon_display_px = max(12, size - 10)
        render_px = self._icon_display_px * 3
        self._icon_pixmap: QPixmap = icon.pixmap(
            QSize(render_px, render_px),
            QIcon.Mode.Normal,
            QIcon.State.Off,
        )
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(size, size)
        self.setStyleSheet(
            "QPushButton { background: transparent; border: none; }"
        )

        self._trace_anim = QVariantAnimation(self)
        self._trace_anim.setDuration(2200)
        self._trace_anim.setStartValue(0.0)
        self._trace_anim.setEndValue(1.0)
        self._trace_anim.setEasingCurve(QEasingCurve.Linear)
        self._trace_anim.setLoopCount(-1)
        self._trace_anim.valueChanged.connect(self._on_trace_value_changed)
        self._trace_anim.start()

    def _on_trace_value_changed(self, value: object) -> None:
        """
        Update trace progression and repaint.

        Args:
            value: Animated progress ratio in [0, 1].
        """
        self._trace_progress = float(value)
        self.update()

    def paintEvent(self, event) -> None:
        """Custom paint: glass fill + moving border trace + centered icon."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        rect = self.rect().adjusted(2, 2, -2, -2)
        radius = 6.0
        palette = self._palette

        if self.isDown():
            bg = palette.pressed_bg
        elif self.underMouse():
            bg = palette.hover_bg
        else:
            bg = palette.normal_bg

        painter.setPen(Qt.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(rect, radius, radius)

        base_pen = QPen(palette.base_border, 1.5)
        painter.setPen(base_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, radius, radius)

        trace_gradient = QConicalGradient(
            rect.center(), -self._trace_progress * 360.0
        )
        trace_gradient.setColorAt(0.00, palette.trace_lo)
        trace_gradient.setColorAt(0.10, palette.trace_hi)
        trace_gradient.setColorAt(0.22, palette.trace_mid)
        trace_gradient.setColorAt(0.45, palette.trace_lo)
        trace_gradient.setColorAt(1.00, palette.trace_lo)
        trace_pen = QPen(QBrush(trace_gradient), 2.0)
        trace_pen.setCapStyle(Qt.RoundCap)
        trace_pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(trace_pen)
        painter.drawRoundedRect(rect, radius, radius)

        if not self._icon_pixmap.isNull():
            icon_side = self._icon_display_px
            icon_rect = QRect(
                rect.x() + (rect.width() - icon_side) // 2,
                rect.y() + (rect.height() - icon_side) // 2,
                icon_side,
                icon_side,
            )
            painter.drawPixmap(icon_rect, self._icon_pixmap)
