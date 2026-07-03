"""
Dialog to create or edit a tag library shelf (title, filter mode, colour).
"""

from typing import Optional

from qtpy.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QDialogButtonBox,
    QButtonGroup,
    QRadioButton,
    QPushButton,
)
from qtpy.QtGui import QColor

from gui.tag_shelves import SHELF_FILTER_AND, SHELF_FILTER_OR

_DEFAULT_SWATCH = "#7c4dff"


class AddShelfDialog(QDialog):
    """Dialog to set a shelf's name, AND/OR filter semantics and colour."""

    def __init__(
        self,
        parent=None,
        *,
        name: str = "",
        filter_mode: str = SHELF_FILTER_OR,
        color: Optional[str] = None,
        is_edit: bool = False,
    ):
        """
        Args:
            parent: Parent widget.
            name: Initial shelf title (without trailing colon).
            filter_mode: Initial filter mode ("and" or "or").
            color: Initial hex colour, or None for no colour.
            is_edit: True to show edit wording, False for creation.
        """
        super().__init__(parent)
        self.setWindowTitle("Edit shelf" if is_edit else "Create shelf")
        self._color: Optional[str] = color
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Shelf title:"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText('e.g. Camera-Angle (":" added automatically)')
        self._name_edit.setText(name)
        layout.addWidget(self._name_edit)

        layout.addWidget(QLabel("When filtering images:"))
        self._filter_group = QButtonGroup(self)
        self._or_radio = QRadioButton("Match any selected tag (OR) — like Camera-Angle")
        self._and_radio = QRadioButton(
            "Match all selected tags (AND) — like Miscellaneous"
        )
        self._filter_group.addButton(self._or_radio)
        self._filter_group.addButton(self._and_radio)
        if filter_mode == SHELF_FILTER_AND:
            self._and_radio.setChecked(True)
        else:
            self._or_radio.setChecked(True)
        layout.addWidget(self._or_radio)
        layout.addWidget(self._and_radio)

        # Colour row
        color_row = QHBoxLayout()
        color_row.addWidget(QLabel("Colour:"))
        self._color_btn = QPushButton()
        self._color_btn.setCursor(self._color_btn.cursor())
        self._color_btn.setFixedHeight(26)
        self._color_btn.clicked.connect(self._pick_color)
        color_row.addWidget(self._color_btn, 1)
        self._clear_color_btn = QPushButton("No colour")
        self._clear_color_btn.clicked.connect(self._clear_color)
        color_row.addWidget(self._clear_color_btn)
        layout.addLayout(color_row)
        self._refresh_color_button()

        hint = QLabel(
            "Shelves appear as bold section headers in the tag library. "
            "Tags placed in a shelf take its colour."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #aaa; font-size: 11px;")
        layout.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _pick_color(self) -> None:
        """Open the compact swatch picker and store the chosen colour."""
        from gui.tag_library.shelf_color_popup import pick_shelf_color

        current = QColor(self._color) if self._color else None
        chosen = pick_shelf_color(current, self)
        if chosen:
            self._color = chosen
            self._refresh_color_button()

    def _clear_color(self) -> None:
        """Remove the shelf colour (falls back to the default hue)."""
        self._color = None
        self._refresh_color_button()

    def _refresh_color_button(self) -> None:
        """Sync the colour preview button with the current selection."""
        if self._color:
            self._color_btn.setText(self._color)
            self._color_btn.setStyleSheet(
                f"QPushButton {{ background: {self._color}; color: #fff;"
                f" border: 1px solid rgba(0,0,0,0.4); border-radius: 6px; }}"
            )
        else:
            self._color_btn.setText("Default")
            self._color_btn.setStyleSheet(
                "QPushButton { background: rgba(255,255,255,0.06); color: #ccc;"
                " border: 1px solid rgba(255,255,255,0.15); border-radius: 6px; }"
            )

    def get_shelf_name(self) -> str:
        """Return the raw shelf title entered by the user."""
        return self._name_edit.text().strip()

    def get_filter_mode(self) -> str:
        """Return shelf filter mode: 'and' or 'or'."""
        if self._and_radio.isChecked():
            return SHELF_FILTER_AND
        return SHELF_FILTER_OR

    def get_color(self) -> Optional[str]:
        """Return the chosen hex colour, or None if no colour is set."""
        return self._color
