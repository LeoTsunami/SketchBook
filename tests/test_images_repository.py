"""Tests for the SQLite images repository."""

import sqlite3
import threading
from pathlib import Path
from typing import Dict

import pytest

from core.db.connection import LibraryConnection
from core.db.images_repository import USER_TAG_SOURCE, ImagesRepository
from core.db.schema import SCHEMA_VERSION, get_schema_version


def _row(image_id: str, **overrides) -> Dict:
    """Build a minimal repository row."""
    data = {
        "id": image_id,
        "path": f"{image_id}.jpg",
        "original_filename": f"{image_id}.jpg",
        "width": 1920,
        "height": 1080,
        "file_size": 100,
        "format": "JPEG",
        "tags": {"existing"},
    }
    data.update(overrides)
    return data


@pytest.fixture
def repository(tmp_path: Path):
    """Isolated repository closed after the test."""
    connection = LibraryConnection(tmp_path / "library.db")
    repo = ImagesRepository(connection)
    yield repo
    connection.close()


def test_schema_version_and_reserved_tables(repository: ImagesRepository) -> None:
    """Version 1 schema includes marketplace tables even if unused."""
    with repository.connection.read() as conn:
        assert get_schema_version(conn) == SCHEMA_VERSION
        names = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    assert {
        "libraries",
        "images",
        "image_tags",
        "vendors",
        "entitlements",
        "tag_taxonomy",
        "tag_shelves",
    }.issubset(names)


def test_upsert_touches_only_changed_row(repository: ImagesRepository) -> None:
    """A flush updates one image without rewriting the others."""
    repository.insert_many(
        [
            _row("a", width=1920, tags={"old-a"}),
            _row("b", width=800, tags={"old-b"}),
        ]
    )
    repository.apply_changes([_row("a", width=50, tags={"x"})], [])

    images = {row["id"]: row for row in repository.fetch_images()}
    tags = repository.fetch_tags()
    assert images["a"]["width"] == 50
    assert images["b"]["width"] == 800
    assert tags["a"] == {"x"}
    assert tags["b"] == {"old-b"}


def test_apply_changes_rolls_back_on_error(
    repository: ImagesRepository, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failure mid-flush leaves the previous rows intact."""
    repository.insert_many([_row("a", width=1920, tags={"keep"})])

    def _boom(*_args, **_kwargs) -> None:
        raise sqlite3.DatabaseError("forced failure")

    monkeypatch.setattr(ImagesRepository, "_replace_user_tags", _boom)
    with pytest.raises(sqlite3.DatabaseError):
        repository.apply_changes([_row("a", width=1, tags={"z"})], [])

    images = repository.fetch_images()
    assert images[0]["width"] == 1920
    assert repository.fetch_tags()["a"] == {"keep"}


def test_user_flush_preserves_vendor_tags(repository: ImagesRepository) -> None:
    """User tag rewrites do not delete vendor-sourced tags."""
    repository.insert_many([_row("a", tags={"UserOld"})])
    with repository.connection.transaction() as conn:
        conn.execute(
            "INSERT INTO image_tags (image_id, tag, source) VALUES (?, ?, ?)",
            ("a", "VendorTag", "vendor"),
        )
    repository.apply_changes([_row("a", tags={"UserNew"})], [])
    assert repository.fetch_tags()["a"] == {"UserNew", "VendorTag"}
    with repository.connection.read() as conn:
        sources = {
            row[0]
            for row in conn.execute(
                "SELECT source FROM image_tags WHERE image_id = ?", ("a",)
            ).fetchall()
        }
    assert sources == {USER_TAG_SOURCE, "vendor"}


def test_delete_cascades_tags(repository: ImagesRepository) -> None:
    """Deleting an image removes its tag rows."""
    repository.insert_many([_row("a"), _row("b")])
    repository.apply_changes([], ["a"])
    assert [row["id"] for row in repository.fetch_images()] == ["b"]
    assert "a" not in repository.fetch_tags()


def test_concurrent_reads_during_write(repository: ImagesRepository) -> None:
    """Readers and a writer can share the locked connection without errors."""
    repository.insert_many([_row(f"img-{i}") for i in range(8)])
    errors = []

    def _reader() -> None:
        try:
            for _ in range(20):
                repository.fetch_images()
                repository.fetch_tags()
        except Exception as exc:  # pragma: no cover - assertion below
            errors.append(exc)

    def _writer() -> None:
        try:
            for index in range(10):
                repository.apply_changes(
                    [_row("img-0", tags={f"t-{index}"})],
                    [],
                )
        except Exception as exc:  # pragma: no cover - assertion below
            errors.append(exc)

    reader = threading.Thread(target=_reader)
    writer = threading.Thread(target=_writer)
    reader.start()
    writer.start()
    reader.join()
    writer.join()
    assert errors == []
    assert repository.count_images() == 8
