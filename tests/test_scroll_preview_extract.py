"""Tests for scroll-preview extract preload ordering."""

from gui.image_grid import ImageGrid


def test_balanced_extract_order_starts_with_top_middle_bottom():
    """First loads should cover the strip extremes and center."""
    order = ImageGrid._build_balanced_extract_order(9)
    assert order[0] == 0
    assert order[1] == 8
    assert order[2] == 4


def test_balanced_extract_order_covers_all_indices():
    """Balanced order should eventually include every extract slot."""
    order = ImageGrid._build_balanced_extract_order(12)
    assert len(order) == 12
    assert set(order) == set(range(12))


def test_scroll_preview_target_uses_nearest_extract_to_viewport_top():
    """Preview should track the top visible row, not a global scroll ratio."""
    grid = ImageGrid.__new__(ImageGrid)
    grid.all_images = [None] * 100
    grid.columns = 4
    grid._extract_indices = [0, 16, 32, 48, 64, 80, 96]
    grid._viewport_top_image_index = lambda: 20
    assert grid._scroll_preview_target_extract_index() == 1

