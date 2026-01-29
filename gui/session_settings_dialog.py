"""
Dialog for configuring session settings.
"""
from typing import Dict, List
from qtpy.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QSpinBox,
    QPushButton,
    QMessageBox
)
from qtpy.QtCore import Qt
from core.image_manager import ImageManager


class SessionSettingsDialog(QDialog):
    """Dialog for configuring session settings."""
    
    def __init__(self, image_manager: ImageManager, image_count: int, parent=None):
        """
        Initialize the session settings dialog.
        
        Args:
            image_manager: Image manager instance
            image_count: Number of images available for the session
            parent: Parent widget
        """
        super().__init__(parent)
        self.image_manager = image_manager
        self.image_count = image_count
        self.session_started = False
        
        self.setWindowTitle("Session Settings")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        self._setup_ui()
        self._apply_theme()
    
    def _setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Label for number of images
        self.images_count_label = QLabel(f"Images: {self.image_count}")
        self.images_count_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self.images_count_label)
        
        # Session type combobox (horizontal layout)
        session_type_layout = QHBoxLayout()
        session_type_label = QLabel("Session Type:")
        session_type_label.setStyleSheet("font-size: 12px;")
        session_type_label.setMinimumWidth(120)
        session_type_layout.addWidget(session_type_label)
        
        self.session_type_combo = QComboBox()
        self.session_type_combo.addItems(["Course", "Constant interval"])
        self.session_type_combo.currentTextChanged.connect(self._on_session_type_changed)
        session_type_layout.addWidget(self.session_type_combo)
        layout.addLayout(session_type_layout)
        
        # Course duration (shown when "Course" is selected) - horizontal layout
        course_duration_layout = QHBoxLayout()
        self.course_duration_label = QLabel("Course Duration:")
        self.course_duration_label.setStyleSheet("font-size: 12px;")
        self.course_duration_label.setMinimumWidth(120)
        course_duration_layout.addWidget(self.course_duration_label)
        
        self.course_duration_spin = QSpinBox()
        self.course_duration_spin.setRange(10, 60)  # Course presets: 10 to 60 minutes (step 10)
        self.course_duration_spin.setSingleStep(10)
        self.course_duration_spin.setSuffix(" minutes")
        self.course_duration_spin.setValue(30)
        course_duration_layout.addWidget(self.course_duration_spin)
        layout.addLayout(course_duration_layout)
        
        # Constant interval duration (shown when "Constant interval" is selected) - horizontal layout
        interval_duration_layout = QHBoxLayout()
        self.interval_duration_label = QLabel("Image Duration:")
        self.interval_duration_label.setStyleSheet("font-size: 12px;")
        self.interval_duration_label.setMinimumWidth(120)
        self.interval_duration_label.setVisible(False)
        interval_duration_layout.addWidget(self.interval_duration_label)
        
        self.interval_duration_combo = QComboBox()
        self.interval_duration_combo.addItems(["30 seconds", "1 minute", "3 minutes", "5 minutes", "10 minutes", "20 minutes"])
        self.interval_duration_combo.setVisible(False)
        interval_duration_layout.addWidget(self.interval_duration_combo)
        layout.addLayout(interval_duration_layout)
        
        # Window Mode combobox (horizontal layout)
        window_mode_layout = QHBoxLayout()
        window_mode_label = QLabel("Window Mode:")
        window_mode_label.setStyleSheet("font-size: 12px;")
        window_mode_label.setMinimumWidth(120)
        window_mode_layout.addWidget(window_mode_label)
        
        self.window_mode_combo = QComboBox()
        self.window_mode_combo.addItems(["FullScreen", "Window always on top"])
        window_mode_layout.addWidget(self.window_mode_combo)
        layout.addLayout(window_mode_layout)
        
        # Add stretch
        layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # Cancel button
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        # Start Session button
        self.start_session_btn = QPushButton("Start Session")
        self.start_session_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.start_session_btn.clicked.connect(self._on_start_session_clicked)
        self.start_session_btn.setDefault(True)
        button_layout.addWidget(self.start_session_btn)
        
        layout.addLayout(button_layout)
        
        # Initialize session type UI (default to "Course")
        self._on_session_type_changed("Course")
    
    def _on_session_type_changed(self, session_type: str):
        """
        Handle session type change.
        
        Args:
            session_type: "Course" or "Constant interval"
        """
        if session_type == "Course":
            # Show course duration controls
            self.course_duration_label.setVisible(True)
            self.course_duration_spin.setVisible(True)
            # Hide interval duration controls
            self.interval_duration_label.setVisible(False)
            self.interval_duration_combo.setVisible(False)
        else:  # Constant interval
            # Hide course duration controls
            self.course_duration_label.setVisible(False)
            self.course_duration_spin.setVisible(False)
            # Show interval duration controls
            self.interval_duration_label.setVisible(True)
            self.interval_duration_combo.setVisible(True)
    
    def _on_start_session_clicked(self):
        """Handle Start Session button click."""
        if self.image_count == 0:
            QMessageBox.warning(
                self,
                "No Images Available",
                "No images match the current tag filters. Please adjust your filters."
            )
            return
        
        self.session_started = True
        self.accept()
    
    def get_session_settings(self) -> Dict:
        """
        Get the current session settings.
        
        Returns:
            Dictionary with session settings
        """
        settings = {
            "session_type": self.session_type_combo.currentText(),
            "window_mode": self.window_mode_combo.currentText(),
        }
        
        if settings["session_type"] == "Course":
            settings["course_duration_minutes"] = self.course_duration_spin.value()
        else:  # Constant interval
            settings["interval_duration"] = self.interval_duration_combo.currentText()
        
        return settings
    
    def _apply_theme(self):
        """Apply theme-aware styles."""
        from core.settings import settings
        
        # The dialog will inherit the global stylesheet from the application
        # This method is kept for potential future custom styling
        pass
