"""
Helpers to read fragments from global theme QSS files (same sources as ``apply_global_stylesheet``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

_GUI_DIR = Path(__file__).resolve().parent
_STYLES_DIR = _GUI_DIR / "styles"


def extract_qmainwindow_rule_from_theme(theme: str) -> Optional[str]:
    """
    Return the ``QMainWindow { ... }`` rule from ``gui/styles/style_{theme}.qss``.

    Used so secondary windows (e.g. session slideshow) can match the main window chrome
    (gradient or solid) without duplicating values.

    Args:
        theme: Theme key (e.g. ``dark``, ``light``, ``neon_night``).

    Returns:
        The rule text including the selector, or None if the file or rule is missing.
    """
    path = _STYLES_DIR / f"style_{theme}.qss"
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    return _extract_first_qmainwindow_rule(text)


def _extract_first_qmainwindow_rule(qss: str) -> Optional[str]:
    """
    Parse the first top-level ``QMainWindow { ... }`` block (brace-balanced).

    Args:
        qss: Full QSS text.

    Returns:
        The rule substring, or None if not found.
    """
    key = "QMainWindow"
    idx = qss.find(key)
    if idx < 0:
        return None
    # Skip whitespace between selector and '{'
    brace_open = qss.find("{", idx + len(key))
    if brace_open < 0:
        return None
    depth = 0
    for i in range(brace_open, len(qss)):
        c = qss[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return qss[idx : i + 1].strip()
    return None
