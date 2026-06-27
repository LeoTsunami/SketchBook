"""
Tag chip widgets for the tag library.

DraggableTagButton  – base button with DnD and context menu signals.
WrappingDraggableTagButton – unified chip used for every cell in the grid
                             (category rows and subtag cells).  Manages its own
                             icon/text layout so the icon fills the chip height
                             without needing external padding.
"""
from __future__ import annotations

from typing import Optional

from qtpy.QtWidgets import (
    QPushButton,
    QLabel,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QSizePolicy,
    QGraphicsDropShadowEffect,
)
from qtpy.QtCore import Qt, Signal, QSize, QMimeData, QRect
from qtpy.QtGui import (
    QColor,
    QDrag,
    QFontMetrics,
    QFont,
    QIcon,
    QPainter,
    QPixmap,
)

from core.settings import settings
from gui.tag_library.constants import (
    TAG_LIBRARY_MIME,
    TAG_LIBRARY_TAG_MIN_HEIGHT_PX,
    TAG_LIBRARY_TAG_BORDER_WIDTH_PX,
    TAG_LIBRARY_TAG_STYLE_V_PADDING_PX,
    TAG_LIBRARY_TAG_MAX_HEIGHT_PX,
    TAG_LIBRARY_TAG_CELL_MIN_WIDTH_PX,
    TAG_LIBRARY_TAG_CELL_ALIGN,
    TAG_LIBRARY_FONT_SUBTAG_PX,
    TAG_LIBRARY_TAG_SHADOW_BLUR_PX,
    TAG_LIBRARY_TAG_SHADOW_OFFSET_PX,
    TAG_LIBRARY_TAG_SHADOW_ALPHA,
    TAG_LIBRARY_TAG_BORDER_WIDTH_PX,
    tag_library_idle_border_css,
)


# ---------------------------------------------------------------------------
# Colour helpers (used by both chips and sections for consistent appearance)
# ---------------------------------------------------------------------------

def get_hierarchy_background_color(branch_key: str, depth: int) -> QColor:
    """
    Return a vivid depth-based colour for a tag chip.

    Args:
        branch_key: Category name used to derive a base hue.
        depth: 0 = category, 1 = subtag, 2+ = nested subtag.

    Returns:
        QColor in HSL space.
    """
    norm = branch_key.lower().replace(" ", "").replace("-", "").replace("_", "")
    if norm == "animal":
        hue = 128
    elif norm == "human":
        hue = 212
    else:
        hue = sum(ord(c) for c in branch_key) % 360
    dark_theme = settings.get("ui.theme", "dark") != "light"
    if dark_theme:
        sat_pct = min(55 + depth * 5, 80)
        light_pct = min(28 + depth * 8, 58)
    else:
        sat_pct = min(50 + depth * 6, 80)
        light_pct = max(80 - depth * 8, 42)
    return QColor.fromHsl(
        hue,
        int(255 * sat_pct / 100),
        int(255 * light_pct / 100),
    )


def blend_color(base: QColor, tint: QColor, ratio: float) -> QColor:
    """
    Mix base colour toward tint by ratio.

    Args:
        base: Source colour.
        tint: Target tint.
        ratio: 0.0 = pure base, 1.0 = pure tint.

    Returns:
        QColor blended result.
    """
    r = int(base.red() + (tint.red() - base.red()) * ratio)
    g = int(base.green() + (tint.green() - base.green()) * ratio)
    b = int(base.blue() + (tint.blue() - base.blue()) * ratio)
    return QColor(max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)), base.alpha())


def chip_gradient(
    bg: QColor,
    *,
    lighter: int = 108,
    darker: int = 112,
    alpha_top: int = 230,
    alpha_bot: int = 215,
) -> str:
    """
    Build a vertical ``qlineargradient`` CSS value for a tag chip.

    Args:
        bg: Base background colour.
        lighter: Factor for the top stop (lighter).
        darker: Factor for the bottom stop (darker).
        alpha_top: Alpha for the top stop.
        alpha_bot: Alpha for the bottom stop.

    Returns:
        str: CSS background value.
    """
    top = bg.lighter(lighter)
    bot = bg.darker(darker)
    top.setAlpha(alpha_top)
    bot.setAlpha(alpha_bot)

    def _rgba(c: QColor) -> str:
        return f"rgba({c.red()},{c.green()},{c.blue()},{c.alpha()})"

    return (
        f"qlineargradient(x1:0,y1:0,x2:0,y2:1,"
        f"stop:0 {_rgba(top)},stop:1 {_rgba(bot)})"
    )


def apply_chip_style(
    button: QPushButton,
    branch_key: str,
    depth: int,
    active: bool,
    selected_for_drag: bool = False,
) -> None:
    """
    Apply the unified gradient style to any tag library button.

    Caches the stylesheet per (branch_key, depth) so subsequent calls only
    update the ``tagState`` property when needed, avoiding costly
    ``setStyleSheet / unpolish / polish`` on every repaint sweep.

    Args:
        button: Target button widget.
        branch_key: Category name (determines hue).
        depth: Visual depth level (0 = category, 1+ = subtag).
        active: Whether the tag is part of the active filter.
        selected_for_drag: Whether the tag is in the drag selection.
    """
    dark_theme = settings.get("ui.theme", "dark") != "light"
    style_key = (branch_key, depth)

    if button.property("_styleKey") != str(style_key):
        bg = get_hierarchy_background_color(branch_key, depth)
        text = "#f5f5f5" if dark_theme else "#1a1a1a"

        grad_rest = chip_gradient(bg, lighter=108, darker=112, alpha_top=220, alpha_bot=200)
        grad_hover = chip_gradient(bg, lighter=128, darker=108, alpha_top=240, alpha_bot=225)

        blue_tint = QColor(80, 150, 255)
        bg_sel = blend_color(bg, blue_tint, 0.30)
        grad_sel = chip_gradient(bg_sel, lighter=115, darker=108, alpha_top=235, alpha_bot=215)
        grad_sel_h = chip_gradient(bg_sel, lighter=135, darker=105, alpha_top=245, alpha_bot=230)

        green_tint = QColor(80, 220, 100)
        bg_act = blend_color(bg, green_tint, 0.30)
        grad_act = chip_gradient(bg_act, lighter=115, darker=108, alpha_top=235, alpha_bot=215)
        grad_act_h = chip_gradient(bg_act, lighter=135, darker=105, alpha_top=245, alpha_bot=230)

        border_idle = tag_library_idle_border_css(bg)
        border_hover = f"2px solid {bg.lighter(165).name()}"
        blue_border = "#5aabff" if dark_theme else "#2b6cb0"
        green_border = "#72f572" if dark_theme else "#2fa84f"

        font_css = f"font-size: {TAG_LIBRARY_FONT_SUBTAG_PX}px; font-weight: 600;"
        is_wrapping = isinstance(button, WrappingDraggableTagButton)
        padding = "0px" if is_wrapping else f"{TAG_LIBRARY_TAG_STYLE_V_PADDING_PX}px 4px"

        def _block(selector: str, grad: str, border: str) -> str:
            return (
                f"{selector} {{ padding: {padding}; color: {text}; {font_css} "
                f"background: {grad}; border: {border}; border-radius: 5px; }}\n"
            )

        css = (
            _block("QPushButton", grad_rest, border_idle)
            + _block("QPushButton:hover", grad_hover, border_hover)
            + _block('QPushButton[tagState="selected"]', grad_sel, f"2px solid {blue_border}")
            + _block('QPushButton[tagState="selected"]:hover', grad_sel_h, f"2px solid {blue_border}")
            + _block('QPushButton[tagState="active"]', grad_act, f"2px solid {green_border}")
            + _block('QPushButton[tagState="active"]:hover', grad_act_h, f"2px solid {green_border}")
        )
        button.setStyleSheet(css)
        button.setProperty("_styleKey", str(style_key))
        button.setCursor(Qt.PointingHandCursor)

        shadow = button.graphicsEffect()
        if not isinstance(shadow, QGraphicsDropShadowEffect):
            shadow = QGraphicsDropShadowEffect(button)
            button.setGraphicsEffect(shadow)
            shadow.setBlurRadius(TAG_LIBRARY_TAG_SHADOW_BLUR_PX)
            shadow.setOffset(0, TAG_LIBRARY_TAG_SHADOW_OFFSET_PX)
            shadow.setColor(QColor(0, 0, 0, TAG_LIBRARY_TAG_SHADOW_ALPHA))

    new_state = "selected" if selected_for_drag else ("active" if active else "")
    if button.property("tagState") != new_state:
        button.setProperty("tagState", new_state)
        button.style().unpolish(button)
        button.style().polish(button)


# ---------------------------------------------------------------------------
# DraggableTagButton
# ---------------------------------------------------------------------------

class DraggableTagButton(QPushButton):
    """
    Tag button with DnD and context menu support.

    Signals:
        contextMenuRequested: Emitted with the tag label when right-clicked.
        drag_session_started: Emitted when a QDrag begins (for panel autoscroll).
        drag_session_ended: Emitted when QDrag finishes.
    """

    contextMenuRequested = Signal(str)
    drag_session_started = Signal()
    drag_session_ended = Signal()

    def __init__(self, text: str, parent: Optional[QWidget] = None) -> None:
        """
        Args:
            text: Button label / tag name.
            parent: Optional parent widget.
        """
        super().__init__(text, parent)
        self._drag_start_pos = None

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def contextMenuEvent(self, event) -> None:
        self.contextMenuRequested.emit(self.property("baseLabel") or self.text())
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        if (
            event.buttons() & Qt.LeftButton
            and self._drag_start_pos is not None
            and (event.pos() - self._drag_start_pos).manhattanLength() >= 10
        ):
            tag_text = self.property("baseLabel") or self.text()
            if not tag_text:
                return
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(tag_text)
            if self.property("userTag"):
                mime_data.setData(TAG_LIBRARY_MIME, tag_text.encode("utf-8"))
            drag.setMimeData(mime_data)

            pixmap = QPixmap(120, 28)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setPen(Qt.white)
            painter.drawText(pixmap.rect(), Qt.AlignCenter, tag_text)
            painter.end()
            drag.setPixmap(pixmap)

            self.drag_session_started.emit()
            try:
                drag.exec_(Qt.MoveAction)
            finally:
                self.drag_session_ended.emit()
            return
        super().mouseMoveEvent(event)


# ---------------------------------------------------------------------------
# WrappingDraggableTagButton
# ---------------------------------------------------------------------------

class WrappingDraggableTagButton(DraggableTagButton):
    """
    Unified chip for every cell in the tag library grid.

    Manages its own icon/text layout so the icon fills the chip height with
    no extra padding.  Width is set externally via ``set_cell_width()``.
    """

    ICON_SIDE_PX = TAG_LIBRARY_TAG_MIN_HEIGHT_PX - TAG_LIBRARY_TAG_BORDER_WIDTH_PX * 2 - 4

    def __init__(self, text: str, cell_width: int, parent: Optional[QWidget] = None) -> None:
        """
        Args:
            text: Chip label.
            cell_width: Fixed pixel width to use for the chip.
            parent: Optional parent widget.
        """
        super().__init__("", parent)
        self._cell_width = 0  # sentinel: 0 forces first set_cell_width to apply
        self._geometry_valid = False
        self._source_icon: Optional[QIcon] = None
        self._icon_label: Optional[QLabel] = None

        self._text_label = QLabel(text)
        self._text_label.setWordWrap(True)
        self._text_label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self._text_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._text_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        label_font = self.font()
        label_font.setPixelSize(TAG_LIBRARY_FONT_SUBTAG_PX)
        label_font.setWeight(QFont.Weight.DemiBold)
        self._text_label.setFont(label_font)

        self._content_row = QWidget(self)
        self._content_row.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._content_row.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._row_layout = QHBoxLayout(self._content_row)
        self._row_layout.setContentsMargins(0, 0, 0, 0)
        self._row_layout.setSpacing(4)
        self._row_layout.setAlignment(TAG_LIBRARY_TAG_CELL_ALIGN)
        self._row_layout.addWidget(self._text_label, 0, TAG_LIBRARY_TAG_CELL_ALIGN)

        self._inner_layout = QVBoxLayout(self)
        self._inner_layout.setContentsMargins(2, 0, 2, 0)
        self._inner_layout.setSpacing(0)
        self._inner_layout.setAlignment(Qt.AlignVCenter)
        self._inner_layout.addWidget(self._content_row, 0, Qt.AlignCenter)

        self.setCursor(Qt.PointingHandCursor)
        self.set_cell_width(cell_width)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_cell_width(self, width: int, *, min_w: int = TAG_LIBRARY_TAG_CELL_MIN_WIDTH_PX) -> None:
        """
        Set fixed cell width and recompute chip geometry.

        Args:
            width: Target pixel width.
            min_w: Minimum enforced width.
        """
        new_w = max(min_w, width)
        if new_w == self._cell_width and self._geometry_valid:
            return
        self._cell_width = new_w
        self.setFixedWidth(self._cell_width)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setProperty("tagLibraryCell", True)
        self._geometry_valid = True
        self._sync_chip_geometry()

    def setText(self, text: str) -> None:
        if self._text_label.text() == text:
            return
        self._text_label.setText(text)
        self._sync_chip_geometry()

    def text(self) -> str:
        return self._text_label.text()

    def setIcon(self, icon: QIcon) -> None:
        self._source_icon = None if icon.isNull() else icon
        if icon.isNull():
            if self._icon_label is not None:
                self._icon_label.setHidden(True)
        else:
            if self._icon_label is None:
                self._icon_label = QLabel(self._content_row)
                self._icon_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
                self._row_layout.insertWidget(0, self._icon_label, 0, TAG_LIBRARY_TAG_CELL_ALIGN)
            self._icon_label.setHidden(False)
        self._sync_chip_geometry()

    def setIconSize(self, _size: QSize) -> None:
        """Icon size derives from chip height; external calls are no-ops."""
        self._sync_chip_geometry()

    def sizeHint(self) -> QSize:
        """Stable size hint — never recomputes to avoid layout feedback loops."""
        h = getattr(self, "_chip_height", TAG_LIBRARY_TAG_MIN_HEIGHT_PX)
        return QSize(self._cell_width, h)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------

    def _sync_chip_geometry(self) -> None:
        """Recompute internal sizes without triggering layout loops."""
        if getattr(self, "_syncing_chip_geometry", False):
            return
        self._syncing_chip_geometry = True
        try:
            self._sync_chip_geometry_impl()
        finally:
            self._syncing_chip_geometry = False

    def _label_height_for_text(self, text_w: int) -> int:
        """
        Stable text height via font metrics.

        Args:
            text_w: Available width in pixels.

        Returns:
            int: Pixel height needed to render the text.
        """
        fm = QFontMetrics(self._text_label.font())
        br = fm.boundingRect(
            QRect(0, 0, text_w, 10000),
            Qt.TextWordWrap | Qt.AlignHCenter,
            self._text_label.text(),
        )
        return max(fm.height(), br.height()) + 2

    def _tight_text_width(self, max_w: int) -> int:
        """
        Minimum width needed to render the label without wasted space.

        Args:
            max_w: Maximum allowed width.

        Returns:
            int: Tight pixel width.
        """
        fm = QFontMetrics(self._text_label.font())
        single_line_w = fm.horizontalAdvance(self._text_label.text()) + 4
        if single_line_w <= max_w:
            return max(20, single_line_w)
        return max(20, max_w)

    def _sync_chip_geometry_impl(self) -> None:
        border_v = TAG_LIBRARY_TAG_BORDER_WIDTH_PX * 2
        chip_h_est = TAG_LIBRARY_TAG_MIN_HEIGHT_PX
        icon_px = chip_h_est - border_v - 4
        has_icon = (
            self._source_icon is not None
            and self._icon_label is not None
            and not self._icon_label.isHidden()
        )
        icon_block_w = (icon_px + self._row_layout.spacing()) if has_icon else 0

        margins = self._inner_layout.contentsMargins()
        h_pad = margins.left() + margins.right()
        raw_inner_w = max(24, self._cell_width - h_pad - border_v - 2)
        max_text_w = max(20, raw_inner_w - icon_block_w)
        text_w = self._tight_text_width(max_text_w)

        label_h = self._label_height_for_text(text_w)
        pad_v = TAG_LIBRARY_TAG_STYLE_V_PADDING_PX * 2
        chip_h = min(
            TAG_LIBRARY_TAG_MAX_HEIGHT_PX,
            max(TAG_LIBRARY_TAG_MIN_HEIGHT_PX, label_h + pad_v + border_v + 4),
        )
        icon_px = chip_h - border_v - 4
        row_h = max(label_h, icon_px if has_icon else 0)
        row_w = text_w + (icon_px + self._row_layout.spacing() if has_icon else 0)

        self._text_label.setFixedSize(text_w, label_h)
        self._content_row.setFixedSize(row_w, row_h)

        if has_icon:
            pm = self._source_icon.pixmap(icon_px, icon_px)
            self._icon_label.setPixmap(pm)
            self._icon_label.setFixedSize(icon_px, icon_px)

        self.setFixedHeight(chip_h)
        self._chip_height = chip_h
