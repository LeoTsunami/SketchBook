"""
Session management for drawing sessions.
Starting fresh - to be built step by step.
"""
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import json
from datetime import datetime
from core.settings import settings
from core.user_data import user_data


@dataclass
class SessionPreset:
    """Preset configuration for a drawing session."""
    
    name: str
    description: str
    duration_seconds: int
    image_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert preset to dictionary for storage."""
        return {
            "name": self.name,
            "description": self.description,
            "duration_seconds": self.duration_seconds,
            "image_count": self.image_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionPreset':
        """Create preset from dictionary."""
        return cls(**data)


@dataclass
class DrawingSession:
    """Active drawing session configuration."""
    
    id: str
    name: str
    preset: SessionPreset
    selected_images: List[str]  # List of image IDs
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for storage."""
        return {
            "id": self.id,
            "name": self.name,
            "preset": self.preset.to_dict(),
            "selected_images": self.selected_images
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DrawingSession':
        """Create session from dictionary."""
        data['preset'] = SessionPreset.from_dict(data['preset'])
        return cls(**data)


class SessionManager:
    """Manages drawing sessions and presets."""
    
    def __init__(self):
        """Initialize the session manager."""
        # Use user data directory for session files
        self.presets_path = user_data.get_session_presets_path()
        self.sessions_path = user_data.get_session_history_path()
        
        # Ensure directories exist
        self.presets_path.parent.mkdir(parents=True, exist_ok=True)
        self.sessions_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize empty state
        self.presets: Dict[str, SessionPreset] = {}
        self.session_history: List[DrawingSession] = []
        self.current_session: Optional[DrawingSession] = None
