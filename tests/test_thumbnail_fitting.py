"""
Tests for gui.thumbnail_fitting – the unified image→cell fitting logic.
"""

import pytest
from gui.thumbnail_fitting import FitMode, compute_fitted_size


# ---------------------------------------------------------------------------
# FitMode enum basics
# ---------------------------------------------------------------------------

class TestFitModeEnum:
    """Sanity checks on the FitMode enum."""

    def test_values(self):
        assert FitMode.FIT_ALL == 0
        assert FitMode.FIT_HEIGHT == 1
        assert FitMode.FIT_WIDTH == 2
        assert FitMode.CROP_ALL == 3

    def test_labels_length_matches_members(self):
        assert len(FitMode.labels()) == len(FitMode)

    def test_labels_are_strings(self):
        for label in FitMode.labels():
            assert isinstance(label, str) and len(label) > 0


# ---------------------------------------------------------------------------
# FIT_ALL mode (default) — image always fits entirely, never exceeds cell
# ---------------------------------------------------------------------------

class TestComputeFittedSizeFitAll:
    """Tests for compute_fitted_size in FIT_ALL mode."""

    def test_landscape_image_in_portrait_cell(self):
        w, h = compute_fitted_size(1920, 1080, 300, 400, FitMode.FIT_ALL)
        assert w == 300
        assert h == 168
        assert w <= 300 and h <= 400

    def test_portrait_image_in_landscape_cell(self):
        w, h = compute_fitted_size(1080, 1920, 400, 300, FitMode.FIT_ALL)
        assert h == 300
        assert w == 168
        assert w <= 400 and h <= 300

    def test_square_image_in_tall_cell(self):
        w, h = compute_fitted_size(500, 500, 200, 300, FitMode.FIT_ALL)
        assert w == 200
        assert h == 200

    def test_exact_fit(self):
        w, h = compute_fitted_size(800, 600, 400, 300, FitMode.FIT_ALL)
        assert w == 400
        assert h == 300

    def test_zero_image(self):
        assert compute_fitted_size(0, 100, 300, 300, FitMode.FIT_ALL) == (0, 0)

    def test_zero_cell(self):
        assert compute_fitted_size(100, 100, 0, 300, FitMode.FIT_ALL) == (0, 0)

    def test_negative_dimensions(self):
        assert compute_fitted_size(-10, 100, 300, 300, FitMode.FIT_ALL) == (0, 0)

    def test_result_never_exceeds_cell(self):
        cases = [
            (1920, 1080, 200, 300),
            (1080, 1920, 300, 200),
            (500, 500, 150, 150),
            (4000, 3000, 250, 250),
            (1, 9999, 100, 100),
        ]
        for iw, ih, cw, ch in cases:
            w, h = compute_fitted_size(iw, ih, cw, ch, FitMode.FIT_ALL)
            assert w <= cw, f"w {w} > cw {cw} for {(iw, ih, cw, ch)}"
            assert h <= ch, f"h {h} > ch {ch} for {(iw, ih, cw, ch)}"


# ---------------------------------------------------------------------------
# CROP_ALL mode — result always equals cell dimensions
# ---------------------------------------------------------------------------

class TestComputeFittedSizeCropAll:
    """Tests for compute_fitted_size in CROP_ALL mode."""

    def test_landscape_image(self):
        w, h = compute_fitted_size(1920, 1080, 300, 400, FitMode.CROP_ALL)
        assert (w, h) == (300, 400)

    def test_portrait_image(self):
        w, h = compute_fitted_size(1080, 1920, 400, 300, FitMode.CROP_ALL)
        assert (w, h) == (400, 300)

    def test_square(self):
        w, h = compute_fitted_size(500, 500, 200, 300, FitMode.CROP_ALL)
        assert (w, h) == (200, 300)

    def test_zero_returns_zero(self):
        assert compute_fitted_size(0, 100, 300, 300, FitMode.CROP_ALL) == (0, 0)


# ---------------------------------------------------------------------------
# FIT_WIDTH mode — width matches cell, height ≤ cell (clamped)
# ---------------------------------------------------------------------------

class TestComputeFittedSizeFitWidth:
    """Tests for compute_fitted_size in FIT_WIDTH mode."""

    def test_landscape_width_limited(self):
        w, h = compute_fitted_size(1920, 1080, 300, 400, FitMode.FIT_WIDTH)
        assert w == 300
        # 300 / (1920/1080) = ~168; fits within 400
        assert h == 168
        assert h <= 400

    def test_portrait_would_exceed_height(self):
        """Very tall portrait: computed height exceeds cell → clamped."""
        w, h = compute_fitted_size(100, 1000, 300, 200, FitMode.FIT_WIDTH)
        assert w == 300
        assert h <= 200  # clamped

    def test_zero_returns_zero(self):
        assert compute_fitted_size(0, 100, 300, 300, FitMode.FIT_WIDTH) == (0, 0)


# ---------------------------------------------------------------------------
# FIT_HEIGHT mode — height matches cell, width ≤ cell (clamped)
# ---------------------------------------------------------------------------

class TestComputeFittedSizeFitHeight:
    """Tests for compute_fitted_size in FIT_HEIGHT mode."""

    def test_portrait_height_limited(self):
        w, h = compute_fitted_size(1080, 1920, 400, 300, FitMode.FIT_HEIGHT)
        assert h == 300
        # 300 * (1080/1920) = ~168
        assert w == 168
        assert w <= 400

    def test_landscape_would_exceed_width(self):
        """Very wide panorama: computed width exceeds cell → clamped."""
        w, h = compute_fitted_size(5000, 100, 200, 300, FitMode.FIT_HEIGHT)
        assert h == 300
        assert w <= 200  # clamped

    def test_zero_returns_zero(self):
        assert compute_fitted_size(100, 0, 300, 300, FitMode.FIT_HEIGHT) == (0, 0)
