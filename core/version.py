"""
Application version helpers (single source of truth: VERSION file at repo root).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path


def _version_file_candidates() -> list[Path]:
    """
    Return likely locations of the VERSION file (dev + frozen).

    Returns:
        list[Path]: Candidate paths ordered by preference.
    """
    here = Path(__file__).resolve().parent
    candidates = [
        here.parent / "VERSION",
        Path.cwd() / "VERSION",
    ]
    import sys

    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.insert(0, Path(meipass) / "VERSION")
        candidates.insert(0, Path(sys.executable).resolve().parent / "VERSION")
    return candidates


@lru_cache(maxsize=1)
def get_version() -> str:
    """
    Read the application version from the VERSION file.

    Returns:
        str: Semantic version string (e.g. ``0.1.0``). Falls back to ``0.0.0``.
    """
    for path in _version_file_candidates():
        try:
            if path.is_file():
                text = path.read_text(encoding="utf-8").strip()
                if text:
                    return text.splitlines()[0].strip()
        except OSError:
            continue
    return "0.0.0"
