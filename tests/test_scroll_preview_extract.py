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


def test_vicinity_load_order_prefers_viewport_then_neighbors():
    """Viewport core load order should fill visible rows before buffer rows."""
    grid = ImageGrid.__new__(ImageGrid)
    grid.all_images = [type("M", (), {"id": f"img_{i}"})() for i in range(40)]
    grid.columns = 4
    grid.loading_images = set()
    grid.pixmap_cache = {}
    grid._viewport_row_range = lambda extra: (2, 3) if extra == 0 else (0, 5)
    order = grid._vicinity_load_order(0, 24, buffer_rows=2)
    assert order[:8] == [f"img_{i}" for i in range(8, 16)]
    assert "img_4" in order
    assert "img_23" in order


def test_grid_extended_load_order_skips_viewport_core_band():
    """Phase 3 should only cover rows outside the core buffer."""
    grid = ImageGrid.__new__(ImageGrid)
    grid.all_images = [type("M", (), {"id": f"img_{i}"})() for i in range(40)]
    grid.columns = 4
    grid.loading_images = set()
    grid.pixmap_cache = {}
    grid.VIEWPORT_BUFFER_ROWS = 1
    grid.GRID_EXTENDED_ROWS = 2
    grid._viewport_row_range = lambda extra: (2, 3)
    grid._viewport_image_index_range = lambda extra: (0, 24)
    order = grid._grid_extended_load_order()
    assert "img_8" not in order
    assert "img_12" not in order
    assert "img_0" in order
    assert "img_20" in order


def test_idle_extra_load_order_skips_viewport_core_band():
    """Alias for extended grid band."""
    test_grid_extended_load_order_skips_viewport_core_band()


def test_viewport_has_unloaded_images_when_pixmap_missing():
    """Preview trigger should detect missing viewport pixmaps."""
    grid = ImageGrid.__new__(ImageGrid)
    grid.all_images = [type("M", (), {"id": f"img_{i}"})() for i in range(8)]
    grid.columns = 4
    grid.loading_images = set()
    grid._load_failed_images = set()
    grid.pixmap_cache = {"img_0": object()}
    grid._viewport_image_index_range = lambda extra: (0, 4)
    grid._is_virtualized = lambda: False
    thumb_loaded = type(
        "T", (), {"pixmap_item": object(), "isVisible": lambda self: True}
    )()
    thumb_missing = type(
        "T", (), {"pixmap_item": None, "isVisible": lambda self: True}
    )()
    grid.thumbnails = {"img_0": thumb_loaded, "img_1": thumb_missing}
    assert grid._viewport_has_unloaded_images() is True


def test_viewport_unloaded_detects_missing_cache_before_widgets_exist():
    """Virtualized scroll should flag unloaded indices even before pool reassignment."""
    grid = ImageGrid.__new__(ImageGrid)
    grid.all_images = [type("M", (), {"id": f"img_{i}"})() for i in range(20)]
    grid.columns = 4
    grid.loading_images = set()
    grid._load_failed_images = set()
    grid.pixmap_cache = {}
    grid.thumbnails = {}
    grid._viewport_image_index_range = lambda extra: (8, 16)
    grid._is_virtualized = lambda: True
    assert grid._viewport_has_unloaded_images() is True


def test_viewport_ready_when_all_cells_have_pixmaps():
    """Preview should close once every viewport cell displays a pixmap."""
    grid = ImageGrid.__new__(ImageGrid)
    grid.all_images = [type("M", (), {"id": f"img_{i}"})() for i in range(4)]
    grid.columns = 4
    grid.loading_images = set()
    grid._load_failed_images = set()
    grid.pixmap_cache = {f"img_{i}": object() for i in range(4)}
    grid._viewport_image_index_range = lambda extra: (0, 4)
    grid._is_virtualized = lambda: False
    grid.thumbnails = {
        f"img_{i}": type(
            "T", (), {"pixmap_item": object(), "isVisible": lambda self: True}
        )()
        for i in range(4)
    }
    assert grid._viewport_has_unloaded_images() is False


def test_extract_vicinity_order_targets_scroll_then_neighbors():
    """Vicinity preload should expand outward from the scroll target."""
    order = ImageGrid._build_extract_vicinity_order(5, 20, radius=3)
    assert order == [5, 6, 4, 7, 3, 8, 2]


def test_post_scroll_load_phase_order():
    """Phases should follow viewport core → extract vicinity → grid extended."""
    grid = ImageGrid.__new__(ImageGrid)
    grid.VIEWPORT_BUFFER_ROWS = 3
    grid.GRID_EXTENDED_ROWS = 5
    grid.EXTRACT_VICINITY_COUNT = 30
    grid.all_images = [type("M", (), {"id": f"img_{i}"})() for i in range(40)]
    grid.columns = 4
    grid.loading_images = set()
    grid._load_failed_images = set()
    grid.pixmap_cache = {"img_0": object()}
    grid.thumbnails = {
        "img_0": type("T", (), {"pixmap_item": object()})(),
    }
    grid._extract_indices = list(range(0, 40, 4))
    grid._extract_pixmaps = {}
    grid._extract_loading = set()
    grid._extract_vicinity_pending = [0]
    grid._extract_vicinity_slot_set = {0}
    grid._extract_balanced_pending = [1, 2]
    grid._tier0_queue = __import__("collections").deque()
    grid._tier3_queue = __import__("collections").deque()
    grid._is_virtualized = lambda: False
    grid._viewport_core_load_order = lambda: ["img_0"]
    grid._grid_extended_load_order = lambda: ["img_4"]
    assert grid._current_post_scroll_load_phase() == grid.PHASE_EXTRACT_VICINITY
    grid._extract_vicinity_pending.clear()
    grid._extract_vicinity_slot_set.clear()
    grid._extract_pixmaps[0] = object()
    assert grid._current_post_scroll_load_phase() == grid.PHASE_GRID_EXTENDED
    grid._tier3_queue.append("img_4")
    grid._tier3_queue.clear()
    grid.pixmap_cache["img_4"] = object()
    grid.thumbnails["img_4"] = type("T", (), {"pixmap_item": object()})()
    assert grid._current_post_scroll_load_phase() == grid.PHASE_EXTRACT_BALANCED


def test_balanced_extract_excludes_vicinity_slots():
    """Phase 4 should use dyadic order without phase-2 slots."""
    grid = ImageGrid.__new__(ImageGrid)
    grid._extract_indices = list(range(0, 48, 4))
    grid._extract_pixmaps = {0: object()}
    grid._extract_vicinity_slot_set = {1, 2, 3}
    grid._extract_vicinity_pending = []
    grid._build_balanced_extract_order = ImageGrid._build_balanced_extract_order
    grid._rebuild_extract_balanced_pending()
    assert 0 not in grid._extract_balanced_pending
    assert 1 not in grid._extract_balanced_pending
    assert grid._extract_balanced_pending[0] == 11

