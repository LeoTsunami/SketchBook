"""
Tests for the image grid (visibility debounce, pending load queue).
"""

import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock
from PIL import Image

from qtpy.QtCore import QTimer, QSize, Qt
from qtpy.QtGui import QResizeEvent
from gui.image_grid import ImageGrid
from core.image_db import ImageMetadata


@pytest.fixture
def image_grid(qtbot, image_manager_with_image):
    """ImageGrid with one image loaded."""
    grid = ImageGrid(image_manager_with_image)
    qtbot.addWidget(grid)
    images = image_manager_with_image.db.list_images()
    grid.load_images_from_list(images, filter_key=("list",))
    # Let layout and visibility timers run
    qtbot.wait(200)
    return grid


def test_scroll_defers_visibility_check_until_idle(image_grid):
    """Scroll should defer thumbnail/load work until the scroll-idle timer fires."""
    with patch.object(image_grid, "_check_visible_thumbnails") as mock_check:
        image_grid.verticalScrollBar().valueChanged.emit(50)
        assert image_grid._scroll_idle_timer.isActive()
        mock_check.assert_not_called()
        assert not image_grid.load_ticker_timer.isActive()


def test_check_visible_thumbnails_enqueues_and_starts_ticker(image_grid):
    """_check_visible_thumbnails should fill tier-0 queue and start load ticker."""
    image_grid._tier0_queue.clear()
    image_grid.load_ticker_timer.stop()
    image_grid._check_visible_thumbnails()
    if image_grid._tier0_queue:
        assert image_grid.load_ticker_timer.isActive()


def test_process_pending_loads_pops_max_per_tick(image_grid):
    """_process_pending_loads should pop at most MAX_LOADS_PER_TICK per call."""
    max_per = image_grid.MAX_LOADS_PER_TICK
    image_grid._tier0_queue.clear()
    remaining = 5
    for i in range(max_per + remaining):
        image_grid._tier0_queue.append(f"fake_id_{i}")
    image_grid.load_ticker_timer.start()

    with patch.object(image_grid, "_load_thumbnail_image"):
        image_grid._process_pending_loads()
    assert len(image_grid._tier0_queue) == remaining
    assert image_grid.load_ticker_timer.isActive()


def test_process_pending_loads_stops_timer_when_queue_empty(image_grid):
    """When no grid phase is active, _process_pending_loads should stop the ticker."""
    image_grid._tier0_queue.clear()
    image_grid._tier3_queue.clear()
    image_grid.load_ticker_timer.start()
    with patch.object(image_grid, "_current_post_scroll_load_phase", return_value=5):
        image_grid._process_pending_loads()
    assert not image_grid.load_ticker_timer.isActive()


def test_clear_stops_timers_and_empties_queue(image_grid):
    """clear() should stop visibility and load ticker timers and empty load queues."""
    image_grid._tier0_queue.append("dummy")
    image_grid.visibility_timer.start()
    image_grid.load_ticker_timer.start()
    image_grid.clear()
    assert not image_grid.visibility_timer.isActive()
    assert not image_grid.load_ticker_timer.isActive()
    assert len(image_grid._tier0_queue) == 0


def test_resize_schedules_finalize_timer(image_grid):
    """Normal width resize uses throttled coarse layout + finalize timer (fluid resize)."""
    with patch.object(image_grid.resize_finalize_timer, "start") as mock_finalize:
        old = image_grid.size()
        image_grid.resizeEvent(QResizeEvent(QSize(old.width() + 25, old.height()), old))
    mock_finalize.assert_called_once()


def test_on_resize_finalize_resets_coarse_throttle_state(image_grid):
    """Finalize clears coarse-throttle state so the next resize gets an immediate layout."""
    image_grid._coarse_throttle_started = True
    image_grid._on_resize_finalize()
    assert image_grid._coarse_throttle_started is False


def test_finalize_restores_smooth_pixmap_scaling(image_grid):
    """After interactive resize, finalize should restore SmoothTransformation on thumbnails."""
    thumbs = list(image_grid.thumbnails.values())
    assert len(thumbs) >= 1
    thumb = thumbs[0]
    if thumb.pixmap_item is None:
        return
    thumb.pixmap_item.setTransformationMode(Qt.FastTransformation)
    image_grid._on_resize_finalize()
    assert thumb.pixmap_item.transformationMode() == Qt.SmoothTransformation


def test_image_id_index_built_on_load(image_grid):
    """_image_id_to_index should contain every image in all_images after load."""
    assert len(image_grid._image_id_to_index) == len(image_grid.all_images)
    for i, meta in enumerate(image_grid.all_images):
        assert image_grid._image_id_to_index[meta.id] == i


def test_clear_empties_image_id_index(image_grid):
    """clear() must also empty the _image_id_to_index dict."""
    assert len(image_grid._image_id_to_index) > 0
    image_grid.clear()
    assert len(image_grid._image_id_to_index) == 0


def test_set_fast_resize_flag_propagates_to_thumbnails(image_grid):
    """_set_fast_resize_flag should set _fast_resize_active on all thumbnails."""
    thumbs = list(image_grid.thumbnails.values())
    assert len(thumbs) >= 1
    image_grid._set_fast_resize_flag(True)
    for thumb in thumbs:
        assert thumb._fast_resize_active is True
    image_grid._set_fast_resize_flag(False)
    for thumb in thumbs:
        assert thumb._fast_resize_active is False


def test_on_resize_finalize_clears_fast_resize_flag(image_grid):
    """After finalize, _fast_resize_active should be False on all thumbnails."""
    image_grid._set_fast_resize_flag(True)
    image_grid._on_resize_finalize()
    for thumb in image_grid.thumbnails.values():
        assert thumb._fast_resize_active is False


def test_resize_event_triggers_schedule(image_grid):
    """Width change in resizeEvent should schedule the window resize relayout."""
    with patch.object(image_grid, "_schedule_window_resize_relayout") as mock_sched:
        old = image_grid.size()
        image_grid.resizeEvent(QResizeEvent(QSize(old.width() + 30, old.height()), old))
    mock_sched.assert_called_once()


def test_resize_event_no_width_change_does_not_schedule(image_grid):
    """Height-only resize should not schedule relayout."""
    with patch.object(image_grid, "_schedule_window_resize_relayout") as mock_sched:
        old = image_grid.size()
        image_grid.resizeEvent(QResizeEvent(QSize(old.width(), old.height() + 30), old))
    mock_sched.assert_not_called()
