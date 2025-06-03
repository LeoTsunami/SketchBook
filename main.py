#!/usr/bin/env python3
"""
SketchBook - A desktop application for timed life drawing sessions.
"""
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow

# Ensure all necessary directories exist
def setup_directories():
    """Create necessary application directories if they don't exist."""
    dirs = ['data/images', 'data/sessions', 'data/config']
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)

def main():
    """Main entry point of the application."""
    # Create application instance
    app = QApplication(sys.argv)
    
    # Ensure directories exist
    setup_directories()
    
    # Initialize and show main window
    window = MainWindow()
    window.show()
    
    # Start event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 