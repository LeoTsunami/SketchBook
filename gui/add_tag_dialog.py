"""
Dialog to add a new user tag: name and optional icon from gui/ressources/icones/tags.
"""
from pathlib import Path
from typing import Callable, List, Optional

from qtpy.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QLabel,
    QPushButton,
    QScrollArea,
    QWidget,
    QGridLayout,
    QDialogButtonBox,
)
from qtpy.QtCore import Qt, QSize
from qtpy.QtGui import QIcon

ICONS_DIR = Path(__file__).parent / "ressources" / "icones" / "tags"
ICON_SIZE = 32


class AddTagDialog(QDialog):
    """Dialog to enter a new tag name and optionally pick an icon."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_icon: Optional[str] = None
        self.setWindowTitle("Add tag")
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Tag name:"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Enter tag name")
        layout.addWidget(self._name_edit)

        layout.addWidget(QLabel("Icon (optional):"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setMinimumHeight(120)
        scroll.setMaximumHeight(200)
        icon_container = QWidget()
        self._icon_layout = QGridLayout(icon_container)
        self._icon_layout.setSpacing(4)
        self._icon_buttons: List[QPushButton] = []
        if ICONS_DIR.exists():
            for idx, path in enumerate(sorted(ICONS_DIR.glob("*.png"))):
                btn = QPushButton()
                btn.setFixedSize(ICON_SIZE + 8, ICON_SIZE + 8)
                btn.setIcon(QIcon(str(path)))
                btn.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
                btn.setCheckable(True)
                btn.setProperty("iconFile", path.name)
                btn.clicked.connect(self._make_icon_click_handler(btn))
                row, col = idx // 6, idx % 6
                self._icon_layout.addWidget(btn, row, col)
                self._icon_buttons.append(btn)
        scroll.setWidget(icon_container)
        layout.addWidget(scroll)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _make_icon_click_handler(self, clicked_btn: QPushButton):
        def handler():
            for b in self._icon_buttons:
                b.setChecked(b is clicked_btn)
            self._selected_icon = clicked_btn.property("iconFile")

        return handler

    def get_tag_name(self) -> str:
        """Return the entered tag name (may be empty)."""
        return self._name_edit.text().strip()

    def get_icon_filename(self) -> Optional[str]:
        """Return the selected icon filename (e.g. Hand.png) or None."""
        return self._selected_icon


class IconPickerDialog(QDialog):
    """Dialog to pick an icon from gui/ressources/icones/tags (e.g. for changing tag icon).
    Optional on_icon_changed(filename) is called when user clicks an icon for live preview.
    """

    def __init__(
        self,
        parent=None,
        current_icon: Optional[str] = None,
        on_icon_changed: Optional[Callable[[Optional[str]], None]] = None,
    ):
        super().__init__(parent)
        self._selected_icon: Optional[str] = current_icon
        self._on_icon_changed = on_icon_changed
        self.setWindowTitle("Choose icon")
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Select an icon:"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setMinimumHeight(120)
        scroll.setMaximumHeight(200)
        icon_container = QWidget()
        self._icon_layout = QGridLayout(icon_container)
        self._icon_layout.setSpacing(4)
        self._icon_buttons: List[QPushButton] = []
        if ICONS_DIR.exists():
            for idx, path in enumerate(sorted(ICONS_DIR.glob("*.png"))):
                btn = QPushButton()
                btn.setFixedSize(ICON_SIZE + 8, ICON_SIZE + 8)
                btn.setIcon(QIcon(str(path)))
                btn.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
                btn.setCheckable(True)
                btn.setProperty("iconFile", path.name)
                if path.name == current_icon:
                    btn.setChecked(True)
                btn.clicked.connect(self._make_icon_click_handler(btn))
                row, col = idx // 6, idx % 6
                self._icon_layout.addWidget(btn, row, col)
                self._icon_buttons.append(btn)
        scroll.setWidget(icon_container)
        layout.addWidget(scroll)

        self._no_icon_btn = QPushButton("No icon")
        self._no_icon_btn.setCheckable(True)
        self._no_icon_btn.setChecked(current_icon is None)
        self._no_icon_btn.clicked.connect(self._on_no_icon_clicked)
        layout.addWidget(self._no_icon_btn)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_no_icon_clicked(self) -> None:
        self._no_icon_btn.setChecked(True)
        for b in self._icon_buttons:
            b.setChecked(False)
        self._selected_icon = None
        if self._on_icon_changed:
            self._on_icon_changed(None)

    def _make_icon_click_handler(self, clicked_btn: QPushButton):
        def handler():
            self._no_icon_btn.setChecked(False)
            for b in self._icon_buttons:
                b.setChecked(b is clicked_btn)
            self._selected_icon = clicked_btn.property("iconFile")
            if self._on_icon_changed:
                self._on_icon_changed(self._selected_icon)

        return handler

    def get_icon_filename(self) -> Optional[str]:
        """Return the selected icon filename (e.g. Hand.png) or None."""
        return self._selected_icon
