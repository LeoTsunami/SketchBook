"""
Settings manager for the SketchBook application.
Handles loading, saving, and validating application settings.
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union
from core.user_data import user_data

class Settings:
    """Manages application settings with validation and type checking."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the settings manager.
        
        Args:
            config_path: Path to the settings file (optional, uses user data dir if not provided)
        """
        if config_path is None:
            # Use user data directory
            self.config_path = user_data.get_settings_path()
        else:
            self.config_path = Path(config_path)
        self._settings: Dict[str, Any] = {}
        self._load_settings()
    
    def _load_settings(self) -> None:
        """Load settings from file or create default if not exists."""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._settings = json.load(f)
        else:
            # Ensure directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            # Create with defaults
            self._settings = self._get_default_settings()
            self.save()
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """Get default settings configuration.
        
        Returns:
            Dict containing default settings
        """
        return {
            "version": "0.1.0",
            "ui": {
                "theme": "dark",
                "language": "fr",
                "window": {
                    "width": 1280,
                    "height": 800,
                    "maximized": False
                },
                "grid": {
                    "columns": 4,
                    "spacing": 16,
                    "card_ratio": "3:4"
                }
            },
            "images": {
                "storage_path": str(user_data.get_images_dir()),
                "max_width": 1920,
                "formats": ["jpg", "jpeg", "png"],
                "compression": {
                    "enabled": True,
                    "quality": 85
                }
            },
            "session": {
                "auto_save": True,
                "save_path": str(user_data.get_sessions_dir()),
                "default_duration": 300,
                "intervals": [30, 60, 120, 300]
            },
            "database": {
                "type": "json",
                "path": str(user_data.get_images_db_path())
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a setting value by key.
        
        Args:
            key: Dot-notation key (e.g. 'ui.theme')
            default: Default value if key not found
            
        Returns:
            Setting value or default
        """
        try:
            value = self._settings
            for k in key.split('.'):
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a setting value.
        
        Args:
            key: Dot-notation key (e.g. 'ui.theme')
            value: Value to set
        """
        keys = key.split('.')
        target = self._settings
        
        # Navigate to the correct nested level
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        
        # Set the value
        target[keys[-1]] = value
    
    def save(self) -> None:
        """Save current settings to file."""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self._settings, f, indent=4)
    
    def reset(self) -> None:
        """Reset settings to default values."""
        self._settings = self._get_default_settings()
        self.save()
    
    @property
    def all(self) -> Dict[str, Any]:
        """Get all settings.
        
        Returns:
            Dict containing all settings
        """
        return self._settings.copy()

# Create global settings instance
settings = Settings() 