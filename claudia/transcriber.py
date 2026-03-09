"""
Speech-to-text transcription engine.

Supports two backends:
  1. Local: faster-whisper (whisper.cpp Python bindings) — private, no API key
  2. Cloud: Groq Whisper API — fast, accurate, requires API key

The local engine downloads the model on first use (~140MB for "base").
"""

import io
import logging
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from claudia.config import TranscriptionConfig, MODELS_DIR

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    """Result of a speech-to-text transcription."""
    text: str
    language: str
    confidence: float
    duration_seconds: float
    engine: str  # "local" or "groq"
    processing_time: float  # how long transcription took


class Transcriber:
    """
    Transcribes audio to text using faster-whisper (local) or Groq API (cloud).

    Usage:
        transcriber = Transcriber(config)
        result = transcriber.transcribe(wav_bytes)
        print(result.text)
    """

    def __init__(self, config: TranscriptionConfig):
        self.config = config
        self._local_model = None
        self._groq_client = None

    def transcribe(self, audio_bytes: bytes) -> TranscriptionResult:
        """
        Transcribe WAV audio bytes to text.

        Args:
            audio_bytes: WAV-formatted audio data.

        Returns:
            TranscriptionResult with the transcribed text and metadata.
        """
        if not audio_bytes:
            return TranscriptionResult(
                text="",
                language="",
                confidence=0.0,
                duration_seconds=0.0,
                engine="none",
                processing_time=0.0,
            )

        start_time = time.monotonic()

        if self.config.engine == "groq" and self.config.groq_api_key:
            try:
                result = self._transcribe_groq(audio_bytes)
                result.processing_time = time.monotonic() - start_time
                return result
            except Exception as e:
                logger.warning("Groq transcription failed, falling back to local: %s", e)

        # Default / fallback: local faster-whisper
        result = self._transcribe_local(audio_bytes)
        result.processing_time = time.monotonic() - start_time
        return result

    def _transcribe_local(self, audio_bytes: bytes) -> TranscriptionResult:
        """Transcribe using local faster-whisper model."""
        model = self._get_local_model()

        # faster-whisper needs a file path, so write to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            segments, info = model.transcribe(
                tmp_path,
                language=self.config.language,
                beam_size=self.config.beam_size,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=int(self.config.vad_silence_duration * 1000),
                ),
            )

            # Collect all segments
            text_parts = []
            total_confidence = 0.0
            segment_count = 0
            for segment in segments:
                text_parts.append(segment.text.strip())
                total_confidence += segment.avg_logprob
                segment_count += 1

            text = " ".join(text_parts).strip()
            avg_confidence = (total_confidence / segment_count) if segment_count > 0 else 0.0
            # Convert log probability to a 0-1 confidence score
            confidence = min(1.0, max(0.0, 1.0 + avg_confidence))

            return TranscriptionResult(
                text=text,
                language=info.language or self.config.language or "en",
                confidence=confidence,
                duration_seconds=info.duration,
                engine="local",
                processing_time=0.0,
            )

        finally:
            os.unlink(tmp_path)

    def _transcribe_groq(self, audio_bytes: bytes) -> TranscriptionResult:
        """Transcribe using Groq Whisper API (cloud)."""
        client = self._get_groq_client()

        # Groq expects a file-like object
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "recording.wav"

        response = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-large-v3",
            language=self.config.language or "en",
            response_format="verbose_json",
        )

        return TranscriptionResult(
            text=response.text.strip(),
            language=response.language or self.config.language or "en",
            confidence=0.95,  # Groq doesn't return per-segment confidence
            duration_seconds=response.duration or 0.0,
            engine="groq",
            processing_time=0.0,
        )

    def _get_local_model(self):
        """Lazy-load the faster-whisper model."""
        if self._local_model is None:
            from faster_whisper import WhisperModel

            model_path = MODELS_DIR / self.config.model_size
            MODELS_DIR.mkdir(parents=True, exist_ok=True)

            logger.info(
                "Loading whisper model '%s' (this may download ~140MB on first run)...",
                self.config.model_size,
            )

            # Use int8 quantization on CPU for speed, float16 on GPU
            compute_type = "int8"

            self._local_model = WhisperModel(
                self.config.model_size,
                device="cpu",
                compute_type=compute_type,
                download_root=str(MODELS_DIR),
            )

            logger.info("Whisper model '%s' loaded successfully", self.config.model_size)

        return self._local_model

    def _get_groq_client(self):
        """Lazy-load the Groq API client."""
        if self._groq_client is None:
            try:
                from groq import Groq
            except ImportError:
                raise ImportError(
                    "Groq API requires the 'groq' package. "
                    "Install with: pip install claudia-chatterley[groq]"
                )

            if not self.config.groq_api_key:
                raise ValueError(
                    "Groq API key is required. Set CLAUDIA_GROQ_API_KEY environment variable "
                    "or configure in ~/.claudia/config.json"
                )

            self._groq_client = Groq(api_key=self.config.groq_api_key)

        return self._groq_client

    def preload_model(self):
        """
        Pre-download and load the whisper model.
        Call this during first-run setup to avoid delay on first transcription.
        """
        if self.config.engine == "local" or not self.config.groq_api_key:
            logger.info("Pre-loading whisper model...")
            self._get_local_model()
            logger.info("Model ready.")
