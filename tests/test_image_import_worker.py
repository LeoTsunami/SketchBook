"""Tests for ImageImportWorker subfolder tag helpers."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from gui.image_import_worker import ImageImportWorker


@pytest.fixture
def worker_no_roots():
    """Worker with a dummy manager (subfolder logic only)."""
    return ImageImportWorker(MagicMock(), [], tags=set())


def test_tokens_from_folder_segment_no_separator(worker_no_roots):
    """Without separator, one capitalized token per segment."""
    w = worker_no_roots
    assert w._tokens_from_folder_segment("hello", None) == {"Hello"}
    assert w._tokens_from_folder_segment("HELLO", None) == {"Hello"}


def test_tokens_from_folder_segment_with_underscore(worker_no_roots):
    """Split on underscore yields capitalized pieces."""
    w = worker_no_roots
    assert w._tokens_from_folder_segment("my_cool_tag", "_") == {
        "My",
        "Cool",
        "Tag",
    }


def test_subfolder_tags_for_respects_split(tmp_path):
    """Path segments are split and capitalized when separator is set."""
    mgr = MagicMock()
    root = tmp_path / "lib"
    sub = root / "a_b" / "c-d"
    sub.mkdir(parents=True)
    img = sub / "x.jpg"
    img.write_bytes(b"\xff\xd8\xff\xd9")

    w = ImageImportWorker(
        mgr,
        [img],
        tags=set(),
        subfolder_tag_roots=[root],
        subfolder_split_separator="_",
    )
    tags = w._subfolder_tags_for(img)
    assert tags == {"A", "B", "C-d"}


def test_subfolder_tags_for_no_split_capitalize_segments(tmp_path):
    """Without split separator, each folder level is one capitalized tag."""
    mgr = MagicMock()
    root = tmp_path / "r"
    sub = root / "animals" / "COOL_CATS"
    sub.mkdir(parents=True)
    img = sub / "p.jpg"
    img.write_bytes(b"x")

    w = ImageImportWorker(
        mgr,
        [img],
        tags=set(),
        subfolder_tag_roots=[root],
        subfolder_split_separator=None,
    )
    tags = w._subfolder_tags_for(img)
    assert tags == {"Animals", "Cool_cats"}
