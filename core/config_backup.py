"""
Backup config files to config/backup/ with date-time in filename.
Keeps the 5 most recent backups per file. Intended to run at app startup in a background thread.

The image library is a SQLite database: it is copied with the SQLite backup API
rather than a file copy, because copying a live WAL database can miss pages.
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from core.db.connection import backup_database
from core.user_data import user_data

# Number of backups to keep per file
BACKUP_HISTORY_COUNT = 5

# (path getter, stem for backup filename)
_CONFIG_FILES: List[Tuple[str, str]] = [
    ("get_settings_path", "settings"),
    ("get_session_presets_path", "session_presets"),
    ("get_session_history_path", "session_history"),
    ("get_user_tags_config_path", "user_tags_config"),
]

# Image library database, backed up with the SQLite backup API.
_LIBRARY_STEM = "library"
_LIBRARY_SUFFIX = ".db"


def run_config_backup() -> None:
    """
    Copy each config JSON to config/backup/{stem}_{YYYYMMDD_HHMMSS}.bak and the
    image library to config/backup/library_{YYYYMMDD_HHMMSS}.db, then keep only
    the last BACKUP_HISTORY_COUNT backups per stem.
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

    try:
        backup_database(
            user_data.get_images_sqlite_path(),
            backup_dir / f"{_LIBRARY_STEM}_{timestamp}{_LIBRARY_SUFFIX}",
        )
    except OSError as e:
        print(f"Config backup: failed to backup image library: {e}")

    for _method_name, stem in _CONFIG_FILES:
        try:
            _prune_old_backups(backup_dir, stem)
        except OSError as e:
            print(f"Config backup: failed to prune {stem}: {e}")

    try:
        _prune_old_backups(backup_dir, _LIBRARY_STEM, suffix=_LIBRARY_SUFFIX)
    except OSError as e:
        print(f"Config backup: failed to prune {_LIBRARY_STEM}: {e}")


def _prune_old_backups(backup_dir: Path, stem: str, suffix: str = ".bak") -> None:
    """
    Keep only the BACKUP_HISTORY_COUNT most recent backups for this stem.

    Args:
        backup_dir: Directory holding the backups.
        stem: Backup filename stem (e.g. "settings", "library").
        suffix: Backup file extension.
    """
    pattern = f"{stem}_*{suffix}"
    backups = sorted(backup_dir.glob(pattern), key=lambda p: p.name, reverse=True)
    for old in backups[BACKUP_HISTORY_COUNT:]:
        try:
            old.unlink()
        except OSError:
            pass
