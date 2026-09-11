"""
Background GitHub update check and Setup.exe download.

Qt widgets must not be touched from ``run()``.
"""

from __future__ import annotations

from pathlib import Path

from qtpy.QtCore import QObject, QRunnable, Signal, Slot

from core.update_check import (
    ReleaseInfo,
    download_file,
    fetch_latest_release,
    is_update_available,
    load_update_feed,
)
from core.version import get_version


class UpdateCheckSignals(QObject):
    """Signals owned by the main thread."""

    available = Signal(object)
    download_progress = Signal(int, int)
    download_finished = Signal(str)
    failed = Signal(str)
    up_to_date = Signal()


class UpdateCheckRunnable(QRunnable):
    """Fetch ``releases/latest`` and emit when a newer Setup.exe exists."""

    def __init__(
        self,
        signals: UpdateCheckSignals,
        skipped_version: str = "",
        *,
        notify_when_current: bool = False,
    ) -> None:
        """
        Initialize the check worker.

        Args:
            signals: Main-thread signals object.
            skipped_version: Version the user asked not to see again.
            notify_when_current: If True, emit ``up_to_date`` (manual check).
        """
        super().__init__()
        self._signals = signals
        self._skipped = skipped_version
        self._notify_when_current = notify_when_current
        self.setAutoDelete(True)

    @Slot()
    def run(self) -> None:
        """Query GitHub; never raise into the thread pool."""
        feed = load_update_feed()
        if not feed:
            if self._notify_when_current:
                self._signals.failed.emit("Update feed is not configured.")
            return
        release = fetch_latest_release(feed["owner"], feed["repo"])
        if release is None:
            if self._notify_when_current:
                self._signals.failed.emit("Could not reach GitHub Releases.")
            return
        current = get_version()
        if is_update_available(release.version, current, self._skipped):
            self._signals.available.emit(release)
            return
        if self._notify_when_current:
            self._signals.up_to_date.emit()


class UpdateDownloadRunnable(QRunnable):
    """Download a Setup.exe to a temp path."""

    def __init__(
        self,
        release: ReleaseInfo,
        dest: Path,
        signals: UpdateCheckSignals,
    ) -> None:
        """
        Initialize the download worker.

        Args:
            release: Parsed GitHub release.
            dest: Destination .exe path.
            signals: Main-thread signals object.
        """
        super().__init__()
        self._release = release
        self._dest = dest
        self._signals = signals
        self.setAutoDelete(True)

    @Slot()
    def run(self) -> None:
        """Download the Setup asset."""
        try:

            def _progress(done: int, total: int) -> None:
                self._signals.download_progress.emit(done, total)

            download_file(self._release.setup_url, self._dest, progress=_progress)
        except OSError as exc:
            self._signals.failed.emit(str(exc))
            return
        self._signals.download_finished.emit(str(self._dest))
