"""
Timer widget for drawing sessions with countdown display and controls.
"""
from typing import Optional
from qtpy.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QFrame
)
from qtpy.QtCore import Qt, QTimer, Signal, QTime
from qtpy.QtGui import QFont, QPalette, QColor


class SessionTimer(QWidget):
    """Timer widget for drawing sessions."""
    
    timer_finished = Signal()  # Emitted when timer reaches zero
    timer_updated = Signal(int)  # Emits remaining seconds
    
    def __init__(self, parent=None):
        """
        Initialize the session timer.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Timer state
        self.total_seconds = 0
        self.remaining_seconds = 0
        self.is_running = False
        self.is_paused = False
        
        # Create timer for updates (tick every second)
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_timer)
        self.update_timer.setInterval(1000)  # Update every 1s for second-by-second countdown
        
        self._setup_ui()
        self._apply_theme()
    
    def _setup_ui(self):
        """Set up the timer UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # Timer display
        self.time_label = QLabel("00:00")
        self.time_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(24)
        font.setBold(True)
        self.time_label.setFont(font)
        layout.addWidget(self.time_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        layout.addWidget(self.progress_bar)
        
        # Control buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start_timer)
        self.start_button.setFixedWidth(60)
        button_layout.addWidget(self.start_button)
        
        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(self.pause_timer)
        self.pause_button.setFixedWidth(60)
        self.pause_button.setEnabled(False)
        button_layout.addWidget(self.pause_button)
        
        self.reset_button = QPushButton("Reset")
        self.reset_button.clicked.connect(self.reset_timer)
        self.reset_button.setFixedWidth(60)
        button_layout.addWidget(self.reset_button)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(10)
        self.status_label.setFont(font)
        layout.addWidget(self.status_label)
    
    def _apply_theme(self):
        """Apply theme-aware styles."""
        from core.settings import settings
        
        if settings.get("ui.theme") == "dark":
            # Dark theme
            self.setStyleSheet("""
                QLabel {
                    color: #ffffff;
                }
                QPushButton {
                    background-color: #3c3f41;
                    color: #ffffff;
                    border: 1px solid #4d4d4d;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #4b6eaf;
                }
                QPushButton:pressed {
                    background-color: #3d5a8c;
                }
                QPushButton:disabled {
                    background-color: #2b2b2b;
                    color: #666666;
                    border: 1px solid #3c3c3c;
                }
                QProgressBar {
                    background-color: #2b2b2b;
                    border: 1px solid #3c3c3c;
                    border-radius: 4px;
                }
                QProgressBar::chunk {
                    background-color: #4b6eaf;
                    border-radius: 3px;
                }
            """)
        else:
            # Light theme
            self.setStyleSheet("""
                QLabel {
                    color: #000000;
                }
                QPushButton {
                    background-color: #f0f0f0;
                    color: #000000;
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #e5e5e5;
                }
                QPushButton:pressed {
                    background-color: #d0d0d0;
                }
                QPushButton:disabled {
                    background-color: #f5f5f5;
                    color: #999999;
                    border: 1px solid #e0e0e0;
                }
                QProgressBar {
                    background-color: #f0f0f0;
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                }
                QProgressBar::chunk {
                    background-color: #4b6eaf;
                    border-radius: 3px;
                }
            """)
    
    def set_duration(self, seconds: int):
        """
        Set the timer duration.
        
        Args:
            seconds: Duration in seconds
        """
        self.total_seconds = max(0, seconds)
        self.remaining_seconds = self.total_seconds
        self._update_display()
        self._update_progress()
    
    def start_timer(self):
        """Start the timer."""
        if self.total_seconds <= 0:
            return
        
        if not self.is_running:
            self.is_running = True
            self.is_paused = False
            self.update_timer.start()
            self.start_button.setText("Stop")
            self.pause_button.setEnabled(True)
            self.status_label.setText("Running")
        else:
            self.stop_timer()
    
    def pause_timer(self):
        """Pause or resume the timer."""
        if not self.is_running:
            return
        
        if self.is_paused:
            # Resume
            self.is_paused = False
            self.update_timer.start()
            self.pause_button.setText("Pause")
            self.status_label.setText("Running")
        else:
            # Pause
            self.is_paused = True
            self.update_timer.stop()
            self.pause_button.setText("Resume")
            self.status_label.setText("Paused")
    
    def stop_timer(self):
        """Stop the timer."""
        self.is_running = False
        self.is_paused = False
        self.update_timer.stop()
        self.start_button.setText("Start")
        self.pause_button.setText("Pause")
        self.pause_button.setEnabled(False)
        self.status_label.setText("Stopped")
    
    def reset_timer(self):
        """Reset the timer to the original duration."""
        self.stop_timer()
        self.remaining_seconds = self.total_seconds
        self._update_display()
        self._update_progress()
        self.status_label.setText("Ready")
    
    def _update_timer(self):
        """Update the timer countdown."""
        if not self.is_running or self.is_paused:
            return
        
        self.remaining_seconds -= 1  # Decrease by one second per tick

        if self.remaining_seconds <= 0:
            self.remaining_seconds = 0
            self._update_display()
            self._update_progress()
            # Emit 0 before stopping so listeners can play the final tick.
            self.timer_updated.emit(0)
            self.stop_timer()
            self.status_label.setText("Time's up!")
            self.timer_finished.emit()
            return

        self._update_display()
        self._update_progress()
        self.timer_updated.emit(int(self.remaining_seconds))
    
    def _update_display(self):
        """Update the time display."""
        minutes = int(self.remaining_seconds) // 60
        seconds = int(self.remaining_seconds) % 60
        self.time_label.setText(f"{minutes:02d}:{seconds:02d}")
        
        # Change color when time is running low
        if self.remaining_seconds <= 10 and self.is_running:
            self.time_label.setStyleSheet("color: #ff4444; font-weight: bold;")
        else:
            self.time_label.setStyleSheet("")
    
    def _update_progress(self):
        """Update the progress bar."""
        if self.total_seconds > 0:
            progress = int((self.remaining_seconds / self.total_seconds) * 100)
            self.progress_bar.setValue(progress)
        else:
            self.progress_bar.setValue(100)
    
    def get_remaining_time(self) -> int:
        """
        Get the remaining time in seconds.
        
        Returns:
            Remaining time in seconds
        """
        return int(self.remaining_seconds)
    
    def is_timer_running(self) -> bool:
        """
        Check if the timer is currently running.
        
        Returns:
            True if timer is running, False otherwise
        """
        return self.is_running and not self.is_paused
    
    def is_timer_paused(self) -> bool:
        """
        Check if the timer is paused.
        
        Returns:
            True if timer is paused, False otherwise
        """
        return self.is_paused 