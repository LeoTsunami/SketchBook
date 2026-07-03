"""Tests for image thumbnail visual state helpers."""

from qtpy.QtCore import Qt
from qtpy.QtGui import QPixmap

from gui.image_thumbnail import ImageThumbnail
from gui.thumbnail_fitting import FitMode


def test_thumbnail_selection_property_updates(qtbot):
    """Selection flag should update dynamic property used by QSS."""
    thumb = ImageThumbnail("img_1", "label")
    qtbot.addWidget(thumb)
    thumb.set_selected(True)
    assert thumb.property("selected") is True
    thumb.set_selected(False)
    assert thumb.property("selected") is False


def test_thumbnail_hover_updates_property(qtbot):
    """Hover enter/leave should toggle the hovered dynamic property."""
    thumb = ImageThumbnail("img_1", "label")
    qtbot.addWidget(thumb)
    thumb._set_hovered(True)
    assert thumb.property("hovered") is True
    thumb._set_hovered(False)
    assert thumb.property("hovered") is False


def test_apply_outer_geometry_refits_after_cell_resize(qtbot):
    """Changing cell size must re-fit the pixmap (e.g. after column count changes)."""
    thumb = ImageThumbnail("img_1", "label")
    qtbot.addWidget(thumb)
    thumb.set_fit_mode(FitMode.CROP_ALL)
    thumb.show()

    pixmap = QPixmap(400, 200)
    pixmap.fill(Qt.red)
    thumb.set_image(pixmap)

    thumb.apply_outer_geometry(300, 200)
    transform_narrow = thumb.graphics_view.transform()

    thumb.apply_outer_geometry(150, 200)
    transform_wide = thumb.graphics_view.transform()

    assert thumb.graphics_view.viewport().width() == 150
    assert transform_narrow.m11() != transform_wide.m11()
