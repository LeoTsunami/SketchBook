"""
Tests for the image management system.
"""
import os
from pathlib import Path
import pytest
from PIL import Image
from core.image_manager import ImageManager

@pytest.fixture
def image_manager(tmp_path):
    """Create an ImageManager instance with temporary storage."""
    manager = ImageManager()
    manager.image_dir = tmp_path / "images"
    manager.db.db_path = tmp_path / "db" / "images.json"
    return manager

@pytest.fixture
def sample_image(tmp_path):
    """Create a sample test image."""
    image_path = tmp_path / "test.jpg"
    # Create a 2000x1500 test image
    image = Image.new('RGB', (2000, 1500), color='red')
    image.save(image_path, 'JPEG')
    return image_path

def test_import_image_with_metadata(image_manager, sample_image):
    """Test image importing with metadata creation."""
    # Import the image
    result_path = image_manager.import_image(sample_image)
    assert result_path is not None
    assert result_path.exists()
    
    # Get metadata
    image_id = result_path.stem
    metadata = image_manager.get_image_metadata(image_id)
    assert metadata is not None
    assert metadata.original_filename == sample_image.name
    assert metadata.width <= ImageManager.MAX_WIDTH
    assert metadata.height == int(1500 * (ImageManager.MAX_WIDTH / 2000))
    assert metadata.format == "JPEG"
    assert metadata.file_size > 0

def test_update_metadata(image_manager, sample_image):
    """Test updating image metadata."""
    # Import image
    result_path = image_manager.import_image(sample_image)
    image_id = result_path.stem
    
    # Update metadata
    assert image_manager.update_image_metadata(
        image_id,
        tags=["test", "landscape"],
        notes="Test image"
    )
    
    # Verify updates
    metadata = image_manager.get_image_metadata(image_id)
    assert metadata.tags == ["test", "landscape"]
    assert metadata.notes == "Test image"

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
        image = Image.new('RGB', (100, 100), color='red')
        image.save(image_path, 'JPEG')
        result_path = image_manager.import_image(image_path)
        
        # Add tags to images
        image_id = result_path.stem
        tags = ["test"]
        if i % 2 == 0:
            tags.append("even")
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
        image = Image.new('RGB', (100, 100), color='red')
        image.save(image_path, 'JPEG')
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