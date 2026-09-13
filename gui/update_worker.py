"""
Background GitHub update check and Setup.exe download.

Qt widgets must not be touched from ``run()``.
"""

from __future__ import annotations

import sys
from pathlib import Path

from qtpy.QtCore import QObject, QRunnable, Signal, Slot

from core.update_check import (
    ReleaseInfo,
    describe_ssl_context,
    describe_update_feed_search,
    download_file,
    fetch_latest_release_with_reason,
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
    debug = Signal(str)


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

    def _log(self, message: str) -> None:
        """
        Emit a developer-log line (queued to the main thread).

        Args:
            message: Diagnostic text.
        """
        self._signals.debug.emit(message)

    @Slot()
    def run(self) -> None:
        """Query GitHub; never raise into the thread pool."""
        current = get_version()
        frozen = bool(getattr(sys, "frozen", False))
        self._log(
            f"Check start current={current} frozen={frozen} "
            f"skipped={self._skipped!r} manual={self._notify_when_current}"
        )
        self._log(f"SSL {describe_ssl_context()}")
        feed = load_update_feed()
        if not feed:
            detail = f"Update feed is not configured. Tried: {describe_update_feed_search()}"
            self._log(detail)
            if self._notify_when_current:
                self._signals.failed.emit(detail)
            return
        owner, repo = feed["owner"], feed["repo"]
        url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
        self._log(f"Feed {owner}/{repo} GET {url}")
        release, reason = fetch_latest_release_with_reason(owner, repo)
        if release is None:
            detail = reason or "Could not reach GitHub Releases."
            self._log(f"Fetch failed: {detail}")
            if self._notify_when_current:
                self._signals.failed.emit(f"Could not reach GitHub Releases. {detail}")
            return
        self._log(
            f"Latest tag={release.tag} version={release.version} "
            f"setup={release.setup_name}"
        )
        if is_update_available(release.version, current, self._skipped):
            self._log(f"Update available: {release.version} > {current}")
            self._signals.available.emit(release)
            return
        self._log(f"No update to install (current={current}, latest={release.version})")
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

            self._signals.debug.emit(
                f"Download {self._release.setup_name} from {self._release.setup_url} "
                f"to {self._dest}"
            )
            download_file(self._release.setup_url, self._dest, progress=_progress)
        except OSError as exc:
            self._signals.debug.emit(f"Download failed: {exc}")
            self._signals.failed.emit(str(exc))
            return
        self._signals.debug.emit(f"Download finished: {self._dest}")
        self._signals.download_finished.emit(str(self._dest))
