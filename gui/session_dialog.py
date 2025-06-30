"""
Dialog for configuring and starting drawing sessions.
"""
from typing import List, Optional
from qtpy.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QSpinBox,
    QCheckBox,
    QPushButton,
    QGroupBox,
    QFormLayout,
    QTextEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox
)
from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QFont
from core.session_manager import SessionManager, SessionPreset, DrawingSession
from core.image_manager import ImageManager


class SessionDialog(QDialog):
    """Dialog for configuring drawing sessions."""
    
    session_started = Signal(DrawingSession)  # Emitted when session is started
    
    def __init__(self, session_manager: SessionManager, image_manager: ImageManager, selected_images: List[str], parent=None):
        """
        Initialize the session dialog.
        
        Args:
            session_manager: Session manager instance
            image_manager: Image manager instance
            selected_images: List of selected image IDs
            parent: Parent widget
        """
        super().__init__(parent)
        self.session_manager = session_manager
        self.image_manager = image_manager
        self.selected_images = selected_images
        
        self.setWindowTitle("Start Drawing Session")
        self.setModal(True)
        self.setFixedSize(500, 600)
        
        self._setup_ui()
        self._apply_theme()
        self._load_presets()
        self._update_image_list()
    
    def _setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Session preset selection
        preset_group = QGroupBox("Session Preset")
        preset_layout = QFormLayout(preset_group)
        
        self.preset_combo = QComboBox()
        self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
        preset_layout.addRow("Preset:", self.preset_combo)
        
        self.preset_description = QTextEdit()
        self.preset_description.setMaximumHeight(80)
        self.preset_description.setReadOnly(True)
        preset_layout.addRow("Description:", self.preset_description)
        
        layout.addWidget(preset_group)
        
        # Session settings
        settings_group = QGroupBox("Session Settings")
        settings_layout = QFormLayout(settings_group)
        
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(10, 3600)  # 10 seconds to 1 hour
        self.duration_spin.setSuffix(" seconds")
        self.duration_spin.setValue(120)
        settings_layout.addRow("Duration:", self.duration_spin)
        
        self.image_count_spin = QSpinBox()
        self.image_count_spin.setRange(1, 50)
        self.image_count_spin.setValue(5)
        settings_layout.addRow("Images per session:", self.image_count_spin)
        
        self.auto_advance_check = QCheckBox("Auto-advance to next image")
        self.auto_advance_check.setChecked(True)
        settings_layout.addRow("", self.auto_advance_check)
        
        self.loop_session_check = QCheckBox("Loop session")
        self.loop_session_check.setChecked(False)
        settings_layout.addRow("", self.loop_session_check)
        
        layout.addWidget(settings_group)
        
        # Selected images
        images_group = QGroupBox(f"Selected Images ({len(self.selected_images)})")
        images_layout = QVBoxLayout(images_group)
        
        self.image_list = QListWidget()
        self.image_list.setMaximumHeight(150)
        images_layout.addWidget(self.image_list)
        
        layout.addWidget(images_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start Session")
        self.start_button.clicked.connect(self._start_session)
        self.start_button.setDefault(True)
        button_layout.addWidget(self.start_button)
        
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
    
    def _apply_theme(self):
        """Apply theme-aware styles."""
        from core.settings import settings
        
        if settings.get("ui.theme") == "dark":
            # Dark theme
            self.setStyleSheet("""
                QDialog {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QGroupBox {
                    font-weight: bold;
                    border: 1px solid #4d4d4d;
                    border-radius: 4px;
                    margin-top: 10px;
                    padding-top: 10px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                }
                QComboBox, QSpinBox, QTextEdit, QListWidget {
                    background-color: #3c3f41;
                    color: #ffffff;
                    border: 1px solid #4d4d4d;
                    border-radius: 4px;
                    padding: 4px;
                }
                QComboBox:focus, QSpinBox:focus, QTextEdit:focus, QListWidget:focus {
                    border: 1px solid #5d5d5d;
                }
                QPushButton {
                    background-color: #3c3f41;
                    color: #ffffff;
                    border: 1px solid #4d4d4d;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #4b6eaf;
                }
                QPushButton:pressed {
                    background-color: #3d5a8c;
                }
                QCheckBox {
                    color: #ffffff;
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                }
                QCheckBox::indicator:unchecked {
                    background-color: #3c3f41;
                    border: 1px solid #4d4d4d;
                    border-radius: 2px;
                }
                QCheckBox::indicator:checked {
                    background-color: #4b6eaf;
                    border: 1px solid #4d4d4d;
                    border-radius: 2px;
                }
            """)
        else:
            # Light theme
            self.setStyleSheet("""
                QDialog {
                    background-color: #ffffff;
                    color: #000000;
                }
                QGroupBox {
                    font-weight: bold;
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                    margin-top: 10px;
                    padding-top: 10px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                }
                QComboBox, QSpinBox, QTextEdit, QListWidget {
                    background-color: #ffffff;
                    color: #000000;
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                    padding: 4px;
                }
                QComboBox:focus, QSpinBox:focus, QTextEdit:focus, QListWidget:focus {
                    border: 1px solid #0078d7;
                }
                QPushButton {
                    background-color: #f0f0f0;
                    color: #000000;
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #e5e5e5;
                }
                QPushButton:pressed {
                    background-color: #d0d0d0;
                }
                QCheckBox {
                    color: #000000;
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                }
                QCheckBox::indicator:unchecked {
                    background-color: #ffffff;
                    border: 1px solid #cccccc;
                    border-radius: 2px;
                }
                QCheckBox::indicator:checked {
                    background-color: #0078d7;
                    border: 1px solid #cccccc;
                    border-radius: 2px;
                }
            """)
    
    def _load_presets(self):
        """Load available presets into the combo box."""
        presets = self.session_manager.get_presets()
        
        self.preset_combo.clear()
        for preset_name in presets.keys():
            self.preset_combo.addItem(preset_name)
        
        # Select first preset if available
        if self.preset_combo.count() > 0:
            self.preset_combo.setCurrentIndex(0)
            self._on_preset_changed(self.preset_combo.currentText())
    
    def _on_preset_changed(self, preset_name: str):
        """Handle preset selection change."""
        if not preset_name:
            return
        
        presets = self.session_manager.get_presets()
        preset = presets.get(preset_name)
        
        if preset:
            # Update description
            self.preset_description.setText(preset.description)
            
            # Update settings
            self.duration_spin.setValue(preset.duration_seconds)
            self.image_count_spin.setValue(preset.image_count)
            self.auto_advance_check.setChecked(preset.auto_advance)
            self.loop_session_check.setChecked(preset.loop_session)
    
    def _update_image_list(self):
        """Update the list of selected images."""
        self.image_list.clear()
        
        for image_id in self.selected_images:
            metadata = self.image_manager.get_image_metadata(image_id)
            if metadata:
                display_name = metadata.original_filename
                if metadata.tags:
                    display_name += f" ({', '.join(metadata.tags)})"
                
                item = QListWidgetItem(display_name)
                item.setData(Qt.UserRole, image_id)
                self.image_list.addItem(item)
    
    def _start_session(self):
        """Start the drawing session."""
        if not self.selected_images:
            QMessageBox.warning(self, "No Images", "Please select at least one image for the session.")
            return
        
        # Get current preset or create custom one
        preset_name = self.preset_combo.currentText()
        presets = self.session_manager.get_presets()
        
        if preset_name in presets:
            # Use existing preset
            preset = presets[preset_name]
        else:
            # Create custom preset
            preset = SessionPreset(
                name="Custom Session",
                description="Custom drawing session",
                duration_seconds=self.duration_spin.value(),
                image_count=self.image_count_spin.value(),
                auto_advance=self.auto_advance_check.isChecked(),
                loop_session=self.loop_session_check.isChecked()
            )
        
        # Limit images to selected count
        session_images = self.selected_images[:self.image_count_spin.value()]
        
        # Create session
        session = self.session_manager.create_session(preset, session_images)
        
        # Emit signal and close dialog
        self.session_started.emit(session)
        self.accept()
    
    def get_session_config(self) -> dict:
        """
        Get the current session configuration.
        
        Returns:
            Dictionary with session configuration
        """
        return {
            'preset_name': self.preset_combo.currentText(),
            'duration': self.duration_spin.value(),
            'image_count': self.image_count_spin.value(),
            'auto_advance': self.auto_advance_check.isChecked(),
            'loop_session': self.loop_session_check.isChecked(),
            'selected_images': self.selected_images.copy()
        } 