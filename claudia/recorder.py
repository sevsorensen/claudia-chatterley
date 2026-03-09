"""
Audio recorder with voice activity detection.

Captures microphone input using sounddevice and detects when the user
has stopped speaking using energy-based VAD (voice activity detection).

The recorder operates in three states:
  IDLE → RECORDING → DONE

Audio is stored as a numpy array of float32 samples at 16kHz mono,
which is exactly what Whisper expects.
"""

import enum
import io
import logging
import threading
import time
import wave
from typing import Callable, Optional

import numpy as np
import sounddevice as sd

from claudia.config import AudioConfig

logger = logging.getLogger(__name__)


class RecorderState(enum.Enum):
    IDLE = "idle"
    RECORDING = "recording"
    PROCESSING = "processing"


class AudioRecorder:
    """
    Captures microphone audio with simple energy-based voice activity detection.

    Usage:
        recorder = AudioRecorder(config)
        recorder.start()          # Begin recording
        # ... user speaks ...
        audio_bytes = recorder.stop()   # Stop and get WAV bytes
    """

    def __init__(
        self,
        config: AudioConfig,
        on_state_change: Optional[Callable[[RecorderState], None]] = None,
        on_level: Optional[Callable[[float], None]] = None,
    ):
        self.config = config
        self.on_state_change = on_state_change or (lambda s: None)
        self.on_level = on_level or (lambda l: None)

        self._state = RecorderState.IDLE
        self._audio_chunks: list[np.ndarray] = []
        self._stream: Optional[sd.InputStream] = None
        self._lock = threading.Lock()

    @property
    def state(self) -> RecorderState:
        return self._state

    def _set_state(self, state: RecorderState):
        self._state = state
        self.on_state_change(state)

    def start(self):
        """Begin recording from microphone."""
        with self._lock:
            if self._state == RecorderState.RECORDING:
                logger.warning("Already recording, ignoring start()")
                return

            self._audio_chunks = []
            self._set_state(RecorderState.RECORDING)

            self._stream = sd.InputStream(
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                dtype="float32",
                blocksize=self.config.chunk_size,
                device=self.config.input_device,
                callback=self._audio_callback,
            )
            self._stream.start()
            logger.info("Recording started (sample_rate=%d)", self.config.sample_rate)

    def stop(self) -> bytes:
        """
        Stop recording and return the captured audio as WAV bytes.

        Returns:
            WAV-formatted audio bytes (16kHz, mono, 16-bit PCM).
        """
        with self._lock:
            if self._state != RecorderState.RECORDING:
                logger.warning("Not recording, returning empty audio")
                return b""

            self._set_state(RecorderState.PROCESSING)

            # Stop the audio stream
            if self._stream is not None:
                self._stream.stop()
                self._stream.close()
                self._stream = None

            # Concatenate all audio chunks
            if not self._audio_chunks:
                self._set_state(RecorderState.IDLE)
                return b""

            audio_data = np.concatenate(self._audio_chunks, axis=0)
            self._audio_chunks = []

            # Trim leading/trailing silence (below -40dB threshold)
            audio_data = self._trim_silence(audio_data)

            if len(audio_data) == 0:
                logger.info("No speech detected in recording")
                self._set_state(RecorderState.IDLE)
                return b""

            # Convert to WAV bytes
            wav_bytes = self._to_wav_bytes(audio_data)
            duration = len(audio_data) / self.config.sample_rate
            logger.info("Recording stopped: %.1f seconds, %d bytes", duration, len(wav_bytes))

            self._set_state(RecorderState.IDLE)
            return wav_bytes

    def cancel(self):
        """Cancel recording without returning audio."""
        with self._lock:
            if self._stream is not None:
                self._stream.stop()
                self._stream.close()
                self._stream = None
            self._audio_chunks = []
            self._set_state(RecorderState.IDLE)
            logger.info("Recording cancelled")

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        """Sounddevice callback — receives audio chunks in real time."""
        if status:
            logger.warning("Audio stream status: %s", status)

        # Store the chunk
        self._audio_chunks.append(indata.copy())

        # Calculate RMS level for the UI meter (0.0 to 1.0)
        rms = float(np.sqrt(np.mean(indata ** 2)))
        # Normalize to a 0-1 range (typical speech RMS is 0.01–0.1)
        level = min(1.0, rms * 10)
        self.on_level(level)

    def _trim_silence(self, audio: np.ndarray, threshold_db: float = -40.0) -> np.ndarray:
        """Trim leading and trailing silence from audio."""
        if audio.ndim > 1:
            audio = audio.flatten()

        threshold = 10 ** (threshold_db / 20)

        # Find where audio exceeds threshold
        above_threshold = np.abs(audio) > threshold
        if not np.any(above_threshold):
            return np.array([], dtype=np.float32)

        # Find first and last non-silent sample (with 0.1s padding)
        indices = np.where(above_threshold)[0]
        pad_samples = int(0.1 * self.config.sample_rate)
        start = max(0, indices[0] - pad_samples)
        end = min(len(audio), indices[-1] + pad_samples)

        return audio[start:end]

    def _to_wav_bytes(self, audio: np.ndarray) -> bytes:
        """Convert float32 numpy audio to WAV bytes (16-bit PCM)."""
        if audio.ndim > 1:
            audio = audio.flatten()

        # Convert float32 [-1.0, 1.0] to int16
        audio_int16 = (audio * 32767).astype(np.int16)

        # Write to WAV format in memory
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(self.config.channels)
            wf.setsampwidth(2)  # 16-bit = 2 bytes
            wf.setframerate(self.config.sample_rate)
            wf.writeframes(audio_int16.tobytes())

        return buffer.getvalue()

    @staticmethod
    def list_devices() -> list[dict]:
        """List available audio input devices."""
        devices = []
        for i, dev in enumerate(sd.query_devices()):
            if dev["max_input_channels"] > 0:
                devices.append({
                    "index": i,
                    "name": dev["name"],
                    "channels": dev["max_input_channels"],
                    "sample_rate": dev["default_samplerate"],
                })
        return devices

    @staticmethod
    def get_default_device() -> Optional[dict]:
        """Get the default input device info."""
        try:
            dev = sd.query_devices(kind="input")
            return {
                "name": dev["name"],
                "channels": dev["max_input_channels"],
                "sample_rate": dev["default_samplerate"],
            }
        except sd.PortAudioError:
            return None
