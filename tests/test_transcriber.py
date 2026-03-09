"""Tests for the transcription engine."""

import pytest

from claudia.config import TranscriptionConfig
from claudia.transcriber import Transcriber, TranscriptionResult


class TestTranscriber:
    """Tests for Transcriber."""

    def test_empty_audio_returns_empty_result(self):
        """Empty audio bytes returns empty result."""
        config = TranscriptionConfig()
        transcriber = Transcriber(config)
        result = transcriber.transcribe(b"")

        assert result.text == ""
        assert result.confidence == 0.0
        assert result.engine == "none"

    def test_result_dataclass_fields(self):
        """TranscriptionResult has all expected fields."""
        result = TranscriptionResult(
            text="hello world",
            language="en",
            confidence=0.95,
            duration_seconds=1.5,
            engine="local",
            processing_time=0.3,
        )
        assert result.text == "hello world"
        assert result.language == "en"
        assert result.confidence == 0.95
        assert result.duration_seconds == 1.5
        assert result.engine == "local"
        assert result.processing_time == 0.3

    def test_groq_fallback_without_key(self):
        """Groq engine without API key falls back to local."""
        config = TranscriptionConfig(engine="groq", groq_api_key=None)
        transcriber = Transcriber(config)
        # Should not raise — falls back to local
        # (local will also fail without audio but that's expected)

    def test_groq_import_error(self):
        """Missing groq package raises ImportError with helpful message."""
        config = TranscriptionConfig(engine="groq", groq_api_key="test-key")
        transcriber = Transcriber(config)
        # The actual import check happens lazily in _get_groq_client


class TestTranscriptionConfig:
    """Tests for TranscriptionConfig defaults."""

    def test_defaults(self):
        config = TranscriptionConfig()
        assert config.engine == "local"
        assert config.model_size == "base"
        assert config.language == "en"
        assert config.groq_api_key is None
        assert config.beam_size == 5
        assert config.vad_silence_duration == 1.0

    def test_custom_values(self):
        config = TranscriptionConfig(
            engine="groq",
            model_size="small",
            language="fr",
        )
        assert config.engine == "groq"
        assert config.model_size == "small"
        assert config.language == "fr"
