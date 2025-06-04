"""
Tests for file system utilities.
"""
import os
import pytest
from pathlib import Path
from utils.file_utils import (
    ensure_dir,
    validate_dir,
    safe_path,
    list_files,
    safe_remove,
    get_file_size
)

@pytest.fixture
def temp_test_dir(tmp_path):
    """Create a temporary test directory."""
    return tmp_path

def test_ensure_dir(temp_test_dir):
    """Test directory creation."""
    # Test creating a new directory
    new_dir = temp_test_dir / "new_dir"
    result = ensure_dir(new_dir)
    assert result.exists()
    assert result.is_dir()
    
    # Test with existing directory (should not raise)
    result2 = ensure_dir(new_dir)
    assert result2 == result

def test_validate_dir(temp_test_dir):
    """Test directory validation."""
    # Test with existing directory
    assert validate_dir(temp_test_dir) is True
    
    # Test with non-existent directory
    non_existent = temp_test_dir / "non_existent"
    assert validate_dir(non_existent) is False
    
    # Test with file instead of directory
    test_file = temp_test_dir / "test.txt"
    test_file.touch()
    assert validate_dir(test_file) is False

def test_safe_path(temp_test_dir):
    """Test safe path joining."""
    # Test valid path joining
    result = safe_path(temp_test_dir, "subdir", "file.txt")
    assert str(result).startswith(str(temp_test_dir))
    
    # Test path traversal attempt
    with pytest.raises(ValueError):
        safe_path(temp_test_dir, "..", "outside.txt")

def test_list_files(temp_test_dir):
    """Test file listing."""
    # Create test files
    (temp_test_dir / "file1.txt").touch()
    (temp_test_dir / "file2.txt").touch()
    subdir = temp_test_dir / "subdir"
    subdir.mkdir()
    (subdir / "file3.txt").touch()
    
    # Test non-recursive listing
    files = list_files(temp_test_dir, "*.txt")
    assert len(files) == 2
    
    # Test recursive listing
    files = list_files(temp_test_dir, "*.txt", recursive=True)
    assert len(files) == 3
    
    # Test with non-existent directory
    with pytest.raises(FileNotFoundError):
        list_files(temp_test_dir / "non_existent")

def test_safe_remove(temp_test_dir):
    """Test safe file/directory removal."""
    # Test file removal
    test_file = temp_test_dir / "test.txt"
    test_file.touch()
    assert safe_remove(test_file) is True
    assert not test_file.exists()
    
    # Test directory removal
    test_dir = temp_test_dir / "test_dir"
    test_dir.mkdir()
    (test_dir / "file.txt").touch()
    assert safe_remove(test_dir) is True
    assert not test_dir.exists()
    
    # Test non-existent path
    assert safe_remove(temp_test_dir / "non_existent") is False

def test_get_file_size(temp_test_dir):
    """Test file size retrieval."""
    # Test with empty file
    test_file = temp_test_dir / "empty.txt"
    test_file.touch()
    assert get_file_size(test_file) == 0
    
    # Test with file containing data
    test_file.write_text("Hello World")
    assert get_file_size(test_file) == 11
    
    # Test with non-existent file
    assert get_file_size(temp_test_dir / "non_existent.txt") is None 