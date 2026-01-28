"""
Settings dialog for configuring application preferences.
"""
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
)
from qtpy.QtCore import Qt
from core.settings import settings


class SettingsDialog(QDialog):
    """Dialog for configuring application settings."""
    
    def __init__(self, parent=None):
        """
        Initialize the settings dialog.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        # Store current values
        self.theme_value = settings.get("ui.theme", "dark")
        self.max_height_value = settings.get("images.max_height", 1080)
        self.compression_quality_value = settings.get("images.compression.quality", 75)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Theme section
        theme_group = QGroupBox("Theme")
        theme_layout = QFormLayout()
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        self.theme_combo.setCurrentText(self.theme_value.capitalize())
        theme_layout.addRow("Theme:", self.theme_combo)
        
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)
        
        # Image compression section
        compression_group = QGroupBox("Image Import Compression")
        compression_layout = QFormLayout()
        
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
            Theme name ('light' or 'dark')
        """
        return self.theme_combo.currentText().lower()
    
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
    
    def accept(self):
        """Save settings and close dialog."""
        # Save settings
        settings.set("ui.theme", self.get_theme())
        settings.set("images.max_height", self.get_max_height())
        settings.set("images.compression.quality", self.get_compression_quality())
        settings.save()
        
        super().accept()
