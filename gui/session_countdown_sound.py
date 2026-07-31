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
_FINAL_TICK_WAV = Path(__file__).resolve().parent / "ressources" / "timer_tick_zero.wav"

_TICK_FREQUENCY_HZ = 880.0
_FINAL_TICK_FREQUENCY_HZ = 1760.0


def _generate_tick_wav(
    path: Path,
    frequency_hz: float,
    duration: float = 0.07,
    amplitude: int = 6000,
) -> Path:
    """
    Write a short sine tick WAV file.

    Args:
        path: Destination file path.
        frequency_hz: Tone frequency in Hz.
        duration: Length in seconds.
        amplitude: Peak sample amplitude.

    Returns:
        Path: Path to the WAV file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    with wave.open(str(path), "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        frames = bytearray()
        for i in range(n_samples):
            t = i / sample_rate
            envelope = 1.0 - (t / duration)
            sample = int(
                amplitude * envelope * math.sin(2 * math.pi * frequency_hz * t)
            )
            frames.extend(struct.pack("<h", sample))
        wav_file.writeframes(bytes(frames))
    return path


def _ensure_tick_wav(path: Path) -> Path:
    """Create the standard countdown tick if missing."""
    if path.exists():
        return path
    return _generate_tick_wav(path, _TICK_FREQUENCY_HZ)


def _ensure_final_tick_wav(path: Path) -> Path:
    """Create the sharper final tick (0 s) if missing."""
    if path.exists():
        return path
    return _generate_tick_wav(path, _FINAL_TICK_FREQUENCY_HZ, duration=0.09, amplitude=6500)


class SessionCountdownSound:
    """Plays soft ticks during the final countdown; a sharper tone at 0 s."""

    def __init__(self, parent=None) -> None:
        """
        Initialize sound effects and preload WAV sources.

        Args:
            parent: Optional QObject parent.
        """
        self._tick_path = _ensure_tick_wav(_TICK_WAV)
        self._final_path = _ensure_final_tick_wav(_FINAL_TICK_WAV)
        self._effect = QSoundEffect(parent)
        self._effect.setVolume(0.35)
        self._effect.setLoopCount(1)
        self._final_effect = QSoundEffect(parent)
        self._final_effect.setVolume(0.42)
        self._final_effect.setLoopCount(1)
        self._played_seconds: set[int] = set()
        self._final_played_this_pose: bool = False
        self._assign_sources()

    def _assign_sources(self) -> None:
        """Assign (or re-assign) WAV sources to both sound effects."""
        self._effect.setSource(QUrl.fromLocalFile(str(self._tick_path)))
        self._final_effect.setSource(QUrl.fromLocalFile(str(self._final_path)))

    def _safe_play(self, effect: QSoundEffect) -> None:
        """
        Play a sound effect, recovering from Error glitches after skip/stop.

        Args:
            effect: The QSoundEffect to play.
        """
        if effect.status() == QSoundEffect.Error:
            self._assign_sources()
        if effect.isPlaying():
            effect.stop()
        effect.play()

    def reset(self) -> None:
        """Clear per-pose tick state; stop regular ticks but let a final tick finish."""
        self._effect.stop()
        # Keep _final_effect playing: auto-advance calls reset() immediately after
        # play_final_tick(), and stop() would mute the 0 s bip (and can Error on Windows).
        self._played_seconds.clear()
        self._final_played_this_pose = False
        if self._effect.status() == QSoundEffect.Error:
            self._effect.setSource(QUrl.fromLocalFile(str(self._tick_path)))

    def play_tick_if_needed(self, remaining_seconds: int) -> None:
        """
        Play ticks for seconds 10→1 once each (timer cadence ≈ 1 s).

        Args:
            remaining_seconds: Seconds left on the current image timer.
        """
        if remaining_seconds < 1 or remaining_seconds > 10:
            return
        if remaining_seconds in self._played_seconds:
            return
        self._played_seconds.add(remaining_seconds)
        self._safe_play(self._effect)

    def play_final_tick(self) -> None:
        """Play the sharper 0 s tone once per pose (end of countdown)."""
        if self._final_played_this_pose:
            return
        self._final_played_this_pose = True
        self._played_seconds.add(0)
        self._safe_play(self._final_effect)
