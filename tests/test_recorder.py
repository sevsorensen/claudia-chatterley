"""Tests for the audio recorder module."""

import io
import struct
import wave

import numpy as np
import pytest

from claudia.config import AudioConfig
from claudia.recorder import AudioRecorder, RecorderState


class TestAudioRecorder:
    """Tests for AudioRecorder."""

    def setup_method(self):
        self.config = AudioConfig()
        self.state_changes = []
        self.levels = []

        def on_state(state):
            self.state_changes.append(state)

        def on_level(level):
            self.levels.append(level)

        self.recorder = AudioRecorder(
            config=self.config,
            on_state_change=on_state,
            on_level=on_level,
        )

    def test_initial_state(self):
        """Recorder starts in IDLE state."""
        assert self.recorder.state == RecorderState.IDLE

    def test_cancel_when_idle(self):
        """Cancelling when idle is safe."""
        self.recorder.cancel()
        assert self.recorder.state == RecorderState.IDLE

    def test_stop_when_idle_returns_empty(self):
        """Stopping when not recording returns empty bytes."""
        result = self.recorder.stop()
        assert result == b""

    def test_trim_silence_all_silent(self):
        """Trim silence removes entirely silent audio."""
        silent = np.zeros(16000, dtype=np.float32)
        trimmed = self.recorder._trim_silence(silent)
        assert len(trimmed) == 0

    def test_trim_silence_preserves_speech(self):
        """Trim silence preserves audio above threshold."""
        # Create audio with silence + speech + silence
        sr = 16000
        silence = np.zeros(sr, dtype=np.float32)
        speech = np.random.uniform(-0.5, 0.5, sr).astype(np.float32)
        audio = np.concatenate([silence, speech, silence])

        trimmed = self.recorder._trim_silence(audio)
        # Should be roughly 1 second of speech + padding
        assert len(trimmed) > 0
        assert len(trimmed) < len(audio)

    def test_to_wav_bytes_valid(self):
        """WAV bytes are valid WAV format."""
        audio = np.random.uniform(-0.5, 0.5, 16000).astype(np.float32)
        wav_bytes = self.recorder._to_wav_bytes(audio)

        # Verify it's valid WAV
        buffer = io.BytesIO(wav_bytes)
        with wave.open(buffer, "rb") as wf:
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2
            assert wf.getframerate() == 16000
            assert wf.getnframes() == 16000

    def test_to_wav_bytes_multichannel_flattened(self):
        """Multi-dimensional audio is flattened correctly."""
        audio = np.random.uniform(-0.5, 0.5, (16000, 1)).astype(np.float32)
        wav_bytes = self.recorder._to_wav_bytes(audio)
        assert len(wav_bytes) > 0


class TestListDevices:
    """Tests for device listing (may fail in CI without audio hardware)."""

    def test_list_devices_returns_list(self):
        """list_devices returns a list (may be empty in CI)."""
        devices = AudioRecorder.list_devices()
        assert isinstance(devices, list)

    def test_device_dict_structure(self):
        """Each device dict has expected keys."""
        devices = AudioRecorder.list_devices()
        for dev in devices:
            assert "index" in dev
            assert "name" in dev
            assert "channels" in dev
            assert "sample_rate" in dev
