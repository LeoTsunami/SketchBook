"""
Overlay widget drawn above the image grid, attached to the scrollbar.
Shown when scrolling fast, hidden when scrolling slowly. Displays one image (e.g. center of view).
Uses fade-in on show and fade-out on hide.
"""
from qtpy.QtWidgets import QFrame, QVBoxLayout, QLabel, QGraphicsOpacityEffect
from qtpy.QtCore import Qt, QPropertyAnimation, QEasingCurve
from qtpy.QtGui import QPixmap


class ScrollPreviewOverlay(QFrame):
    """
    Panel attached to the scrollbar area, drawn above the grid.
    Hidden by default; parent controls visibility based on scroll speed.
    Displays a single image with fade-in / fade-out.
    """

    OVERLAY_WIDTH = 150   # Narrow vertical strip next to scrollbar
    OVERLAY_HEIGHT = 280  # Tall rectangle on height
    MARGIN_RIGHT = 12
    FADE_DURATION_MS = 180  # Duration of fade-in and fade-out

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ScrollPreviewOverlay")
        self.setWindowFlags(Qt.Widget)
        self.setFixedSize(self.OVERLAY_WIDTH, self.OVERLAY_HEIGHT)
        self.setStyleSheet("""
            QFrame#ScrollPreviewOverlay {
                background-color: rgba(35, 35, 35, 0.92);
                border: 1px solid rgba(100, 100, 100, 0.6);
                border-radius: 8px;
            }
        """)
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)
        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignCenter)
        self._image_label.setScaledContents(True)
        self._image_label.setMinimumSize(1, 1)
        self._image_label.setStyleSheet("background: transparent;")
        layout.addWidget(self._image_label)
        self._fade_in_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_in_anim.setDuration(self.FADE_DURATION_MS)
        self._fade_in_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_in_anim.setStartValue(0.0)
        self._fade_in_anim.setEndValue(1.0)
        self._fade_out_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_out_anim.setDuration(self.FADE_DURATION_MS)
        self._fade_out_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self._fade_out_anim.setStartValue(1.0)
        self._fade_out_anim.setEndValue(0.0)
        self._fade_out_anim.finished.connect(self._on_fade_out_finished)
        self.hide()

    def _on_fade_out_finished(self) -> None:
        """After fade-out: hide widget, reset opacity, clear image so next show starts from 0."""
        self.hide()
        self._opacity_effect.setOpacity(0.0)
        self.clear_image()

    def show_animated(self) -> None:
        """Show overlay with fade-in. Stops any running fade-out."""
        self._fade_out_anim.stop()
        if not self.isVisible():
            self.show()
            self._opacity_effect.setOpacity(0.0)
        self._fade_in_anim.stop()
        self._fade_in_anim.setStartValue(self._opacity_effect.opacity())
        self._fade_in_anim.setEndValue(1.0)
        self._fade_in_anim.start()

    def hide_animated(self) -> None:
        """Hide overlay with fade-out. Stops any running fade-in. Image cleared when fade ends."""
        if not self.isVisible():
            return
        self._fade_in_anim.stop()
        self._fade_out_anim.setStartValue(self._opacity_effect.opacity())
        self._fade_out_anim.setEndValue(0.0)
        self._fade_out_anim.start()

    def hide_immediate(self) -> None:
        """Hide overlay immediately without animation (e.g. when clearing the grid)."""
        self._fade_in_anim.stop()
        self._fade_out_anim.stop()
        self._opacity_effect.setOpacity(0.0)
        self.hide()
        self.clear_image()

    def set_image(self, pixmap: QPixmap) -> None:
        """Display the given pixmap filling the overlay (no margin), center-cropped to overlay size."""
        if pixmap.isNull():
            self._image_label.clear()
            return
        w, h = self.OVERLAY_WIDTH, self.OVERLAY_HEIGHT
        scaled = pixmap.scaled(
            w,
            h,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )
        if scaled.width() > w or scaled.height() > h:
            x = (scaled.width() - w) // 2
            y = (scaled.height() - h) // 2
            scaled = scaled.copy(x, y, w, h)
        self._image_label.setPixmap(scaled)

    def clear_image(self) -> None:
        """Clear the displayed image."""
        self._image_label.clear()

    def update_geometry_from_viewport(self, viewport_width: int, viewport_height: int) -> None:
        """Position on the right; Y follows scrollbar thumb (call with scroll values for Y)."""
        x = viewport_width - self.OVERLAY_WIDTH - self.MARGIN_RIGHT
        y = (viewport_height - self.OVERLAY_HEIGHT) // 2
        self.setGeometry(x, y, self.OVERLAY_WIDTH, self.OVERLAY_HEIGHT)

    def update_geometry_from_scroll(
        self,
        viewport_width: int,
        viewport_height: int,
        scroll_value: int,
        scroll_max: int,
    ) -> None:
        """Position the overlay on the right, Y aligned with the scrollbar thumb so it follows scroll."""
        x = viewport_width - self.OVERLAY_WIDTH - self.MARGIN_RIGHT
        track_height = viewport_height - self.OVERLAY_HEIGHT
        if scroll_max > 0 and track_height > 0:
            # Same ratio as the scrollbar thumb position
            y = int((scroll_value / scroll_max) * track_height)
            y = max(0, min(y, track_height))
        else:
            y = (viewport_height - self.OVERLAY_HEIGHT) // 2
        self.setGeometry(x, y, self.OVERLAY_WIDTH, self.OVERLAY_HEIGHT)
