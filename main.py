#!/usr/bin/env python3
"""
SketchBook - A desktop application for timed life drawing sessions.
"""

import sys
import threading
from pathlib import Path
from qtpy.QtWidgets import QApplication
from qtpy.QtGui import QFontDatabase, QFont
from qtpy.QtCore import QTimer
from gui.main_window import MainWindow
from core.settings import settings
from core.user_data import user_data
from core.config_backup import run_config_backup

# Force stdout to be unbuffered for immediate print output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Themes whose QSS sets font-family to Kalam (see gui/styles/style_*.qss).
_KALAM_THEMES = frozenset({"neon_night", "sunset_glass", "midnight_ocean", "light"})


def setup_directories():
    """Create necessary application directories if they don't exist."""
    user_data.ensure_directories()


def load_stylesheet(path: str) -> str:
    """Read a QSS file as UTF-8 text."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_theme_fonts(theme: str) -> None:
    """
    Register embedded fonts only when the active stylesheet references them.

    Kalam is bundled for several themes; dark uses Segoe UI (system). Caveat was
    previously loaded but is not referenced in any QSS, so it is not registered.

    Args:
        theme: Active UI theme key (e.g. dark, light).
    """
    if theme not in _KALAM_THEMES:
        return

    kalam_path = (
        Path(__file__).parent
        / "gui"
        / "ressources"
        / "fonts"
        / "Kalam"
        / "Kalam-Regular.ttf"
    )
    if kalam_path.exists():
        font_id = QFontDatabase.addApplicationFont(str(kalam_path))
        if font_id != -1:
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                print(f"Loaded font: {families[0]}")


def main():
    """Main entry point of the application."""
    app = QApplication(sys.argv)


    theme = settings.get("ui.theme", "dark")
    if theme not in ("dark", "light", "neon_night", "sunset_glass", "midnight_ocean"):
        theme = "dark"

    load_theme_fonts(theme)

    # Reason: The visual direction uses simple system typography for the default dark theme.
    app.setFont(QFont("Segoe UI", 10))

    qss = load_stylesheet(f"gui/styles/style_{theme}.qss")
    app.setStyleSheet(qss)

    setup_directories()

    backup_thread = threading.Thread(target=run_config_backup, daemon=True)
    backup_thread.start()

    window = MainWindow()
    window.show()

    # Reason: Defer DB backfill until after the first paint so large libraries do not block startup.
    QTimer.singleShot(0, window.image_manager.run_import_date_backfill)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

