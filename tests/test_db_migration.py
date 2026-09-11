"""Tests for the one-shot images.json → SQLite migration."""

import json
from pathlib import Path
from typing import Any, Dict

import pytest

from core.db.connection import LibraryConnection
from core.db.images_repository import ImagesRepository
from core.db.migrate_json import export_library_to_json, migrate_json_if_needed
from core.image_db import ImageDatabase


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    """Write a legacy images.json payload."""
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _sample_payload() -> Dict[str, Any]:
    """Legacy catalog with tags, a turnaround group, and an unknown field."""
    return {
        "img1": {
            "id": "img1",
            "path": "a.jpg",
            "original_filename": "original-a.jpg",
            "width": 800,
            "height": 600,
            "file_size": 111,
            "format": "JPEG",
            "original_path": "C:/src/a.jpg",
            "import_date": "2026-01-01T00:00:00",
            "kind": "single",
            "group_id": "",
            "hidden": False,
            "tags": ["Human", "Gesture"],
            "unknown_field": "ignored",
        },
        "root": {
            "id": "root",
            "path": "m1.jpg",
            "original_filename": "Turnaround (2 poses)",
            "width": 100,
            "height": 100,
            "file_size": 50,
            "format": "JPEG",
            "import_date": "2026-02-01T00:00:00",
            "kind": "turnaround",
            "member_ids": ["m1", "m2"],
            "hidden": False,
            "tags": ["Turnaround", "Human"],
        },
        "m1": {
            "id": "m1",
            "path": "m1.jpg",
            "original_filename": "pose1.jpg",
            "width": 100,
            "height": 100,
            "file_size": 50,
            "format": "JPEG",
            "kind": "single",
            "group_id": "root",
            "hidden": True,
            "tags": ["A"],
        },
        "m2": {
            "id": "m2",
            "path": "m2.jpg",
            "original_filename": "pose2.jpg",
            "width": 100,
            "height": 100,
            "file_size": 50,
            "format": "JPEG",
            "kind": "single",
            "group_id": "root",
            "hidden": True,
            "tags": ["B"],
        },
    }


@pytest.fixture
def repository(tmp_path: Path):
    """Isolated repository closed after the test."""
    connection = LibraryConnection(tmp_path / "library.db")
    repo = ImagesRepository(connection)
    yield repo
    connection.close()


def test_migrate_json_imports_tags_and_turnaround(
    tmp_path: Path, repository: ImagesRepository
) -> None:
    """JSON rows, tags and turnaround fields land in SQLite; unknown keys drop."""
    json_path = tmp_path / "images.json"
    _write_json(json_path, _sample_payload())

    imported = migrate_json_if_needed(repository, json_path)
    assert imported == 4
    assert not json_path.exists()
    archived = list(tmp_path.glob("images.json.migrated-*"))
    assert len(archived) == 1

    images = {row["id"]: row for row in repository.fetch_images()}
    tags = repository.fetch_tags()
    assert "unknown_field" not in images["img1"]
    assert images["img1"]["path"] == "a.jpg"
    assert images["img1"]["width"] == 800
    assert tags["img1"] == {"Human", "Gesture"}
    assert images["root"]["kind"] == "turnaround"
    assert images["root"]["member_ids"] == ["m1", "m2"]
    assert images["m1"]["hidden"] is True
    assert images["m1"]["group_id"] == "root"
    assert tags["m1"] == {"A"}
    assert tags["root"] == {"Turnaround", "Human"}


def test_migrate_json_is_idempotent(
    tmp_path: Path, repository: ImagesRepository
) -> None:
    """A second pass does nothing even if images.json reappears."""
    json_path = tmp_path / "images.json"
    _write_json(json_path, _sample_payload())
    assert migrate_json_if_needed(repository, json_path) == 4
    assert migrate_json_if_needed(repository, json_path) == 0

    _write_json(json_path, _sample_payload())
    assert migrate_json_if_needed(repository, json_path) == 0
    assert repository.count_images() == 4
    assert json_path.exists()


def test_migrate_rollback_keeps_json_on_count_mismatch(
    tmp_path: Path, repository: ImagesRepository, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed verification clears SQLite and leaves images.json untouched."""
    json_path = tmp_path / "images.json"
    _write_json(json_path, _sample_payload())

    monkeypatch.setattr(ImagesRepository, "insert_many", lambda self, rows: len(rows))
    imported = migrate_json_if_needed(repository, json_path)
    assert imported == 0
    assert json_path.exists()
    assert repository.count_images() == 0


def test_migrate_repairs_trailing_commas(
    tmp_path: Path, repository: ImagesRepository
) -> None:
    """The legacy JSON repair path still runs during migration."""
    json_path = tmp_path / "images.json"
    json_path.write_text(
        '{\n  "x": {"id": "x", "path": "x.jpg", "original_filename": "x.jpg",'
        ' "width": 1, "height": 1, "file_size": 1, "format": "JPEG", "tags": ["T"],},\n}\n',
        encoding="utf-8",
    )
    imported = migrate_json_if_needed(repository, json_path)
    assert imported == 1
    assert repository.fetch_tags()["x"] == {"T"}


def test_image_database_migrates_sibling_json(tmp_path: Path) -> None:
    """ImageDatabase imports images.json sitting next to library.db."""
    _write_json(tmp_path / "images.json", _sample_payload())
    db = ImageDatabase(tmp_path / "library.db")
    try:
        assert len(db.list_images()) == 4
        assert db.get_image("img1").tags == {"Human", "Gesture"}
        assert db.get_image("root").member_ids == ["m1", "m2"]
        assert db.get_image("m1").hidden is True
    finally:
        db.close()
    assert not (tmp_path / "images.json").exists()


def test_export_library_to_json_roundtrip(
    tmp_path: Path, repository: ImagesRepository
) -> None:
    """Export writes a JSON file that migrates back with the same rows."""
    json_path = tmp_path / "images.json"
    _write_json(json_path, _sample_payload())
    migrate_json_if_needed(repository, json_path)

    export_path = tmp_path / "export.json"
    written = export_library_to_json(repository, export_path)
    assert written == 4

    other_dir = tmp_path / "other"
    other_dir.mkdir()
    other = ImagesRepository(LibraryConnection(other_dir / "library.db"))
    try:
        imported = migrate_json_if_needed(other, export_path)
        assert imported == 4
        assert other.fetch_tags()["img1"] == {"Human", "Gesture"}
        root = next(row for row in other.fetch_images() if row["id"] == "root")
        assert root["member_ids"] == ["m1", "m2"]
    finally:
        other.connection.close()
