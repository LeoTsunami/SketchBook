"""
Floating widget that shows tag chips below a hovered thumbnail.
Displays full tag names (no elision) so all tags are readable.
"""
from typing import Callable, Optional, Set

from qtpy.QtWidgets import QFrame, QGridLayout, QWidget
from qtpy.QtCore import Qt

from gui.image_thumbnail import TagChip


class TagHoverPopover(QFrame):
    """
    Small floating panel shown below a thumbnail on hover.
    Shows all tags for that image with full text; chips can remove tags.
    """

    GAP_BELOW_THUMB = 4
    MAX_ROWS = 2  # Popover shows at most 2 lines of tag chips
    MIN_WIDTH = 180

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TagHoverPopover")
        self.setWindowFlags(Qt.Widget)
        self.setStyleSheet("""
            QFrame#TagHoverPopover {
                background-color: rgba(35, 35, 35, 0.72);
                border: 1px solid rgba(100, 100, 100, 0.5);
                border-radius: 6px;
            }
        """)
        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(6, 6, 6, 6)
        self._layout.setSpacing(4)
        self._chips: dict = {}  # tag -> TagChip
        self._image_id: Optional[str] = None
        self._remove_tag_callback: Optional[Callable[[str], None]] = None
        self._anchor_thumbnail: Optional[QWidget] = None
        self._viewport: Optional[QWidget] = None
        self._stack_under_widget: Optional[QWidget] = None
        self.hide()

    def show_below(
        self,
        thumbnail: QWidget,
        viewport: QWidget,
        tags: Set[str],
        image_id: str,
        remove_tag_callback: Callable[[str], None],
    ) -> None:
        """
        Position the popover below the thumbnail and fill it with tag chips (full text).

        Args:
            thumbnail: The thumbnail widget (child of content).
            viewport: The scroll viewport; popover is positioned in viewport coords.
            tags: Set of tag names to display.
            image_id: Image ID for this thumbnail.
            remove_tag_callback: Called when a tag is removed from a chip.
        """
        self._image_id = image_id
        self._remove_tag_callback = remove_tag_callback

        # Position: thumbnail's (0,0) mapped to viewport, then below
        top_left = thumbnail.mapTo(viewport, thumbnail.rect().bottomLeft())
        x = top_left.x()
        y = top_left.y() + self.GAP_BELOW_THUMB

        # Clear previous chips
        self._clear_chips()

        if not tags:
            self._anchor_thumbnail = None
            self._viewport = None
            self.hide()
            return

        self._anchor_thumbnail = thumbnail
        self._viewport = viewport

        # Build chips with full text (no elision)
        for tag in sorted(tags):
            chip = TagChip(tag, self, elide=False)
            chip.removed.connect(self._on_chip_removed)
            self._chips[tag] = chip

        # Layout chips on at most MAX_ROWS lines (e.g. 2 lines)
        n = len(self._chips)
        chips_per_row = max(1, (n + self.MAX_ROWS - 1) // self.MAX_ROWS)
        row, col = 0, 0
        for tag in sorted(self._chips.keys()):
            if row >= self.MAX_ROWS:
                break
            chip = self._chips[tag]
            self._layout.addWidget(chip, row, col)
            col += 1
            if col >= chips_per_row:
                col = 0
                row += 1

        self._apply_geometry(thumbnail, viewport, x, y)
        self.show()
        self._raise_with_z_order()

    def set_stack_under_widget(self, widget: Optional[QWidget]) -> None:
        """Keep this popover below ``widget`` in stacking order (e.g. Start session button)."""
        self._stack_under_widget = widget

    def refresh_position(self) -> None:
        """Recompute position from the anchored thumbnail (call on scroll/resize)."""
        if not self.isVisible() or not self._chips:
            return
        thumb = self._anchor_thumbnail
        vp = self._viewport
        if thumb is None or vp is None:
            return
        if not thumb.isVisible():
            self.hide_popover()
            return
        top_left = thumb.mapTo(vp, thumb.rect().bottomLeft())
        x = top_left.x()
        y = top_left.y() + self.GAP_BELOW_THUMB
        self._apply_geometry(thumb, vp, x, y)
        self._raise_with_z_order()

    def _apply_geometry(
        self, thumbnail: QWidget, viewport: QWidget, x: int, y: int
    ) -> None:
        """Set size and clamped position inside the viewport."""
        w = max(thumbnail.width(), self.MIN_WIDTH)
        self.setMinimumWidth(w)
        self.adjustSize()

        pw, ph = self.width(), self.height()
        if x + pw > viewport.width():
            x = viewport.width() - pw
        if x < 0:
            x = 0
        if y + ph > viewport.height():
            y = viewport.height() - ph
        if y < 0:
            y = 0

        self.setGeometry(x, y, pw, ph)

    def _raise_with_z_order(self) -> None:
        """Raise above grid content but below optional sibling (e.g. session button)."""
        self.raise_()
        if self._stack_under_widget is not None:
            self.stackUnder(self._stack_under_widget)

    def _clear_chips(self) -> None:
        """Remove all tag chips from the popover."""
        for chip in self._chips.values():
            chip.removed.disconnect(self._on_chip_removed)
            chip.deleteLater()
        self._chips.clear()
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                self._layout.removeWidget(item.widget())

    def _on_chip_removed(self, tag: str) -> None:
        """Handle tag removal from a chip: run callback and remove chip from popover (DB refresh later)."""
        if self._remove_tag_callback:
            self._remove_tag_callback(tag)
        if tag in self._chips:
            chip = self._chips.pop(tag)
            chip.deleteLater()
            self._relayout_chips()
        if not self._chips:
            self._anchor_thumbnail = None
            self._viewport = None
            self.hide()

    def _relayout_chips(self) -> None:
        """Re-add remaining chips to the grid (at most MAX_ROWS lines)."""
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                self._layout.removeWidget(item.widget())
        n = len(self._chips)
        chips_per_row = max(1, (n + self.MAX_ROWS - 1) // self.MAX_ROWS)
        row, col = 0, 0
        for tag in sorted(self._chips.keys()):
            if row >= self.MAX_ROWS:
                break
            self._layout.addWidget(self._chips[tag], row, col)
            col += 1
            if col >= chips_per_row:
                col = 0
                row += 1
        self.adjustSize()

    def hide_popover(self) -> None:
        """Hide and clear the popover (e.g. when hover moves to another image)."""
        self._clear_chips()
        self._image_id = None
        self._anchor_thumbnail = None
        self._viewport = None
        self.hide()
