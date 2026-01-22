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
            target_width, target_height = self.target_size
            
            if target_width > 0:
                # Calculate new height preserving aspect ratio
                aspect_ratio = image.width() / image.height()
                new_height = int(target_width / aspect_ratio)
                
                # Use device pixel ratio for high-DPI displays (usually 1.0, 1.5, or 2.0)
                # This ensures crisp rendering on retina/high-DPI screens
                from qtpy.QtWidgets import QApplication
                app = QApplication.instance()
                device_pixel_ratio = app.devicePixelRatio() if app else 1.0
                
                # Scale to account for device pixel ratio for better quality
                scaled_width = int(target_width * max(device_pixel_ratio, 1.5))
                scaled_height = int(new_height * max(device_pixel_ratio, 1.5))
                
                # First create a fast scaled version for immediate display
                fast_pixmap = QPixmap.fromImage(image.scaled(
                    target_width,
                    new_height,
                    Qt.KeepAspectRatio,
                    Qt.FastTransformation
                ))
                
                # Create high quality version at higher resolution for crisp display
                # Using SmoothTransformation for best quality
                high_quality_pixmap = QPixmap.fromImage(image.scaled(
                    scaled_width,
                    scaled_height,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                ))
                
                # Set device pixel ratio on the pixmap for proper scaling
                high_quality_pixmap.setDevicePixelRatio(device_pixel_ratio)
                
                # Store both versions in a tuple
                result = (fast_pixmap, high_quality_pixmap)
            else:
                result = (QPixmap.fromImage(image), QPixmap.fromImage(image))
            
            # Emit result
            self.signals.finished.emit(self.image_id, result)
            
        except Exception as e:
            self.signals.error.emit(self.image_id, str(e)) 