"""
Main window of the SketchBook application.
"""
from pathlib import Path
from qtpy.QtWidgets import (
    QMainWindow,
    QMenuBar,
    QMenu,
    QFileDialog,
    QMessageBox,
    QStatusBar
)
from qtpy.QtCore import Qt
from qtpy.QtGui import QAction, QActionGroup
from core.settings import settings

class MainWindow(QMainWindow):
    """Main window of the application."""
    
    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        
        # Window setup
        self.setWindowTitle("SketchBook")
        self.resize(1280, 800)
        
        # Initialize UI
        self._setup_ui()
        self._setup_menu()
        self._setup_statusbar()
        
        # Apply theme
        self._apply_theme()
    
    def _setup_ui(self):
        """Set up the main UI components."""
        # Will be implemented in next phase
        pass
    
    def _setup_menu(self):
        """Set up the menu bar."""
        # File menu
        file_menu = self.menuBar().addMenu("&File")
        
        # - Import images
        import_action = QAction("&Import Images...", self)
        import_action.setShortcut("Ctrl+I")
        import_action.triggered.connect(self._on_import_images)
        file_menu.addAction(import_action)
        
        file_menu.addSeparator()
        
        # - Exit
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = self.menuBar().addMenu("&View")
        
        # - Theme submenu
        theme_menu = QMenu("&Theme", self)
        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)
        
        light_theme_action = QAction("&Light", self)
        light_theme_action.setCheckable(True)
        light_theme_action.triggered.connect(lambda: self._set_theme("light"))
        theme_group.addAction(light_theme_action)
        
        dark_theme_action = QAction("&Dark", self)
        dark_theme_action.setCheckable(True)
        dark_theme_action.triggered.connect(lambda: self._set_theme("dark"))
        theme_group.addAction(dark_theme_action)
        
        # Set initial check state
        if settings.get("ui.theme") == "dark":
            dark_theme_action.setChecked(True)
        else:
            light_theme_action.setChecked(True)
        
        theme_menu.addAction(light_theme_action)
        theme_menu.addAction(dark_theme_action)
        view_menu.addMenu(theme_menu)
        
        # Help menu
        help_menu = self.menuBar().addMenu("&Help")
        
        # - About
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _setup_statusbar(self):
        """Set up the status bar."""
        self.statusBar().showMessage("Ready")
    
    def _on_import_images(self):
        """Handle image import action."""
        # Will be implemented in next phase
        self.statusBar().showMessage("Image import not implemented yet")
    
    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About SketchBook",
            "SketchBook - A desktop application for timed life drawing sessions.\n\n"
            "Version: 0.1.0"
        )
    
    def _set_theme(self, theme: str):
        """
        Set application theme.
        
        Args:
            theme: Theme name ('light' or 'dark')
        """
        settings.set("ui.theme", theme)
        settings.save()
        self._apply_theme()
    
    def _apply_theme(self):
        """Apply the current theme from settings."""
        if settings.get("ui.theme") == "dark":
            # Dark theme palette
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QMenuBar {
                    background-color: #3c3f41;
                    color: #ffffff;
                }
                QMenuBar::item:selected {
                    background-color: #4b6eaf;
                }
                QMenu {
                    background-color: #3c3f41;
                    color: #ffffff;
                }
                QMenu::item:selected {
                    background-color: #4b6eaf;
                }
                QStatusBar {
                    background-color: #3c3f41;
                    color: #ffffff;
                }
            """)
        else:
            # Light theme
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #ffffff;
                    color: #000000;
                }
                QMenuBar {
                    background-color: #f0f0f0;
                    color: #000000;
                }
                QMenuBar::item:selected {
                    background-color: #0078d7;
                    color: #ffffff;
                }
                QMenu {
                    background-color: #ffffff;
                    color: #000000;
                }
                QMenu::item:selected {
                    background-color: #0078d7;
                    color: #ffffff;
                }
                QStatusBar {
                    background-color: #f0f0f0;
                    color: #000000;
                }
            """) 