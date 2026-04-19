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
    """Hover enter/leave should toggle subtle brightness effect and enable/disable it."""
    thumb = ImageThumbnail("img_1", "label")
    qtbot.addWidget(thumb)

    assert not thumb._hover_effect.isEnabled(), "effect must start disabled"

    thumb._set_hovered(True)
    assert thumb.property("hovered") is True
    assert thumb._hover_effect.strength() > 0.0
    assert thumb._hover_effect.isEnabled(), "effect must be enabled while hovered"

    thumb._set_hovered(False)
    assert thumb.property("hovered") is False
    assert thumb._hover_effect.strength() == 0.0
    assert not thumb._hover_effect.isEnabled(), "effect must be disabled after leave"


def test_hover_switch_disables_first_effect(qtbot):
    """When hover moves from thumb A to thumb B, A's effect must be disabled (scroll-fix bug)."""
    thumb_a = ImageThumbnail("img_a", "A")
    thumb_b = ImageThumbnail("img_b", "B")
    qtbot.addWidget(thumb_a)
    qtbot.addWidget(thumb_b)

    thumb_a._set_hovered(True)
    assert thumb_a._hover_effect.isEnabled()

    thumb_a._set_hovered(False)
    thumb_b._set_hovered(True)

    assert not thumb_a._hover_effect.isEnabled(), (
        "previous thumbnail's effect must be disabled to avoid stale scroll cache"
    )
    assert thumb_b._hover_effect.isEnabled()


def test_hover_effect_idempotent(qtbot):
    """Calling _set_hovered with same value twice should be a no-op."""
    thumb = ImageThumbnail("img_1", "label")
    qtbot.addWidget(thumb)

    thumb._set_hovered(True)
    thumb._set_hovered(True)
    assert thumb._hover_effect.isEnabled()
    assert thumb._hover_effect.strength() == 0.10

    thumb._set_hovered(False)
    thumb._set_hovered(False)
    assert not thumb._hover_effect.isEnabled()
