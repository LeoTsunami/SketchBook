"""
Helpers to lay out slideshow pixmaps in a fixed scene rect (viewport-sized).

Each pixmap is scaled and centered independently so cross-dissolve between
images of different native sizes does not change the view transform mid-fade.
"""

from qtpy.QtCore import QRectF, Qt
from qtpy.QtGui import QPixmap
from qtpy.QtWidgets import QGraphicsPixmapItem

from gui.thumbnail_fitting import FitMode, compute_fitted_size


def logical_pixmap_size(pixmap: QPixmap) -> tuple[float, float]:
    """
    Return the device-independent (logical) size of a pixmap.

    HQ pixmaps from ``ImageLoaderWorker`` set ``devicePixelRatio``; layout must
    use logical dimensions, not raw pixel buffer width/height.

    Args:
        pixmap: Source pixmap.

    Returns:
        tuple[float, float]: (logical_width, logical_height).
    """
    dpr = pixmap.devicePixelRatio()
    if dpr <= 0:
        dpr = 1.0
    return pixmap.width() / dpr, pixmap.height() / dpr


def scene_display_rect(viewport_width: int, viewport_height: int) -> QRectF:
    """
    Build the fixed scene rectangle matching the viewport in logical pixels.

    Args:
        viewport_width: Viewport width in logical pixels.
        viewport_height: Viewport height in logical pixels.

    Returns:
        QRectF: Scene rect from (0, 0) to (width, height).
    """
    return QRectF(
        0.0, 0.0, float(max(1, viewport_width)), float(max(1, viewport_height))
    )


def display_scale_factor(
    pixmap: QPixmap,
    display_rect: QRectF,
    mode: FitMode = FitMode.FIT_ALL,
) -> float:
    """
    Return the scale factor layout would apply to fit ``pixmap`` in ``display_rect``.

    Values above 1.0 mean the pixmap would be upscaled (risk of pixelation).
    """
    lw, lh = logical_pixmap_size(pixmap)
    if lw <= 0 or lh <= 0:
        return 1.0
    dw, dh = compute_fitted_size(
        int(lw),
        int(lh),
        int(display_rect.width()),
        int(display_rect.height()),
        mode,
    )
    if dw <= 0:
        return 1.0
    return dw / lw


def layout_pixmap_item_in_rect(
    item: QGraphicsPixmapItem,
    pixmap: QPixmap,
    display_rect: QRectF,
    mode: FitMode = FitMode.FIT_ALL,
) -> None:
    """
    Scale and center a pixmap inside ``display_rect`` (KeepAspectRatio fit-all).

    Args:
        item: Graphics item to update.
        pixmap: Source pixmap (may differ from item's current pixmap).
        display_rect: Target area in scene coordinates.
        mode: Fit strategy (session slideshow uses ``FIT_ALL``).
    """
    if pixmap.isNull():
        return

    lw, lh = logical_pixmap_size(pixmap)
    if lw <= 0 or lh <= 0:
        return

    cell_w = int(display_rect.width())
    cell_h = int(display_rect.height())
    dw, dh = compute_fitted_size(int(lw), int(lh), cell_w, cell_h, mode)
    if dw <= 0 or dh <= 0:
        return

    item.setPixmap(pixmap)
    item.setScale(1.0)
    item.setTransformationMode(Qt.SmoothTransformation)
    scale = dw / lw
    item.setScale(scale)
    item.setPos(
        display_rect.x() + (display_rect.width() - dw) / 2.0,
        display_rect.y() + (display_rect.height() - dh) / 2.0,
    )
