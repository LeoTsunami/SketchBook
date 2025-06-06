"""
Worker for asynchronous image loading.
"""
from pathlib import Path
from qtpy.QtCore import QObject, Signal, QRunnable, Qt
from qtpy.QtGui import QImage, QPixmap

class ImageLoaderSignals(QObject):
    """Signals for the image loader worker."""
    finished = Signal(str, QPixmap)  # image_id, pixmap
    error = Signal(str, str)  # image_id, error message

class ImageLoaderWorker(QRunnable):
    """Worker for loading and scaling images asynchronously."""
    
    def __init__(self, image_id: str, image_path: Path, target_size: tuple[int, int]):
        """
        Initialize the worker.
        
        Args:
            image_id: Unique identifier of the image
            image_path: Path to the image file
            target_size: Target size (width, height) for the scaled image
        """
        super().__init__()
        self.image_id = image_id
        self.image_path = image_path
        self.target_size = target_size
        self.signals = ImageLoaderSignals()
        
        # Set low priority to avoid blocking UI
        self.setAutoDelete(True)
    
    def run(self):
        """Load and scale the image."""
        try:
            print(f"[DEBUG] Starting to load image: {self.image_path}")
            
            if not self.image_path.exists():
                print(f"[DEBUG] Image not found: {self.image_path}")
                raise FileNotFoundError(f"Image not found: {self.image_path}")
            
            # Load image
            print(f"[DEBUG] Loading image with QImage")
            image = QImage(str(self.image_path))
            if image.isNull():
                print(f"[DEBUG] QImage is null for: {self.image_path}")
                raise ValueError(f"Failed to load image: {self.image_path}")
            
            print(f"[DEBUG] Creating QPixmap from image")
            # Create pixmap and scale
            pixmap = QPixmap.fromImage(image)
            print(f"[DEBUG] Original image size: {pixmap.width()}x{pixmap.height()}")
            
            # Calculate scaled size preserving aspect ratio
            target_width, target_height = self.target_size
            original_ratio = pixmap.width() / pixmap.height()
            target_ratio = target_width / target_height
            
            if original_ratio > target_ratio:
                # Image is wider than target
                new_width = target_width
                new_height = int(target_width / original_ratio)
            else:
                # Image is taller than target
                new_height = target_height
                new_width = int(target_height * original_ratio)
            
            print(f"[DEBUG] Scaling to: {new_width}x{new_height}")
            # Scale with high quality and proper aspect ratio
            scaled = pixmap.scaled(
                new_width,
                new_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            print(f"[DEBUG] Scaled size: {scaled.width()}x{scaled.height()}")
            
            print(f"[DEBUG] Emitting finished signal")
            # Emit result
            self.signals.finished.emit(self.image_id, scaled)
            
        except Exception as e:
            print(f"[DEBUG] Error loading image: {str(e)}")
            self.signals.error.emit(self.image_id, str(e)) 