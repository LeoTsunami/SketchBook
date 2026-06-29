"""
Worker class for applying or removing a tag on many images in a background thread.
"""
from typing import List, Literal

from qtpy.QtCore import QObject, QRunnable, Signal, Slot


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

    @Slot()
    def run(self) -> None:
        """Apply or remove the tag on all images in one bulk database pass."""
        try:
            if not self.image_ids:
                self.signals.finished.emit(0)
                return

            if self.operation == "add":
                count = self.image_manager.add_tags_to_images(
                    self.image_ids,
                    self.tag,
                    progress=self.signals.progress.emit,
                )
            else:
                count = self.image_manager.remove_tags_from_images(
                    self.image_ids,
                    self.tag,
                    progress=self.signals.progress.emit,
                )

            self.signals.finished.emit(count)

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
