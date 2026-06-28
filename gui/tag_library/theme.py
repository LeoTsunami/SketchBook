"""
Visual theme tokens for the tag library (dark-first).

Shared between the sliding panel overlay, the collapsed rail button, and chip
styles so the library feels cohesive with ``style_dark.qss``.
"""
from __future__ import annotations

from dataclasses import dataclass

from qtpy.QtGui import QColor

from core.settings import settings


@dataclass(frozen=True)
class ChipPalette:
    """Resolved colours for one chip style variant."""

    background: str
    background_hover: str
    border: str
    border_hover: str
    text: str


def tag_library_is_dark_theme() -> bool:
    """
    Return True when the app uses a dark colour scheme.

    Returns:
        bool: True for dark themes.
    """
    return settings.get("ui.theme", "dark") != "light"


@dataclass(frozen=True)
class _CategoryAccent:
    """Fixed hue/sat/light anchors for a main library category."""

    hue: int
    sat_pct: int
    light_pct: int


# Harmonised jewel-tone family for the four main categories (warm dark UI).
_CATEGORY_ACCENTS: dict[str, _CategoryAccent] = {
    "human": _CategoryAccent(258, 54, 48),      # soft periwinkle-lilac
    "animal": _CategoryAccent(158, 50, 44),     # sage green
    "landscape": _CategoryAccent(176, 52, 44),  # seafoam teal
    "objects": _CategoryAccent(318, 48, 45),    # dusty orchid (not fire-red)
}


def _normalise_branch_key(branch_key: str) -> str:
    """
    Normalise a category / branch name for palette lookup.

    Args:
        branch_key: Raw category label.

    Returns:
        str: Lowercase key without spaces or punctuation.
    """
    return branch_key.lower().replace(" ", "").replace("-", "").replace("_", "")


def get_hierarchy_background_color(branch_key: str, depth: int) -> QColor:
    """
    Return a vivid depth-based colour for a tag chip.

    Args:
        branch_key: Category name used to derive a base hue.
        depth: 0 = category, 1 = subtag, 2+ = nested subtag.

    Returns:
        QColor in HSL space.
    """
    norm = _normalise_branch_key(branch_key)
    accent = _CATEGORY_ACCENTS.get(norm)
    dark_theme = tag_library_is_dark_theme()
    if accent is not None:
        hue = accent.hue
        if dark_theme:
            sat_pct = min(accent.sat_pct + depth * 3, 72)
            light_pct = min(accent.light_pct + depth * 5, 58)
        else:
            sat_pct = min(accent.sat_pct + depth * 4, 76)
            light_pct = max(accent.light_pct + 28 - depth * 6, 42)
    else:
        hue = sum(ord(c) for c in branch_key) % 360
        if dark_theme:
            sat_pct = min(52 + depth * 4, 78)
            light_pct = min(32 + depth * 6, 56)
        else:
            sat_pct = min(48 + depth * 5, 78)
            light_pct = max(78 - depth * 7, 40)
    return QColor.fromHsl(
        hue,
        int(255 * sat_pct / 100),
        int(255 * light_pct / 100),
    )


def blend_color(base: QColor, tint: QColor, ratio: float) -> QColor:
    """
    Mix base colour toward tint by ratio.

    Args:
        base: Source colour.
        tint: Target tint.
        ratio: 0.0 = pure base, 1.0 = pure tint.

    Returns:
        QColor blended result.
    """
    r = int(base.red() + (tint.red() - base.red()) * ratio)
    g = int(base.green() + (tint.green() - base.green()) * ratio)
    b = int(base.blue() + (tint.blue() - base.blue()) * ratio)
    return QColor(max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)), base.alpha())


def tag_library_panel_gradient_qss() -> str:
    """
    Return the QSS background gradient for the tag library shell.

    Tuned to sit on top of the main window gradient
    (``#171220`` → ``#3c2442`` in ``style_dark.qss``).

    Returns:
        str: ``qlineargradient(...)`` value.
    """
    return (
        "qlineargradient("
        "x1:0, y1:0, x2:0, y2:1, "
        "stop:0 rgba(40, 28, 44, 248), "
        "stop:0.45 rgba(32, 21, 36, 252), "
        "stop:1 rgba(26, 16, 28, 254)"
        ")"
    )


def tag_library_panel_border_qss() -> str:
    """
    Return a subtle edge highlight for the tag library panel.

    Returns:
        str: CSS border declaration.
    """
    return "1px solid rgba(255, 255, 255, 0.07)"


def tag_library_overlay_stylesheet() -> str:
    """
    Build the full QSS for ``TagPanelOverlay``.

    Returns:
        str: QWidget stylesheet.
    """
    grad = tag_library_panel_gradient_qss()
    border = tag_library_panel_border_qss()
    return f"""
        QFrame#TagPanelOverlay {{
            background: {grad};
            border-top-right-radius: 14px;
            border-bottom-right-radius: 14px;
            border: {border};
        }}
    """


def tag_library_floating_button_stylesheet() -> str:
    """
    Build QSS for the collapsed ``Tags filters`` rail button.

    Uses the same gradient family as the expanded panel.

    Returns:
        str: QPushButton stylesheet.
    """
    grad = tag_library_panel_gradient_qss()
    border = tag_library_panel_border_qss()
    return f"""
        QPushButton#TagFiltersFloatingButton {{
            background: {grad};
            color: #e8e4f2;
            font-size: 11px;
            font-weight: 600;
            padding: 10px 4px;
            border: {border};
            border-left: none;
            border-top-right-radius: 8px;
            border-bottom-right-radius: 8px;
            text-align: center;
        }}
        QPushButton#TagFiltersFloatingButton:hover {{
            color: #ffffff;
            border: 1px solid rgba(255, 255, 255, 0.14);
            border-left: none;
        }}
        QPushButton#TagFiltersFloatingButton:pressed {{
            color: #d8d2e8;
        }}
    """


def tag_library_scroll_stylesheet() -> str:
    """
    Transparent scroll chrome so the panel gradient shows through.

    Returns:
        str: QScrollArea / viewport stylesheet.
    """
    return """
        QScrollArea#TagLibraryScrollArea {
            background: transparent;
            border: none;
        }
        QWidget#TagLibraryScrollViewport {
            background: transparent;
        }
        QWidget#TagLibraryScrollContent {
            background: transparent;
        }
    """


def _rgba(color: QColor, alpha: int) -> str:
    """
    Format a QColor as an ``rgba(...)`` CSS string.

    Args:
        color: Source colour.
        alpha: Alpha 0–255.

    Returns:
        str: CSS colour.
    """
    return f"rgba({color.red()}, {color.green()}, {color.blue()}, {alpha})"


def chip_palette(branch_key: str, depth: int, *, is_category: bool = False) -> ChipPalette:
    """
    Build mature outline-style colours for a tag chip.

    Inspired by modern chip/tag references: dark translucent fill, coloured
  border, and brighter label text.

    Args:
        branch_key: Category / branch name (drives hue).
        depth: Visual nesting depth (0 = main category row).
        is_category: True for full-width category headers.

    Returns:
        ChipPalette: CSS-ready colour strings.
    """
    dark = tag_library_is_dark_theme()
    hue = get_hierarchy_background_color(branch_key, depth)
    accent = hue.lighter(150 if is_category and dark else 155 if dark else 125)
    border_base = hue.lighter(128 if is_category and dark else 135 if dark else 115)
    text_lift = 142 if is_category and dark else 132 if dark else 98
    text = accent.lighter(text_lift).name()

    fill_alpha = 128 if is_category else max(78, 92 - depth * 8)
    hover_alpha = fill_alpha + 26
    fill_base = QColor(22, 18, 28) if is_category else QColor(18, 16, 26)
    fill = blend_color(fill_base, hue, 0.40 if is_category else 0.32)
    fill_hover = blend_color(fill_base.lighter(108), hue, 0.46 if is_category else 0.38)

    if is_category and dark:
        background = (
            f"qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {_rgba(fill, fill_alpha + 12)},"
            f"stop:1 {_rgba(fill, fill_alpha)})"
        )
        background_hover = (
            f"qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {_rgba(fill_hover, hover_alpha + 14)},"
            f"stop:1 {_rgba(fill_hover, hover_alpha)})"
        )
    else:
        background = _rgba(fill, fill_alpha)
        background_hover = _rgba(fill_hover, hover_alpha)

    border_w = "1.5px" if is_category else "1px"
    return ChipPalette(
        background=background,
        background_hover=background_hover,
        border=f"{border_w} solid {_rgba(border_base, 200 if dark else 180)}",
        border_hover=f"{border_w} solid {_rgba(accent, 230 if dark else 200)}",
        text=text,
    )


def chip_state_palette(
    branch_key: str, depth: int, *, selected: bool, active: bool
) -> ChipPalette | None:
    """
    Optional override palette for selected / active chip states.

    Args:
        branch_key: Category / branch name.
        depth: Nesting depth.
        selected: Multi-drag selection.
        active: Filter is ON.

    Returns:
        ChipPalette | None: Override colours, or None to use the base palette.
    """
    dark = tag_library_is_dark_theme()
    hue = get_hierarchy_background_color(branch_key, depth)
    if selected:
        tint = QColor(90, 155, 255)
        fill = blend_color(QColor(20, 28, 48), tint, 0.45)
        accent = tint.lighter(120)
        return ChipPalette(
            background=_rgba(fill, 118 if dark else 140),
            background_hover=_rgba(fill.lighter(108), 135 if dark else 155),
            border=f"1.5px solid {_rgba(accent, 220)}",
            border_hover=f"1.5px solid {_rgba(accent.lighter(110), 240)}",
            text="#eef4ff" if dark else "#15325f",
        )
    if active:
        tint = QColor(72, 196, 118)
        fill = blend_color(QColor(18, 36, 28), tint, 0.4)
        accent = tint.lighter(115)
        return ChipPalette(
            background=_rgba(fill, 120 if dark else 145),
            background_hover=_rgba(fill.lighter(108), 138 if dark else 160),
            border=f"1.5px solid {_rgba(accent, 220)}",
            border_hover=f"1.5px solid {_rgba(accent.lighter(110), 240)}",
            text="#eafff0" if dark else "#14532d",
        )
    return None
