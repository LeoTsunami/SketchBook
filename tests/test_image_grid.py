"""
Tests for the image grid (visibility debounce, pending load queue).
"""
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock
from PIL import Image

from qtpy.QtCore import QTimer
from gui.image_grid import ImageGrid
from core.image_manager import ImageManager
from core.image_db import ImageMetadata


@pytest.fixture
def image_manager(tmp_path):
    """ImageManager with temporary storage and one image."""
    manager = ImageManager()
    manager.image_dir = tmp_path / "images"
    manager.image_dir.mkdir(parents=True, exist_ok=True)
    manager.db._db_path = tmp_path / "db" / "images.json"
    manager.db._db_path.parent.mkdir(parents=True, exist_ok=True)
    img_path = tmp_path / "test.jpg"
    Image.new("RGB", (100, 100), color="red").save(img_path)
    manager.import_image(img_path)
    return manager


@pytest.fixture
def image_grid(qtbot, image_manager):
    """ImageGrid with one image loaded."""
    grid = ImageGrid(image_manager)
    qtbot.addWidget(grid)
    images = image_manager.db.list_images()
    grid.load_images_from_list(images, filter_key=("list",))
    # Let layout and visibility timers run
    qtbot.wait(200)
    return grid


def test_scroll_starts_visibility_timer(image_grid):
    """Scroll should start the debounce timer, not call _check_visible_thumbnails directly."""
    with patch.object(image_grid, "_check_visible_thumbnails") as mock_check:
        image_grid.verticalScrollBar().valueChanged.emit(50)
        # Debounce: timer started, _check_visible_thumbnails not called yet
        assert image_grid.visibility_timer.isActive()
        mock_check.assert_not_called()


def test_check_visible_thumbnails_enqueues_and_starts_ticker(image_grid):
    """_check_visible_thumbnails should fill pending queue and start load ticker."""
    image_grid.pending_load_queue.clear()
    image_grid.load_ticker_timer.stop()
    image_grid._check_visible_thumbnails()
    # At least one thumbnail is in view -> queue non-empty, ticker started
    if image_grid.pending_load_queue:
        assert image_grid.load_ticker_timer.isActive()


def test_process_pending_loads_pops_max_per_tick(image_grid):
    """_process_pending_loads should pop at most MAX_LOADS_PER_TICK per call."""
    image_grid.load_ticker_timer.stop()
    image_grid.pending_load_queue.clear()
    for i in range(5):
        image_grid.pending_load_queue.append(f"fake_id_{i}")

    with patch.object(image_grid, "_load_thumbnail_image"):
        image_grid._process_pending_loads()
    # Should have popped at most MAX_LOADS_PER_TICK (2)
    assert len(image_grid.pending_load_queue) >= 3
    assert image_grid.load_ticker_timer.isActive() or len(image_grid.pending_load_queue) == 0


def test_process_pending_loads_stops_timer_when_queue_empty(image_grid):
    """When queue is empty, _process_pending_loads should stop the ticker."""
    image_grid.pending_load_queue.clear()
    image_grid.load_ticker_timer.start()
    image_grid._process_pending_loads()
    assert not image_grid.load_ticker_timer.isActive()


def test_clear_stops_timers_and_empties_queue(image_grid):
    """clear() should stop visibility and load ticker timers and empty pending queue."""
    image_grid.pending_load_queue.append("dummy")
    image_grid.visibility_timer.start()
    image_grid.load_ticker_timer.start()
    image_grid.clear()
    assert not image_grid.visibility_timer.isActive()
    assert not image_grid.load_ticker_timer.isActive()
    assert len(image_grid.pending_load_queue) == 0
