"""
Local database for image metadata management.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field
from core.settings import settings
from dataclasses import dataclass, asdict, field

@dataclass
class ImageMetadata:
    """Metadata for an imported image."""
    id: str
    path: str
    original_filename: str
    width: int
    height: int
    file_size: int
    format: str
    original_path: str = ""  # Path to the original image file
    tags: Set[str] = field(default_factory=set)

class ImageDatabase:
    """Local database for image metadata."""
    
    def __init__(self):
        """Initialize the database."""
        self._db_path = Path(settings.get("images.db_path", "data/config/images.json")).resolve()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._images = {}
        self._load_db()
    
    def _load_db(self):
        """Load the database from disk."""
        try:
            if self._db_path.exists():
                with open(self._db_path, "r") as f:
                    data = json.load(f)
                    self._images = {
                        id: ImageMetadata(**{
                            k: set(v) if k == "tags" else v
                            for k, v in metadata.items()
                        })
                        for id, metadata in data.items()
                    }
        except Exception as e:
            print(f"Error loading image database: {str(e)}")
            self._images = {}
    
    def _save_db(self):
        """Save the database to disk."""
        try:
            with open(self._db_path, "w") as f:
                json.dump(
                    {
                        id: {
                            k: list(v) if k == "tags" else v
                            for k, v in asdict(metadata).items()
                        }
                        for id, metadata in self._images.items()
                    },
                    f,
                    indent=2
                )
        except Exception as e:
            print(f"Error saving image database: {str(e)}")
    
    def add_image(self, metadata: ImageMetadata):
        """
        Add image metadata only if it does not already exist.
        
        Args:
            metadata: Image metadata to add
        Returns:
            True if added, False if already exists
        """
        if metadata.id in self._images:
            return False
        self._images[metadata.id] = metadata
        self._save_db()
        return True
    
    def get_image(self, image_id: str) -> Optional[ImageMetadata]:
        """
        Get metadata for an image.
        
        Args:
            image_id: ID of the image
            
        Returns:
            Image metadata or None if not found
        """
        return self._images.get(image_id)
    
    def update_image(self, image_id: str, **updates) -> bool:
        """
        Update image metadata.
        
        Args:
            image_id: ID of the image to update
            **updates: Fields to update and their new values
            
        Returns:
            True if successful, False if image not found
        """
        if image_id not in self._images:
            return False
            
        metadata = self._images[image_id]
        for key, value in updates.items():
            if hasattr(metadata, key):
                setattr(metadata, key, value)
        
        self._save_db()
        return True
    
    def delete_image(self, image_id: str) -> bool:
        """
        Delete image metadata.
        
        Args:
            image_id: ID of the image to delete
            
        Returns:
            True if successful, False if image not found
        """
        if image_id in self._images:
            del self._images[image_id]
            self._save_db()
            return True
        return False
    
    def list_images(self) -> List[ImageMetadata]:
        """
        Get list of all image metadata.
        
        Returns:
            List of all image metadata
        """
        return list(self._images.values())
    
    def search_images(self, tags: Optional[List[str]] = None) -> List[ImageMetadata]:
        """
        Search images by tags.
        
        Args:
            tags: List of tags to search for (if None, returns all images)
            
        Returns:
            List of matching image metadata
        """
        if not tags:
            return self.list_images()
            
        tag_set = set(tags)
        return [
            metadata
            for metadata in self._images.values()
            if metadata.tags & tag_set == tag_set
        ]
    
    def search_images_advanced(self, and_tags: Set[str] = None, or_tags: Set[str] = None) -> List[ImageMetadata]:
        """
        Advanced search with AND and OR tag filtering.
        
        Args:
            and_tags: Set of tags that must ALL be present (AND logic)
            or_tags: Set of tags where at least ONE must be present (OR logic)
            
        Returns:
            List of matching image metadata
        """
        if not and_tags and not or_tags:
            return self.list_images()
        
        matching_images = []
        
        for metadata in self._images.values():
            image_tags = metadata.tags
            
            # Check AND condition
            and_condition = True
            if and_tags:
                and_condition = and_tags.issubset(image_tags)
            
            # Check OR condition
            or_condition = True
            if or_tags:
                or_condition = bool(image_tags & or_tags)
            
            # Both conditions must be met
            if and_condition and or_condition:
                matching_images.append(metadata)
        
        return matching_images 