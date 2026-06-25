"""
Shared hover-expand / leave-collapse behaviour for toolbar flyout widgets.
"""

from __future__ import annotations

from qtpy.QtCore import QEvent, QPoint, QRect, QTimer
from qtpy.QtGui import QCursor
from qtpy.QtWidgets import QComboBox, QSlider, QWidget


class HoverFlyoutMixin:
    """Mixin for flyouts that expand on hover and collapse after the pointer leaves."""

    HOVER_DELAY_MS = 300
    LEAVE_DELAY_MS = 300
    ANIM_DURATION_MS = 300

    _expand_timer: QTimer
    _leave_timer: QTimer
    _slider_dragging: bool

    def _init_hover_flyout_timers(self) -> None:
        """Create expand/collapse delay timers."""
        self._slider_dragging = False

        self._expand_timer = QTimer(self)
        self._expand_timer.setSingleShot(True)
        self._expand_timer.timeout.connect(self._on_hover_expand_timer)

        self._leave_timer = QTimer(self)
        self._leave_timer.setSingleShot(True)
        self._leave_timer.timeout.connect(self._deferred_collapse_check)

    def _watch_combo_popup(self, combo: QComboBox) -> None:
        """
        Track combo popup show/hide so collapse works after selection.

        Args:
            combo: Combo box whose popup should keep the flyout open.
        """
        combo.installEventFilter(self)
        view = combo.view()
        if view is not None:
            view.installEventFilter(self)

    def _watch_slider_drag(self, slider: QSlider) -> None:
        """
        Track slider drag so collapse waits until release.

        Args:
            slider: Columns slider on the grid display flyout.
        """
        slider.sliderPressed.connect(self._on_slider_pressed)
        slider.sliderReleased.connect(self._on_slider_released)

    def _on_slider_pressed(self) -> None:
        """Pause collapse while the columns slider is dragged."""
        self._slider_dragging = True
        self._leave_timer.stop()

    def _on_slider_released(self) -> None:
        """Resume collapse checks after the slider is released."""
        self._slider_dragging = False
        self._leave_timer.start(self.LEAVE_DELAY_MS)

    def _global_bounds(self) -> QRect:
        """Return widget bounds in screen coordinates."""
        return QRect(self.mapToGlobal(QPoint(0, 0)), self.size())

    def _popup_bounds(self, combo: QComboBox) -> QRect | None:
        """
        Return the combo popup bounds when visible.

        Args:
            combo: Combo box that may have an open popup.

        Returns:
            Global QRect of the popup, or None if closed.
        """
        view = combo.view()
        if view is None:
            return None
        popup = view.window()
        if popup is None or not popup.isVisible():
            return None
        return QRect(popup.mapToGlobal(QPoint(0, 0)), popup.size())

    def _interaction_bounds(self, combo: QComboBox | None = None) -> QRect:
        """
        Return bounds that should keep the flyout open (widget + popup).

        Args:
            combo: Optional combo whose popup counts as inside.

        Returns:
            United global QRect.
        """
        bounds = self._global_bounds()
        if combo is not None:
            popup_bounds = self._popup_bounds(combo)
            if popup_bounds is not None:
                bounds = bounds.united(popup_bounds)
        return bounds

    def _pointer_inside_interaction(self, combo: QComboBox | None = None) -> bool:
        """
        Return True when the cursor is over the flyout or its combo popup.

        Args:
            combo: Optional combo whose popup counts as inside.

        Returns:
            bool
        """
        return self._interaction_bounds(combo).contains(QCursor.pos())

    def _on_hover_expand_timer(self) -> None:
        """Expand after the hover delay if the pointer is still over the flyout."""
        if self._pointer_inside_interaction(self._hover_combo()):
            self._expand()

    def _hover_combo(self) -> QComboBox | None:
        """
        Return the combo tracked by this flyout, if any.

        Returns:
            QComboBox or None for subclasses without a combo.
        """
        return None

    def _schedule_collapse_check(self) -> None:
        """Start or restart the leave-collapse timer."""
        self._leave_timer.start(self.LEAVE_DELAY_MS)

    def _deferred_collapse_check(self) -> None:
        """Collapse only when the cursor left the flyout and any open popup."""
        combo = self._hover_combo()
        if self._slider_dragging:
            self._schedule_collapse_check()
            return
        if combo is not None and self._popup_bounds(combo) is not None:
            self._schedule_collapse_check()
            return
        if self._pointer_inside_interaction(combo):
            return
        self._collapse()

    def enterEvent(self, event) -> None:
        """Expand after a short hover delay."""
        self._leave_timer.stop()
        if not self._expanded:
            self._expand_timer.start(self.HOVER_DELAY_MS)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        """Schedule collapse after the pointer may have left."""
        super().leaveEvent(event)
        self._expand_timer.stop()
        self._schedule_collapse_check()

    def _combo_event_filter(self, combo: QComboBox, obj, event) -> None:
        """
        React to combo / popup visibility for collapse timing.

        Args:
            combo: Combo box owned by this flyout.
            obj: Object receiving the event.
            event: Qt event.
        """
        view = combo.view()
        if obj not in (combo, view):
            return
        try:
            show_type = QEvent.Type.Show
            hide_type = QEvent.Type.Hide
        except AttributeError:
            show_type = QEvent.Show
            hide_type = QEvent.Hide
        if event.type() == show_type:
            self._leave_timer.stop()
            self._expand_timer.stop()
            self._expand()
        elif event.type() == hide_type:
            self._schedule_collapse_check()
