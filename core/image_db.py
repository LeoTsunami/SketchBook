"""
Local database for image metadata management.
"""
import json
import re
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from core.settings import settings
from core.user_data import user_data
from dataclasses import dataclass, asdict, field

# Windows: file in use / permission denied when renaming
_SAVE_RETRY_COUNT = 5
_SAVE_RETRY_DELAY_S = 0.15
_DEBOUNCE_SAVE_DELAY_S = 0.45

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
        self._save_lock = threading.Lock()
        self._dirty = False
        self._save_timer = None  # threading.Timer for debounced save
        self._load_db()
    
    def _load_db(self):
        """Load the database from disk. Tries to repair common JSON errors (e.g. trailing commas)."""
        if not self._db_path.exists():
            return
        try:
            with open(self._db_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._images = {
                id: ImageMetadata(**{
                    k: set(v) if k == "tags" else v
                    for k, v in metadata.items()
                })
                for id, metadata in data.items()
            }
        except json.JSONDecodeError as e:
            # Try to repair: trailing commas, then truncated last entry
            with open(self._db_path, "r", encoding="utf-8") as f:
                raw = f.read()
            repaired = None
            try:
                repaired = re.sub(r",(\s*})", r"\1", raw)
                repaired = re.sub(r",(\s*])", r"\1", repaired)
                data = json.loads(repaired)
            except json.JSONDecodeError:
                repaired = None
            if repaired is None:
                # Truncated file: remove last incomplete entry (root entries end with "  },")
                last_complete = raw.rfind("\n  },")
                if last_complete >= 0:
                    # Keep content up to "  }" (no trailing comma), then close root
                    repaired = raw[: last_complete + 4] + "\n}\n"
                    try:
                        data = json.loads(repaired)
                        self._images = {
                            id: ImageMetadata(**{
                                k: set(v) if k == "tags" else v
                                for k, v in metadata.items()
                            })
                            for id, metadata in data.items()
                        }
                        self._save_db()
                        print(
                            "Image database repaired (truncated last entry removed) and saved."
                        )
                        return
                    except json.JSONDecodeError:
                        pass
                print(f"Error loading image database: {e}")
                self._images = {}
                return
            self._images = {
                id: ImageMetadata(**{
                    k: set(v) if k == "tags" else v
                    for k, v in metadata.items()
                })
                for id, metadata in data.items()
            }
            self._save_db()
            print("Image database repaired (trailing commas removed) and saved.")
        except Exception as e:
            print(f"Error loading image database: {str(e)}")
            self._images = {}
    
    def _save_db_impl(self) -> None:
        """Write DB to a temp file then replace target. Retry on Windows 'file in use'."""
        tmp_path = self._db_path.with_suffix(self._db_path.suffix + ".tmp")
        data = {
            id: {
                k: list(v) if k == "tags" else v
                for k, v in asdict(metadata).items()
            }
            for id, metadata in self._images.items()
        }
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        # On Windows, replace() can fail with WinError 32 if target is still in use; retry
        last_error = None
        for attempt in range(_SAVE_RETRY_COUNT):
            try:
                tmp_path.replace(self._db_path)
                return
            except OSError as e:
                last_error = e
                if attempt < _SAVE_RETRY_COUNT - 1:
                    time.sleep(_SAVE_RETRY_DELAY_S)
        print(f"Error saving image database: {last_error}")

    def _save_db(self) -> None:
        """Save the database to disk (serialized, for immediate save e.g. repair)."""
        with self._save_lock:
            self._save_db_impl()

    def _request_save(self) -> None:
        """Mark dirty and schedule a single save after a short delay (debounced)."""
        self._dirty = True
        if self._save_timer is None or not self._save_timer.is_alive():
            self._save_timer = threading.Timer(_DEBOUNCE_SAVE_DELAY_S, self._flush_save)
            self._save_timer.start()

    def _flush_save(self) -> None:
        """Timer callback: save once if dirty, then clear timer."""
        with self._save_lock:
            if self._dirty:
                self._dirty = False
                self._save_db_impl()
        self._save_timer = None

    def flush_pending_save(self) -> None:
        """
        Cancel any pending debounced save and write immediately if dirty.
        Call on app exit so the last changes are not lost.
        """
        if self._save_timer is not None and self._save_timer.is_alive():
            self._save_timer.cancel()
            self._save_timer = None
        with self._save_lock:
            if self._dirty:
                self._dirty = False
                self._save_db_impl()
    
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
        self._request_save()
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

        self._request_save()
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
            self._request_save()
            return True
        return False

    def rename_tag(self, old_name: str, new_name: str) -> int:
        """
        Rename a tag on all images that have it.
        Replaces old_name with new_name in each image's tags.

        Args:
            old_name: Current tag name.
            new_name: New tag name.

        Returns:
            Number of images updated.
        """
        if not old_name or not new_name or old_name == new_name:
            return 0
        count = 0
        for metadata in self._images.values():
            if old_name in metadata.tags:
                metadata.tags.discard(old_name)
                metadata.tags.add(new_name)
                count += 1
        if count:
            self._request_save()
        return count

    def list_images(self, sort_by: str = "import_date_desc") -> List[ImageMetadata]:
        """
        Get list of all image metadata, optionally sorted.
        
        Args:
            sort_by: Sort order. Options:
                - "import_date_desc": Most recent first (default)
                - "import_date_asc": Oldest first
                - "filename_asc": Filename A→Z
                - "filename_desc": Filename Z→A
                - "file_size_asc": Lightest first (smallest file size)
                - "file_size_desc": Heaviest first (largest file size)
        
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
        elif sort_by == "file_size_asc":
            return sorted(images, key=lambda m: m.file_size)
        elif sort_by == "file_size_desc":
            return sorted(images, key=lambda m: m.file_size, reverse=True)
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