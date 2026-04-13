"""
Floating tag panel overlay that slides over the image grid.

Appears on hover over a trigger button at the left edge of the viewport,
and hides when the mouse leaves the panel. Uses a semi-transparent dark
background with rounded right corners for a glass-like effect.
"""

from qtpy.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QGraphicsDropShadowEffect,
)
from qtpy.QtCore import (
    Qt,
    QAbstractAnimation,
    QPropertyAnimation,
    QEasingCurve,
    QPoint,
    Signal,
)
from qtpy.QtGui import QColor


class TagPanelOverlay(QFrame):
    """Floating overlay panel for the tag library.

    Parented to the image grid viewport so it hovers on top of the gallery
    without affecting the grid's layout or size.

    Args:
        parent: The QWidget this overlay is parented to (typically the viewport).
        width: Panel width in pixels.
    """

    panel_did_hide = Signal()

    PANEL_WIDTH = 370
    PANEL_EXTRA_HEIGHT = 55
    ANIM_DURATION_MS = 200

    def __init__(
        self, parent=None, width: int = PANEL_WIDTH, top_inset: int = 0
    ) -> None:
        super().__init__(parent)
        self._panel_width = width
        self._top_inset = top_inset
        self._is_showing = False
        self._anim: QPropertyAnimation | None = None
        self._dismiss_locked = False

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

    def lock_dismiss(self, locked: bool) -> None:
        """Prevent automatic dismiss (e.g. while a dialog is open above the panel).

        Args:
            locked: True to prevent dismiss, False to re-enable it.
        """
        self._dismiss_locked = locked

    def reposition(self) -> None:
        """Reposition the panel after the parent viewport resizes."""
        self._update_height()
        # Reason: never snap position while a slide anim runs (show or hide); otherwise
        # reposition() fights QPropertyAnimation and the rail looks like it replays.
        if (
            self._anim is not None
            and self._anim.state() == QAbstractAnimation.Running
        ):
            return
        if self._is_showing:
            self.move(0, self._top_inset)
        else:
            self._place_offscreen()

    # ------------------------------------------------------------------
    # Qt overrides
    # ------------------------------------------------------------------

    def leaveEvent(self, event) -> None:
        """Auto-hide when the mouse leaves the panel."""
        super().leaveEvent(event)
        self.hide_animated()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _place_offscreen(self) -> None:
        """Move the panel just outside the visible area."""
        self.move(-self._panel_width, self._top_inset)

    def _update_height(self) -> None:
        """Match the panel height to the parent minus top inset (below logo)."""
        if self.parentWidget():
            h = max(
                1,
                self.parentWidget().height() - self._top_inset + self.PANEL_EXTRA_HEIGHT,
            )
            self.setFixedHeight(h)

    def set_top_inset(self, inset: int) -> None:
        """Update vertical offset reserved at the top (e.g. floating logo)."""
        self._top_inset = max(0, inset)
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
