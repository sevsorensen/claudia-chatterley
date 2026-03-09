"""
Configuration management for Claudia Chatterley.

Settings are stored in ~/.claudia/config.json and can be overridden
via environment variables prefixed with CLAUDIA_.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


# Default paths
CLAUDIA_HOME = Path.home() / ".claudia"
CONFIG_FILE = CLAUDIA_HOME / "config.json"
MODELS_DIR = CLAUDIA_HOME / "models"
CACHE_DIR = CLAUDIA_HOME / "cache"


@dataclass
class TranscriptionConfig:
    """Speech-to-text settings."""

    # Engine: "local" (faster-whisper) or "groq" (cloud API)
    engine: str = "local"

    # Whisper model size: "tiny", "base", "small", "medium", "large-v3"
    # small is the sweet spot: ~460MB, good speed, noticeably better on proper nouns
    model_size: str = "small"

    # Language code (None = auto-detect)
    language: Optional[str] = "en"

    # Groq API key (only needed if engine="groq")
    groq_api_key: Optional[str] = None

    # Beam size for faster-whisper (higher = more accurate, slower)
    beam_size: int = 5

    # Voice activity detection: minimum silence duration (seconds) to consider speech done
    vad_silence_duration: float = 1.0


@dataclass
class AudioConfig:
    """Audio capture settings."""

    # Sample rate (16kHz is what Whisper expects)
    sample_rate: int = 16000

    # Audio channels (mono for speech)
    channels: int = 1

    # Input device index (None = system default mic)
    input_device: Optional[int] = None

    # Chunk size for recording buffer (samples)
    chunk_size: int = 1024


@dataclass
class UIConfig:
    """User interface settings."""

    # Show floating mic widget (in addition to menubar icon)
    show_floating_widget: bool = True

    # Floating widget position (x, y from top-left)
    widget_x: int = 50
    widget_y: int = 200

    # Widget size (diameter in pixels)
    widget_size: int = 48

    # Play chime sound when transcription is ready
    play_chime: bool = True

    # Auto-paste after transcription (if False, copies to clipboard only)
    auto_paste: bool = True

    # Show tooltip preview of transcription before pasting
    show_preview: bool = False


@dataclass
class ClaudiaConfig:
    """Top-level configuration for Claudia Chatterley."""

    transcription: TranscriptionConfig = field(default_factory=TranscriptionConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    ui: UIConfig = field(default_factory=UIConfig)

    # First run flag
    first_run: bool = True

    @classmethod
    def load(cls) -> "ClaudiaConfig":
        """Load configuration from disk, falling back to defaults."""
        config = cls()

        # Load from file if it exists
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE) as f:
                    data = json.load(f)
                config = cls._from_dict(data)
            except (json.JSONDecodeError, KeyError, TypeError):
                pass  # Fall back to defaults on corrupt config

        # Override with environment variables
        config._apply_env_overrides()

        return config

    @classmethod
    def _from_dict(cls, data: dict) -> "ClaudiaConfig":
        """Reconstruct config from a dictionary."""
        return cls(
            transcription=TranscriptionConfig(**data.get("transcription", {})),
            audio=AudioConfig(**data.get("audio", {})),
            ui=UIConfig(**data.get("ui", {})),
            first_run=data.get("first_run", True),
        )

    def _apply_env_overrides(self):
        """Apply environment variable overrides (CLAUDIA_ prefix)."""
        env_map = {
            "CLAUDIA_ENGINE": ("transcription", "engine"),
            "CLAUDIA_MODEL_SIZE": ("transcription", "model_size"),
            "CLAUDIA_LANGUAGE": ("transcription", "language"),
            "CLAUDIA_GROQ_API_KEY": ("transcription", "groq_api_key"),
            "CLAUDIA_SAMPLE_RATE": ("audio", "sample_rate"),
            "CLAUDIA_AUTO_PASTE": ("ui", "auto_paste"),
        }
        for env_key, (section, attr) in env_map.items():
            value = os.environ.get(env_key)
            if value is not None:
                section_obj = getattr(self, section)
                field_type = type(getattr(section_obj, attr))
                if field_type == bool:
                    value = value.lower() in ("true", "1", "yes")
                elif field_type == int:
                    value = int(value)
                elif field_type == float:
                    value = float(value)
                setattr(section_obj, attr, value)

    def save(self):
        """Persist configuration to disk."""
        CLAUDIA_HOME.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(asdict(self), f, indent=2)

    def ensure_dirs(self):
        """Create required directories."""
        CLAUDIA_HOME.mkdir(parents=True, exist_ok=True)
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
