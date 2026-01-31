"""
Unit tests for TagApplyWorker (apply/remove tag on multiple images).
"""
import pytest
from unittest.mock import MagicMock
from core.image_db import ImageMetadata
from gui.tag_apply_worker import TagApplyWorker, TagApplySignals


@pytest.fixture
def mock_image_manager():
    """Mock ImageManager with get_image_metadata and update_image_metadata."""
    manager = MagicMock()
    return manager


def test_tag_apply_worker_remove_operation(mock_image_manager, qtbot):
    """TagApplyWorker with operation='remove' updates metadata and emits progress/finished."""
    image_id = "img-1"
    tag = "Landscape"
    metadata = ImageMetadata(
        id=image_id,
        path="img1.jpg",
        original_filename="img1.jpg",
        width=100,
        height=100,
        file_size=1000,
        format="JPEG",
        tags={"Landscape", "Nature"},
    )
    mock_image_manager.get_image_metadata.return_value = metadata

    worker = TagApplyWorker(
        mock_image_manager,
        [image_id],
        tag,
        operation="remove",
    )
    finished_vals = []
    worker.signals.finished.connect(finished_vals.append)
    worker.run()

    assert len(finished_vals) == 1
    assert finished_vals[0] == 1
    mock_image_manager.update_image_metadata.assert_called_once()
    call_args = mock_image_manager.update_image_metadata.call_args
    assert call_args[0][0] == image_id
    assert call_args[1]["tags"] == {"Nature"}


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
    mock_image_manager.update_image_metadata.assert_not_called()


def test_tag_apply_worker_error_emits_error_signal(mock_image_manager, qtbot):
    """TagApplyWorker emits error signal when get_image_metadata raises."""
    mock_image_manager.get_image_metadata.side_effect = RuntimeError("DB error")

    worker = TagApplyWorker(
        mock_image_manager,
        ["img-1"],
        "Tag",
        operation="remove",
    )
    errors = []
    worker.signals.error.connect(errors.append)
    worker.run()

    assert len(errors) == 1
    assert "DB error" in errors[0]
