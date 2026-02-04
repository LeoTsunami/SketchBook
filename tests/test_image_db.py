"""
Tests for the image metadata database.
"""
import json
from datetime import datetime
from pathlib import Path
import pytest
from core.image_db import ImageDatabase, ImageMetadata

@pytest.fixture
def image_db(tmp_path):
    """Create a test image database."""
    db = ImageDatabase()
    db.db_path = tmp_path / "test_images.json"
    return db

@pytest.fixture
def sample_metadata():
    """Create sample image metadata."""
    return ImageMetadata(
        id="test_image_123",
        path="test_image.jpg",
        original_filename="original.jpg",
        width=1920,
        height=1080,
        file_size=1024,
        format="JPEG"
    )

def test_add_image(image_db, sample_metadata):
    """Test adding image metadata."""
    # Add image
    assert image_db.add_image(sample_metadata)
    
    # Verify it was added
    saved = image_db.get_image(sample_metadata.id)
    assert saved is not None
    assert saved.path == sample_metadata.path
    assert saved.original_filename == sample_metadata.original_filename
    
    # Try adding same image again
    assert not image_db.add_image(sample_metadata)

def test_update_image(image_db, sample_metadata):
    """Test updating image metadata."""
    # Add image
    image_db.add_image(sample_metadata)
    
    # Update tags
    assert image_db.update_image(
        sample_metadata.id,
        tags={"test", "update"}  # Use set instead of list
    )
    
    # Verify updates
    updated = image_db.get_image(sample_metadata.id)
    assert updated.tags == {"test", "update"}
    
    # Try updating non-existent image
    assert not image_db.update_image("nonexistent", tags={"test"})

def test_delete_image(image_db, sample_metadata):
    """Test deleting image metadata."""
    # Add and then delete image
    image_db.add_image(sample_metadata)
    assert image_db.delete_image(sample_metadata.id)
    
    # Verify it was deleted
    assert image_db.get_image(sample_metadata.id) is None
    
    # Try deleting non-existent image
    assert not image_db.delete_image("nonexistent")

def test_list_images(image_db):
    """Test listing all images."""
    # Add multiple images
    images = []
    for i in range(3):
        metadata = ImageMetadata(
            id=f"test_{i}",
            path=f"test_{i}.jpg",
            original_filename=f"original_{i}.jpg",
            width=1920,
            height=1080,
            file_size=1024,
            format="JPEG"
        )
        image_db.add_image(metadata)
        images.append(metadata)
    
    # List all images
    listed = image_db.list_images()
    assert len(listed) == 3
    assert all(img.id in [m.id for m in listed] for img in images)

def test_search_images(image_db):
    """Test searching images by tags."""
    # Add images with different tags
    metadata1 = ImageMetadata(
        id="test_1",
        path="test_1.jpg",
        original_filename="original_1.jpg",
        width=1920,
        height=1080,
        file_size=1024,
        format="JPEG",
        tags={"nature", "landscape"}
    )
    
    metadata2 = ImageMetadata(
        id="test_2",
        path="test_2.jpg",
        original_filename="original_2.jpg",
        width=1920,
        height=1080,
        file_size=1024,
        format="JPEG",
        tags={"nature", "wildlife"}
    )
    
    image_db.add_image(metadata1)
    image_db.add_image(metadata2)
    
    # Search by single tag
    nature_images = image_db.search_images(["nature"])
    assert len(nature_images) == 2
    
    # Search by multiple tags
    landscape_images = image_db.search_images(["nature", "landscape"])
    assert len(landscape_images) == 1
    assert landscape_images[0].id == "test_1"
    
    # Search with no matches
    no_matches = image_db.search_images(["portrait"])
    assert len(no_matches) == 0

def test_persistence(image_db, sample_metadata, tmp_path):
    """Test database persistence."""
    # Add image
    image_db.add_image(sample_metadata)
    
    # Create new instance with same path
    new_db = ImageDatabase()
    new_db._db_path = image_db._db_path  # Set the same path
    
    # Verify data was loaded
    loaded = new_db.get_image(sample_metadata.id)
    assert loaded is not None
    assert loaded.path == sample_metadata.path
    
    # Test invalid JSON handling
    image_db._db_path.write_text("invalid json")
    new_db = ImageDatabase()
    new_db._db_path = image_db._db_path
    assert len(new_db.list_images()) == 0


def test_rename_tag(image_db):
    """Test renaming a tag across all images."""
    m1 = ImageMetadata(
        id="r1",
        path="r1.jpg",
        original_filename="r1.jpg",
        width=100,
        height=100,
        file_size=100,
        format="JPEG",
        tags={"old_tag", "other"},
    )
    m2 = ImageMetadata(
        id="r2",
        path="r2.jpg",
        original_filename="r2.jpg",
        width=100,
        height=100,
        file_size=100,
        format="JPEG",
        tags={"old_tag"},
    )
    image_db.add_image(m1)
    image_db.add_image(m2)
    n = image_db.rename_tag("old_tag", "new_tag")
    assert n == 2
    assert image_db.get_image("r1").tags == {"new_tag", "other"}
    assert image_db.get_image("r2").tags == {"new_tag"}


def test_rename_tag_no_match(image_db, sample_metadata):
    """Test rename_tag when no image has the old tag."""
    sample_metadata.tags = {"other"}
    image_db.add_image(sample_metadata)
    n = image_db.rename_tag("missing", "new_tag")
    assert n == 0
    assert image_db.get_image(sample_metadata.id).tags == {"other"}


def test_rename_tag_idempotent_same_name(image_db, sample_metadata):
    """Test rename_tag with same old and new name returns 0."""
    sample_metadata.tags = {"same"}
    image_db.add_image(sample_metadata)
    n = image_db.rename_tag("same", "same")
    assert n == 0
    assert image_db.get_image(sample_metadata.id).tags == {"same"}