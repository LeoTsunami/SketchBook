"""
Floating tag panel overlay that slides over the image grid.

Appears on hover over a trigger button at the left edge of the viewport,
and hides when the mouse leaves the panel (after verifying the cursor is
really outside, so in-panel drags and context menus do not collapse it).
Uses a semi-transparent dark background with rounded right corners for a
glass-like effect.
"""

from qtpy.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QGraphicsDropShadowEffect,
    QScrollArea,
)
from qtpy.QtCore import (
    Qt,
    QAbstractAnimation,
    QPropertyAnimation,
    QEasingCurve,
    QPoint,
    QRect,
    QTimer,
    Signal,
)
from qtpy.QtGui import QColor, QCursor


class TagPanelOverlay(QFrame):
    """Floating overlay panel for the tag library.

    Parented to the image grid viewport so it hovers on top of the gallery
    without affecting the grid's layout or size.

    Args:
        parent: The QWidget this overlay is parented to (typically the viewport).
        width: Panel width in pixels.
    """

    panel_did_hide = Signal()

    PANEL_WIDTH = 504  # 420px + 20% for roomier tag grid (3 columns)
    VIEWPORT_MARGIN_PX = 10
    ANIM_DURATION_MS = 200

    def __init__(
        self, parent=None, width: int = PANEL_WIDTH, top_inset: int = 0
    ) -> None:
        super().__init__(parent)
        self._panel_width = width
        self._top_inset = max(top_inset, self.VIEWPORT_MARGIN_PX)
        self._is_showing = False
        self._anim: QPropertyAnimation | None = None
        self._dismiss_locked = False
        self._leave_hide_timer = QTimer(self)
        self._leave_hide_timer.setSingleShot(True)
        self._leave_hide_timer.timeout.connect(self._deferred_leave_hide_check)

        self.setObjectName("TagPanelOverlay")
        self.setFixedWidth(self._panel_width)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(self._build_stylesheet())

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setOffset(4, 0)
        shadow.setColor(QColor(0, 0, 0, 160))
        self.setGraphicsEffect(shadow)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(10, 26, 10, 10)
        self._layout.setSpacing(10)

        self.hide()
        self._place_offscreen()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_content_widget(self, widget) -> None:
        """Insert the tag library content widget into this overlay.

        Args:
            widget: The QWidget containing tag library UI elements.
        """
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        self._layout.addWidget(widget, 1)

    def show_animated(self) -> None:
        """Slide the panel into view from the left edge."""
        self._leave_hide_timer.stop()
        if self._is_showing:
            return
        self._is_showing = True
        self._update_height()
        self.show()
        self.raise_()

        self._stop_anim()
        y0 = self._top_inset
        self._anim = QPropertyAnimation(self, b"pos", self)
        self._anim.setDuration(self.ANIM_DURATION_MS)
        self._anim.setStartValue(QPoint(-self._panel_width, y0))
        self._anim.setEndValue(QPoint(0, y0))
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.finished.connect(self._on_show_anim_finished)
        self._anim.start()

    def _on_show_anim_finished(self) -> None:
        """Snap to final geometry after slide-in (safe for reposition calls)."""
        if self._is_showing:
            self.move(0, self._top_inset)

    def hide_animated(self) -> None:
        """Slide the panel out of view to the left."""
        self._leave_hide_timer.stop()
        if not self._is_showing:
            return
        if self._dismiss_locked:
            return
        self._is_showing = False

        self._stop_anim()
        self._anim = QPropertyAnimation(self, b"pos", self)
        self._anim.setDuration(self.ANIM_DURATION_MS)
        y0 = self._top_inset
        self._anim.setStartValue(self.pos())
        self._anim.setEndValue(QPoint(-self._panel_width, y0))
        self._anim.setEasingCurve(QEasingCurve.InCubic)
        self._anim.finished.connect(self._on_hide_finished)
        self._anim.start()

    def is_panel_visible(self) -> bool:
        """Return True if the panel is currently shown or animating in.

        Returns:
            bool
        """
        return self._is_showing

    def panel_global_rect(self) -> QRect:
        """
        Return the panel bounds in screen coordinates.

        Used for hit-testing during native drags, where Leave events are unreliable.

        Returns:
            QRect: Global geometry of the panel.
        """
        return self._global_panel_rect()

    def is_dismiss_locked(self) -> bool:
        """
        Return True while auto-dismiss is blocked (e.g. context menu or dialog).

        Returns:
            bool: Current lock state.
        """
        return self._dismiss_locked

    def lock_dismiss(self, locked: bool) -> None:
        """Prevent automatic dismiss (e.g. while a dialog is open above the panel).

        Args:
            locked: True to prevent dismiss, False to re-enable it.
        """
        self._dismiss_locked = locked
        if locked:
            self._leave_hide_timer.stop()

    def reposition(self) -> None:
        """Reposition the panel after the parent viewport resizes."""
        self._update_height()
        # Reason: never snap position while a slide anim runs (show or hide); otherwise
        # reposition() fights QPropertyAnimation and the rail looks like it replays.
        if self._anim is not None and self._anim.state() == QAbstractAnimation.Running:
            return
        if self._is_showing:
            self.move(0, self._top_inset)
        else:
            self._place_offscreen()

    # ------------------------------------------------------------------
    # Qt overrides
    # ------------------------------------------------------------------

    def mousePressEvent(self, event) -> None:
        """Consume all mouse presses so clicks don't fall through to the image grid."""
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        """Consume mouse releases for the same reason."""
        event.accept()

    def enterEvent(self, event) -> None:
        """Cancel a pending auto-hide (e.g. after a spurious Leave during drag)."""
        self._leave_hide_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        """Schedule auto-hide only after verifying the cursor really left the panel."""
        super().leaveEvent(event)
        if self._dismiss_locked:
            return
        self._leave_hide_timer.start(50)

    def wheelEvent(self, event) -> None:
        """Consume wheel at scroll limits so the image grid does not scroll underneath."""
        scroll = self.findChild(QScrollArea, "TagLibraryScrollArea")
        if scroll is not None:
            bar = scroll.verticalScrollBar()
            if bar is not None:
                delta = event.angleDelta().y()
                if delta == 0 and hasattr(event, "pixelDelta"):
                    delta = event.pixelDelta().y()
                if delta != 0:
                    at_top = bar.value() <= bar.minimum()
                    at_bottom = bar.value() >= bar.maximum()
                    if (delta > 0 and at_top) or (delta < 0 and at_bottom):
                        event.accept()
                        return
        super().wheelEvent(event)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _global_panel_rect(self) -> QRect:
        """Return the panel bounds in screen coordinates."""
        return QRect(self.mapToGlobal(QPoint(0, 0)), self.size())

    def _deferred_leave_hide_check(self) -> None:
        """Hide only if the cursor is outside the panel (avoids drag/context-menu glitches)."""
        if self._dismiss_locked or not self._is_showing:
            return
        if self._global_panel_rect().contains(QCursor.pos()):
            return
        self.hide_animated()

    def _place_offscreen(self) -> None:
        """Move the panel just outside the visible area."""
        self.move(-self._panel_width, self._top_inset)

    def _update_height(self) -> None:
        """Fit panel height inside the parent viewport with uniform margins."""
        parent = self.parentWidget()
        if not parent:
            return
        m = self.VIEWPORT_MARGIN_PX
        top = max(self._top_inset, m)
        h = max(1, parent.height() - top - m)
        self.setFixedHeight(h)

    def set_top_inset(self, inset: int) -> None:
        """Update vertical offset reserved at the top (e.g. floating logo)."""
        self._top_inset = max(inset, self.VIEWPORT_MARGIN_PX)
        self._update_height()
        if self._is_showing:
            self.move(0, self._top_inset)
        else:
            self._place_offscreen()

    def _stop_anim(self) -> None:
        """Stop any running slide animation."""
        if self._anim is not None:
            self._anim.stop()
            self._anim.deleteLater()
            self._anim = None

    def _on_hide_finished(self) -> None:
        """Clean up after the hide animation completes."""
        self.hide()
        self._place_offscreen()
        self.panel_did_hide.emit()

    @staticmethod
    def _build_stylesheet() -> str:
        """Return the QSS for the semi-transparent dark glass panel."""
        return """
            QFrame#TagPanelOverlay {
                background-color: rgba(30, 33, 38, 230);
                border-top-right-radius: 12px;
                border-bottom-right-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.08);
            }
        """
