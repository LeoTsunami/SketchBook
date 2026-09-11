"""
Main-window helpers for GitHub update checks.

Keeps download / installer launch out of ``main_window.py``.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from qtpy.QtCore import QThreadPool
from qtpy.QtWidgets import QApplication

from core.settings import settings
from core.update_check import ReleaseInfo
from gui.update_dialog import (
    UpdateAvailableDialog,
    UpdateDownloadDialog,
    show_up_to_date,
    show_update_error,
)
from gui.update_worker import (
    UpdateCheckRunnable,
    UpdateCheckSignals,
    UpdateDownloadRunnable,
)

if TYPE_CHECKING:
    from gui.main_window import MainWindow


class UpdateCoordinator:
    """Owns update-check signals for the lifetime of the main window."""

    def __init__(self, window: "MainWindow") -> None:
        """
        Bind to a main window.

        Args:
            window: Main application window.
        """
        self._window = window
        self._signals = UpdateCheckSignals()
        self._signals.available.connect(self._on_available)
        self._signals.up_to_date.connect(self._on_up_to_date)
        self._signals.failed.connect(self._on_failed)
        self._signals.download_progress.connect(self._on_progress)
        self._signals.download_finished.connect(self._on_downloaded)
        self._download_dialog: UpdateDownloadDialog | None = None
        self._notify_errors = False

    def check(self, *, manual: bool = False) -> None:
        """
        Start a background GitHub release check.

        Args:
            manual: If True, tell the user when they are up to date or on error.
        """
        self._notify_errors = manual
        skipped = str(settings.get("updates.skipped_version", "") or "")
        worker = UpdateCheckRunnable(
            self._signals,
            skipped_version=skipped,
            notify_when_current=manual,
        )
        QThreadPool.globalInstance().start(worker)

    def _on_available(self, release: object) -> None:
        """Prompt the user when a newer release exists."""
        if not isinstance(release, ReleaseInfo):
            return
        dialog = UpdateAvailableDialog(release, self._window)
        dialog.exec()
        choice = dialog.choice()
        if choice == UpdateAvailableDialog.SKIP:
            settings.set("updates.skipped_version", release.version)
            settings.save()
            return
        if choice != UpdateAvailableDialog.INSTALL:
            return
        dest = Path(tempfile.gettempdir()) / release.setup_name
        self._download_dialog = UpdateDownloadDialog(self._window)
        self._download_dialog.show()
        worker = UpdateDownloadRunnable(release, dest, self._signals)
        QThreadPool.globalInstance().start(worker)

    def _on_progress(self, downloaded: int, total: int) -> None:
        """Forward download bytes to the progress dialog."""
        if self._download_dialog is not None:
            self._download_dialog.set_progress(downloaded, total)

    def _on_downloaded(self, setup_path: str) -> None:
        """Launch the silent Inno Setup upgrade and quit."""
        if self._download_dialog is not None:
            self._download_dialog.close()
            self._download_dialog = None
        path = Path(setup_path)
        if not path.is_file():
            show_update_error("The installer download is missing.", self._window)
            return
        try:
            self._window.image_manager.db.flush_pending_save()
        except Exception:
            pass
        try:
            subprocess.Popen(
                [str(path), "/VERYSILENT", "/NORESTART"],
                close_fds=True,
            )
        except OSError as exc:
            show_update_error(str(exc), self._window)
            return
        QApplication.instance().quit()

    def _on_up_to_date(self) -> None:
        """Manual check: already on latest."""
        show_up_to_date(self._window)

    def _on_failed(self, message: str) -> None:
        """Show errors for manual checks and failed downloads."""
        download_was_open = self._download_dialog is not None
        if self._download_dialog is not None:
            self._download_dialog.close()
            self._download_dialog = None
        if self._notify_errors or download_was_open:
            show_update_error(message, self._window)
