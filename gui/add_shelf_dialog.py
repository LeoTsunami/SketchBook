"""
Dialog to add a new tag library shelf (titled separator section).
"""

from qtpy.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QDialogButtonBox,
    QButtonGroup,
    QRadioButton,
)
from qtpy.QtCore import Qt

from gui.tag_shelves import SHELF_FILTER_AND, SHELF_FILTER_OR


class AddShelfDialog(QDialog):
    """Dialog to name a new shelf and choose AND vs OR filter semantics."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create shelf")
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Shelf title:"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText('e.g. Camera-Angle (":" added automatically)')
        layout.addWidget(self._name_edit)

        layout.addWidget(QLabel("When filtering images:"))
        self._filter_group = QButtonGroup(self)
        self._or_radio = QRadioButton("Match any selected tag (OR) — like Camera-Angle")
        self._and_radio = QRadioButton(
            "Match all selected tags (AND) — like Miscellaneous"
        )
        self._or_radio.setChecked(True)
        self._filter_group.addButton(self._or_radio)
        self._filter_group.addButton(self._and_radio)
        layout.addWidget(self._or_radio)
        layout.addWidget(self._and_radio)

        hint = QLabel(
            "Shelves appear as bold section headers in the tag library. "
            "Add tags to them with Create tag or drag-and-drop."
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

    def get_shelf_name(self) -> str:
        """Return the raw shelf title entered by the user."""
        return self._name_edit.text().strip()

    def get_filter_mode(self) -> str:
        """Return shelf filter mode: 'and' or 'or'."""
        if self._and_radio.isChecked():
            return SHELF_FILTER_AND
        return SHELF_FILTER_OR
