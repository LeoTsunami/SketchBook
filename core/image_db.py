"""
Local database for image metadata management.
"""
import json
import re
import shutil
import threading
import time
import random
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Callable
from core.settings import settings
from core.user_data import user_data
from dataclasses import dataclass, asdict, field, fields

# Global shuffle timestamp used as part of the seed for course_random shuffles.
# Initialized at import time so each application run starts with a different
# base order in "Session Course Random" mode, then updated again on each
# manual Shuffle click.
_shuffle_timestamp = int(time.time() * 1000000)

# Windows: file in use / permission denied when renaming
_SAVE_RETRY_COUNT = 5
_SAVE_RETRY_DELAY_S = 0.15
_DEBOUNCE_SAVE_DELAY_S = 0.45
# Backup: one backup file before each save so a corrupted write can be recovered
_IMAGES_DB_BACKUP_SUFFIX = ".bak"

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
    kind: str = "single"  # "single" | "turnaround"
    member_ids: List[str] = field(default_factory=list)  # ordered poses (turnaround root)
    group_id: str = ""  # turnaround root id (members only)
    hidden: bool = False  # True for members hidden from grid/session


_IMAGE_METADATA_FIELD_NAMES = {f.name for f in fields(ImageMetadata)}


def metadata_from_dict(raw: Dict[str, Any]) -> ImageMetadata:
    """
    Build ImageMetadata from a JSON row, ignoring unknown keys.

    Args:
        raw: Raw metadata dict from images.json.

    Returns:
        ImageMetadata: Parsed row with tags coerced to a set.
    """
    data: Dict[str, Any] = {
        k: v for k, v in raw.items() if k in _IMAGE_METADATA_FIELD_NAMES
    }
    if "tags" in data and isinstance(data["tags"], list):
        data["tags"] = set(data["tags"])
    if "member_ids" in data and not isinstance(data["member_ids"], list):
        data["member_ids"] = list(data["member_ids"] or [])
    return ImageMetadata(**data)


class ImageDatabase:
    """Local database for image metadata."""
    
    def __init__(self):
        """Initialize the database."""
        # Use user data directory for database
        self._db_path = user_data.get_images_db_path()
        self._backup_path = self._db_path.parent / (self._db_path.name + _IMAGES_DB_BACKUP_SUFFIX)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._images = {}
        self._save_lock = threading.Lock()
        self._dirty = False
        self._save_timer = None  # threading.Timer for debounced save
        self._load_db()
    
    def _load_data_from_path(self, path: Path) -> Optional[Dict]:
        """Load and parse JSON from path. Returns dict of id -> metadata dict, or None on error."""
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def _try_restore_from_backup(self) -> bool:
        """
        If main DB is missing or corrupted, try loading from backup.
        On success, sets self._images and overwrites main file with backup. Returns True.
        """
        data = self._load_data_from_path(self._backup_path)
        if data is None:
            return False
        try:
            self._images = {
                id_: metadata_from_dict(metadata)
                for id_, metadata in data.items()
            }
        except (TypeError, KeyError):
            return False
        try:
            shutil.copy2(self._backup_path, self._db_path)
        except OSError:
            pass
        print("Image database restored from backup (images.json.bak).")
        return True

    def _load_db(self):
        """Load the database from disk. Tries to repair common JSON errors (e.g. trailing commas)."""
        if not self._db_path.exists():
            if self._try_restore_from_backup():
                return
            return
        try:
            with open(self._db_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._images = {
                id_: metadata_from_dict(metadata)
                for id_, metadata in data.items()
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
                            id_: metadata_from_dict(metadata)
                            for id_, metadata in data.items()
                        }
                        self._save_db()
                        print(
                            "Image database repaired (truncated last entry removed) and saved."
                        )
                        return
                    except json.JSONDecodeError:
                        pass
                print(f"Error loading image database: {e}")
                if self._try_restore_from_backup():
                    return
                self._images = {}
                return
            self._images = {
                id_: metadata_from_dict(metadata)
                for id_, metadata in data.items()
            }
            self._save_db()
            print("Image database repaired (trailing commas removed) and saved.")
        except Exception as e:
            print(f"Error loading image database: {str(e)}")
            if self._try_restore_from_backup():
                return
            self._images = {}
    
    def _save_db_impl(self) -> None:
        """Write DB to a temp file then replace target. Backup current file before overwrite."""
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
        # Backup current DB before overwrite so corruption can be recovered
        if self._db_path.exists():
            try:
                shutil.copy2(self._db_path, self._backup_path)
            except OSError:
                pass  # Non-fatal; proceed with replace
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
    
    def snapshot_metadata_values(self) -> List[ImageMetadata]:
        """
        Return a copy of all metadata objects under the save lock.

        Safe to pass to a background thread for sorting (read-only snapshot).

        Returns:
            List of all ImageMetadata rows currently in memory.
        """
        with self._save_lock:
            return list(self._images.values())

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

    def update_images(self, updates: Dict[str, dict]) -> int:
        """
        Update multiple image metadata rows, then request a single save.

        Args:
            updates: Mapping of image_id -> field kwargs to apply.

        Returns:
            Number of images successfully updated.
        """
        updated = 0
        for image_id, fields in updates.items():
            if image_id not in self._images:
                continue
            metadata = self._images[image_id]
            for key, value in fields.items():
                if hasattr(metadata, key):
                    setattr(metadata, key, value)
            updated += 1
        if updated:
            self._request_save()
        return updated
    
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

    def remove_tag(self, tag_name: str) -> int:
        """
        Remove a tag from every image that has it.

        Args:
            tag_name: Tag to remove.

        Returns:
            Number of images updated.
        """
        return self.remove_tags({tag_name})

    def remove_tags(
        self,
        tag_names: Set[str],
        progress: Optional[Callable[[int, int], None]] = None,
    ) -> int:
        """
        Remove several tags from every image that has them (single DB save).

        Args:
            tag_names: Tags to remove.
            progress: Optional callback ``(current_index, total_images)`` while scanning.

        Returns:
            Number of images updated.
        """
        tag_names = {t for t in tag_names if t}
        if not tag_names:
            return 0
        items = list(self._images.values())
        total = len(items)
        if progress:
            progress(0, max(1, total))
        count = 0
        emit_every = 25
        for index, metadata in enumerate(items, start=1):
            if metadata.tags & tag_names:
                metadata.tags -= tag_names
                count += 1
            if progress and (
                index % emit_every == 0 or index == total
            ):
                progress(index, total)
        if count:
            self._request_save()
        return count

    def add_tags_to_images(
        self,
        image_ids: List[str],
        tag_names: Set[str],
        progress: Optional[Callable[[int, int], None]] = None,
    ) -> int:
        """
        Add tags to a specific list of images (single DB save).

        Args:
            image_ids: Images to update.
            tag_names: Tags to add on each image.
            progress: Optional callback ``(current_index, total_ids)`` while scanning.

        Returns:
            Number of images updated.
        """
        tag_names = {t for t in tag_names if t}
        if not tag_names or not image_ids:
            return 0
        total = len(image_ids)
        if progress:
            progress(0, max(1, total))
        count = 0
        emit_every = 25
        for index, image_id in enumerate(image_ids, start=1):
            metadata = self._images.get(image_id)
            if metadata is None:
                continue
            before = len(metadata.tags)
            metadata.tags.update(tag_names)
            if len(metadata.tags) != before:
                count += 1
            if progress and (index % emit_every == 0 or index == total):
                progress(index, total)
        if count:
            self._request_save()
        return count

    def remove_tags_from_images(
        self,
        image_ids: List[str],
        tag_names: Set[str],
        progress: Optional[Callable[[int, int], None]] = None,
    ) -> int:
        """
        Remove tags from a specific list of images (single DB save).

        Args:
            image_ids: Images to update.
            tag_names: Tags to remove from each image.
            progress: Optional callback ``(current_index, total_ids)`` while scanning.

        Returns:
            Number of images updated.
        """
        tag_names = {t for t in tag_names if t}
        if not tag_names or not image_ids:
            return 0
        total = len(image_ids)
        if progress:
            progress(0, max(1, total))
        count = 0
        emit_every = 25
        for index, image_id in enumerate(image_ids, start=1):
            metadata = self._images.get(image_id)
            if metadata is None:
                continue
            if metadata.tags & tag_names:
                metadata.tags -= tag_names
                count += 1
            if progress and (index % emit_every == 0 or index == total):
                progress(index, total)
        if count:
            self._request_save()
        return count

    def list_images(
        self, sort_by: str = "import_date_desc", *, visible_only: bool = False
    ) -> List[ImageMetadata]:
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
            visible_only: If True, skip images marked ``hidden`` (turnaround members).

        Returns:
            List of all image metadata, sorted
        """
        images = list(self._images.values())
        if visible_only:
            images = [m for m in images if not m.hidden]
        return self._sort_images(images, sort_by)
    
    def _shuffle_images_for_session(self, images: List[ImageMetadata], shuffle_iteration: int = 0) -> List[ImageMetadata]:
        """
        Shuffle images using seed based on image IDs, shuffle iteration, and current time.
        
        This ensures different random orders on each shuffle while keeping them deterministic
        for the same shuffle_iteration within a short time window.
        Uses the same algorithm as Course sessions.
        
        Args:
            images: List of ImageMetadata to shuffle.
            shuffle_iteration: Iteration counter (0 = default, increments on each shuffle).
                              Each increment generates a new random order.
            
        Returns:
            Shuffled list (new order on each shuffle).
        """
        if not images:
            return images
        
        # Create seed from sorted image IDs, shuffle iteration, and global shuffle timestamp
        # Reason: Include timestamp to ensure different orders on each shuffle
        # The shuffle_iteration ensures that clicking shuffle multiple times gives different orders
        global _shuffle_timestamp
        ids_sorted = sorted([m.id for m in images])
        seed_string = "|".join(ids_sorted) + f"|iter_{shuffle_iteration}|ts_{_shuffle_timestamp}"
        seed = int(hashlib.md5(seed_string.encode()).hexdigest(), 16) % (2**31)
        
        # Shuffle using the seed
        shuffled = list(images)
        random.Random(seed).shuffle(shuffled)
        return shuffled
    
    def _sort_images(self, images: List[ImageMetadata], sort_by: str, shuffle_iteration: int = 0) -> List[ImageMetadata]:
        """
        Sort images according to the specified criteria.
        
        Args:
            images: List of images to sort
            sort_by: Sort order string
            shuffle_iteration: Iteration counter for course_random sort (allows regenerating order)
            
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
        elif sort_by == "course_random":
            # Random shuffle using the same algorithm as Course sessions
            # Reason: Allows users to preview the session order before starting
            return self._shuffle_images_for_session(images, shuffle_iteration=shuffle_iteration)
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