"""Tests for the SketchBook application icon."""

import importlib.util
from pathlib import Path

from PIL import Image

from gui.icon_utils import app_icon_ico_path, app_logo_path, load_app_icon

ROOT = Path(__file__).resolve().parents[1]


def _load_builder():
    """Load ``scripts/build_app_icon.py`` without requiring a package."""
    spec = importlib.util.spec_from_file_location(
        "build_app_icon", ROOT / "scripts" / "build_app_icon.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_app_logo_png_exists() -> None:
    """The brand logo PNG used in chrome and packaging is present."""
    path = app_logo_path()
    assert path.is_file()
    assert path.name == "SketchBook_logo_B.png"


def test_compose_icon_tile_is_square() -> None:
    """Windows ICO tiles are square with the logo composited on a dark plate."""
    logo = Image.new("RGBA", (80, 40), (255, 255, 255, 255))
    tile = _load_builder().compose_icon_tile(logo, 32)
    assert tile.size == (32, 32)
    assert tile.mode == "RGBA"


def test_load_app_icon_not_null(qtbot) -> None:
    """Qt can load the application icon (ICO and/or PNG)."""
    _ = qtbot
    icon = load_app_icon()
    assert not icon.isNull()


def test_generated_ico_path_matches_helper() -> None:
    """The committed ICO path matches the helper used by PyInstaller and Inno."""
    assert app_icon_ico_path() == (
        Path(__file__).resolve().parents[1]
        / "gui"
        / "ressources"
        / "icones"
        / "SketchBook.ico"
    )


def test_ico_embeds_multiple_sizes() -> None:
    """The Windows icon includes small and large tiles."""
    ico_path = app_icon_ico_path()
    assert ico_path.is_file()
    with Image.open(ico_path) as image:
        sizes = set(image.info.get("sizes") or ())
        if not sizes and getattr(image, "ico", None) is not None:
            sizes = set(image.ico.sizes())
    assert (16, 16) in sizes
    assert (256, 256) in sizes
