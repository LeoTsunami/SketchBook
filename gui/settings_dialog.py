"""
Settings dialog for configuring application preferences.
"""

from pathlib import Path

from qtpy.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QSpinBox,
    QPushButton,
    QGroupBox,
    QFormLayout,
    QSlider,
    QLineEdit,
    QFileDialog,
    QMessageBox,
)
from qtpy.QtCore import Qt
from core.settings import settings
from core.user_data import user_data, set_user_data_directory


class SettingsDialog(QDialog):
    """Dialog for configuring application settings."""

    THEME_OPTIONS = [
        ("Dark", "dark"),
        ("Light", "light"),
        ("Neon Night", "neon_night"),
        ("Sunset Glass", "sunset_glass"),
        ("Midnight Ocean", "midnight_ocean"),
    ]

    def __init__(self, parent=None):
        """
        Initialize the settings dialog.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(520)
        self.setMinimumHeight(480)

        # Store current values
        self.theme_value = settings.get("ui.theme", "dark")
        self.max_width_value = settings.get("images.max_width", 1920)
        self.max_height_value = settings.get("images.max_height", 1080)
        self.compression_quality_value = settings.get("images.compression.quality", 75)
        self._initial_data_dir = Path(user_data.get_base_dir()).resolve()
        self._chosen_data_dir = self._initial_data_dir
        self.data_dir_changed = False

        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Library / data location (most important for distribution & large libs)
        library_group = QGroupBox("Image library location")
        library_layout = QVBoxLayout()
        library_layout.setSpacing(8)

        library_desc = QLabel(
            "Folder where imported images and library metadata are stored "
            "(images/, config/, sessions/). Changing it does not move existing files."
        )
        library_desc.setWordWrap(True)
        library_desc.setStyleSheet("color: #888; font-size: 11px;")
        library_layout.addWidget(library_desc)

        path_row = QHBoxLayout()
        path_row.setSpacing(8)
        self.data_dir_edit = QLineEdit(str(self._chosen_data_dir))
        self.data_dir_edit.setReadOnly(True)
        self.data_dir_edit.setToolTip(str(self._chosen_data_dir))
        path_row.addWidget(self.data_dir_edit, 1)

        self.browse_data_dir_btn = QPushButton("Browse…")
        self.browse_data_dir_btn.clicked.connect(self._on_browse_data_dir)
        path_row.addWidget(self.browse_data_dir_btn)

        self.open_data_dir_btn = QPushButton("Open folder")
        self.open_data_dir_btn.clicked.connect(self._on_open_data_dir)
        path_row.addWidget(self.open_data_dir_btn)

        library_layout.addLayout(path_row)

        if user_data.is_data_dir_locked_by_env():
            env_hint = QLabel(
                "Locked by environment variable SKETCHBOOK_DATA_DIR. "
                "Unset it to choose a folder from Settings."
            )
            env_hint.setWordWrap(True)
            env_hint.setStyleSheet("color: #c9a227; font-size: 11px;")
            library_layout.addWidget(env_hint)
            self.browse_data_dir_btn.setEnabled(False)

        library_group.setLayout(library_layout)
        layout.addWidget(library_group)

        # Theme section
        theme_group = QGroupBox("Theme")
        theme_layout = QFormLayout()

        self.theme_combo = QComboBox()
        for label, theme_key in self.THEME_OPTIONS:
            self.theme_combo.addItem(label, theme_key)
        current_index = self.theme_combo.findData(self.theme_value)
        if current_index < 0:
            current_index = self.theme_combo.findData("dark")
        self.theme_combo.setCurrentIndex(current_index)
        theme_layout.addRow("Theme:", self.theme_combo)

        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)

        # Image compression section
        compression_group = QGroupBox("Image Import Compression")
        compression_layout = QFormLayout()

        # Max width
        self.max_width_spin = QSpinBox()
        self.max_width_spin.setMinimum(360)  # Minimum 360p
        self.max_width_spin.setMaximum(4320)  # Maximum 4K
        self.max_width_spin.setSingleStep(180)  # Step by 180p (common resolutions)
        self.max_width_spin.setSuffix(" px")
        self.max_width_spin.setValue(self.max_width_value)
        compression_layout.addRow("Maximum Width:", self.max_width_spin)

        # Max height
        self.max_height_spin = QSpinBox()
        self.max_height_spin.setMinimum(360)  # Minimum 360p
        self.max_height_spin.setMaximum(4320)  # Maximum 4K
        self.max_height_spin.setSingleStep(180)  # Step by 180p (common resolutions)
        self.max_height_spin.setSuffix(" px")
        self.max_height_spin.setValue(self.max_height_value)
        compression_layout.addRow("Maximum Height:", self.max_height_spin)

        # Compression quality
        quality_layout = QHBoxLayout()
        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setMinimum(30)
        self.quality_slider.setMaximum(100)
        self.quality_slider.setValue(self.compression_quality_value)
        self.quality_slider.valueChanged.connect(self._update_quality_label)

        self.quality_label = QLabel()
        self._update_quality_label(self.compression_quality_value)

        quality_layout.addWidget(self.quality_slider)
        quality_layout.addWidget(self.quality_label)
        quality_layout.setStretch(0, 1)

        compression_layout.addRow("JPEG Quality:", quality_layout)

        # Quality description
        quality_desc = QLabel()
        quality_desc.setWordWrap(True)
        quality_desc.setStyleSheet("color: #888; font-size: 10px;")
        quality_desc.setText(
            "Lower values reduce file size but may introduce artifacts. "
            "Recommended: 70-80 for a good balance."
        )
        compression_layout.addRow("", quality_desc)

        compression_group.setLayout(compression_layout)
        layout.addWidget(compression_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

    def _on_browse_data_dir(self) -> None:
        """Pick a new base folder for the image library and user data."""
        if user_data.is_data_dir_locked_by_env():
            return
        chosen = QFileDialog.getExistingDirectory(
            self,
            "Choose image library folder",
            str(self._chosen_data_dir),
        )
        if not chosen:
            return
        self._chosen_data_dir = Path(chosen).expanduser().resolve()
        self.data_dir_edit.setText(str(self._chosen_data_dir))
        self.data_dir_edit.setToolTip(str(self._chosen_data_dir))

    def _on_open_data_dir(self) -> None:
        """Reveal the currently displayed data folder in the OS file manager."""
        from qtpy.QtGui import QDesktopServices
        from qtpy.QtCore import QUrl

        path = Path(self.data_dir_edit.text().strip() or str(self._chosen_data_dir))
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            QMessageBox.warning(
                self,
                "Open folder",
                f"Could not open folder:\n{path}\n\n{exc}",
            )
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _update_quality_label(self, value: int):
        """Update quality label with current slider value."""
        # Map quality to description
        if value >= 90:
            desc = "Very High"
        elif value >= 80:
            desc = "High"
        elif value >= 70:
            desc = "Medium-High"
        elif value >= 60:
            desc = "Medium"
        elif value >= 50:
            desc = "Medium-Low"
        elif value >= 40:
            desc = "Low"
        else:
            desc = "Very Low"

        self.quality_label.setText(f"{value} ({desc})")

    def get_theme(self) -> str:
        """
        Get selected theme.

        Returns:
            Theme key
        """
        return self.theme_combo.currentData()

    def get_max_width(self) -> int:
        """
        Get maximum width setting.

        Returns:
            Maximum width in pixels
        """
        return self.max_width_spin.value()

    def get_max_height(self) -> int:
        """
        Get maximum height setting.

        Returns:
            Maximum height in pixels
        """
        return self.max_height_spin.value()

    def get_compression_quality(self) -> int:
        """
        Get compression quality setting.

        Returns:
            JPEG compression quality (30-100)
        """
        return self.quality_slider.value()

    def get_chosen_data_dir(self) -> Path:
        """
        Return the library folder selected in the dialog.

        Returns:
            Absolute path chosen for user data / image library.
        """
        return self._chosen_data_dir

    def accept(self):
        """Save settings and close dialog."""
        new_dir = self._chosen_data_dir.resolve()
        if (
            not user_data.is_data_dir_locked_by_env()
            and new_dir != self._initial_data_dir.resolve()
        ):
            reply = QMessageBox.question(
                self,
                "Change library location?",
                (
                    "SketchBook will use this folder for images and library data:\n\n"
                    f"{new_dir}\n\n"
                    "Existing files are not moved automatically. "
                    "Copy your previous SketchBook folder contents here if you want "
                    "to keep the same library.\n\n"
                    "A restart is required after this change.\n\nContinue?"
                ),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
            if not set_user_data_directory(str(new_dir)):
                QMessageBox.warning(
                    self,
                    "Library location",
                    "Could not set the library folder (permission or path error).",
                )
                return
            self.data_dir_changed = True

        # Save settings
        settings.set("ui.theme", self.get_theme())
        settings.set("images.max_width", self.get_max_width())
        settings.set("images.max_height", self.get_max_height())
        settings.set("images.compression.quality", self.get_compression_quality())
        settings.save()

        super().accept()
