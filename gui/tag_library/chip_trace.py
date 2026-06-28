"""
Animated border trace for active / selected tag chips (Start session style).
"""
from __future__ import annotations

from dataclasses import dataclass

from qtpy.QtCore import QEasingCurve, Qt, QVariantAnimation, QAbstractAnimation
from qtpy.QtGui import QBrush, QColor, QConicalGradient, QPainter, QPen
from qtpy.QtWidgets import QPushButton, QWidget

from gui.tag_library.constants import (
    TAG_LIBRARY_CATEGORY_CHIP_RADIUS_PX,
    TAG_LIBRARY_CHIP_TRACE_DURATION_MS,
    TAG_LIBRARY_TAG_CHIP_RADIUS_PX,
)


@dataclass(frozen=True)
class _ChipTracePalette:
    """Perimeter trace colours for one chip highlight state."""

    base_border: QColor
    trace_lo: QColor
    trace_hi: QColor
    trace_mid: QColor


_ACTIVE_TRACE = _ChipTracePalette(
    base_border=QColor(130, 255, 185, 150),
    trace_lo=QColor(90, 255, 150, 65),
    trace_hi=QColor(210, 255, 230, 255),
    trace_mid=QColor(110, 255, 165, 95),
)

_SELECTED_TRACE = _ChipTracePalette(
    base_border=QColor(170, 215, 255, 150),
    trace_lo=QColor(120, 188, 255, 70),
    trace_hi=QColor(190, 232, 255, 255),
    trace_mid=QColor(110, 180, 245, 90),
)


class TagChipTraceOverlay(QWidget):
    """
    Transparent child overlay that draws a rotating border trace on a chip.

    Matches the SessionTraceButton / TraceIconButton shimmer language.
    """

    def __init__(self, host: QWidget) -> None:
        super().__init__(host)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._trace_progress = 0.0
        self._radius = float(TAG_LIBRARY_TAG_CHIP_RADIUS_PX)
        self._border_w = 2.0
        self._inset = 1.0
        self._palette = _ACTIVE_TRACE

        self._trace_anim = QVariantAnimation(self)
        self._trace_anim.setDuration(TAG_LIBRARY_CHIP_TRACE_DURATION_MS)
        self._trace_anim.setStartValue(0.0)
        self._trace_anim.setEndValue(1.0)
        self._trace_anim.setEasingCurve(QEasingCurve.Linear)
        self._trace_anim.setLoopCount(-1)
        self._trace_anim.valueChanged.connect(self._on_trace_value_changed)
        self.hide()

    def configure(self, state: str, *, is_category: bool) -> None:
        """
        Set trace colours and geometry for the current chip state.

        Args:
            state: ``active`` or ``selected``.
            is_category: True for main category header chips.
        """
        self._palette = _SELECTED_TRACE if state == "selected" else _ACTIVE_TRACE
        self._radius = float(
            TAG_LIBRARY_CATEGORY_CHIP_RADIUS_PX
            if is_category
            else TAG_LIBRARY_TAG_CHIP_RADIUS_PX
        )
        self._border_w = 2.5 if is_category else 2.0
        self._inset = 1.5 if is_category else 1.0

    def sync_geometry(self) -> None:
        """Match the host chip bounds."""
        host = self.parentWidget()
        if host is not None:
            self.setGeometry(host.rect())

    def start(self) -> None:
        """Show overlay and loop the perimeter trace."""
        self.sync_geometry()
        self.show()
        self.raise_()
        if self._trace_anim.state() != QAbstractAnimation.Running:
            self._trace_anim.start()

    def stop(self) -> None:
        """Hide overlay and pause animation."""
        self._trace_anim.stop()
        self.hide()

    def _on_trace_value_changed(self, value: object) -> None:
        self._trace_progress = float(value)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = self.rect().adjusted(
            int(self._inset),
            int(self._inset),
            -int(self._inset),
            -int(self._inset),
        )
        palette = self._palette

        base_pen = QPen(palette.base_border, self._border_w)
        painter.setPen(base_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, self._radius, self._radius)

        trace_gradient = QConicalGradient(
            rect.center(), -self._trace_progress * 360.0
        )
        trace_gradient.setColorAt(0.00, palette.trace_lo)
        trace_gradient.setColorAt(0.10, palette.trace_hi)
        trace_gradient.setColorAt(0.22, palette.trace_mid)
        trace_gradient.setColorAt(0.45, palette.trace_lo)
        trace_gradient.setColorAt(1.00, palette.trace_lo)
        trace_pen = QPen(QBrush(trace_gradient), self._border_w)
        trace_pen.setCapStyle(Qt.RoundCap)
        trace_pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(trace_pen)
        painter.drawRoundedRect(rect, self._radius, self._radius)


def sync_chip_trace(
    button: QPushButton,
    state: str,
    branch_key: str,
    depth: int,
    *,
    is_category: bool,
) -> None:
    """
    Start or stop the border-trace shimmer for *state*.

    Args:
        button: Target chip button.
        state: ``tagState`` value (empty when idle).
        branch_key: Category hue branch (reserved for future branch-tinted traces).
        depth: Visual nesting depth (reserved).
        is_category: True for main category header chips.
    """
    _ = branch_key, depth
    overlay = button.property("_traceOverlay")
    if state in ("active", "selected"):
        if overlay is None:
            overlay = TagChipTraceOverlay(button)
            button.setProperty("_traceOverlay", overlay)
        overlay.configure(state, is_category=is_category)
        overlay.start()
    elif overlay is not None:
        overlay.stop()
