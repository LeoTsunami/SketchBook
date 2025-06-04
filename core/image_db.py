"""
Local database for image metadata management.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from core.settings import settings

class ImageMetadata(BaseModel):
    """Model for image metadata."""
    
    id: str = Field(..., description="Unique identifier (filename without extension)")
    path: Path = Field(..., description="Path to image file relative to storage directory")
    original_filename: str = Field(..., description="Original filename before import")
    import_date: datetime = Field(default_factory=datetime.now)
    width: int = Field(..., description="Image width in pixels")
    height: int = Field(..., description="Image height in pixels")
    file_size: int = Field(..., description="File size in bytes")
    format: str = Field(..., description="Image format (e.g., 'JPEG', 'PNG')")
    hash: str = Field(..., description="SHA-256 hash of image content")
    tags: List[str] = Field(default_factory=list, description="User-defined tags")
    notes: str = Field(default="", description="User notes about the image")

class ImageDatabase:
    """Local database for image metadata."""
    
    def __init__(self):
        """Initialize the database."""
        self.db_path = Path(settings.get("images.db_path", "data/config/images.json"))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_db()
    
    def _load_db(self):
        """Load database from file."""
        if self.db_path.exists():
            try:
                data = json.loads(self.db_path.read_text())
                self._images = {
                    id_: ImageMetadata(**metadata)
                    for id_, metadata in data.items()
                }
            except Exception as e:
                print(f"Error loading image database: {e}")
                self._images = {}
        else:
            self._images = {}
    
    def _save_db(self):
        """Save database to file."""
        data = {
            id_: metadata.model_dump()
            for id_, metadata in self._images.items()
        }
        self.db_path.write_text(json.dumps(data, indent=2, default=str))
    
    def add_image(self, metadata: ImageMetadata) -> bool:
        """
        Add image metadata to database.
        
        Args:
            metadata: Image metadata to add
            
        Returns:
            True if successful, False if image already exists
        """
        if metadata.id in self._images:
            return False
        
        self._images[metadata.id] = metadata
        self._save_db()
        return True
    
    def get_image(self, image_id: str) -> Optional[ImageMetadata]:
        """
        Get image metadata by ID.
        
        Args:
            image_id: Image ID to look up
            
        Returns:
            Image metadata or None if not found
        """
        return self._images.get(image_id)
    
    def update_image(self, image_id: str, **updates) -> bool:
        """
        Update image metadata.
        
        Args:
            image_id: ID of image to update
            **updates: Fields to update and their new values
            
        Returns:
            True if successful, False if image not found
        """
        if image_id not in self._images:
            return False
        
        metadata = self._images[image_id]
        for field, value in updates.items():
            setattr(metadata, field, value)
        
        self._save_db()
        return True
    
    def delete_image(self, image_id: str) -> bool:
        """
        Delete image metadata.
        
        Args:
            image_id: ID of image to delete
            
        Returns:
            True if successful, False if image not found
        """
        if image_id not in self._images:
            return False
        
        del self._images[image_id]
        self._save_db()
        return True
    
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
        
        return [
            metadata for metadata in self._images.values()
            if all(tag in metadata.tags for tag in tags)
        ] 