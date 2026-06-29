"""
Colour flash when a tag is dropped onto an image thumbnail.
"""
from __future__ import annotations

from qtpy.QtCore import (
    QEasingCurve,
    QSequentialAnimationGroup,
    QTimer,
    QVariantAnimation,
    Qt,
)
from qtpy.QtGui import QColor, QPainter
from qtpy.QtWidgets import QWidget

PEAK_OPACITY = 0.3


class _TagDropFlashBase(QWidget):
    """Shared overlay shell for tag-drop colour feedback."""

    def __init__(self, color: QColor, parent: QWidget) -> None:
        super().__init__(parent)
        self._base_color = QColor(color)
        self._opacity = 0.0
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)

    def _sync_geometry(self) -> None:
        host = self.parentWidget()
        if host is not None:
            self.setGeometry(host.rect())

    def paintEvent(self, event) -> None:
        if self._opacity <= 0.0:
            return
        painter = QPainter(self)
        fill = QColor(self._base_color)
        fill.setAlpha(int(255 * self._opacity))
        painter.fillRect(self.rect(), fill)
        painter.end()


class TagDropFlashOverlay(_TagDropFlashBase):
    """
    Full-area colour overlay with a smooth opacity pulse (single thumbnail).

    Args:
        color: Tag accent colour (RGB; alpha is animated).
        parent: Host widget (typically the thumbnail image container).
    """

    FADE_IN_MS = 140
    FADE_OUT_MS = 220

    def __init__(self, color: QColor, parent: QWidget) -> None:
        super().__init__(color, parent)

        self._fade_in = QVariantAnimation(self)
        self._fade_in.setDuration(self.FADE_IN_MS)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(PEAK_OPACITY)
        self._fade_in.setEasingCurve(QEasingCurve.OutQuad)
        self._fade_in.valueChanged.connect(self._on_opacity_changed)

        self._fade_out = QVariantAnimation(self)
        self._fade_out.setDuration(self.FADE_OUT_MS)
        self._fade_out.setStartValue(PEAK_OPACITY)
        self._fade_out.setEndValue(0.0)
        self._fade_out.setEasingCurve(QEasingCurve.InQuad)
        self._fade_out.valueChanged.connect(self._on_opacity_changed)

        self._sequence = QSequentialAnimationGroup(self)
        self._sequence.addAnimation(self._fade_in)
        self._sequence.addAnimation(self._fade_out)
        self._sequence.finished.connect(self._on_finished)

    def start(self) -> None:
        """Run opacity pulse and remove the widget when done."""
        self._sync_geometry()
        self._opacity = 0.0
        self.show()
        self.raise_()
        self._sequence.start()

    def _on_opacity_changed(self, value: float) -> None:
        self._opacity = float(value)
        self.update()

    def _on_finished(self) -> None:
        self.hide()
        self.deleteLater()


class TagDropInstantFlash(_TagDropFlashBase):
    """
    Lightweight fixed-opacity flash (no animations, one paint).

    Used when many thumbnails need feedback at once.
    """

    DISPLAY_MS = 200

    def start(self) -> None:
        """Show at peak opacity briefly, then remove."""
        self._sync_geometry()
        self._opacity = PEAK_OPACITY
        self.show()
        self.raise_()
        self.update()
        QTimer.singleShot(self.DISPLAY_MS, self.deleteLater)


def play_tag_drop_flash(
    host: QWidget, color: QColor, *, animated: bool = True
) -> None:
    """
    Play a one-shot tag colour flash on a thumbnail image area.

    Args:
        host: Widget to cover (usually ``ImageThumbnail.image_container``).
        color: Tag accent colour.
        animated: If True, fade in/out; if False, instant tint (cheaper).
    """
    if host is None or color is None:
        return
    if animated:
        overlay = TagDropFlashOverlay(color, host)
    else:
        overlay = TagDropInstantFlash(color, host)
    overlay.start()
