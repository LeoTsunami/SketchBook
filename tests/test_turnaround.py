"""Tests for turnaround image groups."""

from pathlib import Path

import pytest
from PIL import Image

from core.image_db import ImageMetadata, metadata_from_dict
from core.turnaround import (
    TURNAROUND_KIND,
    TURNAROUND_TAG,
    create_turnaround,
    decompose_turnaround,
    get_pose_ids,
    middle_pose_index,
)
from gui.turnaround_scrub import scrub_index_from_drag


def _import_n(image_manager, tmp_path: Path, n: int) -> list:
    """Import n solid-color test images and return their metadata."""
    before = {m.id for m in image_manager.db.list_images()}
    for i in range(n):
        path = tmp_path / f"pose_{i}.jpg"
        Image.new("RGB", (80, 80), color=(i * 40 % 255, 20, 80)).save(path)
        assert image_manager.import_image(path) is not None
    metas = [m for m in image_manager.db.list_images() if m.id not in before]
    # Preserve import order by filename stem order used above
    metas.sort(key=lambda m: m.original_filename)
    assert len(metas) == n
    return metas


def test_middle_pose_index():
    """Middle index is the lower middle for even counts."""
    assert middle_pose_index(0) == 0
    assert middle_pose_index(1) == 0
    assert middle_pose_index(2) == 0
    assert middle_pose_index(3) == 1
    assert middle_pose_index(4) == 1
    assert middle_pose_index(5) == 2


def test_scrub_index_from_drag_loops():
    """Drag scrub wraps at sequence ends."""
    assert scrub_index_from_drag(0, 48 * 4, 0, 4) == 0
    assert scrub_index_from_drag(0, 48 * 5, 3, 4) == 0
    assert scrub_index_from_drag(100, 100 - 48, 0, 4) == 3


def test_create_turnaround_hides_members_and_tags_root(image_manager, tmp_path):
    """Creating a turnaround hides members and tags the root."""
    metas = _import_n(image_manager, tmp_path, 3)
    # Stamp a stable import date on the first member.
    first_date = "2024-01-15T12:00:00"
    image_manager.db.update_image(metas[0].id, import_date=first_date)
    metas[0] = image_manager.db.get_image(metas[0].id)

    member_ids = [m.id for m in metas]
    root = create_turnaround(image_manager, member_ids)

    assert root.kind == TURNAROUND_KIND
    assert root.member_ids == member_ids
    assert TURNAROUND_TAG in root.tags
    assert not root.hidden
    assert root.import_date == first_date
    assert root.path == metas[0].path

    for mid in member_ids:
        member = image_manager.db.get_image(mid)
        assert member is not None
        assert member.hidden is True
        assert member.group_id == root.id

    visible = image_manager.list_visible_images()
    visible_ids = {m.id for m in visible}
    assert root.id in visible_ids
    assert not (set(member_ids) & visible_ids)


def test_decompose_restores_members(image_manager, tmp_path):
    """Decompose restores members and removes the root row."""
    metas = _import_n(image_manager, tmp_path, 4)
    member_ids = [m.id for m in metas]
    root = create_turnaround(image_manager, member_ids)
    root_id = root.id

    restored = decompose_turnaround(image_manager, root_id)
    assert restored == member_ids
    assert image_manager.db.get_image(root_id) is None
    for mid in member_ids:
        member = image_manager.db.get_image(mid)
        assert member is not None
        assert member.hidden is False
        assert member.group_id == ""


def test_create_rejects_already_grouped(image_manager, tmp_path):
    """Cannot nest or re-group images already in a turnaround."""
    metas = _import_n(image_manager, tmp_path, 3)
    ids = [m.id for m in metas]
    create_turnaround(image_manager, ids[:2])
    with pytest.raises(ValueError):
        create_turnaround(image_manager, [ids[0], ids[2]])


def test_get_pose_ids_for_single():
    """Singles expose themselves as the only pose."""
    meta = ImageMetadata(
        id="a",
        path="a.jpg",
        original_filename="a.jpg",
        width=1,
        height=1,
        file_size=1,
        format="JPEG",
    )
    assert get_pose_ids(meta) == ["a"]


def test_metadata_from_dict_ignores_unknown_and_defaults():
    """Legacy JSON rows without turnaround fields still load."""
    raw = {
        "id": "legacy",
        "path": "legacy.jpg",
        "original_filename": "legacy.jpg",
        "width": 10,
        "height": 10,
        "file_size": 100,
        "format": "JPEG",
        "tags": ["Human"],
        "unknown_future_field": 123,
    }
    meta = metadata_from_dict(raw)
    assert meta.id == "legacy"
    assert meta.tags == {"Human"}
    assert meta.kind == "single"
    assert meta.member_ids == []
    assert meta.hidden is False


def test_delete_turnaround_decomposes(image_manager, tmp_path):
    """Deleting a turnaround root decomposes instead of deleting member files."""
    metas = _import_n(image_manager, tmp_path, 2)
    ids = [m.id for m in metas]
    root = create_turnaround(image_manager, ids)
    member_paths = [image_manager.image_dir / m.path for m in metas]
    assert image_manager.delete_image(root.id) is True
    assert image_manager.db.get_image(root.id) is None
    for mid, path in zip(ids, member_paths):
        assert image_manager.db.get_image(mid) is not None
        assert path.exists()
