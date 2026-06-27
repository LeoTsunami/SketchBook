"""
Worker class for applying or removing a tag on many images in a background thread.
"""
import time
from typing import List, Literal

from qtpy.QtCore import QObject, QRunnable, Signal, Slot

# Throttle progress: emit at most every N images to avoid flooding the main thread
_PROGRESS_EMIT_EVERY = 25
# Min interval between progress emissions (seconds) when processing is very fast
_PROGRESS_MIN_INTERVAL_S = 0.08


class TagApplySignals(QObject):
    """Signals for the tag apply/remove worker."""

    progress = Signal(int, int)  # current, total
    finished = Signal(int)  # total processed
    error = Signal(str)


class TagApplyWorker(QRunnable):
    """Worker for applying or removing a tag on multiple images asynchronously."""

    def __init__(
        self,
        image_manager,
        image_ids: List[str],
        tag: str,
        operation: Literal["add", "remove"] = "add",
    ):
        """
        Initialize the worker.

        Args:
            image_manager: ImageManager instance.
            image_ids: List of image IDs to update.
            tag: Tag to add or remove on each image.
            operation: "add" to add the tag, "remove" to remove it.
        """
        super().__init__()
        self.image_manager = image_manager
        self.image_ids = list(image_ids)
        self.tag = tag
        self.operation = operation
        self.signals = TagApplySignals()
        self.setAutoDelete(True)

    def _emit_progress(self, current: int, total: int) -> None:
        """Emit bounded progress."""
        current = min(current, total)
        self.signals.progress.emit(current, total)

    @Slot()
    def run(self) -> None:
        """Apply or remove the tag on all images."""
        try:
            total = len(self.image_ids)
            if total == 0:
                self.signals.finished.emit(0)
                return

            self._emit_progress(0, total)
            last_emit_index = 0
            last_emit_time = time.monotonic()

            for index, image_id in enumerate(self.image_ids, start=1):
                metadata = self.image_manager.get_image_metadata(image_id)
                if metadata:
                    new_tags = metadata.tags.copy()
                    if self.operation == "add":
                        new_tags.add(self.tag)
                    else:
                        new_tags.discard(self.tag)
                    self.image_manager.update_image_metadata(image_id, tags=new_tags)

                # Throttle progress to avoid freezing UI (too many queued slot calls)
                now = time.monotonic()
                if (
                    index - last_emit_index >= _PROGRESS_EMIT_EVERY
                    or (now - last_emit_time) >= _PROGRESS_MIN_INTERVAL_S
                    or index == total
                ):
                    self._emit_progress(index, total)
                    last_emit_index = index
                    last_emit_time = now

            self._emit_progress(total, total)
            self.signals.finished.emit(total)

        except Exception as exc:  # pragma: no cover - defensive
            self.signals.error.emit(str(exc))


class TagLibraryDeleteWorker(QRunnable):
    """Worker that removes tag names from all images in the library."""

    def __init__(self, image_manager, tags: List[str]):
        """
        Initialize the worker.

        Args:
            image_manager: ImageManager instance.
            tags: User tag names to delete from every image.
        """
        super().__init__()
        self.image_manager = image_manager
        self.tags = list(tags)
        self.signals = TagApplySignals()
        self.setAutoDelete(True)

    @Slot()
    def run(self) -> None:
        """Remove tags from all images and emit progress."""
        try:
            count = self.image_manager.db.remove_tags(
                set(self.tags),
                progress=self.signals.progress.emit,
            )
            self.signals.finished.emit(count)
        except Exception as exc:  # pragma: no cover - defensive
            self.signals.error.emit(str(exc))

