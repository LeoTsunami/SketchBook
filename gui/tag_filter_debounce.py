"""
One-shot debounce for image-grid refresh after tag activations.

Tag chips update immediately; the grid waits until the user stops toggling.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from qtpy.QtCore import QObject, QTimer


class TagFilterApplyDebouncer(QObject):
    """Restartable one-shot timer that fires ``callback`` after an idle gap."""

    def __init__(
        self,
        callback: Callable[..., None],
        delay_ms: int = 500,
        parent: Optional[QObject] = None,
    ) -> None:
        """
        Bind a callback and delay.

        Args:
            callback: Invoked with the latest ``schedule`` arguments.
            delay_ms: Idle time before the callback runs.
            parent: Optional Qt parent (owns the timer).
        """
        super().__init__(parent)
        self._callback = callback
        self.delay_ms = delay_ms
        self._args: tuple[Any, ...] = ()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fire)

    def schedule(self, *args: Any) -> None:
        """
        Restart the idle timer. The last ``args`` win.

        Args:
            *args: Forwarded to ``callback`` when the timer fires.
        """
        self._args = args
        self._timer.start(self.delay_ms)

    def cancel(self) -> None:
        """Stop the timer without invoking the callback."""
        self._timer.stop()
        self._args = ()

    def is_active(self) -> bool:
        """
        Return whether a refresh is pending.

        Returns:
            bool: True when the one-shot timer is running.
        """
        return self._timer.isActive()

    def _fire(self) -> None:
        """Invoke the callback with the latest scheduled arguments."""
        args = self._args
        self._args = ()
        self._callback(*args)
