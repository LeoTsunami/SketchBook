"""
Local SQLite storage for the SketchBook image library.

Modules:
    schema: DDL and schema versioning.
    connection: thread-safe SQLite connection wrapper.
    images_repository: SQL CRUD for images, tags and libraries.
    migrate_json: one-shot import of the legacy ``images.json`` database.
"""

from core.db.connection import LibraryConnection, open_connection
from core.db.images_repository import ImagesRepository
from core.db.schema import LOCAL_LIBRARY_ID, SCHEMA_VERSION

__all__ = [
    "ImagesRepository",
    "LibraryConnection",
    "LOCAL_LIBRARY_ID",
    "SCHEMA_VERSION",
    "open_connection",
]
