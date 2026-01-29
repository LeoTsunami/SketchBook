"""
Window for displaying a single image in large size with zoom.
"""
from typing import Optional
from qtpy.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QFrame,
)
from qtpy.QtCore import Qt, QRectF
from qtpy.QtGui import QPixmap, QWheelEvent, QTransform, QPainter
from core.image_manager import ImageManager


class ZoomGraphicsView(QGraphicsView):
    """Graphics view that zooms with mouse wheel."""

    ZOOM_STEP = 1.15
    MIN_ZOOM = 0.1
    MAX_ZOOM = 20.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_scale = 1.0
        self._pixmap_item_ref = None  # Set by parent to track current item

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

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

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

        layout.addWidget(self.graphics_view)

    def set_image(self, image_id: str) -> bool:
        """
        Load and display the image for the given ID.

        Args:
            image_id: ID of the image (metadata id / file stem).

        Returns:
            True if the image was loaded and displayed, False otherwise.
        """
        metadata = self.image_manager.get_image_metadata(image_id)
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
        self.graphics_view.fit_image()
        return True
