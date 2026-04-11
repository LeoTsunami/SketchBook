"""
Tests for the image management system.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image
from core.image_manager import ImageManager


@pytest.fixture
def image_manager(tmp_path):
    """Create an ImageManager instance with temporary storage."""
    manager = ImageManager()
    manager.image_dir = tmp_path / "images"
    # Ensure the image directory exists
    manager.image_dir.mkdir(parents=True, exist_ok=True)
    manager.db._db_path = tmp_path / "db" / "images.json"
    # Ensure the database directory exists
    manager.db._db_path.parent.mkdir(parents=True, exist_ok=True)
    return manager


@pytest.fixture
def sample_image(tmp_path):
    """Create a sample test image."""
    image_path = tmp_path / "test.jpg"
    # Create a 2000x1500 test image
    image = Image.new("RGB", (2000, 1500), color="red")
    image.save(image_path, "JPEG")
    return image_path


def test_import_image_with_metadata(image_manager, sample_image):
    """Test image importing with metadata creation (resize respects max_width/max_height from settings)."""
    # Import the image (2000x1500); default settings limit to 1920x1080
    result_path = image_manager.import_image(sample_image)
    assert result_path is not None
    assert result_path.exists()

    # Get metadata
    image_id = result_path.stem
    metadata = image_manager.get_image_metadata(image_id)
    assert metadata is not None
    assert metadata.original_filename == sample_image.name
    # Resize fits within max_width x max_height (default 1920x1080), aspect ratio preserved
    assert metadata.width <= 1920
    assert metadata.height <= 1080
    assert (
        abs(metadata.width / metadata.height - 2000 / 1500) < 0.01
    )  # aspect ratio preserved
    assert metadata.format == "JPEG"
    assert metadata.file_size > 0


def test_update_metadata(image_manager, sample_image):
    """Test updating image metadata."""
    # Import image
    result_path = image_manager.import_image(sample_image)
    image_id = result_path.stem

    # Update metadata
    assert image_manager.update_image_metadata(
        image_id, tags={"test", "landscape"}  # Use set instead of list
    )

    # Verify updates
    metadata = image_manager.get_image_metadata(image_id)
    assert metadata.tags == {"test", "landscape"}


def test_rotate_image(image_manager, sample_image):
    """Test rotating image 90° clockwise and counterclockwise."""
    result_path = image_manager.import_image(sample_image)
    assert result_path is not None
    image_id = result_path.stem
    meta = image_manager.get_image_metadata(image_id)
    assert meta is not None
    w0, h0 = meta.width, meta.height

    # Rotate 90° clockwise: dimensions swap
    assert image_manager.rotate_image(image_id, clockwise=True)
    meta = image_manager.get_image_metadata(image_id)
    assert meta.width == h0 and meta.height == w0

    # Rotate 90° counterclockwise: back to original dimensions
    assert image_manager.rotate_image(image_id, clockwise=False)
    meta = image_manager.get_image_metadata(image_id)
    assert meta.width == w0 and meta.height == h0


def test_delete_image(image_manager, sample_image):
    """Test deleting image and metadata."""
    # Import image
    result_path = image_manager.import_image(sample_image)
    image_id = result_path.stem

    # Delete image
    assert image_manager.delete_image(image_id)

    # Verify file and metadata are gone
    assert not result_path.exists()
    assert image_manager.get_image_metadata(image_id) is None


def test_search_images(image_manager, tmp_path):
    """Test searching images by tags."""
    # Create and import test images
    for i in range(3):
        image_path = tmp_path / f"test_{i}.jpg"
        image = Image.new("RGB", (100, 100), color="red")
        image.save(image_path, "JPEG")
        result_path = image_manager.import_image(image_path)

        # Add tags to images
        image_id = result_path.stem
        tags = {"test"}  # Use set instead of list
        if i % 2 == 0:
            tags.add("even")  # Use add instead of append
        image_manager.update_image_metadata(image_id, tags=tags)

    # Search by tags
    all_test = image_manager.search_images(["test"])
    assert len(all_test) == 3

    even_images = image_manager.search_images(["test", "even"])
    assert len(even_images) == 2


def test_get_image_list(image_manager, tmp_path):
    """Test getting list of imported images."""
    # Create and import multiple images
    imported_paths = []
    for i in range(3):
        image_path = tmp_path / f"test_{i}.jpg"
        image = Image.new("RGB", (100, 100), color="red")
        image.save(image_path, "JPEG")
        result_path = image_manager.import_image(image_path)
        imported_paths.append(result_path)

    # Get list of images
    image_list = image_manager.get_image_list()
    assert len(image_list) == 3
    assert all(path in image_list for path in imported_paths)


def test_import_invalid_format(image_manager, tmp_path):
    """Test importing an unsupported format."""
    # Create an invalid file
    invalid_file = tmp_path / "test.txt"
    invalid_file.write_text("Not an image")

    # Try to import
    result = image_manager.import_image(invalid_file)
    assert result is None


def test_run_import_date_backfill_calls_internal(image_manager):
    """run_import_date_backfill should invoke the legacy import_date migration."""
    with patch.object(image_manager, "_backfill_import_dates") as mock_bf:
        image_manager.run_import_date_backfill()
        mock_bf.assert_called_once()


def test_run_import_date_backfill_propagates_errors(image_manager):
    """Failures in the backfill scan should surface to the caller."""
    with patch.object(
        image_manager, "_backfill_import_dates", side_effect=RuntimeError("backfill")
    ):
        with pytest.raises(RuntimeError, match="backfill"):
            image_manager.run_import_date_backfill()
