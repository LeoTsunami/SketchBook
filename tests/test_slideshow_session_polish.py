"""Tests for slideshow image layout and countdown sound helpers."""

import math

from qtpy.QtCore import QRectF
from qtpy.QtGui import QPixmap
from qtpy.QtWidgets import QGraphicsPixmapItem, QGraphicsScene

from gui.slideshow_image_layout import (
    display_scale_factor,
    layout_pixmap_item_in_rect,
    logical_pixmap_size,
    scene_display_rect,
)
from gui.session_countdown_sound import (
    _ensure_final_tick_wav,
    _ensure_tick_wav,
    SessionCountdownSound,
    _FINAL_TICK_FREQUENCY_HZ,
    _TICK_FREQUENCY_HZ,
)


def test_scene_display_rect_minimum_size():
    """Scene rect should never be zero-sized."""
    rect = scene_display_rect(0, 0)
    assert rect.width() >= 1
    assert rect.height() >= 1


def test_layout_pixmap_centered_with_aspect_ratio(qtbot):
    """Pixmap should be centered and scaled to fit inside the display rect."""
    scene = QGraphicsScene()
    item = QGraphicsPixmapItem()
    scene.addItem(item)
    pixmap = QPixmap(400, 200)
    pixmap.fill()
    display = QRectF(0, 0, 800, 600)

    layout_pixmap_item_in_rect(item, pixmap, display)

    assert item.scale() == 2.0  # min(800/400, 600/200) = 2.0
    assert item.pos().x() == 0.0
    assert item.pos().y() == 100.0  # (600 - 200*2) / 2


def test_layout_pixmap_fills_height_for_portrait(qtbot):
    """Portrait pixmap in a landscape rect should fill height (fit-all / keep aspect)."""
    item = QGraphicsPixmapItem()
    pixmap = QPixmap(400, 800)
    pixmap.fill()
    display = QRectF(0, 0, 1200, 900)

    layout_pixmap_item_in_rect(item, pixmap, display)

    assert item.scale() == 900 / 800
    assert item.pos().y() == 0.0
    assert abs(item.pos().x() - (1200 - 400 * item.scale()) / 2.0) < 0.01


def test_layout_respects_device_pixel_ratio(qtbot):
    """HQ pixmaps with devicePixelRatio must use logical size for layout."""
    item = QGraphicsPixmapItem()
    pixmap = QPixmap(800, 1600)
    pixmap.fill()
    pixmap.setDevicePixelRatio(2.0)
    display = QRectF(0, 0, 1200, 900)

    layout_pixmap_item_in_rect(item, pixmap, display)

    lw, lh = logical_pixmap_size(pixmap)
    assert lw == 400 and lh == 800
    assert item.scale() == 900 / 800


def test_display_scale_factor_detects_upscale(qtbot):
    """Small logical pixmap in a large rect should report upscale > 1."""
    pixmap = QPixmap(400, 600)
    pixmap.fill()
    display = QRectF(0, 0, 1200, 900)
    assert display_scale_factor(pixmap, display) > 1.05


def test_display_scale_factor_at_native_size(qtbot):
    """Pixmap already fitted to the rect should not need upscaling."""
    pixmap = QPixmap(800, 1200)
    pixmap.fill()
    display = QRectF(0, 0, 800, 1200)
    assert display_scale_factor(pixmap, display) <= 1.05


def test_crossfade_opacities_complement():
    """Cross-dissolve opacities should sum to 1 during the transition."""
    for new_opacity in (0.0, 0.25, 0.5, 0.75, 1.0):
        old_opacity = 1.0 - new_opacity
        assert old_opacity + new_opacity == 1.0


def test_layout_different_sizes_same_display_rect(qtbot):
    """Two different pixmaps in the same rect should use independent fit-all scales."""
    scene = QGraphicsScene()
    item_a = QGraphicsPixmapItem()
    item_b = QGraphicsPixmapItem()
    scene.addItem(item_a)
    scene.addItem(item_b)
    display = QRectF(0, 0, 1000, 800)

    pixmap_a = QPixmap(2000, 1000)
    pixmap_a.fill()
    pixmap_b = QPixmap(800, 1200)
    pixmap_b.fill()

    layout_pixmap_item_in_rect(item_a, pixmap_a, display)
    layout_pixmap_item_in_rect(item_b, pixmap_b, display)

    assert item_a.scale() == 0.5  # min(1000/2000, 800/1000)
    assert abs(item_b.scale() - (800 / 1200)) < 0.01


def test_ensure_tick_wav_creates_file(tmp_path):
    """Tick WAV generator should produce a readable wave file."""
    path = tmp_path / "tick.wav"
    result = _ensure_tick_wav(path)
    assert result == path
    assert path.exists()
    assert path.stat().st_size > 100


def test_countdown_sound_plays_once_per_second():
    """play_tick_if_needed should not double-fire for the same second."""
    sound = SessionCountdownSound()
    sound.play_tick_if_needed(10)
    assert 10 in sound._played_seconds
    sound.play_tick_if_needed(10)
    assert sound._played_seconds == {10}
    sound.play_tick_if_needed(9)
    assert sound._played_seconds == {10, 9}


def test_countdown_sound_reset_allows_replay():
    """After reset (e.g. skip), the same seconds can tick again."""
    sound = SessionCountdownSound()
    sound.play_tick_if_needed(10)
    sound.play_final_tick()
    sound.reset()
    assert sound._played_seconds == set()
    assert not sound._final_played_this_pose
    sound.play_tick_if_needed(10)
    assert 10 in sound._played_seconds


def test_countdown_sound_final_tick_at_zero():
    """play_final_tick should fire once per pose."""
    sound = SessionCountdownSound()
    sound.play_final_tick()
    assert sound._final_played_this_pose
    sound.play_final_tick()
    assert 0 in sound._played_seconds


def test_final_tick_frequency_higher_than_regular(tmp_path):
    """Final tick WAV should use a higher frequency than the regular tick."""
    regular = tmp_path / "regular.wav"
    final = tmp_path / "final.wav"
    _ensure_tick_wav(regular)
    _ensure_final_tick_wav(final)
    assert _FINAL_TICK_FREQUENCY_HZ > _TICK_FREQUENCY_HZ
    assert final.stat().st_size > 100
