"""
Tests for virtualized grid pool sizing (regression: empty rows after column change).
"""

import pytest
from PIL import Image
from qtpy.QtWidgets import QApplication

from gui.image_grid import ImageGrid
from core.image_manager import ImageManager
from core.image_db import ImageMetadata


@pytest.fixture
def image_manager(tmp_path):
    """ImageManager with isolated DB and one real image for workers."""
    manager = ImageManager()
    manager.image_dir = tmp_path / "images"
    manager.image_dir.mkdir(parents=True, exist_ok=True)
    manager.db._db_path = tmp_path / "db" / "images.json"
    manager.db._db_path.parent.mkdir(parents=True, exist_ok=True)
    img_path = tmp_path / "seed.jpg"
    Image.new("RGB", (100, 100), color="red").save(img_path)
    manager.import_image(img_path)
    return manager


def _fake_metadata(count: int) -> list:
    """Build minimal ImageMetadata rows for virtualized layout tests."""
    return [
        ImageMetadata(
            id=f"id_{i}",
            path=f"{i}.jpg",
            original_filename=f"{i}.jpg",
            width=800,
            height=600,
            file_size=1000,
            format="JPEG",
        )
        for i in range(count)
    ]


def test_virtualized_pool_grows_when_columns_increase(
    qtbot, image_manager, monkeypatch
):
    """
    Narrower cells (more columns) mean shorter rows and more rows per viewport;
    the pool must expand so every visible slot gets a widget.
    """
    monkeypatch.setattr(ImageGrid, "VIRTUALIZATION_THRESHOLD", 0)
    grid = ImageGrid(image_manager)
    qtbot.addWidget(grid)
    grid.resize(900, 700)
    grid.show()
    grid.load_images_from_list(_fake_metadata(600), ("virtual_pool_test",))
    QApplication.processEvents()

    initial = len(grid.thumbnail_pool)
    assert initial > 0

    grid.set_columns(12)
    grid._update_layout()
    QApplication.processEvents()

    assert len(grid.thumbnail_pool) >= initial
    required = grid._required_virtualized_pool_size()
    assert len(grid.thumbnail_pool) >= required


def test_required_pool_size_never_exceeds_image_count(
    qtbot, image_manager, monkeypatch
):
    """Small catalogs must not request more pool widgets than images."""
    monkeypatch.setattr(ImageGrid, "VIRTUALIZATION_THRESHOLD", 0)
    grid = ImageGrid(image_manager)
    qtbot.addWidget(grid)
    grid.resize(1200, 800)
    grid.show()
    grid.all_images = _fake_metadata(3)
    grid.columns = 8
    assert grid._required_virtualized_pool_size() <= 3


def test_virtualized_visible_slots_covered_by_pool(qtbot, image_manager, monkeypatch):
    """Visible index span must not exceed pool length (regression guard)."""
    monkeypatch.setattr(ImageGrid, "VIRTUALIZATION_THRESHOLD", 0)
    grid = ImageGrid(image_manager)
    qtbot.addWidget(grid)
    grid.resize(900, 700)
    grid.show()
    grid.load_images_from_list(_fake_metadata(400), ("span_test",))
    QApplication.processEvents()

    grid._update_virtualized_view()
    # Recompute range the same way as _update_virtualized_view (after margin fix)
    tw, row_height = grid._calculate_optimal_dimensions()
    spacing = grid.grid.spacing()
    margins = grid.grid.contentsMargins()
    mt = margins.top()
    row_h = row_height + spacing
    scroll_y = grid.verticalScrollBar().value()
    viewport_h = grid.viewport().height()
    total_images = len(grid.all_images)
    total_rows = (total_images + grid.columns - 1) // grid.columns
    adj_top = scroll_y - mt
    adj_bottom = scroll_y + viewport_h - mt
    first_row = max(0, adj_top // row_h - grid.VIRTUALIZED_POOL_EXTRA_ROWS)
    last_row = min(
        total_rows - 1,
        adj_bottom // row_h + grid.VIRTUALIZED_POOL_EXTRA_ROWS,
    )
    start_index = first_row * grid.columns
    end_index = min(total_images, (last_row + 1) * grid.columns)
    need = end_index - start_index
    assert need <= len(grid.thumbnail_pool)
