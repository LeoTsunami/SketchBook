#!/usr/bin/env python3
"""
SketchBook - A desktop application for timed life drawing sessions.
"""
import sys
import os
from pathlib import Path
from qtpy.QtWidgets import QApplication
from gui.main_window import MainWindow
from core.settings import settings
from core.user_data import user_data

# Force stdout to be unbuffered for immediate print output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)


# Ensure all necessary directories exist
def setup_directories():
    """Create necessary application directories if they don't exist."""
    # Use user data manager to ensure directories exist
    user_data.ensure_directories()

def load_stylesheet(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def main():
    """Main entry point of the application."""
    # Create application instance
    app = QApplication(sys.argv)
    
    # Charger le QSS global depuis gui/styles/ selon le thème
    theme = settings.get("ui.theme", "dark")
    if theme not in ("dark", "light"):
        theme = "dark"
    qss = load_stylesheet(f"gui/styles/style_{theme}.qss")
    app.setStyleSheet(qss)
    
    # Ensure directories exist
    setup_directories()
    
    # Initialize and show main window
    window = MainWindow()
    window.show()
    
    # Start event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 
