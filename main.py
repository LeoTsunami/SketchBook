#!/usr/bin/env python3
"""
SketchBook - A desktop application for timed life drawing sessions.
"""
import sys
import os
import threading
from pathlib import Path
from qtpy.QtWidgets import QApplication
from qtpy.QtGui import QFontDatabase, QFont
from gui.main_window import MainWindow
from core.settings import settings
from core.user_data import user_data
from core.config_backup import run_config_backup


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

def load_fonts():
    """Load custom fonts for the application."""
    fonts_loaded = {}
    
    # Load Kalam Regular font
    kalam_dir = Path(__file__).parent / "gui" / "ressources" / "fonts" / "Kalam"
    kalam_path = kalam_dir / "Kalam-Regular.ttf"
    if kalam_path.exists():
        font_id = QFontDatabase.addApplicationFont(str(kalam_path))
        if font_id != -1:
            font_families = QFontDatabase.applicationFontFamilies(font_id)
            if font_families:
                fonts_loaded["Kalam"] = font_families[0]
                print(f"Loaded font: {font_families[0]}")
    
    # Load Caveat Regular font
    caveat_dir = Path(__file__).parent / "gui" / "ressources" / "fonts" / "Caveat"
    caveat_path = caveat_dir / "static" / "Caveat-Regular.ttf"
    if caveat_path.exists():
        font_id = QFontDatabase.addApplicationFont(str(caveat_path))
        if font_id != -1:
            font_families = QFontDatabase.applicationFontFamilies(font_id)
            if font_families:
                fonts_loaded["Caveat"] = font_families[0]
                print(f"Loaded font: {font_families[0]}")
    
    return fonts_loaded

def main():
    """Main entry point of the application."""
    # Create application instance
    app = QApplication(sys.argv)
    
    # Load custom fonts
    fonts_loaded = load_fonts()
    
    # Use a clean modern UI font for the whole application.
    # Reason: The new visual direction requires simpler typography.
    app.setFont(QFont("Segoe UI", 10))
    
    # Charger le QSS global depuis gui/styles/ selon le thème
    theme = settings.get("ui.theme", "dark")
    if theme not in ("dark", "light", "neon_night", "sunset_glass", "midnight_ocean"):
        theme = "dark"
    qss = load_stylesheet(f"gui/styles/style_{theme}.qss")
    app.setStyleSheet(qss)
    
    # Ensure directories exist
    setup_directories()

    # Backup config JSONs to config/backup/ in a background thread (date-time in name, keep 5)
    backup_thread = threading.Thread(target=run_config_backup, daemon=True)
    backup_thread.start()

    # Initialize and show main window
    window = MainWindow()
    window.show()
    
    # Start event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 
