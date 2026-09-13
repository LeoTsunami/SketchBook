"""Tests for delayed image-grid refresh after tag activations."""

from qtpy.QtCore import QObject

from gui.tag_filter_debounce import TagFilterApplyDebouncer


def test_debouncer_applies_once_after_idle(qtbot) -> None:
    """Each schedule restarts the one-shot; only the last args are applied."""
    hits: list[str] = []
    parent = QObject()
    debouncer = TagFilterApplyDebouncer(
        lambda value: hits.append(value),
        delay_ms=40,
        parent=parent,
    )
    debouncer.schedule("first")
    debouncer.schedule("second")
    assert hits == []
    assert debouncer.is_active()
    qtbot.waitUntil(lambda: hits == ["second"], timeout=500)
    qtbot.wait(50)
    assert hits == ["second"]


def test_debouncer_cancel_skips_callback(qtbot) -> None:
    """cancel() drops a pending apply (used by immediate grid refresh)."""
    hits: list[int] = []
    parent = QObject()
    debouncer = TagFilterApplyDebouncer(
        lambda: hits.append(1),
        delay_ms=80,
        parent=parent,
    )
    debouncer.schedule()
    assert debouncer.is_active()
    debouncer.cancel()
    assert not debouncer.is_active()
    qtbot.wait(120)
    assert hits == []
