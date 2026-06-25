"""Tests for image thumbnail visual state helpers."""

from gui.image_thumbnail import ImageThumbnail


def test_thumbnail_selection_property_updates(qtbot):
    """Selection flag should update dynamic property used by QSS."""
    thumb = ImageThumbnail("img_1", "label")
    qtbot.addWidget(thumb)
    thumb.set_selected(True)
    assert thumb.property("selected") is True
    thumb.set_selected(False)
    assert thumb.property("selected") is False


def test_thumbnail_hover_updates_brightness(qtbot):
    """Hover enter/leave should toggle subtle brightness effect."""
    thumb = ImageThumbnail("img_1", "label")
    qtbot.addWidget(thumb)
    thumb._set_hovered(True)
    assert thumb.property("hovered") is True
    assert thumb._hover_effect.strength() > 0.0
    thumb._set_hovered(False)
    assert thumb.property("hovered") is False
    assert thumb._hover_effect.strength() == 0.0
