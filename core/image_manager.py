"""
Image management system for handling imports and processing.
"""
import os
import shutil
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple, Set
from PIL import Image
from core.settings import settings
from core.image_db import ImageDatabase, ImageMetadata
from utils.file_utils import ensure_dir, safe_path

class ImageManager:
    """Manages image importing, processing, and storage."""
    
    SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png"}
    MAX_WIDTH = 1920  # Maximum width for imported images
    
    def __init__(self):
        """Initialize the image manager."""
        self.image_dir = Path(settings.get("images.storage_path", "data/images")).resolve()
        ensure_dir(self.image_dir)
        self.db = ImageDatabase()
    
    def _compute_image_hash(self, image_path: Path) -> str:
        """
        Compute a hash of the image content.
        
        Args:
            image_path: Path to the image
            
        Returns:
            SHA-256 hash of the image content
        """
        with open(image_path, "rb") as f:
            print(f"Hashing image: {image_path}")
            print(f"File size: {os.path.getsize(image_path)} bytes")
            return hashlib.sha256(f.read()).hexdigest()
    
    def _is_duplicate(self, source_path: Path, hash_value: str) -> bool:
        """
        Check if an image is already imported.
        
        Args:
            source_path: Path to the source image
            hash_value: SHA-256 hash of the image content
            
        Returns:
            True if the image is a duplicate
        """
        # First check if hash exists in metadata
        for metadata in self.db.list_images():
            if hasattr(metadata, 'hash') and metadata.hash == hash_value:
                print(f"Found duplicate by hash: {source_path}")
                return True
            
            # If no hash in metadata (legacy data), check file content
            existing_path = self.image_dir / metadata.path
            if existing_path.exists():
                # Compare file sizes first (quick check)
                if existing_path.stat().st_size == source_path.stat().st_size:
                    # Compare hashes (more thorough)
                    existing_hash = self._compute_image_hash(existing_path)
                    if existing_hash == hash_value:
                        # Update metadata with hash if missing
                        if not hasattr(metadata, 'hash'):
                            self.db.update_image(metadata.id, hash=existing_hash)
                        print(f"Found duplicate by content: {source_path}")
                        return True
        return False
    
    def find_images_in_directory(self, directory: Path) -> List[Path]:
        """
        Find all supported images in a directory recursively.
        
        Args:
            directory: Directory to search
            
        Returns:
            List of paths to supported images
        """
        image_paths = []
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix.lower() in self.SUPPORTED_FORMATS:
                    image_paths.append(file_path)
        return image_paths
    
    def import_directory(self, directory: Path) -> Tuple[int, int, int]:
        """
        Import all supported images from a directory recursively.
        
        Args:
            directory: Directory to import
            
        Returns:
            Tuple of (successful imports, duplicates found, total images)
        """
        image_paths = self.find_images_in_directory(directory)
        successful = 0
        duplicates = 0
        total = len(image_paths)
        
        for path in image_paths:
            # Compute hash before import to check for duplicates
            hash_value = self._compute_image_hash(path)
            if self._is_duplicate(path, hash_value):
                duplicates += 1
                continue
                
            if self.import_image(path) is not None:
                successful += 1
        
        return successful, duplicates, total
    
    def import_image(self, source_path: Path) -> Optional[Path]:
        """
        Import and process a single image.
        
        Args:
            source_path: Path to the source image
            
        Returns:
            Path to the processed image or None if import failed
            
        Raises:
            ValueError: If file is not a supported image format
        """
        try:
            # Validate format
            if source_path.suffix.lower() not in self.SUPPORTED_FORMATS:
                raise ValueError(f"Unsupported image format: {source_path.suffix}")
            
            # Check for duplicates
            hash_value = self._compute_image_hash(source_path)
            if self._is_duplicate(source_path, hash_value):
                print(f"Skipping duplicate image: {source_path}")
                return None
            
            # Create unique filename
            dest_filename = f"{source_path.stem}_{os.urandom(4).hex()}{source_path.suffix.lower()}"
            dest_path = safe_path(self.image_dir, dest_filename)
            
            # Process and save image
            with Image.open(source_path) as img:
                # Get original dimensions
                original_width, original_height = img.size
                
                # Convert to RGB if necessary
                if img.mode != "RGB":
                    img = img.convert("RGB")
                
                # Resize if needed
                if img.width > self.MAX_WIDTH:
                    ratio = self.MAX_WIDTH / img.width
                    new_size = (self.MAX_WIDTH, int(img.height * ratio))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                
                # Save with compression
                img.save(
                    dest_path,
                    format="JPEG",
                    quality=settings.get("images.compression.quality", 85),
                    optimize=True
                )
                
                # Create and save metadata
                metadata = ImageMetadata(
                    id=dest_path.stem,
                    path=dest_path.name,
                    original_filename=source_path.name,
                    width=img.width,
                    height=img.height,
                    file_size=dest_path.stat().st_size,
                    format=img.format or "JPEG",
                    hash=hash_value  # Store hash for future duplicate checks
                )
                self.db.add_image(metadata)
            
            return dest_path
        
        except (OSError, ValueError) as e:
            print(f"Error importing image {source_path}: {str(e)}")
            return None
    
    def import_images(self, source_paths: List[Path]) -> Tuple[int, int, int]:
        """
        Import multiple images.
        
        Args:
            source_paths: List of paths to source images or directories
            
        Returns:
            Tuple of (successful imports, duplicates found, total images)
        """
        successful = 0
        duplicates = 0
        total = 0
        
        for path in source_paths:
            if path.is_dir():
                s, d, t = self.import_directory(path)
                successful += s
                duplicates += d
                total += t
            else:
                total += 1
                # Check for duplicates
                hash_value = self._compute_image_hash(path)
                if self._is_duplicate(path, hash_value):
                    duplicates += 1
                    continue
                    
                if self.import_image(path) is not None:
                    successful += 1
        
        return successful, duplicates, total
    
    def get_image_list(self) -> List[Path]:
        """
        Get list of all imported images.
        
        Returns:
            List of paths to imported images
        """
        return [
            self.image_dir / metadata.path
            for metadata in self.db.list_images()
        ]
    
    def get_image_metadata(self, image_id: str) -> Optional[ImageMetadata]:
        """
        Get metadata for an image.
        
        Args:
            image_id: ID of the image
            
        Returns:
            Image metadata or None if not found
        """
        return self.db.get_image(image_id)
    
    def update_image_metadata(self, image_id: str, **updates) -> bool:
        """
        Update image metadata.
        
        Args:
            image_id: ID of the image to update
            **updates: Fields to update and their new values
            
        Returns:
            True if successful, False if image not found
        """
        return self.db.update_image(image_id, **updates)
    
    def delete_image(self, image_id: str) -> bool:
        """
        Delete an image and its metadata.
        
        Args:
            image_id: ID of the image to delete
            
        Returns:
            True if successful, False if image not found
        """
        metadata = self.db.get_image(image_id)
        if not metadata:
            return False
        
        # Delete file
        image_path = self.image_dir / metadata.path
        try:
            image_path.unlink()
        except OSError:
            print(f"Error deleting image file: {image_path}")
            return False
        
        # Delete metadata
        return self.db.delete_image(image_id)
    
    def search_images(self, tags: Optional[List[str]] = None) -> List[ImageMetadata]:
        """
        Search images by tags.
        
        Args:
            tags: List of tags to search for (if None, returns all images)
            
        Returns:
            List of matching image metadata
        """
        return self.db.search_images(tags) 