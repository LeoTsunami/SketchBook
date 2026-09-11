"""
One-shot import of the legacy ``images.json`` library into SQLite.

Runs when the SQLite library is still empty and a JSON file is present. The
import is transactional and verified by row count: on any mismatch the SQLite
tables are cleared and the JSON file is left untouched, so a failed migration
never loses metadata.
"""

import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from core.db.images_repository import ImagesRepository

# Fields of the frozen images.json format. Declared here rather than imported
# from core.image_db to keep the legacy reader independent of the live model.
_LEGACY_FIELDS = (
    "id",
    "path",
    "original_filename",
    "width",
    "height",
    "file_size",
    "format",
    "original_path",
    "import_date",
    "kind",
    "group_id",
)

_BACKUP_SUFFIX = ".bak"


def migrate_json_if_needed(repository: ImagesRepository, json_path: Path) -> int:
    """
    Import the legacy JSON database into SQLite if it has not been done yet.

    Args:
        repository: Repository bound to the SQLite library.
        json_path: Path to the legacy ``images.json``.

    Returns:
        int: Number of images imported (0 when there is nothing to do).
    """
    json_path = Path(json_path)
    if not json_path.exists():
        return 0
    if repository.count_images() > 0:
        # Already migrated (or a real library exists): never import twice.
        return 0

    data = read_legacy_json(json_path)
    if data is None:
        print(f"Image library migration: cannot read {json_path.name}, skipped.")
        return 0

    rows = [
        row
        for image_id, raw in data.items()
        if (row := _json_entry_to_row(str(image_id), raw)) is not None
    ]
    expected = len(rows)
    if expected == 0:
        _archive_json(json_path)
        return 0

    repository.ensure_library()
    try:
        inserted = repository.insert_many(rows)
    except sqlite3.DatabaseError as exc:
        print(f"Image library migration failed ({exc}); images.json kept.")
        _safe_clear(repository)
        return 0

    if inserted != expected or repository.count_images() != expected:
        print(
            "Image library migration aborted: expected "
            f"{expected} images, wrote {repository.count_images()}; images.json kept."
        )
        _safe_clear(repository)
        return 0

    _archive_json(json_path)
    print(f"Image library migrated to SQLite: {inserted} images imported.")
    return inserted


def read_legacy_json(path: Path) -> Optional[Dict[str, Any]]:
    """
    Read ``images.json``, repairing the corruptions the JSON backend produced.

    Tries the file as-is, then trailing-comma and truncated-tail repairs, then
    the ``.bak`` sibling written before each JSON save.

    Args:
        path: Path to the legacy JSON file.

    Returns:
        Parsed mapping of image id to metadata dict, or None if unreadable.
    """
    data = _load_json_file(path)
    if data is not None:
        return data
    data = _repair_json_file(path)
    if data is not None:
        return data
    return _load_json_file(path.parent / (path.name + _BACKUP_SUFFIX))


def export_library_to_json(repository: ImagesRepository, path: Path) -> int:
    """
    Write the SQLite library back to the legacy JSON format.

    Kept as an escape hatch (downgrade, inspection) and as the base for library
    pack export.

    Args:
        repository: Repository bound to the SQLite library.
        path: Destination JSON file.

    Returns:
        int: Number of images written.
    """
    tags = repository.fetch_tags()
    payload: Dict[str, Dict[str, Any]] = {}
    for row in repository.fetch_images():
        image_id = str(row["id"])
        entry: Dict[str, Any] = {field: row.get(field) for field in _LEGACY_FIELDS}
        entry["tags"] = sorted(tags.get(image_id, set()))
        entry["member_ids"] = list(row.get("member_ids") or [])
        entry["hidden"] = bool(row.get("hidden"))
        payload[image_id] = entry

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    return len(payload)


def _json_entry_to_row(
    image_id: str, raw: Mapping[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Convert one legacy JSON entry into a repository row.

    Args:
        image_id: Key of the entry in the JSON object.
        raw: Raw metadata mapping.

    Returns:
        Row dict, or None when the entry is not usable.
    """
    if not isinstance(raw, Mapping):
        return None
    resolved_id = str(raw.get("id") or image_id)
    if not resolved_id:
        return None

    tags = raw.get("tags") or []
    member_ids = raw.get("member_ids") or []
    row: Dict[str, Any] = {
        "id": resolved_id,
        "path": str(raw.get("path") or ""),
        "original_filename": str(raw.get("original_filename") or ""),
        "width": _as_int(raw.get("width")),
        "height": _as_int(raw.get("height")),
        "file_size": _as_int(raw.get("file_size")),
        "format": str(raw.get("format") or ""),
        "original_path": str(raw.get("original_path") or ""),
        "import_date": str(raw.get("import_date") or ""),
        "kind": str(raw.get("kind") or "single"),
        "group_id": str(raw.get("group_id") or ""),
        "hidden": bool(raw.get("hidden")),
        "member_ids": [str(member) for member in member_ids if member],
        "tags": {str(tag) for tag in tags if tag},
    }
    return row


def _as_int(value: Any) -> int:
    """
    Coerce a legacy value to int, defaulting to 0.

    Args:
        value: Raw JSON value.

    Returns:
        int: Parsed integer or 0.
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _load_json_file(path: Path) -> Optional[Dict[str, Any]]:
    """
    Load a JSON object from disk.

    Args:
        path: File to read.

    Returns:
        Parsed dict, or None if missing, invalid, or not an object.
    """
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def _repair_json_file(path: Path) -> Optional[Dict[str, Any]]:
    """
    Try to parse a damaged JSON file (trailing commas, truncated tail).

    Args:
        path: File to read.

    Returns:
        Parsed dict, or None if it stays unreadable.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None

    without_trailing_commas = re.sub(r",(\s*})", r"\1", raw)
    without_trailing_commas = re.sub(r",(\s*])", r"\1", without_trailing_commas)
    try:
        data = json.loads(without_trailing_commas)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    # Truncated write: drop the incomplete last entry and close the root object.
    last_complete = raw.rfind("\n  },")
    if last_complete < 0:
        return None
    try:
        data = json.loads(raw[: last_complete + 4] + "\n}\n")
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _archive_json(path: Path) -> None:
    """
    Rename the migrated JSON file so it is kept but no longer used.

    Args:
        path: Legacy JSON file to archive.
    """
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = path.with_name(f"{path.name}.migrated-{stamp}")
    counter = 1
    while target.exists():
        target = path.with_name(f"{path.name}.migrated-{stamp}-{counter}")
        counter += 1
    try:
        path.rename(target)
    except OSError as exc:
        # Not fatal: re-migration is prevented by the row count check.
        print(f"Image library migration: could not archive {path.name}: {exc}")


def _safe_clear(repository: ImagesRepository) -> None:
    """
    Empty the image tables after a failed migration.

    Args:
        repository: Repository bound to the SQLite library.
    """
    try:
        repository.delete_all_images()
    except sqlite3.DatabaseError as exc:
        print(f"Image library migration: cleanup failed: {exc}")


__all__ = [
    "export_library_to_json",
    "migrate_json_if_needed",
    "read_legacy_json",
]
