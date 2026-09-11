"""
SQLite schema for the local image library.

Version 1 holds the tables used today (libraries, images, image_tags) plus
tables reserved for online library purchase and sharing (vendors, entitlements,
tag_taxonomy, tag_shelves). The reserved tables are created empty so adding the
online features later needs no schema migration.
"""

import sqlite3
from typing import Tuple

# Bump when adding a new _Vn_STATEMENTS block, and extend apply_migrations.
SCHEMA_VERSION = 1

# Library id used for images the user imported himself.
LOCAL_LIBRARY_ID = "local"

_V1_STATEMENTS: Tuple[str, ...] = (
    # ------------------------------------------------------------------ active
    """
    CREATE TABLE IF NOT EXISTS libraries (
        id            TEXT PRIMARY KEY,
        name          TEXT NOT NULL,
        kind          TEXT NOT NULL DEFAULT 'local',
        version       TEXT NOT NULL DEFAULT '',
        remote_id     TEXT,
        vendor_id     TEXT,
        license       TEXT NOT NULL DEFAULT '',
        installed_at  TEXT NOT NULL DEFAULT '',
        updated_at    TEXT NOT NULL DEFAULT '',
        manifest_json TEXT NOT NULL DEFAULT '{}'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS images (
        id                TEXT PRIMARY KEY,
        library_id        TEXT NOT NULL DEFAULT 'local' REFERENCES libraries(id),
        path              TEXT NOT NULL,
        original_filename TEXT NOT NULL DEFAULT '',
        width             INTEGER NOT NULL DEFAULT 0,
        height            INTEGER NOT NULL DEFAULT 0,
        file_size         INTEGER NOT NULL DEFAULT 0,
        format            TEXT NOT NULL DEFAULT '',
        original_path     TEXT NOT NULL DEFAULT '',
        import_date       TEXT NOT NULL DEFAULT '',
        kind              TEXT NOT NULL DEFAULT 'single',
        group_id          TEXT NOT NULL DEFAULT '',
        hidden            INTEGER NOT NULL DEFAULT 0,
        member_ids_json   TEXT NOT NULL DEFAULT '[]',
        checksum          TEXT NOT NULL DEFAULT '',
        remote_id         TEXT,
        license           TEXT NOT NULL DEFAULT '',
        protected         INTEGER NOT NULL DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS image_tags (
        image_id TEXT NOT NULL REFERENCES images(id) ON DELETE CASCADE,
        tag      TEXT NOT NULL,
        source   TEXT NOT NULL DEFAULT 'user',
        PRIMARY KEY (image_id, tag, source)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_image_tags_tag ON image_tags(tag)",
    "CREATE INDEX IF NOT EXISTS idx_images_library ON images(library_id)",
    "CREATE INDEX IF NOT EXISTS idx_images_hidden ON images(hidden)",
    "CREATE INDEX IF NOT EXISTS idx_images_group ON images(group_id)",
    # ---------------------------------------------------------------- reserved
    """
    CREATE TABLE IF NOT EXISTS vendors (
        id            TEXT PRIMARY KEY,
        name          TEXT NOT NULL,
        url           TEXT NOT NULL DEFAULT '',
        avatar_path   TEXT NOT NULL DEFAULT '',
        remote_id     TEXT,
        metadata_json TEXT NOT NULL DEFAULT '{}'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS entitlements (
        library_id TEXT PRIMARY KEY REFERENCES libraries(id) ON DELETE CASCADE,
        user_ref   TEXT NOT NULL DEFAULT '',
        source     TEXT NOT NULL DEFAULT 'local',
        status     TEXT NOT NULL DEFAULT 'active',
        expires_at TEXT NOT NULL DEFAULT '',
        token_hash TEXT NOT NULL DEFAULT '',
        checked_at TEXT NOT NULL DEFAULT ''
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tag_taxonomy (
        tag             TEXT PRIMARY KEY,
        parent_tag      TEXT NOT NULL DEFAULT '',
        category        TEXT NOT NULL DEFAULT '',
        icon            TEXT NOT NULL DEFAULT '',
        library_id      TEXT NOT NULL DEFAULT 'local',
        registered_only INTEGER NOT NULL DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tag_shelves (
        name        TEXT PRIMARY KEY,
        filter_mode TEXT NOT NULL DEFAULT 'or',
        color       TEXT NOT NULL DEFAULT '',
        position    INTEGER NOT NULL DEFAULT 0,
        library_id  TEXT NOT NULL DEFAULT 'local'
    )
    """,
)


def ensure_local_library(conn: sqlite3.Connection) -> None:
    """
    Make sure the ``local`` library row exists so image rows satisfy the FK.

    Args:
        conn: Open SQLite connection.
    """
    conn.execute(
        "INSERT OR IGNORE INTO libraries (id, name, kind) VALUES (?, ?, ?)",
        (LOCAL_LIBRARY_ID, "My library", "local"),
    )


def get_schema_version(conn: sqlite3.Connection) -> int:
    """
    Read the schema version stored in ``PRAGMA user_version``.

    Args:
        conn: Open SQLite connection.

    Returns:
        int: Current schema version (0 for a brand new file).
    """
    row = conn.execute("PRAGMA user_version").fetchone()
    return int(row[0]) if row is not None else 0


def apply_migrations(conn: sqlite3.Connection) -> int:
    """
    Create or upgrade the schema up to SCHEMA_VERSION.

    Args:
        conn: Open SQLite connection (autocommit mode).

    Returns:
        int: Schema version after migration.
    """
    version = get_schema_version(conn)
    if version >= SCHEMA_VERSION:
        ensure_local_library(conn)
        return version

    conn.execute("BEGIN IMMEDIATE")
    try:
        if version < 1:
            for statement in _V1_STATEMENTS:
                conn.execute(statement)
        ensure_local_library(conn)
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    except sqlite3.DatabaseError:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")
    return SCHEMA_VERSION
