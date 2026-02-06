"""
Session management for drawing sessions.
Handles Course (phased: WarmUp / Gesture / Anatomy / Shading) and Constant-interval runs.
"""
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
import json
import random
import hashlib
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


def _shuffle_image_ids_for_session(image_ids: List[str], shuffle_iteration: int = 0) -> List[str]:
    """
    Shuffle image IDs using seed based on sorted IDs, shuffle iteration, and current time.
    
    This ensures different random orders on each shuffle while keeping them deterministic
    for the same shuffle_iteration within a short time window.
    Matches the order shown in the grid when "Session Course Random" sort is selected.
    
    Args:
        image_ids: List of image IDs to shuffle.
        shuffle_iteration: Iteration counter (0 = default, increments on each shuffle).
                          Each increment generates a new random order.
        
    Returns:
        Shuffled list (new order on each shuffle).
    """
    if not image_ids:
        return image_ids
    
    # Create seed from sorted image IDs, shuffle iteration, and global shuffle timestamp
    # Reason: Include timestamp to ensure different orders on each shuffle
    # The shuffle_iteration ensures that clicking shuffle multiple times gives different orders
    from core.image_db import _shuffle_timestamp
    ids_sorted = sorted(image_ids)
    seed_string = "|".join(ids_sorted) + f"|iter_{shuffle_iteration}|ts_{_shuffle_timestamp}"
    seed = int(hashlib.md5(seed_string.encode()).hexdigest(), 16) % (2**31)
    
    # Shuffle using the seed
    shuffled = list(image_ids)
    random.Random(seed).shuffle(shuffled)
    return shuffled


def build_course_run(
    image_ids: List[str],
    course_presets: List[Dict[str, Any]],
    duration_minutes: int,
    shuffle_iteration: int = 0,
    use_exact_order: bool = False,
) -> List[Tuple[str, int]]:
    """
    Build a session run: list of (image_id, duration_seconds) from a course preset.
    Images are shuffled using deterministic seed (same as grid sort); if fewer than needed, they are cycled.

    Args:
        image_ids: List of image IDs (will be shuffled unless use_exact_order=True).
        course_presets: List from load_course_config()["course_presets"].
        duration_minutes: Desired course duration (e.g. 10, 30).
        shuffle_iteration: Iteration counter for shuffle (matches grid shuffle counter).
        use_exact_order: If True, use image_ids in exact order (no shuffle). For course_random mode.

    Returns:
        List of (image_id, duration_seconds) in phase order.
    """
    preset = next(
        (p for p in course_presets if p["duration_minutes"] == duration_minutes),
        None,
    )
    if not preset or not image_ids:
        return []

    # Use exact order if requested (for course_random mode), otherwise shuffle
    if use_exact_order:
        ids = list(image_ids)  # Use exact order from grid
        print(f"[DEBUG] build_course_run: Using EXACT order (no shuffle) - First 5 IDs: {ids[:5]}")
    else:
        # Use deterministic shuffle to match grid sort order
        ids = _shuffle_image_ids_for_session(image_ids, shuffle_iteration=shuffle_iteration)
        print(f"[DEBUG] build_course_run: Shuffled - First 5 IDs: {ids[:5]}")
    
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
        # Use user data directory for session files (for future persistence)
        # TODO: Implement preset and session history persistence when needed
        self.presets_path = user_data.get_session_presets_path()
        self.sessions_path = user_data.get_session_history_path()

        # Ensure directories exist
        self.presets_path.parent.mkdir(parents=True, exist_ok=True)
        self.sessions_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize empty state (for future persistence)
        # TODO: Load presets and session history from files when implementing persistence
        self.presets: Dict[str, SessionPreset] = {}
        self.session_history: List[DrawingSession] = []

        # Active run state (built when starting a session)
        self.session_run: List[Tuple[str, int]] = []  # (image_id, duration_seconds)
        self._run_index: int = 0
        self._session_display_name: str = ""
        self._window_mode: str = "FullScreen"
        # Course only: (phase_name, start_index, count, duration_per_image) for each phase
        self._course_phases: List[Tuple[str, int, int, int]] = []

    def start_session(
        self,
        image_ids: List[str],
        session_type: str,
        course_duration_minutes: Optional[int] = None,
        interval_seconds: Optional[int] = None,
        window_mode: str = "FullScreen",
        course_config: Optional[Dict[str, Any]] = None,
        shuffle_iteration: int = 0,
        use_exact_order: bool = False,
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
            shuffle_iteration: Iteration counter for shuffle (matches grid shuffle counter).

        Returns:
            True if run was built and has at least one image, False otherwise.
        """
        self.end_session()
        self._window_mode = window_mode or "FullScreen"

        if session_type == "Course" and course_duration_minutes is not None and course_config:
            presets = course_config.get("course_presets", [])
            preset = next(
                (p for p in presets if p["duration_minutes"] == course_duration_minutes),
                None,
            )
            # Debug: print what we receive
            print(f"[DEBUG] start_session (Course): Received {len(image_ids)} image IDs")
            print(f"[DEBUG] start_session (Course): First 5 IDs: {image_ids[:5]}")
            
            self.session_run = build_course_run(
                image_ids, 
                presets, 
                course_duration_minutes, 
                shuffle_iteration=shuffle_iteration,
                use_exact_order=use_exact_order
            )
            self._session_display_name = f"Course {course_duration_minutes} min"
            self._course_phases = []
            if preset and preset.get("phases"):
                idx = 0
                for ph in preset["phases"]:
                    name = ph.get("name", "")
                    count = ph.get("count", 0)
                    sec = ph.get("duration_seconds_per_image", 30)
                    if count > 0:
                        self._course_phases.append((name, idx, count, sec))
                    idx += count
        elif session_type == "Constant interval" and interval_seconds is not None and image_ids:
            # Use exact order if requested (for course_random mode), otherwise shuffle
            if use_exact_order:
                ids = list(image_ids)  # Use exact order from grid
                print(f"[DEBUG] start_session (Constant): Using EXACT order (no shuffle) - First 5 IDs: {ids[:5]}")
            else:
                # Use deterministic shuffle to match grid sort order
                ids = _shuffle_image_ids_for_session(image_ids, shuffle_iteration=shuffle_iteration)
                print(f"[DEBUG] start_session (Constant): Shuffled - First 5 IDs: {ids[:5]}")
            
            self.session_run = [(iid, interval_seconds) for iid in ids]
            self._session_display_name = f"Constant {interval_seconds}s"
            self._course_phases = []
        else:
            self.session_run = []
            self._session_display_name = ""
            self._course_phases = []

        self._run_index = 0
        return len(self.session_run) > 0

    def get_phase_info_at_index(self, index: int) -> Optional[Tuple[str, int, int]]:
        """
        For Course mode only: if index is the start of a phase, return (phase_name, count, duration_seconds).
        Otherwise return None.
        """
        for name, start, count, sec in self._course_phases:
            if index == start:
                return (name, count, sec)
        return None

    def is_course_session(self) -> bool:
        """True if current run is a course (has phases)."""
        return len(self._course_phases) > 0

    def get_run_index(self) -> int:
        """Return current run index (0-based)."""
        return self._run_index

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
        """Clear run state."""
        self.session_run = []
        self._run_index = 0
        self._session_display_name = ""
        self._course_phases = []
