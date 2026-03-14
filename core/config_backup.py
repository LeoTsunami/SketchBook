"""
Backup config JSON files to config/backup/ with date-time in filename.
Keeps the 5 most recent backups per file. Intended to run at app startup in a background thread.
"""
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from core.user_data import user_data

# Number of backups to keep per JSON file
BACKUP_HISTORY_COUNT = 5

# (path getter, stem for backup filename)
_CONFIG_FILES: List[Tuple[str, str]] = [
    ("get_images_db_path", "images"),
    ("get_settings_path", "settings"),
    ("get_session_presets_path", "session_presets"),
    ("get_session_history_path", "session_history"),
    ("get_user_tags_config_path", "user_tags_config"),
]


def run_config_backup() -> None:
    """
    Copy each config JSON to config/backup/{stem}_{YYYYMMDD_HHMMSS}.bak,
    then keep only the last BACKUP_HISTORY_COUNT backups per stem.
    Safe to call from a background thread; catches and logs errors.
    """
    backup_dir = user_data.get_backup_dir()
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for method_name, stem in _CONFIG_FILES:
        try:
            path = getattr(user_data, method_name)()
            if not path.exists():
                continue
            dest = backup_dir / f"{stem}_{timestamp}.bak"
            shutil.copy2(path, dest)
        except OSError as e:
            print(f"Config backup: failed to backup {stem}: {e}")

    for _method_name, stem in _CONFIG_FILES:
        try:
            _prune_old_backups(backup_dir, stem)
        except OSError as e:
            print(f"Config backup: failed to prune {stem}: {e}")


def _prune_old_backups(backup_dir: Path, stem: str) -> None:
    """
    Keep only the BACKUP_HISTORY_COUNT most recent backups for this stem.
    Files are named {stem}_{YYYYMMDD_HHMMSS}.bak; sort descending and delete the rest.
    """
    pattern = f"{stem}_*.bak"
    backups = sorted(backup_dir.glob(pattern), key=lambda p: p.name, reverse=True)
    for old in backups[BACKUP_HISTORY_COUNT:]:
        try:
            old.unlink()
        except OSError:
            pass
