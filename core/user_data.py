"""
User data directory management for SketchBook.
Handles the user's data directory configuration and path resolution.
"""
import os
import json
from pathlib import Path
from typing import Optional


class UserDataManager:
    """Manages the user's data directory for SketchBook."""
    
    # Default base directory name
    APP_NAME = "SketchBook"
    
    # Configuration file name (stored in user's home directory)
    CONFIG_FILE_NAME = ".sketchbook_config.json"
    
    def __init__(self):
        """Initialize the user data manager."""
        self._base_dir: Optional[Path] = None
        self._config_path = Path.home() / self.CONFIG_FILE_NAME
        self._load_base_dir()
    
    def _load_base_dir(self) -> None:
        """Load the base directory from config file or environment variable."""
        # First, check environment variable (highest priority)
        env_path = os.getenv("SKETCHBOOK_DATA_DIR")
        if env_path:
            self._base_dir = Path(env_path).expanduser().resolve()
            return
        
        # Then, check config file
        if self._config_path.exists():
            try:
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    if 'data_dir' in config:
                        self._base_dir = Path(config['data_dir']).expanduser().resolve()
                        return
            except (json.JSONDecodeError, KeyError, OSError) as e:
                print(f"Warning: Could not load config file: {e}")
        
        # Default: use Documents/SketchBook
        self._base_dir = self._get_default_base_dir()
    
    def _get_default_base_dir(self) -> Path:
        """
        Get the default base directory.
        
        Returns:
            Path to the default user data directory (Documents/SketchBook)
        """
        # Get Documents directory
        documents_dir = Path.home() / "Documents"
        
        # If Documents doesn't exist, fallback to home directory
        if not documents_dir.exists():
            documents_dir = Path.home()
        
        return (documents_dir / self.APP_NAME).resolve()
    
    def get_base_dir(self) -> Path:
        """
        Get the base user data directory.
        
        Returns:
            Path to the base user data directory
        """
        if self._base_dir is None:
            self._base_dir = self._get_default_base_dir()
        return self._base_dir
    
    def set_base_dir(self, path: Path) -> bool:
        """
        Set the base user data directory.
        
        Args:
            path: Path to the new base directory
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Resolve and expand the path
            resolved_path = Path(path).expanduser().resolve()
            
            # Create directory if it doesn't exist
            resolved_path.mkdir(parents=True, exist_ok=True)
            
            # Save to config file
            config = {'data_dir': str(resolved_path)}
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            
            # Update internal state
            self._base_dir = resolved_path
            
            # Create subdirectories
            self.ensure_directories()
            
            return True
        except (OSError, PermissionError) as e:
            print(f"Error setting base directory: {e}")
            return False
    
    def ensure_directories(self) -> None:
        """Ensure all necessary subdirectories exist."""
        base = self.get_base_dir()
        dirs = [
            base / "images",
            base / "sessions",
            base / "config",
            self.get_backup_dir(),
        ]
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)

    def get_backup_dir(self) -> Path:
        """Get the config backup directory (config/backup). Created on first backup or ensure_directories."""
        return self.get_config_dir() / "backup"
    
    def get_images_dir(self) -> Path:
        """Get the images directory path."""
        return self.get_base_dir() / "images"
    
    def get_sessions_dir(self) -> Path:
        """Get the sessions directory path."""
        return self.get_base_dir() / "sessions"
    
    def get_config_dir(self) -> Path:
        """Get the config directory path."""
        return self.get_base_dir() / "config"
    
    def get_settings_path(self) -> Path:
        """Get the settings file path."""
        return self.get_config_dir() / "settings.json"
    
    def get_images_db_path(self) -> Path:
        """Get the images database file path."""
        return self.get_config_dir() / "images.json"
    
    def get_session_presets_path(self) -> Path:
        """Get the session presets file path."""
        return self.get_config_dir() / "session_presets.json"
    
    def get_session_history_path(self) -> Path:
        """Get the session history file path."""
        return self.get_config_dir() / "session_history.json"

    def get_user_tags_config_path(self) -> Path:
        """Get the user tags config file path (placements and icons for user tags)."""
        return self.get_config_dir() / "user_tags_config.json"


# Global instance
user_data = UserDataManager()


def set_user_data_directory(path: str) -> bool:
    """
    Set the user data directory (for use by installer or configuration).
    
    This is the public API for installers to configure the user data directory path.
    The installer can call this function during installation to set a custom path
    chosen by the user (e.g., D:\\SketchBook instead of default Documents\\SketchBook).
    
    Args:
        path: Path to the user data directory (will be created if it doesn't exist)
        
    Returns:
        True if successful, False otherwise
        
    Example:
        >>> set_user_data_directory("D:\\MySketchBook")
        True
    """
    return user_data.set_base_dir(Path(path))


def get_user_data_directory() -> str:
    """
    Get the current user data directory path.
    
    This is the public API for installers or other tools to query the current
    user data directory path.
    
    Returns:
        String path to the user data directory
        
    Example:
        >>> get_user_data_directory()
        'C:\\Users\\username\\Documents\\SketchBook'
    """
    return str(user_data.get_base_dir())
