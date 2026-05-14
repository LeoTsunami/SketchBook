"""
Worker class for handling image imports in a background thread.
"""

from pathlib import Path
from typing import List, Set, Optional, FrozenSet
import traceback
from PIL import Image
from qtpy.QtCore import QObject, QRunnable, Signal, Slot


class ImageImportSignals(QObject):
    """Signals for the image import worker."""

    progress = Signal(int, int)  # current, total
    finished = Signal(int, int, int)  # successful, duplicates, total
    error = Signal(str)
    log = Signal(str, str)  # message, level
    image_imported = Signal(str)  # image_id of successfully imported image


class ImageImportWorker(QRunnable):
    """Worker for importing images in a background thread."""

    _ALLOWED_SUBFOLDER_SEPARATORS: FrozenSet[str] = frozenset({"-", "_", " ", "."})

    def __init__(
        self,
        image_manager,
        paths: List[Path],
        tags: Optional[Set[str]] = None,
        subfolder_tag_roots: Optional[List[Path]] = None,
        subfolder_split_separator: Optional[str] = None,
    ):
        """
        Initialize the worker.

        Args:
            image_manager: ImageManager instance
            paths: List of paths to import
            tags: Optional set of tags to apply to imported images
            subfolder_tag_roots: When set, each image gets extra tags derived from
                its subfolder names relative to the closest root directory.
            subfolder_split_separator: When set (and in the allowed set), each path
                segment is split on this character into several tags; each tag is
                capitalized. When None, each segment is one tag (capitalized).
        """
        super().__init__()
        self.image_manager = image_manager
        self.paths = paths
        self.tags = tags or set()
        self.subfolder_tag_roots = subfolder_tag_roots
        self.subfolder_split_separator = subfolder_split_separator
        self.signals = ImageImportSignals()
        self.setAutoDelete(True)

    def _emit_progress(self, current: int, total: int):
        """
        Emit progress signal with bounds checking.

        Args:
            current: Current progress
            total: Total items
        """
        # Ensure current doesn't exceed total
        current = min(current, total)
        self.signals.progress.emit(current, total)

    def _log(self, message: str, level: str = "INFO"):
        """Emit a log message."""
        self.signals.log.emit(message, level)

    def _subfolder_tags_for(self, image_path: Path) -> Set[str]:
        """
        Derive tag names from the subfolder hierarchy between a root dir and *image_path*.

        For ``root/Animals/Cats/img.jpg`` the returned set is ``{"Animals", "Cats"}``
        (capitalized). With split on ``_``, ``my_tag`` becomes ``{"My", "Tag"}``.

        Args:
            image_path: Absolute path to the image file.

        Returns:
            Set of folder-name tags (may be empty).
        """
        if not self.subfolder_tag_roots:
            return set()
        sep = self.subfolder_split_separator
        if sep not in self._ALLOWED_SUBFOLDER_SEPARATORS:
            sep = None
        for root in self.subfolder_tag_roots:
            try:
                rel = image_path.parent.relative_to(root)
            except ValueError:
                continue
            parts = [p for p in rel.parts if p]
            if not parts:
                continue
            out: Set[str] = set()
            for folder_name in parts:
                out.update(self._tokens_from_folder_segment(folder_name, sep))
            return out
        return set()

    def _tokens_from_folder_segment(
        self, folder_name: str, sep: Optional[str]
    ) -> Set[str]:
        """
        Build capitalized tag tokens from one path segment (one folder name).

        Args:
            folder_name: Single directory name (no path separators).
            sep: Allowed split character, or None for one token per segment.

        Returns:
            Non-empty capitalized tag strings.
        """
        raw = folder_name.strip()
        if not raw:
            return set()
        if sep is None:
            pieces = [raw]
        else:
            pieces = [p.strip() for p in raw.split(sep)]
            pieces = [p for p in pieces if p]
        result: Set[str] = set()
        for p in pieces:
            cap = p.capitalize()
            if cap:
                result.add(cap)
        return result

    @Slot()
    def run(self):
        """Run the import process."""
        try:
            # First, collect all image paths
            self._log("Scanning for images...")
            all_images = []
            for path in self.paths:
                try:
                    if path.is_dir():
                        found_images = self.image_manager.find_images_in_directory(path)
                        self._log(
                            f"Found {len(found_images)} images in directory: {path}"
                        )
                        all_images.extend(found_images)
                    else:
                        if path.suffix.lower() in self.image_manager.SUPPORTED_FORMATS:
                            all_images.append(path)
                        else:
                            self._log(f"Skipping unsupported file: {path}", "WARNING")
                except Exception as e:
                    self._log(f"Error scanning path {path}: {str(e)}", "ERROR")
                    self._log(traceback.format_exc(), "ERROR")

            total = len(all_images)
            if total == 0:
                self._log("No valid images found to import", "WARNING")
                self.signals.finished.emit(0, 0, 0)
                return

            self._log(f"Starting import of {total} images...")
            successful = 0
            duplicates = 0
            errors = 0

            # Emit initial progress
            self._emit_progress(0, total)

            # Process each image
            for i, path in enumerate(all_images, 1):
                try:
                    self._log(f"Processing {path.name} ({i}/{total})")

                    # Try to import the image directly - duplicate check is handled in import_image
                    result = self.image_manager.import_image(path)
                    if result is not None:
                        successful += 1
                        self._log(f"Successfully imported: {path.name}")

                        # Merge manually-selected tags with auto-detected subfolder tags
                        combined_tags = set(self.tags)
                        sf_tags = self._subfolder_tags_for(path)
                        combined_tags.update(sf_tags)

                        if combined_tags:
                            image_id = result.stem
                            tags_list = list(combined_tags)
                            if self.image_manager.add_tags(image_id, tags_list):
                                self._log(
                                    f"Applied {len(tags_list)} tag(s) to {path.name}"
                                )
                            else:
                                self._log(
                                    f"Warning: Could not apply tags to {path.name}",
                                    "WARNING",
                                )

                        # Emit signal with the stem (ID) of the imported image
                        self.signals.image_imported.emit(result.stem)
                    else:
                        # If result is None, it might be a duplicate or error
                        self._log(
                            f"Image not imported (possible duplicate): {path.name}",
                            "INFO",
                        )
                        duplicates += 1

                except Exception as e:
                    self._log(f"Error processing {path.name}: {str(e)}", "ERROR")
                    self._log(traceback.format_exc(), "ERROR")
                    errors += 1
                    continue
                finally:
                    # Emit progress even if there was an error
                    self._emit_progress(i, total)

            # Ensure we emit 100% progress
            self._emit_progress(total, total)

            # Final summary
            self._log(
                f"Import completed. Success: {successful}, Duplicates: {duplicates}, Errors: {errors}, Total: {total}"
            )

            # Emit final results
            self.signals.finished.emit(successful, duplicates, total)

        except Exception as e:
            error_msg = f"Critical error during import: {str(e)}"
            self._log(error_msg, "ERROR")
            self._log(traceback.format_exc(), "ERROR")
            self.signals.error.emit(error_msg)
