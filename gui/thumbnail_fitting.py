"""
Unified image fitting logic for grid thumbnails.

This module is the single source of truth for how images are displayed
inside grid cells. It supports four user-selectable display modes and
handles re-fitting on resize so images always look correct.

Usage
-----
Call ``fit_pixmap_in_view`` whenever the displayed pixmap or view size
changes:  ``set_image()``, ``resizeEvent()``, relayout, etc.

Call ``compute_fitted_size`` when you need the logical (w, h) of the
image *as it will appear* inside a cell, without actually touching a view.
"""

from __future__ import annotations

from enum import IntEnum

from qtpy.QtCore import Qt, QRectF
from qtpy.QtGui import QPixmap
from qtpy.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem


class FitMode(IntEnum):
    """Image-to-cell display strategy chosen by the user."""

    FIT_ALL = 0      # Entire image visible, no crop (may have bars)
    FIT_HEIGHT = 1   # Fill cell height, width may overflow/crop
    FIT_WIDTH = 2    # Fill cell width, height may overflow/crop
    CROP_ALL = 3     # Fill entire cell, crop excess on both axes

    @classmethod
    def labels(cls) -> list[str]:
        """Combo-box display labels in enum order.

        Returns:
            List of human-readable labels.
        """
        return ["Fit All", "Fit Height", "Fit Width", "Crop All"]


def fit_pixmap_in_view(
    view: QGraphicsView,
    scene: QGraphicsScene,
    pixmap_item: QGraphicsPixmapItem | None,
    mode: FitMode = FitMode.FIT_ALL,
) -> None:
    """
    Scale and position a pixmap inside a QGraphicsView according to *mode*.

    Args:
        view: The target QGraphicsView.
        scene: The QGraphicsScene that owns *pixmap_item*.
        pixmap_item: The QGraphicsPixmapItem to fit; ``None`` is a no-op.
        mode: Display strategy (default ``FIT_ALL``).
    """
    if pixmap_item is None or scene is None or view is None:
        return

    rect = pixmap_item.boundingRect()
    if rect.isEmpty():
        return

    scene.setSceneRect(rect)

    if mode == FitMode.FIT_ALL:
        view.fitInView(rect, Qt.KeepAspectRatio)

    elif mode == FitMode.CROP_ALL:
        # Reason: KeepAspectRatioByExpanding scales so the *shorter* axis
        # fills the view; the other axis overflows and gets clipped — this
        # is the classic "cover / crop" behavior.
        view.fitInView(rect, Qt.KeepAspectRatioByExpanding)
        view.centerOn(rect.center())

    elif mode == FitMode.FIT_WIDTH:
        _fit_one_axis(view, rect, match_width=True)

    elif mode == FitMode.FIT_HEIGHT:
        _fit_one_axis(view, rect, match_width=False)


def _fit_one_axis(
    view: QGraphicsView,
    rect: QRectF,
    *,
    match_width: bool,
) -> None:
    """
    Scale so one axis fills the view exactly; the other axis may overflow.

    Args:
        view: Target view.
        rect: Scene rectangle of the pixmap item.
        match_width: If True, match the view width (height may crop).
                     If False, match the view height (width may crop).
    """
    vw = view.viewport().width()
    vh = view.viewport().height()
    if vw <= 0 or vh <= 0 or rect.width() <= 0 or rect.height() <= 0:
        return

    if match_width:
        scale = vw / rect.width()
    else:
        scale = vh / rect.height()

    view.resetTransform()
    view.scale(scale, scale)
    view.centerOn(rect.center())


def compute_fitted_size(
    image_width: int,
    image_height: int,
    cell_width: int,
    cell_height: int,
    mode: FitMode = FitMode.FIT_ALL,
) -> tuple[int, int]:
    """
    Compute the display size of an image fitted inside a cell.

    Args:
        image_width: Source image width in pixels.
        image_height: Source image height in pixels.
        cell_width: Available cell width in pixels.
        cell_height: Available cell height in pixels.
        mode: Display strategy.

    Returns:
        (display_width, display_height) — visible portion in pixels.
        For FIT_ALL this is always <= cell; for crop modes it equals cell.
    """
    if image_width <= 0 or image_height <= 0:
        return (0, 0)
    if cell_width <= 0 or cell_height <= 0:
        return (0, 0)

    img_r = image_width / image_height
    cell_r = cell_width / cell_height

    if mode == FitMode.FIT_ALL:
        if img_r > cell_r:
            dw = cell_width
            dh = int(cell_width / img_r)
        else:
            dh = cell_height
            dw = int(cell_height * img_r)
        return (max(1, dw), max(1, dh))

    if mode == FitMode.CROP_ALL:
        return (cell_width, cell_height)

    if mode == FitMode.FIT_WIDTH:
        dw = cell_width
        dh = int(cell_width / img_r)
        return (max(1, dw), max(1, min(dh, cell_height)))

    if mode == FitMode.FIT_HEIGHT:
        dh = cell_height
        dw = int(cell_height * img_r)
        return (max(1, min(dw, cell_width)), max(1, dh))

    return (cell_width, cell_height)
