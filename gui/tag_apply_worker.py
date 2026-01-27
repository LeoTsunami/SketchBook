"""
Worker class for applying a tag to many images in a background thread.
"""
from typing import List

from qtpy.QtCore import QObject, QRunnable, Signal, Slot


class TagApplySignals(QObject):
    """Signals for the tag apply worker."""

    progress = Signal(int, int)  # current, total
    finished = Signal(int)  # total processed
    error = Signal(str)


class TagApplyWorker(QRunnable):
    """Worker for applying a tag to multiple images asynchronously."""

    def __init__(self, image_manager, image_ids: List[str], tag: str):
        """
        Initialize the worker.

        Args:
            image_manager: ImageManager instance.
            image_ids: List of image IDs to update.
            tag: Tag to add to each image.
        """
        super().__init__()
        self.image_manager = image_manager
        self.image_ids = list(image_ids)
        self.tag = tag
        self.signals = TagApplySignals()
        self.setAutoDelete(True)

    def _emit_progress(self, current: int, total: int) -> None:
        """Emit bounded progress."""
        current = min(current, total)
        self.signals.progress.emit(current, total)

    @Slot()
    def run(self) -> None:
        """Apply the tag to all images."""
        try:
            total = len(self.image_ids)
            if total == 0:
                self.signals.finished.emit(0)
                return

            self._emit_progress(0, total)

            for index, image_id in enumerate(self.image_ids, start=1):
                metadata = self.image_manager.get_image_metadata(image_id)
                if metadata:
                    new_tags = metadata.tags.copy()
                    new_tags.add(self.tag)
                    self.image_manager.update_image_metadata(image_id, tags=new_tags)

                self._emit_progress(index, total)

            # Ensure 100% progress
            self._emit_progress(total, total)
            self.signals.finished.emit(total)

        except Exception as exc:  # pragma: no cover - defensive
            self.signals.error.emit(str(exc))

