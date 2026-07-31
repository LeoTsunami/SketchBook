#!/usr/bin/env python3
"""
Bootstrap entry for SketchBook (dev + frozen PyInstaller builds).

Ensures the working directory and sys.path point at the app root so relative
paths (QSS, ressources) resolve correctly.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def resolve_app_root() -> Path:
    """
    Resolve the directory that contains app resources (gui/, VERSION, …).

    Returns:
        Path: Resource root for the running process.
    """
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def prepare_environment() -> Path:
    """
    Chdir and prepend sys.path for imports and relative resource paths.

    Returns:
        Path: The resolved application root.
    """
    root = resolve_app_root()
    os.chdir(root)
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    return root


def main() -> None:
    """Prepare environment then launch the Qt application."""
    prepare_environment()
    from main import main as app_main

    app_main()


if __name__ == "__main__":
    main()
