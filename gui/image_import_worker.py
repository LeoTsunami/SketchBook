"""
Worker class for handling image imports in a background thread.
"""
from pathlib import Path
from typing import List
import traceback
from qtpy.QtCore import QObject, QRunnable, Signal, Slot, QThread

class ImageImportSignals(QObject):
    """Signals for the image import worker."""
    progress = Signal(int, int)  # current, total
    finished = Signal(int, int, int)  # successful, duplicates, total
    error = Signal(str)
    log = Signal(str, str)  # message, level

class ImageImportWorker(QRunnable):
    """Worker for importing images in a background thread."""
    
    def __init__(self, image_manager, paths: List[Path]):
        """
        Initialize the worker.
        
        Args:
            image_manager: ImageManager instance
            paths: List of paths to import
        """
        super().__init__()
        self.image_manager = image_manager
        self.paths = paths
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
                        self._log(f"Found {len(found_images)} images in directory: {path}")
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
                    
                    # Check for duplicates
                    try:
                        hash_value = self.image_manager._compute_image_hash(path)
                    except Exception as e:
                        self._log(f"Error computing hash for {path.name}: {str(e)}", "ERROR")
                        self._log(traceback.format_exc(), "ERROR")
                        errors += 1
                        self._emit_progress(i, total)
                        continue
                    
                    try:
                        if self.image_manager._is_duplicate(path, hash_value):
                            self._log(f"Skipping duplicate: {path.name}", "INFO")
                            duplicates += 1
                        else:
                            result = self.image_manager.import_image(path)
                            if result is not None:
                                successful += 1
                                self._log(f"Successfully imported: {path.name}")
                            else:
                                self._log(f"Failed to import: {path.name}", "ERROR")
                                errors += 1
                    except Exception as e:
                        self._log(f"Error processing {path.name}: {str(e)}", "ERROR")
                        self._log(traceback.format_exc(), "ERROR")
                        errors += 1
                        continue
                    finally:
                        # Emit progress even if there was an error
                        self._emit_progress(i, total)
                    
                except Exception as e:
                    self._log(f"Unexpected error processing {path.name}: {str(e)}", "ERROR")
                    self._log(traceback.format_exc(), "ERROR")
                    errors += 1
                    self._emit_progress(i, total)
                    continue
            
            # Ensure we emit 100% progress
            self._emit_progress(total, total)
            
            # Final summary
            self._log(f"Import completed. Success: {successful}, Duplicates: {duplicates}, Errors: {errors}, Total: {total}")
            
            # Emit final results
            self.signals.finished.emit(successful, duplicates, total)
            
        except Exception as e:
            error_msg = f"Critical error during import: {str(e)}"
            self._log(error_msg, "ERROR")
            self._log(traceback.format_exc(), "ERROR")
            self.signals.error.emit(error_msg) 