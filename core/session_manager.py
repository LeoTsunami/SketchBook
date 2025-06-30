"""
Session management for drawing sessions with presets and configuration.
"""
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
import json
from datetime import datetime
from core.settings import settings
from core.image_db import ImageMetadata


@dataclass
class SessionPreset:
    """Preset configuration for a drawing session."""
    
    name: str
    description: str
    duration_seconds: int
    image_count: int
    transition_duration: float = 1.0
    auto_advance: bool = True
    loop_session: bool = False
    tags: List[str] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.tags is None:
            self.tags = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert preset to dictionary for storage."""
        return asdict(self)
    
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
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    current_image_index: int = 0
    current_timer: int = 0
    is_active: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for storage."""
        data = asdict(self)
        # Convert datetime objects to strings
        if self.start_time:
            data['start_time'] = self.start_time.isoformat()
        if self.end_time:
            data['end_time'] = self.end_time.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DrawingSession':
        """Create session from dictionary."""
        # Convert string timestamps back to datetime
        if data.get('start_time'):
            data['start_time'] = datetime.fromisoformat(data['start_time'])
        if data.get('end_time'):
            data['end_time'] = datetime.fromisoformat(data['end_time'])
        return cls(**data)


class SessionManager:
    """Manages drawing sessions and presets."""
    
    def __init__(self):
        """Initialize the session manager."""
        self.presets_path = Path(settings.get("sessions.presets_path", "data/config/session_presets.json"))
        self.sessions_path = Path(settings.get("sessions.history_path", "data/config/session_history.json"))
        
        # Ensure directories exist
        self.presets_path.parent.mkdir(parents=True, exist_ok=True)
        self.sessions_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load presets and session history
        self.presets: Dict[str, SessionPreset] = {}
        self.session_history: List[DrawingSession] = []
        self.current_session: Optional[DrawingSession] = None
        
        self._load_presets()
        self._load_session_history()
        self._create_default_presets()
    
    def _load_presets(self):
        """Load presets from disk."""
        try:
            if self.presets_path.exists():
                with open(self.presets_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.presets = {
                        name: SessionPreset.from_dict(preset_data)
                        for name, preset_data in data.items()
                    }
        except Exception as e:
            print(f"Error loading session presets: {str(e)}")
            self.presets = {}
    
    def _save_presets(self):
        """Save presets to disk."""
        try:
            with open(self.presets_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        name: preset.to_dict()
                        for name, preset in self.presets.items()
                    },
                    f,
                    indent=2,
                    ensure_ascii=False
                )
        except Exception as e:
            print(f"Error saving session presets: {str(e)}")
    
    def _load_session_history(self):
        """Load session history from disk."""
        try:
            if self.sessions_path.exists():
                with open(self.sessions_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.session_history = []
                    for session_data in data:
                        # Convert preset dict back to SessionPreset object
                        if 'preset' in session_data and isinstance(session_data['preset'], dict):
                            session_data['preset'] = SessionPreset.from_dict(session_data['preset'])
                        self.session_history.append(DrawingSession.from_dict(session_data))
        except Exception as e:
            print(f"Error loading session history: {str(e)}")
            self.session_history = []
    
    def _save_session_history(self):
        """Save session history to disk."""
        try:
            with open(self.sessions_path, "w", encoding="utf-8") as f:
                json.dump(
                    [session.to_dict() for session in self.session_history],
                    f,
                    indent=2,
                    ensure_ascii=False
                )
        except Exception as e:
            print(f"Error saving session history: {str(e)}")
    
    def _create_default_presets(self):
        """Create default presets if none exist."""
        if not self.presets:
            default_presets = {
                "Quick Sketch (30s)": SessionPreset(
                    name="Quick Sketch (30s)",
                    description="Quick gesture drawing practice",
                    duration_seconds=30,
                    image_count=10,
                    transition_duration=0.5,
                    auto_advance=True,
                    loop_session=True,
                    tags=["gesture", "quick"]
                ),
                "Standard (2min)": SessionPreset(
                    name="Standard (2min)",
                    description="Standard figure drawing session",
                    duration_seconds=120,
                    image_count=5,
                    transition_duration=1.0,
                    auto_advance=True,
                    loop_session=False,
                    tags=["figure", "standard"]
                ),
                "Long Pose (5min)": SessionPreset(
                    name="Long Pose (5min)",
                    description="Extended pose for detailed work",
                    duration_seconds=300,
                    image_count=3,
                    transition_duration=2.0,
                    auto_advance=False,
                    loop_session=False,
                    tags=["long", "detailed"]
                ),
                "Warm-up (1min)": SessionPreset(
                    name="Warm-up (1min)",
                    description="Quick warm-up session",
                    duration_seconds=60,
                    image_count=6,
                    transition_duration=0.8,
                    auto_advance=True,
                    loop_session=True,
                    tags=["warmup", "quick"]
                )
            }
            
            self.presets.update(default_presets)
            self._save_presets()
    
    def get_presets(self) -> Dict[str, SessionPreset]:
        """
        Get all available presets.
        
        Returns:
            Dictionary of preset names to preset objects
        """
        return self.presets.copy()
    
    def add_preset(self, preset: SessionPreset):
        """
        Add a new preset.
        
        Args:
            preset: Preset to add
        """
        self.presets[preset.name] = preset
        self._save_presets()
    
    def update_preset(self, name: str, preset: SessionPreset):
        """
        Update an existing preset.
        
        Args:
            name: Name of the preset to update
            preset: Updated preset
        """
        if name in self.presets:
            self.presets[name] = preset
            self._save_presets()
    
    def delete_preset(self, name: str):
        """
        Delete a preset.
        
        Args:
            name: Name of the preset to delete
        """
        if name in self.presets:
            del self.presets[name]
            self._save_presets()
    
    def create_session(self, preset: SessionPreset, selected_images: List[str], name: str = None) -> DrawingSession:
        """
        Create a new drawing session.
        
        Args:
            preset: Preset to use for the session
            selected_images: List of image IDs to use
            name: Optional custom name for the session
            
        Returns:
            Created drawing session
        """
        if not name:
            name = f"{preset.name} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        session = DrawingSession(
            id=f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            name=name,
            preset=preset,
            selected_images=selected_images.copy()
        )
        
        return session
    
    def start_session(self, session: DrawingSession):
        """
        Start a drawing session.
        
        Args:
            session: Session to start
        """
        if self.current_session and self.current_session.is_active:
            self.end_session()
        
        session.start_time = datetime.now()
        session.is_active = True
        session.current_image_index = 0
        session.current_timer = session.preset.duration_seconds
        
        self.current_session = session
    
    def end_session(self):
        """End the current session."""
        if self.current_session and self.current_session.is_active:
            self.current_session.end_time = datetime.now()
            self.current_session.is_active = False
            
            # Add to history
            self.session_history.append(self.current_session)
            self._save_session_history()
            
            self.current_session = None
    
    def get_current_session(self) -> Optional[DrawingSession]:
        """
        Get the currently active session.
        
        Returns:
            Current session or None if no active session
        """
        return self.current_session
    
    def get_session_history(self) -> List[DrawingSession]:
        """
        Get session history.
        
        Returns:
            List of completed sessions
        """
        return self.session_history.copy()
    
    def advance_image(self):
        """Advance to the next image in the current session."""
        if not self.current_session or not self.current_session.is_active:
            return False
        
        session = self.current_session
        session.current_image_index += 1
        
        # Check if we've reached the end
        if session.current_image_index >= len(session.selected_images):
            if session.preset.loop_session:
                session.current_image_index = 0
            else:
                self.end_session()
                return False
        
        # Reset timer for new image
        session.current_timer = session.preset.duration_seconds
        
        return True
    
    def previous_image(self):
        """Go to the previous image in the current session."""
        if not self.current_session or not self.current_session.is_active:
            return False
        
        session = self.current_session
        session.current_image_index -= 1
        
        if session.current_image_index < 0:
            if session.preset.loop_session:
                session.current_image_index = len(session.selected_images) - 1
            else:
                session.current_image_index = 0
                return False
        
        # Reset timer for new image
        session.current_timer = session.preset.duration_seconds
        
        return True
    
    def update_timer(self, elapsed_seconds: int):
        """
        Update the session timer.
        
        Args:
            elapsed_seconds: Seconds elapsed since last update
        """
        if not self.current_session or not self.current_session.is_active:
            return
        
        session = self.current_session
        session.current_timer -= elapsed_seconds
        
        # Check if timer has expired
        if session.current_timer <= 0:
            if session.preset.auto_advance:
                self.advance_image()
            else:
                # Timer expired but auto-advance is disabled
                session.current_timer = 0
    
    def get_current_image_id(self) -> Optional[str]:
        """
        Get the current image ID in the active session.
        
        Returns:
            Current image ID or None if no active session
        """
        if not self.current_session or not self.current_session.is_active:
            return None
        
        session = self.current_session
        if session.current_image_index < len(session.selected_images):
            return session.selected_images[session.current_image_index]
        
        return None
    
    def get_session_progress(self) -> tuple:
        """
        Get the current session progress.
        
        Returns:
            Tuple of (current_image_index, total_images, time_remaining)
        """
        if not self.current_session or not self.current_session.is_active:
            return (0, 0, 0)
        
        session = self.current_session
        return (
            session.current_image_index + 1,
            len(session.selected_images),
            max(0, session.current_timer)
        ) 