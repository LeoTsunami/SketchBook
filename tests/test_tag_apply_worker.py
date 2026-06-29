"""
Unit tests for TagApplyWorker (apply/remove tag on multiple images).
"""
import pytest
from unittest.mock import MagicMock, ANY
from gui.tag_apply_worker import TagApplyWorker, TagApplySignals


@pytest.fixture
def mock_image_manager():
    """Mock ImageManager with bulk tag helpers."""
    manager = MagicMock()
    manager.add_tags_to_images.return_value = 1
    manager.remove_tags_from_images.return_value = 1
    return manager


def test_tag_apply_worker_remove_operation(mock_image_manager, qtbot):
    """TagApplyWorker with operation='remove' uses bulk remove and emits finished."""
    image_id = "img-1"
    tag = "Landscape"

    worker = TagApplyWorker(
        mock_image_manager,
        [image_id],
        tag,
        operation="remove",
    )
    finished_vals = []
    worker.signals.finished.connect(finished_vals.append)
    worker.run()

    assert finished_vals == [1]
    mock_image_manager.remove_tags_from_images.assert_called_once_with(
        [image_id],
        tag,
        progress=ANY,
    )


def test_tag_apply_worker_add_operation(mock_image_manager, qapp):
    """TagApplyWorker with operation='add' uses bulk add."""
    worker = TagApplyWorker(
        mock_image_manager,
        ["img-1", "img-2"],
        "Human",
        operation="add",
    )
    finished_vals = []
    worker.signals.finished.connect(finished_vals.append)
    worker.run()

    assert finished_vals == [1]
    mock_image_manager.add_tags_to_images.assert_called_once_with(
        ["img-1", "img-2"],
        "Human",
        progress=ANY,
    )


def test_tag_apply_worker_empty_image_ids_emits_finished_zero(mock_image_manager, qapp):
    """TagApplyWorker with empty image_ids emits finished(0) and does not call update."""
    worker = TagApplyWorker(
        mock_image_manager,
        [],
        "SomeTag",
        operation="remove",
    )
    finished_vals = []
    worker.signals.finished.connect(finished_vals.append)
    worker.run()

    assert finished_vals == [0]
    mock_image_manager.remove_tags_from_images.assert_not_called()


def test_tag_apply_worker_error_emits_error_signal(mock_image_manager, qtbot):
    """TagApplyWorker emits error signal when bulk add raises."""
    mock_image_manager.add_tags_to_images.side_effect = RuntimeError("DB error")

    worker = TagApplyWorker(
        mock_image_manager,
        ["img-1"],
        "Tag",
        operation="add",
    )
    errors = []
    worker.signals.error.connect(errors.append)
    worker.run()

    assert len(errors) == 1
    assert "DB error" in errors[0]
