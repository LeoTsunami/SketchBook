"""
Worker for asynchronous image loading.
"""
from pathlib import Path
from qtpy.QtCore import QObject, Signal, QRunnable, Qt
from qtpy.QtGui import QImage, QPixmap

class ImageLoaderSignals(QObject):
    """Signals for the image loader worker."""
    finished = Signal(str, tuple)  # image_id, (fast_pixmap, high_quality_pixmap)
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
            if not self.image_path.exists():
                raise FileNotFoundError(f"Image not found: {self.image_path}")
            
            # Load image with QImage for better memory management
            image = QImage(str(self.image_path))
            if image.isNull():
                raise ValueError(f"Failed to load image: {self.image_path}")
            
            # Get target width and calculate new height based on aspect ratio
            target_width, _ = self.target_size
            
            if target_width > 0:
                # Calculate new height preserving aspect ratio
                aspect_ratio = image.width() / image.height()
                new_height = int(target_width / aspect_ratio)
                
                # First create a fast scaled version for immediate display
                fast_pixmap = QPixmap.fromImage(image.scaled(
                    target_width,
                    new_height,
                    Qt.KeepAspectRatio,
                    Qt.FastTransformation
                ))
                
                # Then create a high quality version
                high_quality_pixmap = QPixmap.fromImage(image.scaled(
                    target_width,
                    new_height,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                ))
                
                # Store both versions in a tuple
                result = (fast_pixmap, high_quality_pixmap)
            else:
                result = (QPixmap.fromImage(image), QPixmap.fromImage(image))
            
            # Emit result
            self.signals.finished.emit(self.image_id, result)
            
        except Exception as e:
            self.signals.error.emit(self.image_id, str(e)) 