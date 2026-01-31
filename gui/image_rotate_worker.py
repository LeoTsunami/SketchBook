"""
Worker for asynchronous image rotation (90° CW/CCW) to avoid freezing the UI.
"""
from pathlib import Path
from qtpy.QtCore import QObject, Signal, QRunnable


class RotateImageSignals(QObject):
    """Signals for the rotate image worker."""
    finished = Signal(str, bool, int, int)  # image_id, success, new_width, new_height
    error = Signal(str, str)  # image_id, error message


class RotateImageWorker(QRunnable):
    """Worker that rotates an image file in a background thread (file I/O only)."""

    def __init__(self, image_id: str, image_path: Path, clockwise: bool, image_format: str, image_manager):
        """
        Initialize the worker.

        Args:
            image_id: Unique identifier of the image.
            image_path: Full path to the image file.
            clockwise: True for 90° clockwise, False for counterclockwise.
            image_format: Image format ("JPEG", "PNG", etc.).
            image_manager: ImageManager instance (only rotate_image_file is called).
        """
        super().__init__()
        self.image_id = image_id
        self.image_path = image_path
        self.clockwise = clockwise
        self.image_format = image_format
        self.image_manager = image_manager
        self.signals = RotateImageSignals()
        self.setAutoDelete(True)

    def run(self):
        """Rotate the image file (runs in thread pool)."""
        try:
            success, w, h = self.image_manager.rotate_image_file(
                self.image_path, self.clockwise, self.image_format
            )
            self.signals.finished.emit(self.image_id, success, w, h)
        except Exception as e:
            self.signals.error.emit(self.image_id, str(e))
