"""
User tags configuration: placements (category or parent tag) and optional icons.
Stored in user data config dir as user_tags_config.json.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.user_data import user_data


def get_config_path() -> Path:
    """Return the path to the user tags config file."""
    return user_data.get_user_tags_config_path()


def load_config() -> Dict[str, Any]:
    """
    Load user tags config (placements, icons, registered_only).
    Returns dict with "placements", "icons", "registered_only" keys; missing file returns defaults.
    """
    path = get_config_path()
    if not path.exists():
        return {"placements": {}, "icons": {}, "registered_only": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            import json
            data = json.load(f)
        placements = data.get("placements", {})
        icons = data.get("icons", {})
        registered_only = data.get("registered_only", [])
        return {
            "placements": dict(placements),
            "icons": dict(icons),
            "registered_only": list(registered_only),
        }
    except (OSError, ValueError) as e:
        print(f"Error loading user tags config: {e}")
        return {"placements": {}, "icons": {}, "registered_only": []}


def save_config(
    placements: Dict[str, Any],
    icons: Dict[str, str],
    registered_only: Optional[List[str]] = None,
) -> bool:
    """
    Save user tags config.

    Args:
        placements: Map tag name -> {"category": "Human"} or {"parent_tag": "Portrait"}.
        icons: Map tag name -> icon filename e.g. "Hand.png".
        registered_only: Tags added via UI but not yet on any image (optional).

    Returns:
        True if saved successfully.
    """
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"placements": placements, "icons": icons}
    if registered_only is not None:
        payload["registered_only"] = registered_only
    try:
        with open(path, "w", encoding="utf-8") as f:
            import json
            json.dump(payload, f, indent=2)
        return True
    except OSError as e:
        print(f"Error saving user tags config: {e}")
        return False


def get_placement(config: Dict[str, Any], tag: str) -> Optional[Dict[str, str]]:
    """
    Get placement for a tag: {"category": "Human"} or {"parent_tag": "Portrait"}.

    Args:
        config: Result of load_config().
        tag: Tag name.

    Returns:
        Placement dict or None if not set.
    """
    return config.get("placements", {}).get(tag)


def get_icon_filename(config: Dict[str, Any], tag: str) -> Optional[str]:
    """Get icon filename for a tag, or None."""
    return config.get("icons", {}).get(tag)


def set_placement(config_placements: Dict[str, Any], tag: str, category: Optional[str] = None, parent_tag: Optional[str] = None) -> None:
    """
    Set placement for a user tag (mutates config_placements).
    Exactly one of category or parent_tag must be set.

    Args:
        config_placements: Placements dict to update.
        tag: Tag name.
        category: Category name (e.g. "Human") to place the tag under.
        parent_tag: Another tag name to place this tag under (as sub-category).
    """
    if category is not None and parent_tag is not None:
        raise ValueError("Use either category or parent_tag, not both")
    if category is not None:
        config_placements[tag] = {"category": category}
    elif parent_tag is not None:
        config_placements[tag] = {"parent_tag": parent_tag}
    else:
        config_placements.pop(tag, None)


def rename_in_config(
    config_placements: Dict[str, Any],
    config_icons: Dict[str, str],
    old_name: str,
    new_name: str,
) -> None:
    """
    Rename a tag in the config (mutates both dicts).
    Updates keys from old_name to new_name; removes old_name.
    """
    if old_name == new_name:
        return
    if old_name in config_placements:
        config_placements[new_name] = config_placements.pop(old_name)
    if old_name in config_icons:
        config_icons[new_name] = config_icons.pop(old_name)
