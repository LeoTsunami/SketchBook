"""
SQL access layer for the image library: images, their tags, and libraries.

This module holds no business logic (no sorting, no filtering, no tag
hierarchy). It maps plain dicts keyed by column name to rows, so ``core.image_db``
stays the only place that knows about ``ImageMetadata``.
"""

import json
import sqlite3
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set

from core.db.connection import LibraryConnection
from core.db.schema import LOCAL_LIBRARY_ID

# Column order used by every insert/update statement.
IMAGE_COLUMNS = (
    "id",
    "library_id",
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
    "hidden",
    "member_ids_json",
    "checksum",
    "remote_id",
    "license",
    "protected",
)

# Columns owned by ImageMetadata. The remaining ones (library_id, checksum,
# remote_id, license, protected) belong to whoever installed the image (local
# import or, later, a purchased pack) and must survive an update.
MANAGED_COLUMNS = (
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
    "hidden",
    "member_ids_json",
)

# Tag rows written by the application itself. Rows from a purchased library are
# stored with a different source ('vendor') and are never touched by a flush,
# so a pack update cannot wipe the tags the user added on top.
USER_TAG_SOURCE = "user"

_INSERT_IMAGE_SQL = (
    f"INSERT INTO images ({', '.join(IMAGE_COLUMNS)}) "
    f"VALUES ({', '.join('?' * len(IMAGE_COLUMNS))})"
)

_UPSERT_IMAGE_SQL = (
    _INSERT_IMAGE_SQL
    + " ON CONFLICT(id) DO UPDATE SET "
    + ", ".join(f"{column} = excluded.{column}" for column in MANAGED_COLUMNS)
)

_INSERT_TAG_SQL = (
    "INSERT OR IGNORE INTO image_tags (image_id, tag, source) VALUES (?, ?, ?)"
)


class ImagesRepository:
    """Persists image rows and their tags in SQLite."""

    def __init__(self, connection: LibraryConnection) -> None:
        """
        Initialize the repository.

        Args:
            connection: Shared library connection.
        """
        self._connection = connection

    @property
    def connection(self) -> LibraryConnection:
        """Underlying library connection."""
        return self._connection

    # ----------------------------------------------------------------- reading

    def fetch_images(self) -> List[Dict[str, Any]]:
        """
        Read every image row.

        Returns:
            List of dicts keyed by column name, with ``member_ids`` decoded to a
            list and ``hidden`` / ``protected`` decoded to booleans.
        """
        with self._connection.read() as conn:
            rows = conn.execute(
                f"SELECT {', '.join(IMAGE_COLUMNS)} FROM images"
            ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def fetch_tags(self) -> Dict[str, Set[str]]:
        """
        Read tags for every image, merging all sources.

        Returns:
            Mapping of image id to its set of tags.
        """
        with self._connection.read() as conn:
            rows = conn.execute("SELECT image_id, tag FROM image_tags").fetchall()
        tags: Dict[str, Set[str]] = {}
        for image_id, tag in rows:
            tags.setdefault(image_id, set()).add(tag)
        return tags

    def count_images(self) -> int:
        """
        Count image rows.

        Returns:
            int: Number of rows in the ``images`` table.
        """
        with self._connection.read() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM images").fetchone()[0])

    # ----------------------------------------------------------------- writing

    def apply_changes(
        self,
        upserts: Sequence[Mapping[str, Any]],
        deleted_ids: Iterable[str] = (),
    ) -> None:
        """
        Write changed images and drop deleted ones in a single transaction.

        Args:
            upserts: Rows to insert or update; each mapping holds the
                ``ImageMetadata`` fields plus an optional ``tags`` set.
            deleted_ids: Image ids to remove (their tags cascade).
        """
        deleted = [(image_id,) for image_id in deleted_ids]
        if not upserts and not deleted:
            return
        with self._connection.transaction() as conn:
            if deleted:
                conn.executemany("DELETE FROM images WHERE id = ?", deleted)
            for row in upserts:
                conn.execute(_UPSERT_IMAGE_SQL, self._to_params(row))
                self._replace_user_tags(conn, str(row["id"]), row.get("tags") or ())

    def insert_many(self, rows: Sequence[Mapping[str, Any]]) -> int:
        """
        Bulk insert rows, for the initial JSON import.

        Args:
            rows: Rows to insert; each mapping holds the ``ImageMetadata``
                fields plus an optional ``tags`` set.

        Returns:
            int: Number of image rows inserted.
        """
        if not rows:
            return 0
        image_params = [self._to_params(row) for row in rows]
        tag_params = [
            (str(row["id"]), tag, USER_TAG_SOURCE)
            for row in rows
            for tag in (row.get("tags") or ())
        ]
        with self._connection.transaction() as conn:
            conn.executemany(_INSERT_IMAGE_SQL, image_params)
            if tag_params:
                conn.executemany(_INSERT_TAG_SQL, tag_params)
        return len(image_params)

    def delete_all_images(self) -> None:
        """Remove every image row (and its tags, by cascade)."""
        with self._connection.transaction() as conn:
            conn.execute("DELETE FROM images")

    def ensure_library(
        self,
        library_id: str = LOCAL_LIBRARY_ID,
        name: str = "My library",
        kind: str = "local",
    ) -> None:
        """
        Create a library row if it does not exist yet.

        Args:
            library_id: Library identifier.
            name: Display name.
            kind: ``local``, ``purchased`` or ``shared``.
        """
        with self._connection.transaction() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO libraries (id, name, kind) VALUES (?, ?, ?)",
                (library_id, name, kind),
            )

    # ----------------------------------------------------------------- mapping

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        """
        Convert a SQLite row into a plain dict.

        Args:
            row: Row selected with ``IMAGE_COLUMNS``.

        Returns:
            Dict with decoded ``member_ids``, ``hidden`` and ``protected``.
        """
        data: Dict[str, Any] = {key: row[key] for key in row.keys()}
        data["hidden"] = bool(data.get("hidden"))
        data["protected"] = bool(data.get("protected"))
        data["member_ids"] = _decode_member_ids(data.pop("member_ids_json", "[]"))
        return data

    @staticmethod
    def _to_params(row: Mapping[str, Any]) -> tuple:
        """
        Build statement parameters in ``IMAGE_COLUMNS`` order.

        Args:
            row: Mapping holding image fields (``member_ids`` as a list).

        Returns:
            tuple: Values ready for the insert/upsert statement.
        """
        values: List[Any] = []
        for column in IMAGE_COLUMNS:
            if column == "member_ids_json":
                values.append(json.dumps(list(row.get("member_ids") or [])))
            elif column == "library_id":
                values.append(row.get("library_id") or LOCAL_LIBRARY_ID)
            elif column in ("hidden", "protected"):
                values.append(1 if row.get(column) else 0)
            elif column == "remote_id":
                values.append(row.get("remote_id"))
            elif column in ("width", "height", "file_size"):
                values.append(int(row.get(column) or 0))
            else:
                values.append(row.get(column) if row.get(column) is not None else "")
        return tuple(values)

    @staticmethod
    def _replace_user_tags(
        conn: sqlite3.Connection, image_id: str, tags: Iterable[str]
    ) -> None:
        """
        Rewrite the ``user`` tag rows of one image, leaving other sources alone.

        Args:
            conn: Connection inside an open transaction.
            image_id: Target image id.
            tags: Tags currently held in memory for this image.
        """
        conn.execute(
            "DELETE FROM image_tags WHERE image_id = ? AND source = ?",
            (image_id, USER_TAG_SOURCE),
        )
        rows = [(image_id, tag, USER_TAG_SOURCE) for tag in tags if tag]
        if rows:
            conn.executemany(_INSERT_TAG_SQL, rows)


def _decode_member_ids(raw: Optional[str]) -> List[str]:
    """
    Decode the JSON list of turnaround member ids.

    Args:
        raw: JSON array string, possibly empty or invalid.

    Returns:
        List of member ids (empty when unreadable).
    """
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return [str(item) for item in value] if isinstance(value, list) else []
