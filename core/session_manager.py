"""
Session management for drawing sessions.
Handles Course (phased: WarmUp / Gesture / Anatomy / Shading) and Constant-interval runs.
"""
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
import json
import random
from datetime import datetime
from core.settings import settings
from core.user_data import user_data


def load_course_config(config_path: Path) -> Dict[str, Any]:
    """
    Load course presets from a JSON file.

    Args:
        config_path: Path to session_configs.json.

    Returns:
        Dict with key "course_presets" (list of {duration_minutes, phases}).
    """
    if not config_path.exists():
        return {"course_presets": []}
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_course_run(
    image_ids: List[str],
    course_presets: List[Dict[str, Any]],
    duration_minutes: int,
) -> List[Tuple[str, int]]:
    """
    Build a session run: list of (image_id, duration_seconds) from a course preset.
    Images are shuffled; if fewer than needed, they are cycled.

    Args:
        image_ids: List of image IDs (will be shuffled).
        course_presets: List from load_course_config()["course_presets"].
        duration_minutes: Desired course duration (e.g. 10, 30).

    Returns:
        List of (image_id, duration_seconds) in phase order.
    """
    preset = next(
        (p for p in course_presets if p["duration_minutes"] == duration_minutes),
        None,
    )
    if not preset or not image_ids:
        return []

    ids = list(image_ids)
    random.shuffle(ids)
    run: List[Tuple[str, int]] = []
    n = 0
    for phase in preset["phases"]:
        count = phase.get("count", 0)
        sec = phase.get("duration_seconds_per_image", 30)
        for _ in range(count):
            run.append((ids[n % len(ids)], sec))
            n += 1
    return run


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

        # Active run state (built when starting a session)
        self.session_run: List[Tuple[str, int]] = []  # (image_id, duration_seconds)
        self._run_index: int = 0
        self._session_display_name: str = ""
        self._window_mode: str = "FullScreen"
        self.current_session: Optional[DrawingSession] = None

    def start_session(
        self,
        image_ids: List[str],
        session_type: str,
        course_duration_minutes: Optional[int] = None,
        interval_seconds: Optional[int] = None,
        window_mode: str = "FullScreen",
        course_config: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Start a session: build run from image_ids and config, set current index to 0.

        Args:
            image_ids: Filtered image IDs (will be shuffled for Course).
            session_type: "Course" or "Constant interval".
            course_duration_minutes: For Course: 10, 20, ..., 60.
            interval_seconds: For Constant: seconds per image.
            window_mode: "FullScreen" or "Window always on top".
            course_config: Result of load_course_config(); required for Course.

        Returns:
            True if run was built and has at least one image, False otherwise.
        """
        self.end_session()
        self._window_mode = window_mode or "FullScreen"

        if session_type == "Course" and course_duration_minutes is not None and course_config:
            presets = course_config.get("course_presets", [])
            self.session_run = build_course_run(image_ids, presets, course_duration_minutes)
            self._session_display_name = f"Course {course_duration_minutes} min"
        elif session_type == "Constant interval" and interval_seconds is not None and image_ids:
            ids = list(image_ids)
            random.shuffle(ids)
            self.session_run = [(iid, interval_seconds) for iid in ids]
            self._session_display_name = f"Constant {interval_seconds}s"
        else:
            self.session_run = []
            self._session_display_name = ""

        self._run_index = 0
        return len(self.session_run) > 0

    def get_current_image_id(self) -> Optional[str]:
        """Return the image ID for the current step, or None if no run."""
        if not self.session_run or self._run_index < 0 or self._run_index >= len(self.session_run):
            return None
        return self.session_run[self._run_index][0]

    def get_current_duration(self) -> int:
        """Return the duration in seconds for the current image. 0 if no run."""
        if not self.session_run or self._run_index < 0 or self._run_index >= len(self.session_run):
            return 0
        return self.session_run[self._run_index][1]

    def get_session_progress(self) -> Tuple[int, int, int]:
        """
        Return (current 1-based index, total steps, duration_seconds for current image).
        """
        total = len(self.session_run)
        if total == 0:
            return 0, 0, 0
        cur = self._run_index + 1
        dur = self.get_current_duration()
        return cur, total, dur

    def advance_image(self) -> bool:
        """Move to next image. Returns False if already at end (session ended)."""
        if not self.session_run:
            return False
        if self._run_index >= len(self.session_run) - 1:
            return False
        self._run_index += 1
        return True

    def previous_image(self) -> bool:
        """Move to previous image. Returns False if already at first."""
        if not self.session_run or self._run_index <= 0:
            return False
        self._run_index -= 1
        return True

    def get_session_display_name(self) -> str:
        """Display name for the current session (e.g. 'Course 30 min')."""
        return self._session_display_name

    def get_window_mode(self) -> str:
        """'FullScreen' or 'Window always on top'."""
        return self._window_mode

    def end_session(self) -> None:
        """Clear run state and current session."""
        self.session_run = []
        self._run_index = 0
        self._session_display_name = ""
        self.current_session = None

    def get_current_session(self) -> Optional[Any]:
        """Return a minimal session object for UI (has .preset.name and .preset.duration_seconds)."""
        if not self.session_run:
            return None
        # Build a minimal object so existing UI (session.preset.name, session.preset.duration_seconds) works.
        class MinimalPreset:
            def __init__(self, name: str, duration_seconds: int):
                self.name = name
                self.duration_seconds = duration_seconds

        class MinimalSession:
            def __init__(self, name: str, duration_seconds: int):
                self.preset = MinimalPreset(name, duration_seconds)

        return MinimalSession(
            self._session_display_name,
            self.get_current_duration(),
        )
