"""
Local database for image metadata management.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from core.settings import settings
from core.user_data import user_data
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
    import_date: str = ""  # ISO format date string of when image was imported

class ImageDatabase:
    """Local database for image metadata."""
    
    def __init__(self):
        """Initialize the database."""
        # Use user data directory for database
        self._db_path = user_data.get_images_db_path()
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
    
    def list_images(self, sort_by: str = "import_date_desc") -> List[ImageMetadata]:
        """
        Get list of all image metadata, optionally sorted.
        
        Args:
            sort_by: Sort order. Options:
                - "import_date_desc": Most recent first (default)
                - "import_date_asc": Oldest first
                - "filename_asc": Filename A→Z
                - "filename_desc": Filename Z→A
        
        Returns:
            List of all image metadata, sorted
        """
        images = list(self._images.values())
        return self._sort_images(images, sort_by)
    
    def _sort_images(self, images: List[ImageMetadata], sort_by: str) -> List[ImageMetadata]:
        """
        Sort images according to the specified criteria.
        
        Args:
            images: List of images to sort
            sort_by: Sort order string
            
        Returns:
            Sorted list of images
        """
        if not images:
            return images
        
        # Sentinel for missing import_date: sort last in both directions
        # Reason: old images (imported before import_date existed) have "" and would
        # otherwise keep arbitrary dict order instead of true date order
        SENTINEL_OLDEST = "0000-00-00T00:00:00"
        SENTINEL_NEWEST = "9999-12-31T23:59:59"

        # Default: most recent first
        if sort_by == "import_date_desc":
            return sorted(
                images,
                key=lambda m: m.import_date if m.import_date else SENTINEL_OLDEST,
                reverse=True
            )
        elif sort_by == "import_date_asc":
            return sorted(
                images,
                key=lambda m: m.import_date if m.import_date else SENTINEL_NEWEST
            )
        elif sort_by == "filename_asc":
            return sorted(
                images,
                key=lambda m: m.original_filename.lower()
            )
        elif sort_by == "filename_desc":
            return sorted(
                images,
                key=lambda m: m.original_filename.lower(),
                reverse=True
            )
        else:
            # Default fallback: most recent first
            return sorted(
                images,
                key=lambda m: m.import_date if m.import_date else SENTINEL_OLDEST,
                reverse=True
            )
    
    def search_images(self, tags: Optional[List[str]] = None, sort_by: str = "import_date_desc") -> List[ImageMetadata]:
        """
        Search images by tags.
        
        .. deprecated:: 0.1.0
            Use :meth:`search_images_advanced` instead for more flexible filtering.
        
        Args:
            tags: List of tags to search for (if None, returns all images)
            sort_by: Sort order (see list_images for options)
            
        Returns:
            List of matching image metadata, sorted
        """
        if not tags:
            return self.list_images(sort_by)
            
        tag_set = set(tags)
        matching = [
            metadata
            for metadata in self._images.values()
            if metadata.tags & tag_set == tag_set
        ]
        return self._sort_images(matching, sort_by)
    
    def search_images_advanced(self, and_tags: Set[str] = None, or_tags: Set[str] = None, sort_by: str = "import_date_desc") -> List[ImageMetadata]:
        """
        Advanced search with AND and OR tag filtering.
        
        Args:
            and_tags: Set of tags that must ALL be present (AND logic)
            or_tags: Set of tags where at least ONE must be present (OR logic)
            sort_by: Sort order (see list_images for options)
            
        Returns:
            List of matching image metadata, sorted
        """
        if not and_tags and not or_tags:
            return self.list_images(sort_by)
        
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
        
        return self._sort_images(matching_images, sort_by) 