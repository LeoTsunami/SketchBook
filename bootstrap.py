#!/usr/bin/env python3
"""
Bootstrap entry for SketchBook (dev + frozen PyInstaller builds).

Ensures the working directory and sys.path point at the app root so relative
paths (QSS, ressources) resolve correctly.
"""

from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path

WINDOWS_APP_USER_MODEL_ID = "LeoTsunami.SketchBook"


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


def ensure_stdio() -> None:
    """
    Attach dummy stdout/stderr when the process has no console.

    PyInstaller windowed builds (``console=False``) set ``sys.stdout`` and
    ``sys.stderr`` to ``None``. Importing ``main`` would then crash on
    ``reconfigure`` / ``print``.
    """
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")


def set_windows_app_user_model_id() -> None:
    """
    Pin the process to a stable Windows AppUserModelID.

    Without this, the taskbar often shows a generic/Python icon and keeps
    a stale cache after an in-place Setup upgrade.
    """
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            WINDOWS_APP_USER_MODEL_ID
        )
    except (AttributeError, OSError):
        pass


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
    ensure_stdio()
    set_windows_app_user_model_id()
    prepare_environment()
    from main import main as app_main

    app_main()


if __name__ == "__main__":
    main()
