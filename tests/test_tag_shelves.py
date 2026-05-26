"""Tests for tag library shelf helpers."""

from pathlib import Path

from gui.tag_shelves import (
    MISCELLANEOUS_SHELF,
    is_tag_shelf,
    load_default_tags_taxonomy,
    merge_custom_shelves,
    normalize_shelf_name,
    parse_category_tags,
    shelf_categories_with_filter,
    shelf_default_filter_mode,
)


def test_is_tag_shelf() -> None:
    assert is_tag_shelf("Camera-Angle:")
    assert not is_tag_shelf("Human")


def test_parse_category_tags_list_and_object() -> None:
    assert parse_category_tags(["A", "B"]) == (["A", "B"], None)
    tags, mode = parse_category_tags({"filter": "or", "tags": ["X"]})
    assert tags == ["X"]
    assert mode == "or"


def test_load_default_tags_taxonomy_skips_metadata() -> None:
    path = Path(__file__).resolve().parents[1] / "gui" / "ressources" / "default_tags.json"
    categories, modes = load_default_tags_taxonomy(path)
    assert "_shelf_filters" not in categories
    assert "Human" in categories
    assert modes[MISCELLANEOUS_SHELF] == "and"
    assert modes["Camera-Angle:"] == "or"


def test_new_shelf_in_json_gets_or_filter_by_default(tmp_path: Path) -> None:
    path = tmp_path / "tags.json"
    path.write_text(
        '{"Lighting:": ["Studio", "Natural"], "Miscellaneous:": []}',
        encoding="utf-8",
    )
    categories, modes = load_default_tags_taxonomy(path)
    assert "Lighting:" in categories
    assert modes["Lighting:"] == "or"
    assert shelf_default_filter_mode("Lighting:") == "or"


def test_normalize_shelf_name_appends_colon() -> None:
    assert normalize_shelf_name("Lighting") == "Lighting:"
    assert normalize_shelf_name("Camera-Angle:") == "Camera-Angle:"


def test_merge_custom_shelves_before_miscellaneous() -> None:
    categories = {"Human": [], MISCELLANEOUS_SHELF: []}
    modes: dict = {}
    merged = merge_custom_shelves(
        categories,
        modes,
        [{"name": "Lighting", "filter": "or", "tags": ["Studio"]}],
    )
    keys = list(merged.keys())
    assert keys.index("Lighting:") < keys.index(MISCELLANEOUS_SHELF)
    assert merged["Lighting:"] == ["Studio"]
    assert modes["Lighting:"] == "or"


def test_shelf_categories_with_filter() -> None:
    modes = {MISCELLANEOUS_SHELF: "and", "Camera-Angle:": "or", "Lighting:": "or"}
    assert shelf_categories_with_filter(modes, "and") == [MISCELLANEOUS_SHELF]
    assert "Camera-Angle:" in shelf_categories_with_filter(modes, "or")
