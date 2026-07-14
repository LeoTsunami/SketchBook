"""Tests for TagGridHost layout with nested user tags."""

from gui.tag_library.grid_host import TagGridHost
from gui.tag_library.state import TagLibraryTaxonomy


def test_compute_layout_lines_expands_active_parent() -> None:
    """Active parent tags reserve a frame row for their children."""
    taxonomy = TagLibraryTaxonomy(
        categories_order=["Miscellaneous:"],
        subtag_order={
            "Miscellaneous:": ["Climbing", "Sitting"],
        },
        placements={"Sitting": {"parent_tag": "Climbing"}},
        subtag_to_category={
            "Climbing": "Miscellaneous:",
            "Sitting": "Miscellaneous:",
        },
        children_map={"Climbing": ["Sitting"]},
    )
    lines = TagGridHost._compute_layout_lines(
        ["Climbing"], taxonomy, {"Climbing"}
    )
    assert ("row", [(0, "Climbing")]) in lines
    assert ("frame", "Climbing") in lines

    collapsed = TagGridHost._compute_layout_lines(
        ["Climbing"], taxonomy, set()
    )
    assert ("frame", "Climbing") not in collapsed
