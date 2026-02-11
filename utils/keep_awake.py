"""
Keep display and system awake during long operations (e.g. drawing session).
Uses Windows SetThreadExecutionState when on Windows; no-op on other platforms.
"""
import sys
# Windows: ES_CONTINUOUS | ES_DISPLAY_REQUIRED | ES_SYSTEM_REQUIRED
# Reason: ES_DISPLAY_REQUIRED resets display idle timer; ES_SYSTEM_REQUIRED resets system idle;
# both needed to prevent screen sleep. ES_CONTINUOUS keeps the state until we clear it.
_ES_CONTINUOUS = 0x80000000
_ES_DISPLAY_REQUIRED = 0x00000002
_ES_SYSTEM_REQUIRED = 0x00000001


def prevent_sleep() -> None:
    """
    Prevent display and system from going to sleep (e.g. during a fullscreen session).
    On Windows calls SetThreadExecutionState; on other platforms does nothing.
    Idempotent: safe to call multiple times.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(
            _ES_CONTINUOUS | _ES_DISPLAY_REQUIRED | _ES_SYSTEM_REQUIRED
        )
    except (AttributeError, OSError):
        pass


def allow_sleep() -> None:
    """
    Restore normal power behavior (allow display and system to sleep again).
    Call when the session or long operation ends.
    Idempotent: safe to call multiple times.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(_ES_CONTINUOUS)
    except (AttributeError, OSError):
        pass
