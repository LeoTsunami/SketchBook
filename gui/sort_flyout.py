"""
Hover-expand strip for the sort combo: icon when collapsed, label + combo on hover.
"""

from __future__ import annotations

from qtpy.QtCore import (
    QEasingCurve,
    Property,
    QParallelAnimationGroup,
    QPropertyAnimation,
    Qt,
    QSize,
)
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import (
    QComboBox,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QWidget,
)

from gui.hover_flyout_base import HoverFlyoutMixin


class SortFlyout(HoverFlyoutMixin, QFrame):
    """Sort control that collapses to an icon and expands on hover."""

    COLLAPSED_WIDTH = 28
    ICON_SIZE = 18

    def __init__(self, collapsed_icon: QIcon, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._expanded = False
        self._anim_width = self.COLLAPSED_WIDTH
        self._controls_full_width = 0
        self._expanded_width = self.COLLAPSED_WIDTH
        self._anim_group: QParallelAnimationGroup | None = None
        self._init_hover_flyout_timers()

        self.setMouseTracking(True)
        self.setObjectName("SortFlyout")
        self.setFixedHeight(28)
        self.setFixedWidth(self.COLLAPSED_WIDTH)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Hover to expand sort options")
        self.setStyleSheet("""
            QFrame#SortFlyout {
                background-color: #3c3f41;
                color: #ffffff;
                border: 1px solid #4d4d4d;
                border-radius: 4px;
            }
            QFrame#SortFlyout:hover {
                border-color: #5a7ec8;
            }
            QLabel {
                color: #ffffff;
                font-size: 11px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        self._icon_label = QLabel(self)
        self._icon_label.setAlignment(Qt.AlignCenter)
        self._icon_label.setFixedSize(self.ICON_SIZE, self.ICON_SIZE)
        if not collapsed_icon.isNull():
            self._icon_label.setPixmap(
                collapsed_icon.pixmap(QSize(self.ICON_SIZE, self.ICON_SIZE))
            )
        layout.addWidget(self._icon_label, 0, Qt.AlignCenter)

        self._icon_fx = QGraphicsOpacityEffect(self._icon_label)
        self._icon_label.setGraphicsEffect(self._icon_fx)
        self._icon_fx.setOpacity(1.0)

        self._controls = QWidget(self)
        controls_layout = QHBoxLayout(self._controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(6)

        sort_label = QLabel("Sort:", self._controls)
        self.sort_combo = QComboBox(self._controls)
        self.sort_combo.setFixedWidth(132)

        controls_layout.addWidget(sort_label, 0, Qt.AlignVCenter)
        controls_layout.addWidget(self.sort_combo, 0, Qt.AlignVCenter)

        self._controls_fx = QGraphicsOpacityEffect(self._controls)
        self._controls.setGraphicsEffect(self._controls_fx)
        self._controls_fx.setOpacity(0.0)
        self._controls.setMaximumWidth(0)

        layout.addWidget(self._controls, 0, Qt.AlignVCenter)

        self._expanded_width = self._measure_expanded_width()
        self._apply_collapsed_geometry()

        self._watch_combo_popup(self.sort_combo)

    def _hover_combo(self) -> QComboBox:
        """Return the sort combo tracked for popup hit-testing."""
        return self.sort_combo

    def eventFilter(self, obj, event) -> bool:
        """Track combo popup visibility for collapse timing."""
        self._combo_event_filter(self.sort_combo, obj, event)
        return super().eventFilter(obj, event)

    def get_anim_width(self) -> int:
        """Return the animated outer width."""
        return self._anim_width

    def set_anim_width(self, width: int) -> None:
        """
        Set outer width and interpolate inner controls during the stretch.

        Args:
            width: Target width in pixels.
        """
        self._anim_width = int(width)
        self.setFixedWidth(self._anim_width)

        span = max(1, self._expanded_width - self.COLLAPSED_WIDTH)
        progress = max(0.0, min(1.0, (self._anim_width - self.COLLAPSED_WIDTH) / span))
        controls_w = int(self._controls_full_width * progress)
        self._controls.setMaximumWidth(controls_w)

    animWidth = Property(int, get_anim_width, set_anim_width)

    def _measure_expanded_width(self) -> int:
        """
        Measure the fully expanded width of the sort controls.

        Returns:
            Width in pixels including margins.
        """
        self._controls.setMaximumWidth(16777215)
        self._controls_full_width = self._controls.sizeHint().width()
        margins = self.layout().contentsMargins()
        return (
            self._controls_full_width
            + margins.left()
            + margins.right()
            + 4
        )

    def _apply_collapsed_geometry(self) -> None:
        """Snap to the compact icon-only state without animation."""
        self._expanded = False
        self._anim_width = self.COLLAPSED_WIDTH
        self.setFixedWidth(self.COLLAPSED_WIDTH)
        self._controls.setMaximumWidth(0)
        self._icon_fx.setOpacity(1.0)
        self._controls_fx.setOpacity(0.0)
        self._icon_label.show()

    def _stop_anim(self) -> None:
        """Stop any running animation group."""
        if self._anim_group is not None:
            self._anim_group.stop()
            self._anim_group.deleteLater()
            self._anim_group = None

    def _expand(self) -> None:
        """Animate stretch open with icon fade-out and combo fade-in."""
        if self._expanded:
            return
        self._expanded = True
        self._stop_anim()

        width_anim = QPropertyAnimation(self, b"animWidth", self)
        width_anim.setDuration(self.ANIM_DURATION_MS)
        width_anim.setStartValue(self._anim_width)
        width_anim.setEndValue(self._expanded_width)
        width_anim.setEasingCurve(QEasingCurve.OutCubic)

        icon_anim = QPropertyAnimation(self._icon_fx, b"opacity", self)
        icon_anim.setDuration(self.ANIM_DURATION_MS)
        icon_anim.setStartValue(self._icon_fx.opacity())
        icon_anim.setEndValue(0.0)
        icon_anim.setEasingCurve(QEasingCurve.OutCubic)

        controls_anim = QPropertyAnimation(self._controls_fx, b"opacity", self)
        controls_anim.setDuration(self.ANIM_DURATION_MS)
        controls_anim.setStartValue(self._controls_fx.opacity())
        controls_anim.setEndValue(1.0)
        controls_anim.setEasingCurve(QEasingCurve.OutCubic)

        self._anim_group = QParallelAnimationGroup(self)
        self._anim_group.addAnimation(width_anim)
        self._anim_group.addAnimation(icon_anim)
        self._anim_group.addAnimation(controls_anim)
        self._anim_group.finished.connect(self._on_anim_group_finished)
        self._anim_group.start()

    def _on_anim_group_finished(self) -> None:
        """Finalize visibility after expand/collapse animations."""
        if self._expanded:
            self._icon_label.hide()
        else:
            self._apply_collapsed_geometry()

    def _collapse(self) -> None:
        """Animate stretch closed with icon fade-in and combo fade-out."""
        if not self._expanded:
            return
        self._expanded = False
        self._icon_label.show()
        self._stop_anim()

        width_anim = QPropertyAnimation(self, b"animWidth", self)
        width_anim.setDuration(self.ANIM_DURATION_MS)
        width_anim.setStartValue(self._anim_width)
        width_anim.setEndValue(self.COLLAPSED_WIDTH)
        width_anim.setEasingCurve(QEasingCurve.InCubic)

        icon_anim = QPropertyAnimation(self._icon_fx, b"opacity", self)
        icon_anim.setDuration(self.ANIM_DURATION_MS)
        icon_anim.setStartValue(self._icon_fx.opacity())
        icon_anim.setEndValue(1.0)
        icon_anim.setEasingCurve(QEasingCurve.InCubic)

        controls_anim = QPropertyAnimation(self._controls_fx, b"opacity", self)
        controls_anim.setDuration(self.ANIM_DURATION_MS)
        controls_anim.setStartValue(self._controls_fx.opacity())
        controls_anim.setEndValue(0.0)
        controls_anim.setEasingCurve(QEasingCurve.InCubic)

        self._anim_group = QParallelAnimationGroup(self)
        self._anim_group.addAnimation(width_anim)
        self._anim_group.addAnimation(icon_anim)
        self._anim_group.addAnimation(controls_anim)
        self._anim_group.finished.connect(self._on_anim_group_finished)
        self._anim_group.start()
