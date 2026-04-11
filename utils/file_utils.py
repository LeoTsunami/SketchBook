"""
File system utilities for handling paths and directory operations.
"""

import os
import shutil
from pathlib import Path
from typing import Union, List, Optional


def ensure_dir(path: Union[str, Path]) -> Path:
    """
    Ensure a directory exists, create it if it doesn't.

    Args:
        path: Directory path to ensure exists

    Returns:
        Path object of the ensured directory

    Raises:
        OSError: If directory creation fails
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def validate_dir(path: Union[str, Path]) -> bool:
    """
    Validate if a directory exists and is accessible.

    Args:
        path: Directory path to validate

    Returns:
        True if directory exists and is accessible, False otherwise
    """
    path = Path(path)
    return path.exists() and path.is_dir() and os.access(path, os.R_OK | os.W_OK)


def safe_path(base_path: Union[str, Path], *parts: str) -> Path:
    """
    Safely join path components and resolve to absolute path.
    Ensures the resulting path is within the base path.

    Args:
        base_path: Base directory path
        *parts: Additional path components to join

    Returns:
        Resolved absolute Path object

    Raises:
        ValueError: If resulting path would be outside base_path
    """
    base_path = Path(base_path).resolve()
    full_path = base_path.joinpath(*parts).resolve()

    if not str(full_path).startswith(str(base_path)):
        raise ValueError(f"Path {full_path} is outside base path {base_path}")

    return full_path


def list_files(
    directory: Union[str, Path], pattern: str = "*", recursive: bool = False
) -> List[Path]:
    """
    List files in a directory matching a pattern.

    Args:
        directory: Directory to search in
        pattern: Glob pattern to match files (default: "*")
        recursive: Whether to search recursively (default: False)

    Returns:
        List of Path objects for matching files

    Raises:
        FileNotFoundError: If directory doesn't exist
    """
    directory = Path(directory)
    if not directory.exists():
        raise FileNotFoundError(f"Directory {directory} not found")

    if recursive:
        return list(directory.rglob(pattern))
    return list(directory.glob(pattern))


def safe_remove(path: Union[str, Path]) -> bool:
    """
    Safely remove a file or directory.

    Args:
        path: Path to remove

    Returns:
        True if removal was successful, False otherwise
    """
    try:
        path = Path(path)
        if not path.exists():
            return False
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
        else:
            return False
        return True
    except (OSError, PermissionError):
        return False


def get_file_size(path: Union[str, Path]) -> Optional[int]:
    """
    Get file size in bytes.

    Args:
        path: Path to the file

    Returns:
        File size in bytes or None if file doesn't exist
    """
    try:
        return Path(path).stat().st_size
    except (OSError, FileNotFoundError):
        return None
