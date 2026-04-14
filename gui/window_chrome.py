"""
Reusable frameless window chrome widgets and helpers.
"""

from __future__ import annotations

from typing import Optional

from qtpy.QtCore import Qt, QPoint, QSize
from qtpy.QtGui import QMouseEvent
from qtpy.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStyle,
    QWidget,
)


class WindowChromeBar(QWidget):
    """Custom title bar with window controls and drag support."""

    def __init__(
        self,
        title: str,
        parent_window: QWidget,
        *,
        show_minimize: bool = True,
        show_maximize: bool = True,
        show_close: bool = True,
    ) -> None:
        super().__init__(parent_window)
        self._parent_window = parent_window
        self._show_maximize = show_maximize
        self._drag_offset = QPoint()
        self._dragging = False
        self.setObjectName("UnifiedChromeBar")
        self.setFixedHeight(38)

        row = QHBoxLayout(self)
        row.setContentsMargins(10, 0, 8, 0)
        row.setSpacing(6)

        self._title_label = QLabel(title, self)
        self._title_label.setObjectName("UnifiedChromeTitle")
        self._title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        row.addWidget(self._title_label, 1, Qt.AlignVCenter)

        self._min_btn: Optional[QPushButton] = None
        self._max_btn: Optional[QPushButton] = None
        self._close_btn: Optional[QPushButton] = None

        if show_minimize:
            self._min_btn = self._make_control_button("-", "Minimize")
            self._assign_standard_icon(self._min_btn, "SP_TitleBarMinButton")
            self._min_btn.clicked.connect(parent_window.showMinimized)
            row.addWidget(self._min_btn, 0, Qt.AlignVCenter)
        if show_maximize:
            self._max_btn = self._make_control_button("□", "Maximize")
            self._max_btn.clicked.connect(self._toggle_maximize_restore)
            row.addWidget(self._max_btn, 0, Qt.AlignVCenter)
        if show_close:
            self._close_btn = self._make_control_button("X", "Close")
            self._assign_standard_icon(self._close_btn, "SP_TitleBarCloseButton")
            self._close_btn.setObjectName("UnifiedChromeCloseButton")
            self._close_btn.clicked.connect(parent_window.close)
            row.addWidget(self._close_btn, 0, Qt.AlignVCenter)

        self._apply_local_styles()
        self.sync_window_state()

    def _make_control_button(self, text: str, tooltip: str) -> QPushButton:
        btn = QPushButton(text, self)
        btn.setToolTip(tooltip)
        btn.setFixedSize(30, 22)
        btn.setObjectName("UnifiedChromeButton")
        return btn

    def _assign_standard_icon(self, button: QPushButton, icon_name: str) -> None:
        """Apply a native titlebar icon when available."""
        style = QApplication.style()
        if style is None:
            return
        sp = getattr(QStyle, icon_name, None)
        if sp is None:
            return
        icon = style.standardIcon(sp)
        if not icon.isNull():
            button.setIcon(icon)
            side = int(min(button.width(), button.height()) * 0.55)
            button.setIconSize(QSize(side, side))
            button.setText("")

    def _apply_local_styles(self) -> None:
        self.setStyleSheet("""
            QWidget#UnifiedChromeBar {
                background-color: rgba(10, 12, 20, 0.45);
                border-bottom: 1px solid rgba(255, 255, 255, 0.10);
            }
            QLabel#UnifiedChromeTitle {
                color: #f0f0f0;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton#UnifiedChromeButton {
                background-color: rgba(45, 48, 52, 0.90);
                color: #e0e0e0;
                border: 1px solid #555;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton#UnifiedChromeButton:hover {
                background-color: rgba(60, 64, 70, 0.95);
                border-color: #6b9bd1;
            }
            QPushButton#UnifiedChromeButton:pressed {
                background-color: rgba(35, 38, 42, 0.95);
            }
            QPushButton#UnifiedChromeCloseButton {
                background-color: rgba(140, 45, 45, 0.90);
                color: #ffffff;
                border: 1px solid #8a3a3a;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton#UnifiedChromeCloseButton:hover {
                background-color: rgba(180, 55, 55, 0.95);
                border-color: #d17a7a;
            }
            QPushButton#UnifiedChromeCloseButton:pressed {
                background-color: rgba(120, 35, 35, 0.95);
            }
            """)

    def set_title(self, title: str) -> None:
        """Update title text."""
        self._title_label.setText(title)

    def _toggle_maximize_restore(self) -> None:
        if self._parent_window.isMaximized():
            self._parent_window.showNormal()
        else:
            self._parent_window.showMaximized()
        self.sync_window_state()

    def sync_window_state(self) -> None:
        """Sync maximize icon with current window state."""
        if self._max_btn is None:
            return
        if self._parent_window.isMaximized():
            self._assign_standard_icon(self._max_btn, "SP_TitleBarNormalButton")
            if self._max_btn.text():
                self._max_btn.setText("❐")
            self._max_btn.setToolTip("Restore")
        else:
            self._assign_standard_icon(self._max_btn, "SP_TitleBarMaxButton")
            if self._max_btn.text():
                self._max_btn.setText("□")
            self._max_btn.setToolTip("Maximize")

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.LeftButton:
            super().mousePressEvent(event)
            return
        self._dragging = True
        gp = (
            event.globalPosition().toPoint()
            if hasattr(event, "globalPosition")
            else event.globalPos()
        )
        self._drag_offset = gp - self._parent_window.frameGeometry().topLeft()
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self._dragging or not (event.buttons() & Qt.LeftButton):
            super().mouseMoveEvent(event)
            return
        if self._parent_window.isMaximized() and self._show_maximize:
            self._parent_window.showNormal()
            self.sync_window_state()
        gp = (
            event.globalPosition().toPoint()
            if hasattr(event, "globalPosition")
            else event.globalPos()
        )
        self._parent_window.move(gp - self._drag_offset)
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._dragging = False
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if (
            event.button() == Qt.LeftButton
            and self._show_maximize
            and self._max_btn is not None
        ):
            self._toggle_maximize_restore()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


def enable_frameless_window(window: QWidget) -> None:
    """Enable frameless mode for a top-level window."""
    window.setWindowFlags(window.windowFlags() | Qt.FramelessWindowHint)


def apply_glass_button_style(button: QPushButton, *, primary: bool = False) -> None:
    """Apply reusable glass style to action buttons."""
    if primary:
        button.setStyleSheet("""
            QPushButton {
                background-color: rgba(82, 158, 255, 0.35);
                color: #ffffff;
                border: 1px solid rgba(166, 214, 255, 0.75);
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(98, 174, 255, 0.45);
                border-color: rgba(200, 233, 255, 0.95);
            }
            QPushButton:pressed {
                background-color: rgba(58, 130, 220, 0.45);
            }
            QPushButton:disabled {
                background-color: rgba(66, 78, 98, 0.45);
                color: rgba(224, 224, 224, 0.7);
                border-color: rgba(120, 130, 150, 0.5);
            }
            """)
    else:
        button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.11);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.28);
                border-radius: 8px;
                padding: 7px 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.17);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.24);
            }
            QPushButton:disabled {
                background-color: rgba(120, 120, 120, 0.20);
                color: rgba(220, 220, 220, 0.70);
                border-color: rgba(150, 150, 150, 0.30);
            }
            """)
