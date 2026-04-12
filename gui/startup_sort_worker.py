"""
Background sort of image metadata for faster application startup.

Runs in QThreadPool so the main thread can paint the empty window first.
Qt widgets must not be touched from the worker run() method.
"""

from typing import List

from qtpy.QtCore import QObject, QRunnable, Signal

from core.image_db import ImageDatabase, ImageMetadata


class StartupSortSignals(QObject):
    """Signals owned by the main thread; emitted when background sort completes."""

    finished = Signal(object)


class StartupSortRunnable(QRunnable):
    """
    Sort a snapshot of image metadata off the GUI thread.

    Args:
        db: Image database (only ``snapshot_metadata_values`` / ``_sort_images`` used).
        sort_by: Sort mode string (same as ``ImageDatabase.list_images``).
        shuffle_iteration: Shuffle iteration for ``course_random`` (usually 0 at startup).
        signals: ``StartupSortSignals`` instance created on the main thread.
    """

    def __init__(
        self,
        db: ImageDatabase,
        sort_by: str,
        shuffle_iteration: int,
        signals: StartupSortSignals,
    ) -> None:
        super().__init__()
        self._db = db
        self._sort_by = sort_by
        self._shuffle_iteration = shuffle_iteration
        self._signals = signals

    def run(self) -> None:
        """Load snapshot and sort; emit sorted list or an Exception."""
        try:
            raw: List[ImageMetadata] = self._db.snapshot_metadata_values()
            out: List[ImageMetadata] = self._db._sort_images(
                raw,
                self._sort_by,
                shuffle_iteration=self._shuffle_iteration,
            )
            self._signals.finished.emit(out)
        except Exception as exc:  # pragma: no cover - defensive
            self._signals.finished.emit(exc)
