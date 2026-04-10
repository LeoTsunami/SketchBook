"""
Worker for asynchronous image loading.
"""
from pathlib import Path
from qtpy.QtCore import QObject, Signal, QRunnable, Qt
from qtpy.QtGui import QImage, QPixmap
from gui.thumbnail_fitting import FitMode

class ImageLoaderSignals(QObject):
    """Signals for the image loader worker."""
    finished = Signal(str, tuple)  # image_id, (fast_pixmap, high_quality_pixmap)
    error = Signal(str, str)  # image_id, error message

class ImageLoaderWorker(QRunnable):
    """Worker for loading and scaling images asynchronously."""
    
    def __init__(
        self,
        image_id: str,
        image_path: Path,
        target_size: tuple[int, int],
        fit_mode: FitMode = FitMode.CROP_ALL,
    ):
        """
        Initialize the worker.

        Args:
            image_id: Unique identifier of the image
            image_path: Path to the image file
            target_size: Target size (width, height) for the scaled image
            fit_mode: Rendering mode used by grid for final display
        """
        super().__init__()
        self.image_id = image_id
        self.image_path = image_path
        self.target_size = target_size
        self.fit_mode = fit_mode
        self.signals = ImageLoaderSignals()
        
        # Set low priority to avoid blocking UI
        self.setAutoDelete(True)
    
    def run(self):
        """Load and scale the image."""
        try:
            if not self.image_path.exists():
                raise FileNotFoundError(f"Image not found: {self.image_path}")
            
            # Load image with QImage for better memory management
            image = QImage(str(self.image_path))
            if image.isNull():
                raise ValueError(f"Failed to load image: {self.image_path}")
            
            # Fit image into target box while preserving aspect ratio (no crop).
            target_width, target_height = self.target_size

            if target_width > 0 and target_height > 0:
                # Use device pixel ratio for high-DPI displays (usually 1.0, 1.5, or 2.0)
                # and upscale slightly even on standard displays for crisper thumbnails.
                # Reason: loading a larger source pixmap and letting Qt downscale improves
                # perceived quality in the grid, especially after resizes.
                from qtpy.QtWidgets import QApplication
                app = QApplication.instance()
                device_pixel_ratio = app.devicePixelRatio() if app else 1.0

                # Scale to account for device pixel ratio for better quality.
                # Reason: crop/fill modes can zoom more aggressively than fit-all,
                # so we keep a larger source to avoid visible pixelation.
                scale_factor = max(device_pixel_ratio, 3.0)
                scaled_width = int(target_width * scale_factor)
                scaled_height = int(target_height * scale_factor)

                aspect_mode = (
                    Qt.KeepAspectRatioByExpanding
                    if self.fit_mode in (FitMode.CROP_ALL, FitMode.FIT_HEIGHT, FitMode.FIT_WIDTH)
                    else Qt.KeepAspectRatio
                )

                fast_pixmap = QPixmap.fromImage(
                    image.scaled(
                        target_width,
                        target_height,
                        aspect_mode,
                        Qt.FastTransformation,
                    )
                )
                high_quality_pixmap = QPixmap.fromImage(
                    image.scaled(
                        scaled_width,
                        scaled_height,
                        aspect_mode,
                        Qt.SmoothTransformation,
                    )
                )
                high_quality_pixmap.setDevicePixelRatio(device_pixel_ratio)
                result = (fast_pixmap, high_quality_pixmap)
            else:
                result = (QPixmap.fromImage(image), QPixmap.fromImage(image))
            
            # Emit result (guard: receiver may be deleted if window closed)
            self._safe_emit_finished(result)
            
        except Exception as e:
            self._safe_emit_error(str(e))

    def _safe_emit_finished(self, result: tuple) -> None:
        """Emit finished signal; no-op if signal source/receiver was deleted (e.g. window closed)."""
        try:
            self.signals.finished.emit(self.image_id, result)
        except RuntimeError:
            # Signal source or receiver deleted (window closed); ignore
            pass

    def _safe_emit_error(self, message: str) -> None:
        """Emit error signal; no-op if signal source/receiver was deleted (e.g. window closed)."""
        try:
            self.signals.error.emit(self.image_id, message)
        except RuntimeError:
            pass 