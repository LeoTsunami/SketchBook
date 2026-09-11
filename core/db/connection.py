"""
Thread-safe SQLite connection for the local image library.

A single connection is shared by the whole process and serialized with a
re-entrant lock: the library is read by the startup preload thread and written
by Qt thread-pool workers (tag apply/remove), so every statement must run under
the same guard.
"""

import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

from core.db.schema import apply_migrations

# WAL keeps reads working while a write transaction is open; NORMAL sync is a
# safe trade-off for a desktop app that already keeps dated backups.
_PRAGMAS = (
    "PRAGMA journal_mode=WAL",
    "PRAGMA foreign_keys=ON",
    "PRAGMA synchronous=NORMAL",
    "PRAGMA busy_timeout=5000",
)


def open_connection(path: Path) -> sqlite3.Connection:
    """
    Open the library database, apply pragmas and migrate the schema.

    A file that is not a valid SQLite database is quarantined and replaced
    with a fresh empty library, matching the old JSON backend (corrupt file
    became an empty catalog rather than a crash).

    Args:
        path: Path to the SQLite file (parent directories are created).

    Returns:
        sqlite3.Connection: Connection in autocommit mode with row access by name.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        return _open_and_migrate(path)
    except sqlite3.DatabaseError as exc:
        print(f"Library DB: opening failed ({exc}); replacing corrupt file.")
        _quarantine_db_files(path)
        return _open_and_migrate(path)


def _open_and_migrate(path: Path) -> sqlite3.Connection:
    """
    Connect, set pragmas and apply schema migrations.

    Args:
        path: Path to the SQLite file.

    Returns:
        sqlite3.Connection: Ready connection.

    Raises:
        sqlite3.DatabaseError: If the file is not a usable database.
    """
    # isolation_level=None: no implicit transactions, they are opened explicitly.
    conn = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    try:
        for pragma in _PRAGMAS:
            try:
                conn.execute(pragma)
            except sqlite3.DatabaseError as exc:
                # e.g. WAL is unavailable on some network shares; keep the default.
                print(f"Library DB: {pragma} failed: {exc}")
        apply_migrations(conn)
    except sqlite3.DatabaseError:
        conn.close()
        raise
    return conn


def _quarantine_db_files(path: Path) -> None:
    """
    Rename a corrupt SQLite file and its WAL sidecars so a new file can be created.

    Args:
        path: Path of the main ``.db`` file.
    """
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(f"{path}{suffix}") if suffix else path
        if not candidate.exists():
            continue
        dest = candidate.with_name(f"{candidate.name}.corrupt-{stamp}")
        try:
            candidate.replace(dest)
        except OSError:
            try:
                candidate.unlink()
            except OSError:
                pass


def backup_database(source: Path, dest: Path) -> bool:
    """
    Copy a SQLite database file using the backup API.

    Opens its own connection and does not migrate the schema, so it is safe to
    call on a database owned by another connection (or another process).

    Args:
        source: Existing SQLite file.
        dest: Destination file (overwritten if it exists).

    Returns:
        True if the backup completed.
    """
    source = Path(source)
    dest = Path(dest)
    if not source.exists():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    src_conn = None
    dest_conn = None
    try:
        src_conn = sqlite3.connect(str(source))
        dest_conn = sqlite3.connect(str(dest))
        src_conn.backup(dest_conn)
        return True
    except sqlite3.DatabaseError as exc:
        print(f"Library DB backup failed: {exc}")
        return False
    finally:
        if dest_conn is not None:
            dest_conn.close()
        if src_conn is not None:
            src_conn.close()


class LibraryConnection:
    """Shared SQLite connection guarded by a re-entrant lock."""

    def __init__(self, path: Path) -> None:
        """
        Open the database at the given path.

        Args:
            path: Path to the SQLite file.
        """
        self._path = Path(path)
        self._lock = threading.RLock()
        self._depth = 0
        self._conn = open_connection(self._path)

    @property
    def path(self) -> Path:
        """Path of the SQLite file backing this connection."""
        return self._path

    @contextmanager
    def read(self) -> Iterator[sqlite3.Connection]:
        """
        Borrow the connection for read-only statements.

        Yields:
            sqlite3.Connection: The shared connection, lock held.
        """
        with self._lock:
            yield self._conn

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """
        Run statements in a single transaction; nested calls join the outer one.

        Yields:
            sqlite3.Connection: The shared connection, lock held.

        Raises:
            sqlite3.DatabaseError: Propagated after rollback.
        """
        with self._lock:
            outermost = self._depth == 0
            if outermost:
                self._conn.execute("BEGIN IMMEDIATE")
            self._depth += 1
            try:
                yield self._conn
            except BaseException:
                self._depth -= 1
                if outermost:
                    self._conn.execute("ROLLBACK")
                raise
            self._depth -= 1
            if outermost:
                self._conn.execute("COMMIT")

    def backup_to(self, dest: Path) -> None:
        """
        Copy the database to ``dest`` using the SQLite backup API.

        A plain file copy of a live WAL database can miss committed pages, so
        backups must go through this method.

        Args:
            dest: Destination file (overwritten if it exists).
        """
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            target = sqlite3.connect(str(dest))
            try:
                self._conn.backup(target)
            finally:
                target.close()

    def close(self) -> None:
        """Close the underlying connection."""
        with self._lock:
            self._conn.close()
