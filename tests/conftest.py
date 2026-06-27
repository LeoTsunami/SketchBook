"""Shared pytest fixtures for SketchBook tests."""

import pytest
from PIL import Image

from core.image_manager import ImageManager
from core.user_data import user_data


@pytest.fixture
def image_manager(tmp_path, monkeypatch):
    """
    ImageManager with isolated temp storage.

    Patches user data paths before the DB is created so lazy loading never
    touches the real images.json library.
    """
    images_dir = tmp_path / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    db_path = tmp_path / "db" / "images.json"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(user_data, "get_images_dir", lambda: images_dir)
    monkeypatch.setattr(user_data, "get_images_db_path", lambda: db_path)
    manager = ImageManager()
    manager.image_dir = images_dir
    return manager


@pytest.fixture
def image_manager_with_image(image_manager, tmp_path):
    """ImageManager with one imported test image."""
    img_path = tmp_path / "test.jpg"
    Image.new("RGB", (100, 100), color="red").save(img_path)
    image_manager.import_image(img_path)
    return image_manager
