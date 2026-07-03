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
    QApplication,
    QPushButton,
    QLabel,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QSizePolicy,
    QGraphicsDropShadowEffect,
)
from qtpy.QtCore import Qt, Signal, QSize, QMimeData, QRect, QPoint, QRectF
from qtpy.QtGui import (
    QColor,
    QDrag,
    QFontMetrics,
    QFont,
    QIcon,
    QPainter,
    QPainterPath,
    QPixmap,
    QRegion,
)

from gui.icon_utils import tint_icon
from gui.tag_library.constants import (
    TAG_LIBRARY_MIME,
    TAG_LIBRARY_TAG_MIN_HEIGHT_PX,
    TAG_LIBRARY_TAG_BORDER_WIDTH_PX,
    TAG_LIBRARY_TAG_STYLE_V_PADDING_PX,
    TAG_LIBRARY_TAG_MAX_HEIGHT_PX,
    TAG_LIBRARY_TAG_CELL_MIN_WIDTH_PX,
    TAG_LIBRARY_TAG_CELL_ALIGN,
    TAG_LIBRARY_FONT_SUBTAG_PX,
    TAG_LIBRARY_FONT_CATEGORY_PX,
    TAG_LIBRARY_TAG_SHADOW_BLUR_PX,
    TAG_LIBRARY_TAG_SHADOW_OFFSET_X_PX,
    TAG_LIBRARY_TAG_SHADOW_OFFSET_Y_PX,
    TAG_LIBRARY_TAG_SHADOW_ALPHA,
    TAG_LIBRARY_CATEGORY_SHADOW_BLUR_PX,
    TAG_LIBRARY_CATEGORY_SHADOW_OFFSET_X_PX,
    TAG_LIBRARY_CATEGORY_SHADOW_OFFSET_Y_PX,
    TAG_LIBRARY_CATEGORY_SHADOW_ALPHA,
    TAG_LIBRARY_DRAG_SHADOW_BLUR_PX,
    TAG_LIBRARY_DRAG_SHADOW_OFFSET_X_PX,
    TAG_LIBRARY_DRAG_SHADOW_OFFSET_Y_PX,
    TAG_LIBRARY_DRAG_SHADOW_ALPHA,
    TAG_LIBRARY_DRAG_CURSOR_OFFSET_X_PX,
    TAG_LIBRARY_DRAG_CURSOR_OFFSET_Y_PX,
    TAG_LIBRARY_TAG_CHIP_RADIUS_PX,
    TAG_LIBRARY_CATEGORY_CHIP_RADIUS_PX,
    TAG_LIBRARY_CATEGORY_MIN_HEIGHT_PX,
    TAG_LIBRARY_TAG_ICON_SLOT_PX,
    TAG_LIBRARY_CATEGORY_ICON_SLOT_PX,
    TAG_LIBRARY_CHIP_CONTENT_HPAD_PX,
)
from gui.tag_library.chip_trace import sync_chip_trace
from gui.tag_library.theme import (
    blend_color,
    chip_palette,
    chip_state_palette,
    get_hierarchy_background_color,
    ChipPalette,
)


# Re-export colour helpers used by section.py and legacy call sites.
__all__ = [
    "get_hierarchy_background_color",
    "blend_color",
    "apply_chip_style",
    "grab_chip_for_drag",
    "get_chip_drag_source",
    "build_chip_drag_pixmap",
    "prepare_chip_drag_pixmap",
    "chip_drag_hot_spot",
    "apply_drag_cursor_offset",
    "invalidate_chip_drag_pixmap",
    "drag_pixmap_with_shadow",
    "DraggableTagButton",
    "WrappingDraggableTagButton",
]


# ---------------------------------------------------------------------------
# Colour helpers (re-exported from theme)
# ---------------------------------------------------------------------------


def _apply_chip_drop_shadow(button: QPushButton, *, is_category: bool) -> None:
    """
    Apply a soft neutral drop shadow (no colored glow).

    Called on every style pass so the effect is never left stale by the cache.

    Args:
        button: Target chip button.
        is_category: True for main category header chips.
    """
    effect = button.graphicsEffect()
    if not isinstance(effect, QGraphicsDropShadowEffect):
        effect = QGraphicsDropShadowEffect(button)
        button.setGraphicsEffect(effect)
    if is_category:
        effect.setBlurRadius(TAG_LIBRARY_CATEGORY_SHADOW_BLUR_PX)
        effect.setOffset(
            TAG_LIBRARY_CATEGORY_SHADOW_OFFSET_X_PX,
            TAG_LIBRARY_CATEGORY_SHADOW_OFFSET_Y_PX,
        )
        effect.setColor(QColor(0, 0, 0, TAG_LIBRARY_CATEGORY_SHADOW_ALPHA))
    else:
        effect.setBlurRadius(TAG_LIBRARY_TAG_SHADOW_BLUR_PX)
        effect.setOffset(
            TAG_LIBRARY_TAG_SHADOW_OFFSET_X_PX,
            TAG_LIBRARY_TAG_SHADOW_OFFSET_Y_PX,
        )
        effect.setColor(QColor(0, 0, 0, TAG_LIBRARY_TAG_SHADOW_ALPHA))
    effect.setEnabled(True)
    effect.update()
    button.update()


def _chip_corner_radius(widget: QWidget) -> int:
    """Return rounded-corner radius for a tag chip widget."""
    if bool(widget.property("tagGridCategory")):
        return TAG_LIBRARY_CATEGORY_CHIP_RADIUS_PX
    return TAG_LIBRARY_TAG_CHIP_RADIUS_PX


def _mask_pixmap_rounded(pixmap: QPixmap, radius_px: int) -> QPixmap:
    """Clip pixmap alpha to a rounded rectangle."""
    if pixmap.isNull() or radius_px <= 0:
        return pixmap
    out = QPixmap(pixmap.size())
    out.fill(Qt.transparent)
    painter = QPainter(out)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    path = QPainterPath()
    path.addRoundedRect(QRectF(pixmap.rect()), float(radius_px), float(radius_px))
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, pixmap)
    painter.end()
    return out


def grab_chip_for_drag(widget: QWidget) -> QPixmap:
    """
    Render a chip into a transparent pixmap without its live drop shadow.

    Args:
        widget: Tag chip button.

    Returns:
        QPixmap: Rounded chip appearance suitable for drag compositing.
    """
    effect = widget.graphicsEffect()
    shadow_was_enabled = False
    if isinstance(effect, QGraphicsDropShadowEffect):
        shadow_was_enabled = effect.isEnabled()
        effect.setEnabled(False)

    trace_overlay = widget.property("_traceOverlay")
    if trace_overlay is not None:
        trace_overlay.hide()
    widget.update()
    if QApplication.instance() is not None:
        QApplication.processEvents()

    pm = QPixmap(widget.size())
    if pm.isNull():
        if trace_overlay is not None:
            trace_overlay.show()
            trace_overlay.sync_geometry()
        if isinstance(effect, QGraphicsDropShadowEffect):
            effect.setEnabled(shadow_was_enabled)
        return pm

    pm.fill(Qt.transparent)
    try:
        render_flags = (
            QWidget.RenderFlag.DrawChildren
            | QWidget.RenderFlag.DrawWindowBackground
        )
    except AttributeError:
        render_flags = QWidget.DrawChildren | QWidget.DrawWindowBackground
    widget.render(pm, QPoint(), QRegion(), render_flags)
    pm = _mask_pixmap_rounded(pm, _chip_corner_radius(widget))

    if trace_overlay is not None:
        trace_overlay.show()
        trace_overlay.sync_geometry()
    if isinstance(effect, QGraphicsDropShadowEffect):
        effect.setEnabled(shadow_was_enabled)
    widget.update()
    return pm


class _DragShadowComposer:
    """Reusable offscreen widget used to composite drag shadows (no per-drag alloc)."""

    def __init__(self) -> None:
        self._pad = int(
            TAG_LIBRARY_DRAG_SHADOW_BLUR_PX
            + max(
                abs(TAG_LIBRARY_DRAG_SHADOW_OFFSET_X_PX),
                abs(TAG_LIBRARY_DRAG_SHADOW_OFFSET_Y_PX),
            )
            + 8
        )
        self._container = QWidget()
        self._container.setAttribute(Qt.WA_DontShowOnScreen, True)
        self._container.setAttribute(Qt.WA_TranslucentBackground, True)
        self._container.setAttribute(Qt.WA_NoSystemBackground, True)
        self._container.setAutoFillBackground(False)

        self._label = QLabel(self._container)
        self._label.setAttribute(Qt.WA_TranslucentBackground, True)

        self._shadow = QGraphicsDropShadowEffect(self._label)
        self._shadow.setBlurRadius(float(TAG_LIBRARY_DRAG_SHADOW_BLUR_PX))
        self._shadow.setOffset(
            float(TAG_LIBRARY_DRAG_SHADOW_OFFSET_X_PX),
            float(TAG_LIBRARY_DRAG_SHADOW_OFFSET_Y_PX),
        )
        self._shadow.setColor(
            QColor(0, 0, 0, TAG_LIBRARY_DRAG_SHADOW_ALPHA)
        )
        self._label.setGraphicsEffect(self._shadow)

    def compose(self, source: QPixmap, hot_spot: QPoint) -> tuple[QPixmap, QPoint]:
        """
        Draw *source* with drop shadow into a new pixmap.

        Args:
            source: Chip pixmap without shadow.
            hot_spot: Cursor anchor in *source* coordinates.

        Returns:
            tuple[QPixmap, QPoint]: Composited pixmap and adjusted hot spot.
        """
        if source.isNull():
            return source, hot_spot

        pad = self._pad
        self._label.setPixmap(source)
        self._label.resize(source.size())
        self._label.move(pad, pad)
        self._container.resize(source.width() + pad * 2, source.height() + pad * 2)

        out = self._container.grab()
        if out.isNull():
            return source, hot_spot
        return out, hot_spot + QPoint(pad, pad)


_drag_shadow_composer: Optional[_DragShadowComposer] = None


def _shadow_composer() -> _DragShadowComposer:
    """Return the process-wide reusable drag-shadow composer."""
    global _drag_shadow_composer
    if _drag_shadow_composer is None:
        _drag_shadow_composer = _DragShadowComposer()
    return _drag_shadow_composer


def drag_pixmap_with_shadow(
    source: QPixmap,
    hot_spot: QPoint,
    *,
    blur: int = TAG_LIBRARY_DRAG_SHADOW_BLUR_PX,
    offset_x: int = TAG_LIBRARY_DRAG_SHADOW_OFFSET_X_PX,
    offset_y: int = TAG_LIBRARY_DRAG_SHADOW_OFFSET_Y_PX,
    alpha: int = TAG_LIBRARY_DRAG_SHADOW_ALPHA,
) -> tuple[QPixmap, QPoint]:
    """
    Composite *source* with a Qt-rendered drop shadow for QDrag feedback.

    Args:
        source: Chip pixmap without shadow.
        hot_spot: Cursor anchor in *source* coordinates.
        blur: Shadow blur radius in pixels.
        offset_x: Horizontal shadow offset.
        offset_y: Vertical shadow offset.
        alpha: Shadow opacity 0–255.

    Returns:
        tuple[QPixmap, QPoint]: Pixmap and adjusted hot spot.
    """
    if source.isNull():
        return source, hot_spot

    composer = _shadow_composer()
    if (
        blur == TAG_LIBRARY_DRAG_SHADOW_BLUR_PX
        and offset_x == TAG_LIBRARY_DRAG_SHADOW_OFFSET_X_PX
        and offset_y == TAG_LIBRARY_DRAG_SHADOW_OFFSET_Y_PX
        and alpha == TAG_LIBRARY_DRAG_SHADOW_ALPHA
    ):
        return composer.compose(source, hot_spot)

    # Non-default shadow params (rare): one-off offscreen grab.
    pad = int(blur + max(abs(offset_x), abs(offset_y)) + 8)
    container = QWidget()
    container.setAttribute(Qt.WA_DontShowOnScreen, True)
    container.setAttribute(Qt.WA_TranslucentBackground, True)
    container.setAttribute(Qt.WA_NoSystemBackground, True)
    container.setAutoFillBackground(False)

    label = QLabel(container)
    label.setAttribute(Qt.WA_TranslucentBackground, True)
    label.setPixmap(source)
    label.resize(source.size())
    label.move(pad, pad)

    shadow = QGraphicsDropShadowEffect(label)
    shadow.setBlurRadius(float(blur))
    shadow.setOffset(float(offset_x), float(offset_y))
    shadow.setColor(QColor(0, 0, 0, alpha))
    label.setGraphicsEffect(shadow)

    container.resize(source.width() + pad * 2, source.height() + pad * 2)
    out = container.grab()
    container.deleteLater()

    if out.isNull():
        return source, hot_spot
    return out, hot_spot + QPoint(pad, pad)


def _chip_drag_cache_key(widget: QWidget) -> str:
    """Build a cache key from chip geometry and style snapshot."""
    style = widget.property("_styleCacheKey") or ""
    label = widget.property("tagGridKey") or widget.property("baseLabel") or ""
    return f"{widget.width()}x{widget.height()}:{style}:{label}:tr-o15"


def chip_drag_hot_spot(source: QPixmap) -> QPoint:
    """
    Return the QDrag attach point: top-right of the chip on the cursor.

    The chip body sits to the bottom-left of the pointer.

    Args:
        source: Chip pixmap before shadow padding.

    Returns:
        QPoint: Hot spot in *source* coordinates.
    """
    if source.isNull():
        return QPoint()
    return QPoint(max(0, source.width() - 1), 0)


def apply_drag_cursor_offset(hot_spot: QPoint, pixmap: QPixmap) -> QPoint:
    """
    Nudge the drag hot spot so the chip sits further up-left of the cursor.

    Args:
        hot_spot: Hot spot in the shadow-padded drag pixmap.
        pixmap: Full drag pixmap passed to QDrag.

    Returns:
        QPoint: Adjusted hot spot, clamped inside the pixmap.
    """
    adjusted = hot_spot + QPoint(
        TAG_LIBRARY_DRAG_CURSOR_OFFSET_X_PX,
        TAG_LIBRARY_DRAG_CURSOR_OFFSET_Y_PX,
    )
    if pixmap.isNull():
        return adjusted
    return QPoint(
        min(max(0, pixmap.width() - 1), adjusted.x()),
        min(max(0, pixmap.height() - 1), adjusted.y()),
    )


def invalidate_chip_drag_pixmap(widget: QWidget) -> None:
    """
    Drop cached drag pixmaps for a chip (after text, size, or style change).

    Args:
        widget: Tag chip button.
    """
    for attr in ("_drag_pixmap_cache", "_drag_source_cache"):
        if hasattr(widget, attr):
            delattr(widget, attr)


def get_chip_drag_source(widget: QWidget) -> QPixmap:
    """
    Return a cached chip grab without live drop shadow.

    Args:
        widget: Tag chip button.

    Returns:
        QPixmap: Rounded chip appearance for drag compositing.
    """
    key = _chip_drag_cache_key(widget)
    cache = getattr(widget, "_drag_source_cache", None)
    if cache and cache.get("key") == key:
        pixmap = cache.get("pixmap")
        if pixmap is not None and not pixmap.isNull():
            return pixmap

    pixmap = grab_chip_for_drag(widget)
    widget._drag_source_cache = {"key": key, "pixmap": pixmap}
    return pixmap


def build_chip_drag_pixmap(widget: QWidget) -> tuple[QPixmap, QPoint]:
    """
    Return drag pixmap and hot spot, using a per-chip cache when possible.

    Args:
        widget: Tag chip button.

    Returns:
        tuple[QPixmap, QPoint]: Pixmap for QDrag and cursor hot spot.
    """
    key = _chip_drag_cache_key(widget)
    cache = getattr(widget, "_drag_pixmap_cache", None)
    if cache and cache.get("key") == key:
        pixmap = cache.get("pixmap")
        hot_spot = cache.get("hot_spot")
        if (
            pixmap is not None
            and not pixmap.isNull()
            and hot_spot is not None
        ):
            return pixmap, hot_spot

    source = get_chip_drag_source(widget)
    hot_spot = chip_drag_hot_spot(source)
    pixmap, hot_spot = drag_pixmap_with_shadow(source, hot_spot)
    widget._drag_pixmap_cache = {
        "key": key,
        "pixmap": pixmap,
        "hot_spot": hot_spot,
    }
    return pixmap, hot_spot


def prepare_chip_drag_pixmap(widget: QWidget) -> None:
    """
    Pre-build drag feedback while the pointer is held before drag threshold.

    Args:
        widget: Tag chip button under the cursor.
    """
    if widget is None or not widget.isVisible():
        return
    build_chip_drag_pixmap(widget)


def apply_chip_style(
    button: QPushButton,
    branch_key: str,
    depth: int,
    active: bool,
    selected_for_drag: bool = False,
) -> None:
    """
    Apply the unified outline-chip style to any tag library button.

    Args:
        button: Target button widget.
        branch_key: Category name (determines hue).
        depth: Visual depth level (0 = category, 1+ = subtag).
        active: Whether the tag is part of the active filter.
        selected_for_drag: Whether the tag is in the drag selection.
    """
    is_category = depth == 0 and bool(button.property("tagGridCategory"))
    style_key = (branch_key, depth, is_category)
    new_state = "selected" if selected_for_drag else ("active" if active else "")
    cache_key = (str(style_key), new_state)

    if button.property("_styleCacheKey") == str(cache_key):
        _apply_chip_drop_shadow(button, is_category=is_category)
        sync_chip_trace(
            button, new_state, branch_key, depth, is_category=is_category
        )
        return

    font_px = TAG_LIBRARY_FONT_CATEGORY_PX if is_category else TAG_LIBRARY_FONT_SUBTAG_PX
    radius = (
        TAG_LIBRARY_CATEGORY_CHIP_RADIUS_PX
        if is_category
        else TAG_LIBRARY_TAG_CHIP_RADIUS_PX
    )
    is_wrapping = isinstance(button, WrappingDraggableTagButton)
    padding = "0px" if is_wrapping else f"{TAG_LIBRARY_TAG_STYLE_V_PADDING_PX}px 8px"
    font_css = f"font-size: {font_px}px; font-weight: 600; letter-spacing: 0.2px;"

    base = chip_palette(branch_key, depth, is_category=is_category)
    hover = ChipPalette(
        background=base.background_hover,
        background_hover=base.background_hover,
        border=base.border_hover,
        border_hover=base.border_hover,
        text=base.text,
    )
    selected = chip_state_palette(branch_key, depth, selected=True, active=False)
    active_palette = chip_state_palette(branch_key, depth, selected=False, active=True)

    def _block(selector: str, palette: ChipPalette) -> str:
        return (
            f"{selector} {{ padding: {padding}; color: {palette.text}; {font_css} "
            f"background: {palette.background}; border: {palette.border}; "
            f"border-radius: {radius}px; }}\n"
        )

    css = _block("QPushButton", base) + _block("QPushButton:hover", hover)
    if selected is not None:
        sel_hover = ChipPalette(
            background=selected.background_hover,
            background_hover=selected.background_hover,
            border=selected.border_hover,
            border_hover=selected.border_hover,
            text=selected.text,
        )
        css += _block('QPushButton[tagState="selected"]', selected)
        css += _block('QPushButton[tagState="selected"]:hover', sel_hover)
    if active_palette is not None:
        act_hover = ChipPalette(
            background=active_palette.background_hover,
            background_hover=active_palette.background_hover,
            border=active_palette.border_hover,
            border_hover=active_palette.border_hover,
            text=active_palette.text,
        )
        css += _block('QPushButton[tagState="active"]', active_palette)
        css += _block('QPushButton[tagState="active"]:hover', act_hover)

    button.setStyleSheet(css)
    button.setProperty("_styleKey", str(style_key))
    button.setProperty("_styleCacheKey", str(cache_key))
    button.setProperty("tagState", new_state)
    button.setCursor(Qt.PointingHandCursor)

    button.style().unpolish(button)
    button.style().polish(button)

    label_palette = base
    if new_state == "selected" and selected is not None:
        label_palette = selected
    elif new_state == "active" and active_palette is not None:
        label_palette = active_palette

    if isinstance(button, WrappingDraggableTagButton):
        button.apply_label_palette(label_palette.text, font_px)

    _apply_chip_drop_shadow(button, is_category=is_category)
    sync_chip_trace(button, new_state, branch_key, depth, is_category=is_category)
    invalidate_chip_drag_pixmap(button)


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

    def __init__(
        self,
        text: str,
        cell_width: int,
        parent: Optional[QWidget] = None,
        *,
        is_category: bool = False,
    ) -> None:
        """
        Args:
            text: Chip label.
            cell_width: Fixed pixel width to use for the chip.
            parent: Optional parent widget.
            is_category: True for full-width main category header chips.
        """
        super().__init__("", parent)
        if is_category:
            self.setProperty("tagGridCategory", True)
        self._cell_width = 0  # sentinel: 0 forces first set_cell_width to apply
        self._geometry_valid = False
        self._raw_icon: Optional[QIcon] = None
        self._icon_label: Optional[QLabel] = None
        self._label_color = "#e8e4f2"

        self._text_label = QLabel(text)
        self._text_label.setWordWrap(True)
        self._text_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._text_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._text_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        label_font = self.font()
        label_font.setPixelSize(TAG_LIBRARY_FONT_SUBTAG_PX)
        label_font.setWeight(QFont.Weight.DemiBold)
        self._text_label.setFont(label_font)

        self._content_row = QWidget(self)
        self._content_row.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._content_row.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._row_layout = QHBoxLayout(self._content_row)
        self._row_layout.setContentsMargins(0, 0, 0, 0)
        self._row_layout.setSpacing(8)
        self._row_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._ensure_icon_slot()
        self._row_layout.addWidget(self._text_label, 1, Qt.AlignLeft | Qt.AlignVCenter)

        h_pad = TAG_LIBRARY_CHIP_CONTENT_HPAD_PX
        self._inner_layout = QVBoxLayout(self)
        self._inner_layout.setContentsMargins(h_pad, 0, h_pad - 2, 0)
        self._inner_layout.setSpacing(0)
        self._inner_layout.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self._inner_layout.addWidget(self._content_row, 0, Qt.AlignLeft | Qt.AlignVCenter)

        self.setCursor(Qt.PointingHandCursor)
        # Reason: clicking a chip must not steal focus, else the QScrollArea
        # auto-scrolls to the focused widget and the scroll position jumps.
        self.setFocusPolicy(Qt.NoFocus)
        self.set_cell_width(cell_width)

    def resizeEvent(self, event) -> None:
        """Keep trace overlay aligned when the chip is resized."""
        super().resizeEvent(event)
        overlay = self.property("_traceOverlay")
        if overlay is not None:
            overlay.sync_geometry()

    def mouseMoveEvent(self, event) -> None:
        """
        All tag-library drags are handled by MainWindow (ghost, multi-select).
        """
        QPushButton.mouseMoveEvent(self, event)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def apply_label_palette(self, text_color: str, font_px: int) -> None:
        """
        Apply accent colour and size to the internal QLabel (not the QPushButton).

        Args:
            text_color: CSS colour for the label text.
            font_px: Font size in pixels.
        """
        self._label_color = text_color
        self._text_label.setStyleSheet(
            f"color: {text_color}; background: transparent; border: none; "
            f"font-size: {font_px}px; font-weight: 600; letter-spacing: 0.2px;"
        )
        font = self._text_label.font()
        if font.pixelSize() != font_px:
            font.setPixelSize(font_px)
            font.setWeight(QFont.Weight.DemiBold)
            self._text_label.setFont(font)
        if self.property("tagGridCategory"):
            self._text_label.setWordWrap(False)
        self._sync_chip_geometry()

    def _is_category_chip(self) -> bool:
        """Return True for full-width main category header chips."""
        return bool(self.property("tagGridCategory"))

    def _has_icon(self) -> bool:
        """Return True when this chip displays a tag icon."""
        return self._raw_icon is not None and not self._raw_icon.isNull()

    def _icon_slot_px(self) -> int:
        """Return the icon column width (0 when the chip has no icon)."""
        if not self._has_icon():
            return 0
        if self._is_category_chip():
            return TAG_LIBRARY_CATEGORY_ICON_SLOT_PX
        return TAG_LIBRARY_TAG_ICON_SLOT_PX

    def _effective_width(self) -> int:
        """Return the layout width used for internal geometry."""
        return self._cell_width

    def _ensure_icon_slot(self) -> QLabel:
        """
        Ensure a fixed-width icon column exists at the left of the chip.

        Returns:
            QLabel: Icon slot widget (may be empty).
        """
        slot_px = self._icon_slot_px()
        if self._icon_label is None:
            self._icon_label = QLabel(self._content_row)
            self._icon_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            self._icon_label.setAlignment(Qt.AlignCenter)
            self._row_layout.insertWidget(0, self._icon_label, 0, Qt.AlignVCenter)
        self._icon_label.setFixedSize(slot_px, slot_px)
        return self._icon_label

    def set_cell_width(self, width: int, *, min_w: int = TAG_LIBRARY_TAG_CELL_MIN_WIDTH_PX) -> None:
        """
        Set fixed cell width and recompute chip geometry.

        Args:
            width: Target pixel width.
            min_w: Minimum enforced width.
        """
        new_w = max(min_w, width)
        if new_w == self._cell_width and self._geometry_valid and not self._is_category_chip():
            return
        self._cell_width = new_w
        if self._is_category_chip():
            self.setFixedWidth(self._cell_width)
            self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        else:
            self.setFixedWidth(self._cell_width)
            self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setProperty("tagLibraryCell", True)
        self._geometry_valid = True
        invalidate_chip_drag_pixmap(self)
        self._sync_chip_geometry()

    def setText(self, text: str) -> None:
        if self._text_label.text() == text:
            return
        self._text_label.setText(text)
        invalidate_chip_drag_pixmap(self)
        self._sync_chip_geometry()

    def text(self) -> str:
        return self._text_label.text()

    def setIcon(self, icon: QIcon) -> None:
        """Store the untinted source icon; tint follows the label accent colour."""
        self._raw_icon = None if icon.isNull() else QIcon(icon)
        self._ensure_icon_slot()
        if icon.isNull():
            self._icon_label.clear()
        invalidate_chip_drag_pixmap(self)
        self._sync_chip_geometry()

    def setIconSize(self, _size: QSize) -> None:
        """Icon size derives from chip height; external calls are no-ops."""
        self._sync_chip_geometry()

    def sizeHint(self) -> QSize:
        """Stable size hint — never recomputes to avoid layout feedback loops."""
        h = getattr(self, "_chip_height", TAG_LIBRARY_TAG_MIN_HEIGHT_PX)
        return QSize(self._effective_width(), h)

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
            Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignVCenter,
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
        is_category = self._is_category_chip()
        chip_w = self._effective_width()
        chip_h_est = (
            TAG_LIBRARY_CATEGORY_MIN_HEIGHT_PX
            if is_category
            else TAG_LIBRARY_TAG_MIN_HEIGHT_PX
        )
        slot_px = self._icon_slot_px()
        has_icon = slot_px > 0

        margins = self._inner_layout.contentsMargins()
        h_pad = margins.left() + margins.right()
        inner_w = max(24, chip_w - h_pad - border_v - 2)
        row_spacing = self._row_layout.spacing() if has_icon else 0
        text_w = max(20, inner_w - slot_px - row_spacing)

        if is_category:
            self._text_label.setWordWrap(False)
            fm = QFontMetrics(self._text_label.font())
            label_h = fm.height() + 2
        else:
            label_h = self._label_height_for_text(text_w)

        pad_v = TAG_LIBRARY_TAG_STYLE_V_PADDING_PX * 2
        min_h = (
            TAG_LIBRARY_CATEGORY_MIN_HEIGHT_PX
            if is_category
            else TAG_LIBRARY_TAG_MIN_HEIGHT_PX
        )
        chip_h = min(
            TAG_LIBRARY_TAG_MAX_HEIGHT_PX,
            max(min_h, label_h + pad_v + border_v + 4),
        )
        icon_px = min(max(slot_px, 1) - 4, chip_h - border_v - 6) if has_icon else 0
        row_h = max(label_h, slot_px) if has_icon else label_h

        self._text_label.setFixedHeight(label_h)
        if is_category:
            self._text_label.setMinimumWidth(text_w)
            self._text_label.setMaximumWidth(text_w)
        else:
            self._text_label.setFixedWidth(text_w)

        self._content_row.setFixedHeight(row_h)
        self._content_row.setMinimumWidth(inner_w)
        self._content_row.setMaximumWidth(inner_w)

        if has_icon:
            self._ensure_icon_slot()
            self._icon_label.setFixedSize(slot_px, slot_px)
            self._icon_label.show()
            if icon_px > 0:
                tinted = tint_icon(self._raw_icon, QColor(self._label_color), icon_px)
                self._icon_label.setPixmap(tinted.pixmap(icon_px, icon_px))
            else:
                self._icon_label.clear()
        elif self._icon_label is not None:
            self._icon_label.clear()
            self._icon_label.setFixedSize(0, 0)
            self._icon_label.hide()

        self.setFixedHeight(chip_h)
        self._chip_height = chip_h
