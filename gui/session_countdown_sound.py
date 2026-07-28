"""
Light tick sound for the last seconds of a session image timer.
"""

import math
import struct
import wave
from pathlib import Path

from qtpy.QtCore import QUrl
from qtpy.QtMultimedia import QSoundEffect


_TICK_WAV = Path(__file__).resolve().parent / "ressources" / "timer_tick.wav"


def _ensure_tick_wav(path: Path) -> Path:
    """
  Create a short soft tick WAV if the resource file is missing.

  Args:
      path: Destination file path.

  Returns:
      Path: Path to the WAV file.
  """
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 44100
    duration = 0.07
    frequency = 880.0
    n_samples = int(sample_rate * duration)
    with wave.open(str(path), "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        frames = bytearray()
        for i in range(n_samples):
            t = i / sample_rate
            envelope = 1.0 - (t / duration)
            sample = int(6000 * envelope * math.sin(2 * math.pi * frequency * t))
            frames.extend(struct.pack("<h", sample))
        wav_file.writeframes(bytes(frames))
    return path


class SessionCountdownSound:
    """Plays a soft tick once per second during the final countdown."""

    def __init__(self, parent=None) -> None:
        """
        Initialize the sound effect (loads WAV on first play).

        Args:
            parent: Optional QObject parent.
        """
        self._effect = QSoundEffect(parent)
        self._effect.setVolume(0.35)
        self._loaded = False
        self._last_played_second: int = -1

    def reset(self) -> None:
        """Clear last-played second so ticks can fire again on the next image."""
        self._last_played_second = -1

    def play_tick_if_needed(self, remaining_seconds: int) -> None:
        """
        Play one tick when ``remaining_seconds`` is in 1..10 and not yet played.

        Args:
            remaining_seconds: Seconds left on the current image timer.
        """
        if remaining_seconds < 1 or remaining_seconds > 10:
            return
        if remaining_seconds == self._last_played_second:
            return
        self._last_played_second = remaining_seconds
        if not self._loaded:
            wav_path = _ensure_tick_wav(_TICK_WAV)
            self._effect.setSource(QUrl.fromLocalFile(str(wav_path)))
            self._loaded = True
        self._effect.play()
