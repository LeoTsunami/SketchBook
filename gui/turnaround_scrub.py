"""
Shared helpers for turnaround pose scrubbing (viewer + session).
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from qtpy.QtGui import QPixmap

from core.image_manager import ImageManager
from core.turnaround import (
    TURNAROUND_KIND,
    get_pose_ids,
    resolve_pose_path,
)
from core.image_db import ImageMetadata


def turnaround_pose_setup(
    image_manager: ImageManager, image_id: str
) -> Tuple[List[str], int]:
    """
    Resolve pose IDs and default pose index for an image.

    Args:
        image_manager: Image manager.
        image_id: Current image id (root or single).

    Returns:
        (pose_ids, default_index). Default is the first pose (index 0).
    """
    meta = image_manager.get_image_metadata(image_id)
    if meta is None:
        return ([image_id], 0)
    poses = get_pose_ids(meta)
    return (poses, 0)


def is_turnaround_meta(meta: Optional[ImageMetadata]) -> bool:
    """
    Return True if metadata is a turnaround root with multiple poses.

    Args:
        meta: Image metadata or None.

    Returns:
        bool: Whether scrubbing applies.
    """
    return (
        meta is not None
        and meta.kind == TURNAROUND_KIND
        and len(meta.member_ids) >= 2
    )


def pose_index_from_x(x: float, width: float, pose_count: int) -> int:
    """
    Map a horizontal position to a pose index.

    Args:
        x: Pointer X in the scrub area (0 .. width).
        width: Scrub area width.
        pose_count: Number of poses.

    Returns:
        int: Clamped pose index.
    """
    if pose_count <= 1 or width <= 0:
        return 0
    ratio = max(0.0, min(1.0, x / width))
    idx = int(ratio * pose_count)
    return max(0, min(pose_count - 1, idx))


def load_pose_pixmap(
    image_manager: ImageManager, root: ImageMetadata, pose_index: int
) -> Optional[QPixmap]:
    """
    Load a full-resolution pixmap for a turnaround pose.

    Args:
        image_manager: Image manager.
        root: Turnaround (or single) metadata.
        pose_index: Pose index.

    Returns:
        QPixmap or None.
    """
    rel = resolve_pose_path(image_manager, root, pose_index)
    if not rel:
        return None
    path = image_manager.image_dir / rel
    if not path.exists():
        return None
    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        return None
    return pixmap


def scrub_index_from_drag(
    start_x: float,
    current_x: float,
    start_index: int,
    pose_count: int,
    pixels_per_pose: float = 48.0,
) -> int:
    """
    Compute pose index from horizontal drag delta (click-drag scrub).

    Args:
        start_x: Drag start X.
        current_x: Current pointer X.
        start_index: Pose index at drag start.
        pose_count: Number of poses.
        pixels_per_pose: Horizontal pixels to move one pose.

    Returns:
        int: New pose index.
    """
    if pose_count <= 1:
        return 0
    delta = current_x - start_x
    steps = int(round(delta / max(1.0, pixels_per_pose)))
    return (start_index + steps) % pose_count
