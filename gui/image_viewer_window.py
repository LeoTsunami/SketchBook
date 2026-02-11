"""
Window for displaying a single image in large size with zoom.
"""
from typing import Optional, List, Callable
from qtpy.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QFrame,
    QPushButton,
    QMessageBox,
)
from qtpy.QtCore import Qt, QRectF, QRect, QPointF, QTimer, QEvent
from qtpy.QtGui import (
    QPixmap,
    QWheelEvent,
    QTransform,
    QPainter,
    QPen,
    QColor,
    QBrush,
)
from core.image_manager import ImageManager
from PIL import Image

# Minimum crop size in scene pixels
CROP_MIN_SIZE = 20


class CropHandleItem(QGraphicsEllipseItem):
    """
    Draggable corner handle for crop rectangle.
    On press calls on_press(handle_index) so the view can capture drag in viewport.
    on_moved(handle_index, scene_pos) is called from viewport event filter during drag.
    """

    def __init__(
        self,
        handle_index: int,
        on_moved: Callable[[int, QPointF], None],
        on_press: Callable[[int], None],
        parent=None,
    ):
        # Radius 8 in scene coords; pos will be set so center is at corner
        r = 8
        super().__init__(-r, -r, 2 * r, 2 * r, parent)
        self._handle_index = handle_index
        self._on_moved = on_moved
        self._on_press = on_press
        self.setPen(QPen(QColor(255, 255, 255), 2))
        self.setBrush(QBrush(QColor(60, 60, 60, 200)))
        self.setZValue(10_002)
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self.setCursor(Qt.SizeFDiagCursor if handle_index in (0, 2) else Qt.SizeBDiagCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._on_press(self._handle_index)
        super().mousePressEvent(event)


class ZoomGraphicsView(QGraphicsView):
    """Graphics view that zooms with mouse wheel."""

    ZOOM_STEP = 1.15
    MIN_ZOOM = 0.1
    MAX_ZOOM = 20.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_scale = 1.0
        self._pixmap_item_ref: Optional[QGraphicsPixmapItem] = None

    def set_pixmap_item_ref(self, item):
        """Reference to the pixmap item for fitInView and zoom."""
        self._pixmap_item_ref = item

    def wheelEvent(self, event: QWheelEvent):
        """Zoom in/out with mouse wheel."""
        if self._pixmap_item_ref is None:
            super().wheelEvent(event)
            return
        delta = event.angleDelta().y()
        if delta == 0:
            super().wheelEvent(event)
            return
        factor = self.ZOOM_STEP if delta > 0 else 1.0 / self.ZOOM_STEP
        new_scale = self._current_scale * factor
        new_scale = max(self.MIN_ZOOM, min(self.MAX_ZOOM, new_scale))
        self._current_scale = new_scale
        transform = QTransform()
        transform.scale(new_scale, new_scale)
        self.setTransform(transform)
        event.accept()

    def fit_image(self):
        """Fit the image in view and sync scale."""
        if self._pixmap_item_ref is None:
            return
        self.fitInView(self._pixmap_item_ref, Qt.KeepAspectRatio)
        self._current_scale = self.transform().m11()

    def get_scale(self):
        return self._current_scale

    def set_scale(self, scale: float):
        self._current_scale = scale


class ImageViewerWindow(QMainWindow):
    """Window that displays a single image at screen size with zoom in/out."""

    def __init__(self, image_manager: ImageManager, parent=None):
        """
        Initialize the viewer window.

        Args:
            image_manager: ImageManager instance to resolve image paths.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.image_manager = image_manager
        self.setWindowTitle("Image")
        self.setMinimumSize(400, 300)
        # Start maximized so image is "screen size"
        self.showMaximized()

        self._image_ids: List[str] = []
        self._current_index: int = -1
        self._current_image_id: Optional[str] = None

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Center area: < button | image | > button
        center_row = QWidget()
        center_layout = QHBoxLayout(center_row)
        center_layout.setContentsMargins(8, 8, 8, 8)
        center_layout.setSpacing(8)

        self.prev_button = QPushButton("<")
        self.prev_button.setFixedWidth(40)
        self.prev_button.clicked.connect(self.show_previous_image)
        center_layout.addWidget(self.prev_button)

        self.graphics_view = ZoomGraphicsView(self)
        self.graphics_view.setRenderHint(QPainter.SmoothPixmapTransform)
        self.graphics_view.setDragMode(QGraphicsView.ScrollHandDrag)
        self.graphics_view.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.graphics_view.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.graphics_view.setFrameShape(QFrame.NoFrame)

        self.scene = QGraphicsScene()
        self.graphics_view.setScene(self.scene)
        self.pixmap_item: Optional[QGraphicsPixmapItem] = None

        center_layout.addWidget(self.graphics_view, 1)

        self.next_button = QPushButton(">")
        self.next_button.setFixedWidth(40)
        self.next_button.clicked.connect(self.show_next_image)
        center_layout.addWidget(self.next_button)

        main_layout.addWidget(center_row)

        # Bottom controls: centered rotate/crop
        controls = QWidget()
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(8, 4, 8, 4)
        controls_layout.setSpacing(8)

        controls_layout.addStretch()

        self.rotate_ccw_button = QPushButton("Rotate ⟲")
        self.rotate_ccw_button.clicked.connect(lambda: self._rotate_current(clockwise=False))
        controls_layout.addWidget(self.rotate_ccw_button)

        self.rotate_cw_button = QPushButton("Rotate ⟳")
        self.rotate_cw_button.clicked.connect(lambda: self._rotate_current(clockwise=True))
        controls_layout.addWidget(self.rotate_cw_button)

        self.crop_button = QPushButton("Crop")
        self.crop_button.clicked.connect(self._enter_crop_mode)
        controls_layout.addWidget(self.crop_button)

        self.crop_validate_button = QPushButton("Valider")
        self.crop_validate_button.clicked.connect(self._apply_crop)
        self.crop_validate_button.hide()

        self.crop_cancel_button = QPushButton("Annuler")
        self.crop_cancel_button.clicked.connect(self._cancel_crop)
        self.crop_cancel_button.hide()

        controls_layout.addWidget(self.crop_validate_button)
        controls_layout.addWidget(self.crop_cancel_button)

        controls_layout.addStretch()

        main_layout.addWidget(controls)

        # Crop mode overlay (rule-of-thirds grid + 4 draggable corners)
        self._crop_mode = False
        self._crop_rect: Optional[QRectF] = None
        self._crop_rect_item: Optional[QGraphicsRectItem] = None
        self._crop_grid_lines: List[QGraphicsLineItem] = []
        self._crop_handles: List[CropHandleItem] = []
        self._prev_drag_mode = self.graphics_view.dragMode()
        # When dragging a handle, viewport event filter drives move; release clears this
        self._crop_drag_handle_index: Optional[int] = None

    def _ensure_sequence_from_grid(self, current_id: str) -> None:
        """
        Ensure we have the current image sequence from the parent ImageGrid.

        The sequence matches the current visible order in the grid so that
        Previous/Next navigation is intuitive for the user.
        """
        parent = self.parent()
        grid = None
        while parent is not None:
            if hasattr(parent, "image_grid"):
                grid = getattr(parent, "image_grid")
                break
            parent = parent.parent()
        if grid is not None and hasattr(grid, "all_images"):
            self._image_ids = [m.id for m in grid.all_images]
        else:
            self._image_ids = [current_id]
        try:
            self._current_index = self._image_ids.index(current_id)
        except ValueError:
            self._current_index = -1

    def set_image(self, image_id: str) -> bool:
        """
        Load and display the image for the given ID.

        Args:
            image_id: ID of the image (metadata id / file stem).

        Returns:
            True if the image was loaded and displayed, False otherwise.
        """
        # Initialize navigation sequence from grid so Previous/Next work
        self._ensure_sequence_from_grid(image_id)
        self._current_image_id = image_id
        return self._load_current_image()

    def _load_current_image(self) -> bool:
        """Internal helper to load and display the current image id."""
        if not self._current_image_id:
            return False
        metadata = self.image_manager.get_image_metadata(self._current_image_id)
        if not metadata:
            return False
        path = self.image_manager.image_dir / metadata.path
        if not path.exists():
            return False

        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            return False

        self.scene.clear()
        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.pixmap_item.setTransformationMode(Qt.SmoothTransformation)
        self.scene.addItem(self.pixmap_item)
        self.scene.setSceneRect(QRectF(pixmap.rect()))

        self.graphics_view.set_pixmap_item_ref(self.pixmap_item)
        self.setWindowTitle(metadata.original_filename)

        # Fit image after the window/layout has had a chance to resize,
        # so the first open uses the full available size as well.
        QTimer.singleShot(0, self.graphics_view.fit_image)
        return True

    def show_previous_image(self) -> None:
        """Show the previous image in the current sequence."""
        if not self._image_ids or self._current_index <= 0:
            return
        self._current_index -= 1
        self._current_image_id = self._image_ids[self._current_index]
        self._load_current_image()

    def show_next_image(self) -> None:
        """Show the next image in the current sequence."""
        if not self._image_ids or self._current_index < 0:
            return
        if self._current_index >= len(self._image_ids) - 1:
            return
        self._current_index += 1
        self._current_image_id = self._image_ids[self._current_index]
        self._load_current_image()

    def _rotate_current(self, clockwise: bool) -> None:
        """Rotate the current image 90° clockwise or counterclockwise and reload it."""
        if not self._current_image_id:
            return
        success = self.image_manager.rotate_image(self._current_image_id, clockwise=clockwise)
        if not success:
            QMessageBox.warning(self, "Rotate image", "Could not rotate the image on disk.")
            return
        # Reload image with updated orientation
        self._load_current_image()

    def _image_scene_rect(self) -> QRectF:
        """Return the image bounds in scene coordinates (for clamping crop)."""
        if self.pixmap_item is None:
            return QRectF()
        return self.pixmap_item.sceneBoundingRect()

    def _enter_crop_mode(self) -> None:
        """
        Enter crop mode: show rule-of-thirds grid and 4 draggable corner handles.
        Crop rect starts as the full image; user adjusts corners then Valider or Annuler.
        """
        if not self._current_image_id or self.pixmap_item is None:
            return
        self._crop_mode = True
        self._crop_drag_handle_index = None
        # Disable panning so dragging works on corner handles
        self._prev_drag_mode = self.graphics_view.dragMode()
        self.graphics_view.setDragMode(QGraphicsView.NoDrag)
        # Capture move/release at viewport so we get drag even when cursor leaves the handle
        self.graphics_view.viewport().installEventFilter(self)
        self._crop_rect = self._image_scene_rect()
        if self._crop_rect.isEmpty():
            self._crop_mode = False
            self.graphics_view.viewport().removeEventFilter(self)
            self.graphics_view.setDragMode(self._prev_drag_mode)
            return

        self._ensure_crop_overlay_items()
        self._update_crop_overlay()
        self._show_crop_buttons(True)

    def _exit_crop_mode(self) -> None:
        """Leave crop mode: remove overlay items from scene and show normal toolbar."""
        self._crop_mode = False
        self._crop_drag_handle_index = None
        self.graphics_view.viewport().removeEventFilter(self)
        # Restore previous drag mode (panning) for normal navigation
        self.graphics_view.setDragMode(self._prev_drag_mode)
        self._hide_crop_overlay()
        # Remove overlay items so they are not left as stale refs after scene.clear()
        if self._crop_rect_item is not None and self.scene is not None:
            self.scene.removeItem(self._crop_rect_item)
            self._crop_rect_item = None
        for line in self._crop_grid_lines:
            if self.scene is not None:
                self.scene.removeItem(line)
        self._crop_grid_lines = []
        for handle in self._crop_handles:
            if self.scene is not None:
                self.scene.removeItem(handle)
        self._crop_handles = []
        self._show_crop_buttons(False)

    def _ensure_crop_overlay_items(self) -> None:
        """Create crop rect, grid lines and 4 handle items once."""
        if self._crop_rect_item is not None:
            return
        pen = QPen(QColor(255, 255, 255, 200), 2)
        self._crop_rect_item = QGraphicsRectItem()
        self._crop_rect_item.setPen(pen)
        self._crop_rect_item.setBrush(QBrush(QColor(0, 0, 0, 0)))
        self._crop_rect_item.setZValue(10_000)
        # Let mouse events pass through the rect to the corner handles
        self._crop_rect_item.setAcceptedMouseButtons(Qt.NoButton)
        self.scene.addItem(self._crop_rect_item)

        grid_pen = QPen(QColor(255, 255, 255, 150), 1)
        self._crop_grid_lines = []
        for _ in range(4):
            line = QGraphicsLineItem()
            line.setPen(grid_pen)
            line.setZValue(10_001)
            # Lines are visual only; do not steal mouse events
            line.setAcceptedMouseButtons(Qt.NoButton)
            self.scene.addItem(line)
            self._crop_grid_lines.append(line)

        for i in range(4):
            handle = CropHandleItem(
                i,
                self._on_crop_handle_moved,
                on_press=self._start_crop_handle_drag,
            )
            self.scene.addItem(handle)
            self._crop_handles.append(handle)

    def _update_crop_overlay(self) -> None:
        """Refresh crop rect, rule-of-thirds grid and handle positions from _crop_rect."""
        if self._crop_rect is None or self._crop_rect_item is None:
            return
        r = self._crop_rect
        self._crop_rect_item.setRect(r)
        self._crop_rect_item.show()

        x1, y1, x2, y2 = r.left(), r.top(), r.right(), r.bottom()
        dx = (x2 - x1) / 3.0
        dy = (y2 - y1) / 3.0
        self._crop_grid_lines[0].setLine(x1 + dx, y1, x1 + dx, y2)
        self._crop_grid_lines[1].setLine(x1 + 2 * dx, y1, x1 + 2 * dx, y2)
        self._crop_grid_lines[2].setLine(x1, y1 + dy, x2, y1 + dy)
        self._crop_grid_lines[3].setLine(x1, y1 + 2 * dy, x2, y1 + 2 * dy)
        for line in self._crop_grid_lines:
            line.show()

        # Handles at corners: 0=top-left, 1=top-right, 2=bottom-right, 3=bottom-left
        corners = [r.topLeft(), r.topRight(), r.bottomRight(), r.bottomLeft()]
        for i, handle in enumerate(self._crop_handles):
            handle.setPos(corners[i])
            handle.show()

    def _hide_crop_overlay(self) -> None:
        """Hide crop rect, grid and handles."""
        if self._crop_rect_item is not None:
            self._crop_rect_item.hide()
        for line in self._crop_grid_lines:
            line.hide()
        for handle in self._crop_handles:
            handle.hide()

    def _show_crop_buttons(self, show: bool) -> None:
        """Show/hide Valider and Annuler; hide/show Rotate and Crop."""
        self.rotate_ccw_button.setVisible(not show)
        self.rotate_cw_button.setVisible(not show)
        self.crop_button.setVisible(not show)
        self.crop_validate_button.setVisible(show)
        self.crop_cancel_button.setVisible(show)

    def _start_crop_handle_drag(self, handle_index: int) -> None:
        """Called by CropHandleItem on press; viewport event filter will drive move until release."""
        self._crop_drag_handle_index = handle_index

    def eventFilter(self, obj, event):
        """
        When in crop mode and a handle was pressed, capture move/release on the viewport
        so we get drag events even when the cursor leaves the small handle circle.
        """
        if obj is not self.graphics_view.viewport():
            return super().eventFilter(obj, event)
        if not self._crop_mode or self._crop_drag_handle_index is None:
            return super().eventFilter(obj, event)
        t = event.type()
        if t == QEvent.MouseMove and (event.buttons() & Qt.LeftButton):
            scene_pos = self.graphics_view.mapToScene(event.pos())
            self._on_crop_handle_moved(self._crop_drag_handle_index, scene_pos)
            return True
        if t == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            self._crop_drag_handle_index = None
            return False
        return super().eventFilter(obj, event)

    def _on_crop_handle_moved(self, handle_index: int, scene_pos: QPointF) -> None:
        """
        Update crop rect when a corner handle is dragged.
        handle_index: 0=top-left, 1=top-right, 2=bottom-right, 3=bottom-left.
        """
        if self._crop_rect is None:
            return
        bounds = self._image_scene_rect()
        x = max(bounds.left(), min(bounds.right(), scene_pos.x()))
        y = max(bounds.top(), min(bounds.bottom(), scene_pos.y()))

        r = self._crop_rect
        left, right = r.left(), r.right()
        top, bottom = r.top(), r.bottom()
        if handle_index == 0:
            left = min(x, right - CROP_MIN_SIZE)
            top = min(y, bottom - CROP_MIN_SIZE)
        elif handle_index == 1:
            right = max(x, left + CROP_MIN_SIZE)
            top = min(y, bottom - CROP_MIN_SIZE)
        elif handle_index == 2:
            right = max(x, left + CROP_MIN_SIZE)
            bottom = max(y, top + CROP_MIN_SIZE)
        else:
            left = min(x, right - CROP_MIN_SIZE)
            bottom = max(y, top + CROP_MIN_SIZE)

        self._crop_rect = QRectF(QPointF(left, top), QPointF(right, bottom)).normalized()
        self._update_crop_overlay()

    def _apply_crop(self) -> None:
        """Validate crop: apply crop to image on disk and exit crop mode."""
        if not self._crop_mode or self._crop_rect is None or not self._current_image_id:
            return
        crop_rect_scene = self._crop_rect
        if crop_rect_scene.width() < CROP_MIN_SIZE or crop_rect_scene.height() < CROP_MIN_SIZE:
            QMessageBox.information(
                self,
                "Crop image",
                "Crop area is too small. Drag the corners to select a larger region.",
            )
            return

        confirm = QMessageBox.question(
            self,
            "Confirm crop",
            "Are you sure you want to crop this image?\n\nThis will overwrite the original file on disk.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        metadata = self.image_manager.get_image_metadata(self._current_image_id)
        if not metadata:
            return
        path = self.image_manager.image_dir / metadata.path
        if not path.exists():
            QMessageBox.warning(self, "Crop image", "Image file not found on disk.")
            self._exit_crop_mode()
            return

        x1 = max(0, int(crop_rect_scene.left()))
        y1 = max(0, int(crop_rect_scene.top()))
        x2 = min(metadata.width, int(crop_rect_scene.right()))
        y2 = min(metadata.height, int(crop_rect_scene.bottom()))
        if x2 - x1 < 10 or y2 - y1 < 10:
            QMessageBox.information(
                self,
                "Crop image",
                "Crop area is too small. Please select a larger region.",
            )
            return

        try:
            with Image.open(path) as img:
                w, h = img.size
                x1_clamped = max(0, min(w - 1, x1))
                y1_clamped = max(0, min(h - 1, y1))
                x2_clamped = max(x1_clamped + 1, min(w, x2))
                y2_clamped = max(y1_clamped + 1, min(h, y2))
                cropped = img.crop((x1_clamped, y1_clamped, x2_clamped, y2_clamped))
                fmt = (metadata.format or "jpg").upper()
                if fmt in ("JPG", "JPEG"):
                    if cropped.mode in ("RGBA", "P"):
                        cropped = cropped.convert("RGB")
                    cropped.save(path, format="JPEG", quality=95)
                else:
                    cropped.save(path, format="PNG")
                new_w, new_h = cropped.size
        except Exception as exc:  # pylint: disable=broad-except
            QMessageBox.critical(
                self,
                "Crop image",
                f"Error while cropping image:\n{exc}",
            )
            return

        try:
            file_size = path.stat().st_size
        except OSError:
            file_size = metadata.file_size
        self.image_manager.update_image_metadata(
            self._current_image_id,
            width=new_w,
            height=new_h,
            file_size=file_size,
        )
        self._exit_crop_mode()
        self._load_current_image()

    def _cancel_crop(self) -> None:
        """Cancel crop mode without saving."""
        self._exit_crop_mode()
