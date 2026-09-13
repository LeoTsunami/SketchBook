#!/usr/bin/env python3
"""
Build ``gui/ressources/icones/SketchBook.ico`` from ``SketchBook_logo_B.png``.

The source logo is white-on-transparent. Windows shortcuts sit on light
Explorer backgrounds, so each ICO size is composited on a dark square
(Windows 11 then rounds the tile).
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PNG = ROOT / "gui" / "ressources" / "icones" / "SketchBook_logo_B.png"
DEST_ICO = ROOT / "gui" / "ressources" / "icones" / "SketchBook.ico"
ICON_SIZES: tuple[int, ...] = (16, 24, 32, 48, 64, 128, 256)
BACKGROUND_RGBA = (18, 22, 30, 255)
LOGO_INSET_RATIO = 0.10


def compose_icon_tile(
    logo: Image.Image,
    size: int,
    *,
    background: Sequence[int] = BACKGROUND_RGBA,
    inset_ratio: float = LOGO_INSET_RATIO,
) -> Image.Image:
    """
    Draw the logo centered on a dark square canvas.

    Args:
        logo: Source logo (RGBA).
        size: Output edge length in pixels.
        background: RGBA fill for the tile.
        inset_ratio: Padding around the logo as a fraction of ``size``.

    Returns:
        Image.Image: Square RGBA tile.
    """
    tile = Image.new("RGBA", (size, size), tuple(background))
    inset = max(1, int(round(size * inset_ratio)))
    inner = max(1, size - (2 * inset))
    fitted = logo.copy()
    fitted.thumbnail((inner, inner), Image.Resampling.LANCZOS)
    x = (size - fitted.width) // 2
    y = (size - fitted.height) // 2
    tile.paste(fitted, (x, y), fitted)
    return tile


def build_ico(
    source: Path = SOURCE_PNG,
    dest: Path = DEST_ICO,
    sizes: Iterable[int] = ICON_SIZES,
) -> Path:
    """
    Write a multi-size Windows icon file.

    Args:
        source: Brand logo PNG.
        dest: Output ``.ico`` path.
        sizes: Pixel sizes to embed.

    Returns:
        Path: Written ``.ico`` path.

    Raises:
        FileNotFoundError: Source PNG is missing.
    """
    if not source.is_file():
        raise FileNotFoundError(f"Missing logo: {source}")
    logo = Image.open(source).convert("RGBA")
    size_list = list(sizes)
    master = compose_icon_tile(logo, max(size_list))
    dest.parent.mkdir(parents=True, exist_ok=True)
    master.save(
        dest,
        format="ICO",
        sizes=[(size, size) for size in size_list],
    )
    return dest


def main() -> int:
    """
    CLI entry: generate ``SketchBook.ico`` next to the source PNG.

    Returns:
        int: Process exit code.
    """
    path = build_ico()
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
