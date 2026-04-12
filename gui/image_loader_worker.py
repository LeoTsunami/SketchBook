"""
Worker for asynchronous image loading with two-phase display.

Phase 1 (fast): Emit a cell-sized pixmap with FastTransformation for instant visual feedback.
Phase 2 (HQ):  Emit a higher-resolution pixmap with SmoothTransformation for crisp display.

The fast pixmap is emitted *before* the expensive HQ scaling begins, so the main thread
can display it while the worker is still computing the sharp version.
"""

from pathlib import Path
from qtpy.QtCore import QObject, Signal, QRunnable, Qt
from qtpy.QtGui import QImage, QPixmap
from gui.thumbnail_fitting import FitMode


class ImageLoaderSignals(QObject):
    """Signals for the image loader worker."""

    fast_ready = Signal(str, object)  # image_id, fast QPixmap (cell-sized, rough)
    finished = Signal(str, object)  # image_id, high-quality QPixmap
    error = Signal(str, str)  # image_id, error message


class ImageLoaderWorker(QRunnable):
    """Worker for loading and scaling images asynchronously.

    Args:
        image_id: Unique identifier of the image.
        image_path: Path to the image file.
        target_size: Target size (width, height) for the cell.
        fit_mode: Rendering mode used by grid for final display.
        emit_fast: If True, emit ``fast_ready`` before computing HQ.
            Set False for background preloads (e.g. scroll-preview extracts)
            where instant visual feedback is not needed.
    """

    def __init__(
        self,
        image_id: str,
        image_path: Path,
        target_size: tuple[int, int],
        fit_mode: FitMode = FitMode.CROP_ALL,
        emit_fast: bool = True,
    ):
        super().__init__()
        self.image_id = image_id
        self.image_path = image_path
        self.target_size = target_size
        self.fit_mode = fit_mode
        self.emit_fast = emit_fast
        self.signals = ImageLoaderSignals()
        self.setAutoDelete(True)

    def run(self):
        """Load, scale, and emit pixmaps (fast then HQ)."""
        try:
            if not self.image_path.exists():
                raise FileNotFoundError(f"Image not found: {self.image_path}")

            image = QImage(str(self.image_path))
            if image.isNull():
                raise ValueError(f"Failed to load image: {self.image_path}")

            target_width, target_height = self.target_size
            if target_width <= 0 or target_height <= 0:
                px = QPixmap.fromImage(image)
                self._safe_emit_finished(px)
                return

            aspect_mode = (
                Qt.KeepAspectRatioByExpanding
                if self.fit_mode
                in (FitMode.CROP_ALL, FitMode.FIT_HEIGHT, FitMode.FIT_WIDTH)
                else Qt.KeepAspectRatio
            )

            # Phase 1: fast pixmap at cell size — emitted immediately so the
            # main thread can show *something* while we compute the sharp version.
            if self.emit_fast:
                fast_pixmap = QPixmap.fromImage(
                    image.scaled(
                        target_width,
                        target_height,
                        aspect_mode,
                        Qt.FastTransformation,
                    )
                )
                self._safe_emit_fast(fast_pixmap)

            # Phase 2: HQ pixmap at 2x cell size for crisp rendering after
            # Qt downscale. Previous 3x was excessive and doubled decode time.
            from qtpy.QtWidgets import QApplication

            app = QApplication.instance()
            device_pixel_ratio = app.devicePixelRatio() if app else 1.0
            scale_factor = max(device_pixel_ratio, 2.0)
            scaled_width = int(target_width * scale_factor)
            scaled_height = int(target_height * scale_factor)

            hq_pixmap = QPixmap.fromImage(
                image.scaled(
                    scaled_width,
                    scaled_height,
                    aspect_mode,
                    Qt.SmoothTransformation,
                )
            )
            hq_pixmap.setDevicePixelRatio(device_pixel_ratio)
            self._safe_emit_finished(hq_pixmap)

        except Exception as e:
            self._safe_emit_error(str(e))

    def _safe_emit_fast(self, pixmap: QPixmap) -> None:
        """Emit fast_ready signal; no-op if receiver was deleted."""
        try:
            self.signals.fast_ready.emit(self.image_id, pixmap)
        except RuntimeError:
            pass

    def _safe_emit_finished(self, pixmap: QPixmap) -> None:
        """Emit finished signal; no-op if receiver was deleted."""
        try:
            self.signals.finished.emit(self.image_id, pixmap)
        except RuntimeError:
            pass

    def _safe_emit_error(self, message: str) -> None:
        """Emit error signal; no-op if receiver was deleted."""
        try:
            self.signals.error.emit(self.image_id, message)
        except RuntimeError:
            pass
