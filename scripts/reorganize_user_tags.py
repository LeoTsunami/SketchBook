#!/usr/bin/env python3
"""
One-shot migration: reorganize user tag placements and clean image tags.

Run from repo root:
    python scripts/reorganize_user_tags.py
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any, Dict, Set

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config_backup import run_config_backup
from core.image_manager import ImageManager
from core import user_tags_config

# Merge duplicate tags on all images (old name -> canonical name).
TAG_MERGE: Dict[str, str] = {
    "Cats": "Cat",
    "Daggers": "Dagger",
    "Owls": "Owl",
    "Penguins": "Penguin",
    "Pistols": "Pistol",
    "Swords": "Sword",
    "Vultures": "Vulture",
    "Snakes": "Snake",
    "Reptiles": "Reptile",
    "Toads": "Toad",
    "Turtles": "Turtle",
    "crocodile": "Crocodile",
    "Wolves": "Wolf",
}

# Remove from every image (and from config placements).
TAGS_TO_DELETE: Set[str] = {
    "test",
    "Animal",
    "Human",
    "Landscape",
    "Objects",
}

# New or updated placements for previously orphan / misplaced tags.
NEW_PLACEMENTS: Dict[str, Dict[str, str]] = {
    # Intermediate group
    "Rodents": {"parent_tag": "Terrestrial"},
    # Terrestrial mammals
    "Moose": {"parent_tag": "Terrestrial"},
    "Okapi": {"parent_tag": "Terrestrial"},
    "Nyala": {"parent_tag": "Terrestrial"},
    "Manedwolves": {"parent_tag": "Terrestrial"},
    "Red kangaroo": {"parent_tag": "Terrestrial"},
    "Red necked wallabies": {"parent_tag": "Terrestrial"},
    "Yellow footed rock wallabies": {"parent_tag": "Terrestrial"},
    "Red wolves": {"parent_tag": "Terrestrial"},
    "Polar bears": {"parent_tag": "Terrestrial"},
    "Pygmy": {"parent_tag": "Terrestrial"},
    "Rocky mountain goats": {"parent_tag": "Terrestrial"},
    "Sichuan takin": {"parent_tag": "Terrestrial"},
    "Rhinoceros": {"parent_tag": "Terrestrial"},
    "Southern white rhinoceroses": {"parent_tag": "Terrestrial"},
    "Red foxes": {"parent_tag": "Terrestrial"},
    "Mustelids": {"parent_tag": "Rodents"},
    "Otters": {"parent_tag": "Rodents"},
    "Wolverines": {"parent_tag": "Rodents"},
    "beaver": {"parent_tag": "Rodents"},
    "Primates": {"parent_tag": "Monkey"},
    "Siamangs": {"parent_tag": "Monkey"},
    "White cheeked gibbons": {"parent_tag": "Monkey"},
    "Red ruffed lemurs": {"parent_tag": "Monkey"},
    "Ring tailed lemurs": {"parent_tag": "Monkey"},
    "Sand cats": {"parent_tag": "Felin"},
    "Small cats": {"parent_tag": "Felin"},
    "Snow leopards": {"parent_tag": "Felin"},
    "Sumatran tigers": {"parent_tag": "Felin"},
    # Birds
    "Rails": {"parent_tag": "Bird"},
    "Ratites": {"parent_tag": "Bird"},
    "Rhea": {"parent_tag": "Bird"},
    "Rhinoceros hornbill": {"parent_tag": "Bird"},
    # Fish / aquatic
    "Lamprey": {"parent_tag": "Fish"},
    "Red bellied piranha": {"parent_tag": "Fish"},
    "Rollands damselfish": {"parent_tag": "Fish"},
    "Sailfins": {"parent_tag": "Fish"},
    "Wolf eels": {"parent_tag": "Fish"},
    # Reptiles / amphibians
    "Perenties": {"parent_tag": "Reptile"},
    "Tomistoma": {"parent_tag": "Reptile"},
    "Timor pythons": {"parent_tag": "Snake"},
    "Yellow anaconda": {"parent_tag": "Snake"},
    "Zebra spitting cobras": {"parent_tag": "Snake"},
    "Prehensiletailed": {"parent_tag": "Reptile"},
    "Smoky jungle frog": {"parent_tag": "Frog"},
    "Red spotted toads": {"parent_tag": "Toad"},
    "Sulcata tortoises": {"parent_tag": "Turtle"},
    "Turtle": {"parent_tag": "Reptile"},
    # Actions / regions
    "Standing": {"category": "Actions:"},
    "Poses": {"category": "Actions:"},
    "Northern": {"category": "Regions:"},
    "Pacific": {"category": "Regions:"},
    # Periods (moved out of Miscellaneous)
    "Samurai": {"category": "Periods:"},
    "Eastern warrior": {"category": "Periods:"},
    "Military": {"category": "Periods:"},
    # Objects / weapons
    "Skull": {"category": "Objects"},
    "Rope": {"category": "Objects"},
    "Revolvers": {"parent_tag": "Weapon"},
    "Shotgun": {"parent_tag": "Weapon"},
    # Cross-cutting
    "Juveniles": {"category": "Miscellaneous:"},
    "Lighting": {"category": "Camera-Angle:"},
}


def _merge_placements(
    placements: Dict[str, Any], icons: Dict[str, str]
) -> None:
    """Merge duplicate tag keys in config and fix parent references."""
    for old, new in TAG_MERGE.items():
        if old in placements and new not in placements:
            placements[new] = placements.pop(old)
        elif old in placements:
            placements.pop(old, None)
        user_tags_config.rename_in_config(placements, icons, old, new)

    for placement in placements.values():
        parent = placement.get("parent_tag")
        if parent in TAG_MERGE:
            placement["parent_tag"] = TAG_MERGE[parent]

    if "Pallas" in placements:
        placements["Pallas"] = {"parent_tag": "Cat"}


def _apply_new_placements(placements: Dict[str, Any]) -> None:
    """Set placements for orphan / relocated tags."""
    for tag, placement in NEW_PLACEMENTS.items():
        placements[tag] = dict(placement)


def _prune_deleted(placements: Dict[str, Any], icons: Dict[str, str]) -> None:
    """Remove deleted tags from config."""
    for tag in TAGS_TO_DELETE | set(TAG_MERGE.keys()):
        placements.pop(tag, None)
        icons.pop(tag, None)


def reorganize(*, dry_run: bool = False) -> None:
    """
    Run tag library reorganization.

    Args:
        dry_run: When True, print actions without writing.
    """
    print("Running config backup...")
    if not dry_run:
        run_config_backup()

    im = ImageManager()
    cfg = user_tags_config.load_config()
    placements = copy.deepcopy(cfg.get("placements", {}))
    icons = copy.deepcopy(cfg.get("icons", {}))
    registered = list(cfg.get("registered_only", []))

    print("Merging duplicate tags on images...")
    merge_counts = {}
    for old, new in TAG_MERGE.items():
        if dry_run:
            merge_counts[old] = sum(1 for m in im.db.list_images() if old in m.tags)
        else:
            merge_counts[old] = im.db.rename_tag(old, new)

    print("Removing obsolete tags from images...")
    if dry_run:
        remove_count = sum(
            1 for m in im.db.list_images() if m.tags & TAGS_TO_DELETE
        )
    else:
        remove_count = im.db.remove_tags(TAGS_TO_DELETE)

    _merge_placements(placements, icons)
    _apply_new_placements(placements)
    _prune_deleted(placements, icons)

    registered = [TAG_MERGE.get(t, t) for t in registered if t not in TAGS_TO_DELETE]
    registered = sorted(set(registered))

    print("\n=== Summary ===")
    for old, count in sorted(merge_counts.items()):
        if count:
            print(f"  merged {old!r} -> {TAG_MERGE[old]!r}: {count} images")
    print(f"  images cleaned (category/test tags): {remove_count}")
    print(f"  placements after migration: {len(placements)}")

    unplaced_used = set()
    for meta in im.db.list_images():
        unplaced_used.update(meta.tags)
    default_path = ROOT / "gui" / "ressources" / "default_tags.json"
    import json

    defaults = json.loads(default_path.read_text(encoding="utf-8"))
    all_defaults = {
        t for cat, tags in defaults.items() if not cat.startswith("_") for t in tags
    }
    orphans = sorted(unplaced_used - set(placements.keys()) - all_defaults)
    print(f"  still unplaced on images: {len(orphans)}")
    if orphans:
        for tag in orphans[:20]:
            print(f"    - {tag}")
        if len(orphans) > 20:
            print(f"    ... +{len(orphans) - 20} more")

    if dry_run:
        print("\n(dry run — no files written)")
        return

    user_tags_config.save_config(placements, icons, registered)
    im.db.flush_pending_save()
    print("\nDone. Config and images updated.")


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    reorganize(dry_run=dry)
