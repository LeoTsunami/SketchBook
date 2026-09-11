"""
Dialogs for offering and downloading a SketchBook update.
"""

from __future__ import annotations

from qtpy.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from core.update_check import ReleaseInfo
from core.version import get_version


class UpdateAvailableDialog(QDialog):
    """Ask the user whether to install a newer GitHub Release."""

    INSTALL = 1
    LATER = 2
    SKIP = 3

    def __init__(self, release: ReleaseInfo, parent=None) -> None:
        """
        Initialize the prompt.

        Args:
            release: Newer release from GitHub.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("SketchBook update")
        self._choice = self.LATER
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        current = get_version()
        summary = QLabel(
            f"SketchBook {release.version} is available "
            f"(you have {current}).\n\n"
            "The installer will replace the application files and leave "
            "your image library unchanged."
        )
        summary.setWordWrap(True)
        layout.addWidget(summary)
        if release.notes:
            notes = QLabel(release.notes[:800])
            notes.setWordWrap(True)
            notes.setStyleSheet("color: #888; font-size: 11px;")
            layout.addWidget(notes)
        buttons = QHBoxLayout()
        install_btn = QPushButton("Download and install")
        later_btn = QPushButton("Later")
        skip_btn = QPushButton("Skip this version")
        install_btn.clicked.connect(lambda: self._finish(self.INSTALL))
        later_btn.clicked.connect(lambda: self._finish(self.LATER))
        skip_btn.clicked.connect(lambda: self._finish(self.SKIP))
        buttons.addWidget(install_btn)
        buttons.addWidget(later_btn)
        buttons.addWidget(skip_btn)
        layout.addLayout(buttons)

    def _finish(self, choice: int) -> None:
        """Store the choice and close."""
        self._choice = choice
        self.accept()

    def choice(self) -> int:
        """
        Return the user's decision.

        Returns:
            int: ``INSTALL``, ``LATER``, or ``SKIP``.
        """
        return self._choice


class UpdateDownloadDialog(QDialog):
    """Modal progress dialog while the Setup.exe downloads."""

    def __init__(self, parent=None) -> None:
        """
        Initialize the download progress dialog.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("Downloading update")
        self.setModal(True)
        layout = QVBoxLayout(self)
        self._label = QLabel("Downloading SketchBook Setup…")
        layout.addWidget(self._label)
        self._bar = QProgressBar()
        self._bar.setMinimum(0)
        self._bar.setMaximum(0)
        layout.addWidget(self._bar)

    def set_progress(self, downloaded: int, total: int) -> None:
        """
        Update the progress bar.

        Args:
            downloaded: Bytes received.
            total: Total bytes, or 0 if unknown.
        """
        if total <= 0:
            self._bar.setMaximum(0)
            return
        self._bar.setMaximum(100)
        self._bar.setValue(min(100, int(downloaded * 100 / total)))
        mb = downloaded / (1024 * 1024)
        total_mb = total / (1024 * 1024)
        self._label.setText(
            f"Downloading SketchBook Setup… {mb:.1f} / {total_mb:.1f} MiB"
        )


def show_up_to_date(parent=None) -> None:
    """Show a short message when the installed version is current."""
    QMessageBox.information(
        parent,
        "SketchBook update",
        f"You are on the latest version ({get_version()}).",
    )


def show_update_error(message: str, parent=None) -> None:
    """
    Show a check/download error.

    Args:
        message: Error text.
        parent: Parent widget.
    """
    QMessageBox.warning(parent, "SketchBook update", message)
