"""
Turnaround image groups: multi-pose entries treated as a single grid/session image.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional, Sequence

from core.image_db import ImageMetadata

if TYPE_CHECKING:
    from core.image_manager import ImageManager

TURNAROUND_TAG = "Turnaround"
TURNAROUND_KIND = "turnaround"
SINGLE_KIND = "single"


def middle_pose_index(count: int) -> int:
    """
    Return the default pose index (middle frame) for a turnaround.

    Args:
        count: Number of poses.

    Returns:
        int: Clamped middle index (0 when empty).
    """
    if count <= 0:
        return 0
    return (count - 1) // 2


def get_pose_ids(meta: ImageMetadata) -> List[str]:
    """
    Resolve ordered pose image IDs for a metadata row.

    Args:
        meta: Image metadata (turnaround root or single).

    Returns:
        List of pose IDs; for singles, a one-element list with ``meta.id``.
    """
    if meta.kind == TURNAROUND_KIND and meta.member_ids:
        return list(meta.member_ids)
    return [meta.id]


def create_turnaround(
    image_manager: "ImageManager", member_ids: Sequence[str]
) -> ImageMetadata:
    """
    Group selected images into a single turnaround root; hide members.

    Args:
        image_manager: Image manager owning the database.
        member_ids: Ordered pose IDs (selection order). Must have at least 2.

    Returns:
        ImageMetadata: The new turnaround root.

    Raises:
        ValueError: If fewer than two valid members, or a member is already grouped.
    """
    if len(member_ids) < 2:
        raise ValueError("A turnaround requires at least two images.")

    db = image_manager.db
    members: List[ImageMetadata] = []
    for mid in member_ids:
        meta = db.get_image(mid)
        if meta is None:
            raise ValueError(f"Image not found: {mid}")
        if meta.hidden or meta.group_id or meta.kind == TURNAROUND_KIND:
            raise ValueError(f"Image already in a turnaround: {mid}")
        members.append(meta)

    ordered_ids = [m.id for m in members]
    first = members[0]
    root_id = f"turnaround_{uuid.uuid4().hex[:12]}"

    # Union tags from all members, plus Turnaround.
    union_tags = set()
    for m in members:
        union_tags |= set(m.tags)
    union_tags.add(TURNAROUND_TAG)

    root = ImageMetadata(
        id=root_id,
        path=first.path,
        original_filename=f"Turnaround ({len(ordered_ids)} poses)",
        width=first.width,
        height=first.height,
        file_size=first.file_size,
        format=first.format,
        original_path=first.original_path,
        tags=union_tags,
        import_date=first.import_date or datetime.now().isoformat(),
        kind=TURNAROUND_KIND,
        member_ids=ordered_ids,
        group_id="",
        hidden=False,
    )
    if not db.add_image(root):
        raise ValueError(f"Failed to add turnaround root: {root_id}")

    for m in members:
        db.update_image(m.id, group_id=root_id, hidden=True)

    return root


def decompose_turnaround(
    image_manager: "ImageManager", root_id: str
) -> List[str]:
    """
    Restore turnaround members to the grid and remove the root entry.

    Args:
        image_manager: Image manager owning the database.
        root_id: Turnaround root id.

    Returns:
        List[str]: Restored member ids (selection order).

    Raises:
        ValueError: If root is missing or not a turnaround.
    """
    db = image_manager.db
    root = db.get_image(root_id)
    if root is None:
        raise ValueError(f"Turnaround not found: {root_id}")
    if root.kind != TURNAROUND_KIND:
        raise ValueError(f"Image is not a turnaround: {root_id}")

    member_ids = list(root.member_ids)
    for mid in member_ids:
        member = db.get_image(mid)
        if member is None:
            continue
        db.update_image(mid, group_id="", hidden=False)

    # Root reuses a member path — do not delete the file, only metadata.
    db.delete_image(root_id)
    return member_ids


def sync_turnaround_root_dimensions(
    image_manager: "ImageManager", root_id: str
) -> None:
    """
    Refresh turnaround root dimensions from its first pose after batch edits.

    Args:
        image_manager: Image manager owning the database.
        root_id: Turnaround root id.
    """
    db = image_manager.db
    root = db.get_image(root_id)
    if root is None or root.kind != TURNAROUND_KIND or not root.member_ids:
        return
    first = db.get_image(root.member_ids[0])
    if first is None:
        return
    db.update_image(
        root_id,
        width=first.width,
        height=first.height,
        file_size=first.file_size,
    )


def batch_edit_image_ids(
    image_manager: "ImageManager", image_id: str
) -> List[str]:
    """
    Resolve image IDs that should receive the same crop/rotate edit.

    Args:
        image_manager: Image manager owning the database.
        image_id: Turnaround root, hidden member, or single image id.

    Returns:
        Member ids for a turnaround group, otherwise a one-element list.
    """
    db = image_manager.db
    meta = db.get_image(image_id)
    if meta is None:
        return []
    if meta.kind == TURNAROUND_KIND and meta.member_ids:
        return list(meta.member_ids)
    if meta.group_id:
        root = db.get_image(meta.group_id)
        if root is not None and root.kind == TURNAROUND_KIND and root.member_ids:
            return list(root.member_ids)
    return [image_id]


def turnaround_root_id_for_edit(
    image_manager: "ImageManager", image_id: str
) -> Optional[str]:
    """
    Return the turnaround root id when ``image_id`` belongs to a group.

    Args:
        image_manager: Image manager owning the database.
        image_id: Image id being edited.

    Returns:
        Root id, or None for singles.
    """
    db = image_manager.db
    meta = db.get_image(image_id)
    if meta is None:
        return None
    if meta.kind == TURNAROUND_KIND:
        return meta.id
    if meta.group_id:
        root = db.get_image(meta.group_id)
        if root is not None and root.kind == TURNAROUND_KIND:
            return root.id
    return None


def resolve_pose_path(
    image_manager: "ImageManager", root: ImageMetadata, pose_index: int
) -> Optional[str]:
    """
    Resolve the on-disk relative path for a pose index on a turnaround.

    Args:
        image_manager: Image manager.
        root: Turnaround (or single) metadata.
        pose_index: Pose index into ``get_pose_ids``.

    Returns:
        Relative path string, or None if unresolved.
    """
    pose_ids = get_pose_ids(root)
    if not pose_ids:
        return None
    idx = max(0, min(len(pose_ids) - 1, pose_index))
    pose_id = pose_ids[idx]
    if pose_id == root.id:
        return root.path
    member = image_manager.db.get_image(pose_id)
    if member is None:
        return root.path
    return member.path
