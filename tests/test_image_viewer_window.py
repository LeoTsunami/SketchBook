"""
Tests for ImageViewerWindow (transparent theme background around the image).
"""

import pytest

from gui.image_viewer_window import ImageViewerWindow
from PIL import Image


def test_viewer_uses_transparent_scene_and_view_style(qtbot, image_manager_with_image):
    """
    Expected: graphics scene and view are set up so letterboxing is not default gray.

    The window should show the global QMainWindow theme behind the image.
    """
    viewer = ImageViewerWindow(image_manager)
    qtbot.addWidget(viewer)
    assert viewer.scene.backgroundBrush().color().alpha() == 0
    assert "transparent" in viewer.graphics_view.styleSheet().lower()


def test_scene_background_stays_transparent_after_clear(qtbot, image_manager):
    """
    Edge case: scene.clear() must not reset the transparent background brush.

    We only clear an empty scene here so no deferred fit_image runs on deleted items.
    """
    viewer = ImageViewerWindow(image_manager)
    qtbot.addWidget(viewer)
    viewer.scene.clear()
    assert viewer.scene.backgroundBrush().color().alpha() == 0


def test_set_image_returns_false_for_unknown_id(qtbot, image_manager):
    """
    Failure path: missing image id should not crash and should return False.
    """
    viewer = ImageViewerWindow(image_manager)
    qtbot.addWidget(viewer)
    assert viewer.set_image("nonexistent-id-xyz") is False
