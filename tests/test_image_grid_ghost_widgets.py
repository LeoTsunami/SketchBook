"""
Regression tests for orphan QGridLayout cells (non-interactive ghost thumbnails).
"""

import pytest
from PIL import Image
from qtpy.QtWidgets import QApplication, QFrame

from gui.image_grid import ImageGrid
from core.image_manager import ImageManager
from core.image_db import ImageMetadata


@pytest.fixture
def image_manager(tmp_path):
    """ImageManager with isolated DB and one real image."""
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


def test_clear_drains_grid_when_thumbnail_pool_exists(
    qtbot, image_manager, monkeypatch
):
    """
    Expected: clear() removes all QGridLayout children even when the pool shortcut runs.

    Previously the pool branch returned without draining the grid, leaving stale cells.
    """
    monkeypatch.setattr(ImageGrid, "VIRTUALIZATION_THRESHOLD", 0)
    grid = ImageGrid(image_manager)
    qtbot.addWidget(grid)
    grid.resize(900, 700)
    grid.show()
    grid.load_images_from_list(_fake_metadata(600), ("ghost_clear",))
    QApplication.processEvents()
    assert len(grid.thumbnail_pool) > 0

    orphan = QFrame(grid.content)
    orphan.setObjectName("GhostOrphan")
    grid.grid.addWidget(orphan, 0, 0)
    assert grid.grid.count() >= 1

    grid.clear()
    QApplication.processEvents()

    assert grid.grid.count() == 0


def test_update_virtualized_view_drains_orphan_grid_cells(
    qtbot, image_manager, monkeypatch
):
    """
    Edge case: if a grid cell survives without going through clear(), a virtualized
    refresh must still remove it so ghosts do not stack over the pool.
    """
    monkeypatch.setattr(ImageGrid, "VIRTUALIZATION_THRESHOLD", 0)
    grid = ImageGrid(image_manager)
    qtbot.addWidget(grid)
    grid.resize(900, 700)
    grid.show()
    grid.load_images_from_list(_fake_metadata(400), ("ghost_virtual",))
    QApplication.processEvents()

    orphan = QFrame(grid.content)
    grid.grid.addWidget(orphan, 2, 2)
    assert grid.grid.count() >= 1

    grid._update_virtualized_view()
    QApplication.processEvents()

    assert grid.grid.count() == 0


def test_clear_without_pool_still_empties_thumbnail_dict(qtbot, image_manager):
    """
    Failure path: non-virtualized clear must not crash when thumbnails lived in the grid.
    """
    grid = ImageGrid(image_manager)
    qtbot.addWidget(grid)
    grid.resize(800, 600)
    images = image_manager.db.list_images()
    grid.load_images_from_list(images, ("no_pool",))
    QApplication.processEvents()
    assert grid.thumbnails

    grid.clear()
    QApplication.processEvents()

    assert not grid.thumbnails
    assert grid.grid.count() == 0
