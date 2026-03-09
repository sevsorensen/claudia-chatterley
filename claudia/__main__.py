"""
Entry point for Claudia Chatterley.

Usage:
    claudia              # Start the voice-to-text companion
    claudia --devices    # List available microphones
    claudia --engine groq --groq-key sk-...  # Use Groq cloud API
    python -m claudia    # Alternative launch method
"""

import argparse
import logging
import sys

from claudia import __version__
from claudia.config import ClaudiaConfig


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # Quiet down noisy libraries
    logging.getLogger("faster_whisper").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def print_banner():
    """Print startup banner."""
    print(f"""
╔══════════════════════════════════════════════════╗
║         🎤 Claudia Chatterley v{__version__}          ║
║    Voice-to-Text for Claude Cowork & macOS       ║
║                                                  ║
║  Click the floating mic to speak.                ║
║  Your words become text in any app.              ║
║                                                  ║
║  3x faster than typing. Zero cognitive load.     ║
╚══════════════════════════════════════════════════╝
""")


def list_devices():
    """Print available audio input devices."""
    from claudia.recorder import AudioRecorder

    print("\nAvailable microphones:\n")
    devices = AudioRecorder.list_devices()
    if not devices:
        print("  No input devices found.")
        return

    default = AudioRecorder.get_default_device()
    for dev in devices:
        marker = " ★" if default and dev["name"] == default["name"] else ""
        print(f"  [{dev['index']}] {dev['name']} ({dev['channels']}ch, {int(dev['sample_rate'])}Hz){marker}")

    print(f"\n  ★ = default device")
    print(f"\n  To use a specific device: claudia --device <index>\n")


def first_run_setup(config: ClaudiaConfig):
    """Interactive first-run setup."""
    print("Welcome to Claudia Chatterley! Let's get you set up.\n")

    # Show available devices
    list_devices()

    # Check for Groq API key
    import os
    groq_key = os.environ.get("CLAUDIA_GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")
    if groq_key:
        print(f"  Found Groq API key in environment. Cloud transcription available.\n")
        config.transcription.groq_api_key = groq_key

    print("  Using local Whisper model (base, ~140MB). Downloading on first transcription...")
    print("  You can change settings later in ~/.claudia/config.json\n")

    # Pre-download the model
    print("  Downloading Whisper model... (this only happens once)")
    try:
        from claudia.transcriber import Transcriber
        t = Transcriber(config.transcription)
        t.preload_model()
        print("  ✓ Model downloaded successfully!\n")
    except Exception as e:
        print(f"  ⚠ Model download failed: {e}")
        print("    The model will be downloaded on first transcription.\n")

    config.first_run = False
    config.ensure_dirs()
    config.save()
    print("  Configuration saved to ~/.claudia/config.json\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="claudia",
        description="Claudia Chatterley — Voice-to-text for Claude Cowork and any macOS app.",
    )
    parser.add_argument(
        "--version", action="version", version=f"claudia {__version__}"
    )
    parser.add_argument(
        "--devices", action="store_true", help="List available microphones"
    )
    parser.add_argument(
        "--device", type=int, default=None, help="Audio input device index"
    )
    parser.add_argument(
        "--engine", choices=["local", "groq"], default=None,
        help="Transcription engine (default: local)"
    )
    parser.add_argument(
        "--model", choices=["tiny", "base", "small", "medium", "large-v3"],
        default=None, help="Whisper model size (default: base)"
    )
    parser.add_argument(
        "--groq-key", default=None, help="Groq API key for cloud transcription"
    )
    parser.add_argument(
        "--language", default=None, help="Language code (default: en, use 'auto' for detection)"
    )
    parser.add_argument(
        "--no-widget", action="store_true", help="Don't show floating mic widget"
    )
    parser.add_argument(
        "--no-paste", action="store_true",
        help="Don't auto-paste (copy to clipboard only)"
    )
    parser.add_argument(
        "--no-chime", action="store_true", help="Don't play chime after transcription"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging"
    )
    parser.add_argument(
        "--setup", action="store_true", help="Run first-time setup"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(verbose=args.verbose)

    # List devices mode
    if args.devices:
        list_devices()
        return

    # Load config
    config = ClaudiaConfig.load()
    config.ensure_dirs()

    # Apply CLI overrides
    if args.device is not None:
        config.audio.input_device = args.device
    if args.engine:
        config.transcription.engine = args.engine
    if args.model:
        config.transcription.model_size = args.model
    if args.groq_key:
        config.transcription.groq_api_key = args.groq_key
    if args.language:
        lang = args.language if args.language != "auto" else None
        config.transcription.language = lang
    if args.no_widget:
        config.ui.show_floating_widget = False
    if args.no_paste:
        config.ui.auto_paste = False
    if args.no_chime:
        config.ui.play_chime = False

    # First run or explicit setup
    if config.first_run or args.setup:
        first_run_setup(config)

    # Check platform
    if sys.platform != "darwin":
        print("⚠️  Claudia Chatterley is designed for macOS.")
        print("   Some features (menubar, floating widget, paste simulation) may not work.")
        print("   Transcription will still work — text will be copied to clipboard.\n")

    # Print banner and start
    print_banner()

    from claudia.app import ClaudiaApp
    app = ClaudiaApp(config)

    try:
        app.run()
    except KeyboardInterrupt:
        print("\n\n👋 Claudia Chatterley shutting down. Goodbye!")
        stats = app.get_stats()
        if stats["transcriptions"] > 0:
            print(
                f"   Session: {stats['transcriptions']} transcriptions, "
                f"{stats['total_audio_seconds']:.0f}s of audio processed."
            )


if __name__ == "__main__":
    main()
