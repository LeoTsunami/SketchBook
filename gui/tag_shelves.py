"""
Tag library shelves: titled sections like "Camera-Angle:" in default_tags.json.

Add a shelf by adding a key that ends with ":" to gui/ressources/default_tags.json.
Use a tag list or {"filter": "or"|"and", "tags": [...]}. Miscellaneous: defaults to AND;
other shelves default to OR (any selected tag). Override per shelf via "_shelf_filters".
"""

from __future__ import annotations

import json
from pathlib import Path
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

MISCELLANEOUS_SHELF = "Miscellaneous:"
SHELF_FILTER_AND = "and"
SHELF_FILTER_OR = "or"


def is_tag_shelf(category: str) -> bool:
    """Return True if category is a titled shelf (name ends with ':')."""
    return bool(category) and category.endswith(":")


def is_metadata_key(key: str) -> bool:
    """Return True for JSON metadata keys (e.g. _shelf_filters), not categories."""
    return key.startswith("_")


def shelf_default_filter_mode(category: str) -> str:
    """
    Default filter semantics for a shelf when not specified in JSON.

    Miscellaneous: image must have all selected tags (AND).
    Other shelves: image must match at least one selected tag (OR).
    """
    if category == MISCELLANEOUS_SHELF:
        return SHELF_FILTER_AND
    return SHELF_FILTER_OR


def parse_category_tags(value: Any) -> Tuple[Any, Optional[str]]:
    """
    Normalize a category entry from default_tags.json.

    Args:
        value: List of tags, or dict with "tags" and optional "filter".

    Returns:
        Tuple of (data for collect_subtags, filter override or None).
    """
    if isinstance(value, list):
        return value, None
    if isinstance(value, dict):
        tags = value.get("tags", [])
        raw_filter = str(value.get("filter", "")).lower()
        if raw_filter in (SHELF_FILTER_AND, SHELF_FILTER_OR):
            return tags, raw_filter
        return tags, None
    return [], None


def load_default_tags_taxonomy(path: Path) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """
    Load default_tags.json categories and per-shelf filter modes.

    Args:
        path: Path to default_tags.json.

    Returns:
        Tuple of (category_name -> tags value, shelf_name -> "and"|"or").
    """
    if not path.exists():
        return {}, {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {}, {}

    shelf_modes: Dict[str, str] = {}
    raw_filters = data.get("_shelf_filters")
    if isinstance(raw_filters, dict):
        for name, mode in raw_filters.items():
            m = str(mode).lower()
            if m in (SHELF_FILTER_AND, SHELF_FILTER_OR):
                shelf_modes[str(name)] = m

    categories: Dict[str, Any] = {}
    for key, value in data.items():
        if is_metadata_key(key):
            continue
        categories[key] = value
        if is_tag_shelf(key):
            _, override = parse_category_tags(value)
            shelf_modes[key] = (
                override or shelf_modes.get(key) or shelf_default_filter_mode(key)
            )
    return categories, shelf_modes


def shelf_categories_with_filter(modes: Dict[str, str], filter_mode: str) -> List[str]:
    """Return shelf names that use the given filter mode ('and' or 'or')."""
    return [name for name, mode in modes.items() if mode == filter_mode]


def normalize_shelf_name(name: str) -> str:
    """
    Normalize a shelf title for storage (trim; append ':' if missing).

    Args:
        name: Raw shelf title from the user.

    Returns:
        Shelf key used in the tag library grid.
    """
    text = name.strip()
    if not text:
        return ""
    if not text.endswith(":"):
        text += ":"
    return text


def merge_custom_shelves(
    categories: Dict[str, Any],
    shelf_modes: Dict[str, str],
    custom_shelves: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Insert user-created shelves into the taxonomy before Miscellaneous.

    Args:
        categories: Built-in categories from default_tags.json.
        shelf_modes: Per-shelf filter modes (mutated for new shelves).
        custom_shelves: List of {"name", "filter", "tags"} from user config.

    Returns:
        Ordered category map including custom shelves.
    """
    pending: List[Tuple[str, List[Any], str]] = []
    for shelf in custom_shelves:
        if not isinstance(shelf, dict):
            continue
        name = normalize_shelf_name(str(shelf.get("name", "")))
        if not name or name in categories:
            continue
        tags = shelf.get("tags", [])
        if not isinstance(tags, list):
            tags = []
        raw_filter = str(shelf.get("filter", "")).lower()
        mode = (
            raw_filter
            if raw_filter in (SHELF_FILTER_AND, SHELF_FILTER_OR)
            else shelf_default_filter_mode(name)
        )
        shelf_modes[name] = mode
        pending.append((name, tags, mode))

    if not pending:
        return dict(categories)

    out: OrderedDict[str, Any] = OrderedDict()
    inserted = False
    for key, value in categories.items():
        if key == MISCELLANEOUS_SHELF and not inserted:
            for name, tags, _mode in pending:
                out[name] = list(tags)
            inserted = True
        out[key] = value
    if not inserted:
        for name, tags, _mode in pending:
            out[name] = list(tags)
    return dict(out)
