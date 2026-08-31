"""
Compact bar listing active tag filters with a reset control.
"""

from __future__ import annotations

from typing import Iterable, List

from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QWidget,
)


class ActiveFiltersBar(QFrame):
    """Shows active filter tags and a reset button."""

    reset_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Initialize the active filters bar.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setObjectName("ActiveFiltersBar")
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet(
            """
            QFrame#ActiveFiltersBar {
                background: rgba(0, 0, 0, 0.22);
                border-top: 1px solid rgba(255, 255, 255, 0.08);
            }
            QLabel#ActiveFiltersEmpty {
                color: rgba(255, 255, 255, 0.45);
                font-size: 11px;
            }
            QLabel#ActiveFilterChip {
                color: #f4f2f8;
                background: rgba(75, 110, 175, 0.55);
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 10px;
                padding: 2px 8px;
                font-size: 11px;
            }
            QPushButton#ActiveFiltersReset {
                color: #f4f2f8;
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton#ActiveFiltersReset:hover {
                background: rgba(255, 255, 255, 0.14);
            }
            QPushButton#ActiveFiltersReset:disabled {
                color: rgba(255, 255, 255, 0.35);
                background: rgba(255, 255, 255, 0.04);
            }
            """
        )

        root = QHBoxLayout(self)
        root.setContentsMargins(8, 6, 8, 6)
        root.setSpacing(8)

        title = QLabel("Active")
        title.setStyleSheet(
            "color: rgba(255, 255, 255, 0.72); font-size: 11px; font-weight: 600;"
        )
        root.addWidget(title)

        self._scroll = QScrollArea()
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._scroll.setMaximumHeight(28)

        self._chips_host = QWidget()
        self._chips_layout = QHBoxLayout(self._chips_host)
        self._chips_layout.setContentsMargins(0, 0, 0, 0)
        self._chips_layout.setSpacing(6)
        self._empty_label = QLabel("No filters")
        self._empty_label.setObjectName("ActiveFiltersEmpty")
        self._chips_layout.addWidget(self._empty_label)
        self._chips_layout.addStretch(1)
        self._scroll.setWidget(self._chips_host)
        root.addWidget(self._scroll, 1)

        self._reset_btn = QPushButton("Reset")
        self._reset_btn.setObjectName("ActiveFiltersReset")
        self._reset_btn.setFixedHeight(24)
        self._reset_btn.clicked.connect(self.reset_clicked.emit)
        root.addWidget(self._reset_btn)

    def set_active_tags(self, tags: Iterable[str]) -> None:
        """
        Refresh the chip list.

        Args:
            tags: Active filter tag names in display order.
        """
        ordered: List[str] = []
        seen = set()
        for tag in tags:
            if tag and tag not in seen:
                seen.add(tag)
                ordered.append(tag)

        while self._chips_layout.count():
            item = self._chips_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if not ordered:
            self._empty_label = QLabel("No filters")
            self._empty_label.setObjectName("ActiveFiltersEmpty")
            self._chips_layout.addWidget(self._empty_label)
            self._chips_layout.addStretch(1)
            self._reset_btn.setEnabled(False)
            return

        for tag in ordered:
            chip = QLabel(tag)
            chip.setObjectName("ActiveFilterChip")
            self._chips_layout.addWidget(chip)
        self._chips_layout.addStretch(1)
        self._reset_btn.setEnabled(True)
