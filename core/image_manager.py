"""
Image management system for handling imports and processing.
"""
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple, Set
from PIL import Image
from core.settings import settings
from core.image_db import ImageDatabase, ImageMetadata
from core.user_data import user_data
from utils.file_utils import ensure_dir, safe_path

class ImageManager:
    """Manages image importing, processing, and storage."""
    
    SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png"}
    MAX_WIDTH = 1920  # Maximum width for imported images
    
    def __init__(self):
        """Initialize the image manager."""
        # Use user data directory for images
        self.image_dir = user_data.get_images_dir()
        ensure_dir(self.image_dir)
        self.db = ImageDatabase()
    
    def _is_duplicate(self, source_path: Path, source_img: Image.Image) -> bool:
        """
        Check if an image is already imported by comparing name, size and resolution.
        
        Args:
            source_path: Path to the source image
            source_img: PIL Image object of the source image
            
        Returns:
            True if the image is a duplicate
        """
        print(f"\n=== Starting duplicate check for: {source_path} ===")
        source_name = source_path.stem.lower()  # Nom sans extension en minuscules
        source_size = source_path.stat().st_size
        source_resolution = source_img.size
        
        print(f"Source details:")
        print(f"- Name (without extension): {source_name}")
        print(f"- Size: {source_size} bytes")
        print(f"- Resolution: {source_resolution}")
        
        for metadata in self.db.list_images():
            # Si le chemin original est le même, c'est un doublon
            if metadata.original_path and Path(metadata.original_path) == source_path:
                print(f"\n=== DUPLICATE FOUND (same path) ===")
                print(f"Matches with: {metadata.original_filename}")
                return True
            
            # Compare la taille et la résolution
            if metadata.file_size == source_size and \
               metadata.width == source_resolution[0] and \
               metadata.height == source_resolution[1]:
                # Si même taille et résolution, on compare les noms (sans extension)
                existing_name = metadata.original_filename.rsplit('.', 1)[0].lower()
                if source_name == existing_name:
                    print(f"\n=== DUPLICATE FOUND ===")
                    print(f"Matches with: {metadata.original_filename}")
                    print(f"Same name: {source_name}")
                    print(f"Same size: {source_size}")
                    print(f"Same resolution: {source_resolution}")
                    return True
        
        print(f"\n=== No duplicates found ===\n")
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
            try:
                # Ouvrir l'image pour vérifier les doublons
                with Image.open(path) as img:
                    if self._is_duplicate(path, img):
                        duplicates += 1
                        continue
                        
                    if self.import_image(path) is not None:
                        successful += 1
            except Exception as e:
                print(f"Error processing image {path}: {str(e)}")
                continue
        
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
            
            # Ouvre l'image pour vérifier si c'est un doublon
            with Image.open(source_path) as img:
                if self._is_duplicate(source_path, img):
                    print(f"Skipping duplicate image: {source_path}")
                    return None
                
                # Create unique filename
                dest_filename = f"{source_path.stem}_{os.urandom(4).hex()}{source_path.suffix.lower()}"
                dest_path = safe_path(self.image_dir, dest_filename)
                
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
                    original_path=str(source_path)
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
                try:
                    # Ouvrir l'image pour vérifier les doublons
                    with Image.open(path) as img:
                        if self._is_duplicate(path, img):
                            duplicates += 1
                            continue
                            
                        if self.import_image(path) is not None:
                            successful += 1
                except Exception as e:
                    print(f"Error processing image {path}: {str(e)}")
                    continue
        
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
        
        .. deprecated:: 0.1.0
            Use :meth:`search_images_advanced` instead for more flexible filtering.
        
        Args:
            tags: List of tags to search for (if None, returns all images)
            
        Returns:
            List of matching image metadata
        """
        return self.db.search_images(tags)
    
    def get_all_tags(self) -> List[str]:
        """
        Get a sorted list of all unique tags in the image database.
        
        Returns:
            List of unique tags
        """
        tags = set()
        for metadata in self.db.list_images():
            tags.update(metadata.tags)
        return sorted(tags)
    
    def add_tags(self, image_id: str, tags: List[str]) -> bool:
        """
        Add tags to an image.
        
        Args:
            image_id: ID of the image to add tags to
            tags: List of tags to add
            
        Returns:
            True if successful, False if image not found
        """
        metadata = self.db.get_image(image_id)
        if not metadata:
            return False
        
        # Add new tags to existing tags
        metadata.tags.update(tags)
        
        # Update the database
        return self.db.update_image(image_id, tags=metadata.tags)
    
    def search_images_advanced(self, and_tags: Set[str] = None, or_tags: Set[str] = None) -> List[ImageMetadata]:
        """
        Advanced search with AND and OR tag filtering.
        
        Args:
            and_tags: Set of tags that must ALL be present (AND logic)
            or_tags: Set of tags where at least ONE must be present (OR logic)
            
        Returns:
            List of matching image metadata
        """
        return self.db.search_images_advanced(and_tags, or_tags) 