"""
Hover-expand panel for grid display controls (columns + fit mode).

The widget is a single button that stretches on hover: the icon fades out
while column/display controls fade in inside the same chrome.
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
    QSlider,
    QWidget,
)

from gui.hover_flyout_base import HoverFlyoutMixin
from gui.thumbnail_fitting import FitMode

_COLUMNS_SLIDER_STYLE = """
    QSlider#GridColumnsSlider::groove:horizontal {
        border: 1px solid #4d4d4d;
        height: 6px;
        background: #2b2d30;
        border-radius: 3px;
    }
    QSlider#GridColumnsSlider::sub-page:horizontal {
        background: #4b6eaf;
        border-radius: 3px;
    }
    QSlider#GridColumnsSlider::add-page:horizontal {
        background: #2b2d30;
        border-radius: 3px;
    }
    QSlider#GridColumnsSlider::handle:horizontal {
        background: #4b6eaf;
        border: 1px solid #6b8fd4;
        width: 14px;
        height: 14px;
        margin: -5px 0;
        border-radius: 7px;
    }
    QSlider#GridColumnsSlider::handle:horizontal:hover {
        background: #5d7bc0;
    }
"""


class GridDisplayFlyout(HoverFlyoutMixin, QFrame):
    """Single chrome that stretches on hover to reveal grid display controls."""

    COLLAPSED_WIDTH = 28
    ICON_SIZE = 18

    def __init__(
        self, collapsed_icon: QIcon, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._expanded = False
        self._anim_width = self.COLLAPSED_WIDTH
        self._controls_full_width = 0
        self._expanded_width = self.COLLAPSED_WIDTH
        self._anim_group: QParallelAnimationGroup | None = None
        self._init_hover_flyout_timers()

        self.setMouseTracking(True)
        self.setObjectName("GridDisplayFlyout")
        self.setFixedHeight(28)
        self.setFixedWidth(self.COLLAPSED_WIDTH)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Hover to expand grid display options")
        self.setStyleSheet("""
            QFrame#GridDisplayFlyout {
                background-color: #3c3f41;
                color: #ffffff;
                border: 1px solid #4d4d4d;
                border-radius: 4px;
            }
            QFrame#GridDisplayFlyout:hover {
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

        columns_label = QLabel("Columns:", self._controls)
        self.columns_slider = QSlider(Qt.Horizontal, self._controls)
        self.columns_slider.setObjectName("GridColumnsSlider")
        self.columns_slider.setStyleSheet(_COLUMNS_SLIDER_STYLE)
        self.columns_slider.setMinimum(3)
        self.columns_slider.setMaximum(10)
        self.columns_slider.setTickPosition(QSlider.NoTicks)
        self.columns_slider.setFixedWidth(100)
        self.columns_count = QLabel("4", self._controls)
        self.columns_count.setMinimumWidth(14)

        fit_label = QLabel("Display:", self._controls)
        self.fit_mode_combo = QComboBox(self._controls)
        self.fit_mode_combo.addItems(FitMode.labels())
        self.fit_mode_combo.setFixedWidth(100)

        controls_layout.addWidget(columns_label, 0, Qt.AlignVCenter)
        controls_layout.addWidget(self.columns_slider, 0, Qt.AlignVCenter)
        controls_layout.addWidget(self.columns_count, 0, Qt.AlignVCenter)
        controls_layout.addWidget(fit_label, 0, Qt.AlignVCenter)
        controls_layout.addWidget(self.fit_mode_combo, 0, Qt.AlignVCenter)

        self._controls_fx = QGraphicsOpacityEffect(self._controls)
        self._controls.setGraphicsEffect(self._controls_fx)
        self._controls_fx.setOpacity(0.0)
        self._controls.setMaximumWidth(0)

        layout.addWidget(self._controls, 0, Qt.AlignVCenter)

        self._expanded_width = self._measure_expanded_width()
        self._apply_collapsed_geometry()

        self._watch_slider_drag(self.columns_slider)
        self._watch_combo_popup(self.fit_mode_combo)

    def _hover_combo(self) -> QComboBox:
        """Return the display mode combo tracked for popup hit-testing."""
        return self.fit_mode_combo

    def eventFilter(self, obj, event) -> bool:
        """Track combo popup visibility for collapse timing."""
        self._combo_event_filter(self.fit_mode_combo, obj, event)
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
        Measure the fully expanded width of the control strip.

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
        """Snap to the compact icon state without animation."""
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
        """Animate stretch open with icon fade-out and controls fade-in."""
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
        """Animate stretch closed with icon fade-in and controls fade-out."""
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
