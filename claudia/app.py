"""
Main application — orchestrates the voice-to-text pipeline.

Pipeline:
  Mic Widget Click → AudioRecorder → Transcriber → TextInjector → Active App

This module wires together all components and manages the recording lifecycle.
"""

import logging
import sys
import threading
import time
from typing import Optional

from claudia.config import ClaudiaConfig
from claudia.recorder import AudioRecorder, RecorderState
from claudia.transcriber import Transcriber, TranscriptionResult
from claudia.injector import TextInjector, play_chime
from claudia.ui.mic_widget import MicWidgetController, WidgetState

logger = logging.getLogger(__name__)


class ClaudiaApp:
    """
    Main Claudia Chatterley application.

    Manages the voice-to-text pipeline:
    1. User clicks mic widget → starts recording
    2. User clicks again → stops recording
    3. Audio is transcribed by Whisper
    4. Transcribed text is pasted into the active window
    5. User reviews, edits if needed, presses Enter

    Usage:
        config = ClaudiaConfig.load()
        app = ClaudiaApp(config)
        app.run()  # Blocks — runs the macOS event loop
    """

    def __init__(self, config: ClaudiaConfig):
        self.config = config
        self._is_recording = False
        self._transcription_count = 0
        self._total_audio_seconds = 0.0

        # Initialize components
        self.recorder = AudioRecorder(
            config=config.audio,
            on_state_change=self._on_recorder_state_change,
            on_level=self._on_audio_level,
        )

        self.transcriber = Transcriber(config=config.transcription)

        self.injector = TextInjector(
            auto_paste=config.ui.auto_paste,
            restore_clipboard=True,
        )

        self.widget = MicWidgetController(
            on_toggle=self.toggle_recording,
            x=config.ui.widget_x,
            y=config.ui.widget_y,
            size=config.ui.widget_size,
        )

        self._menubar = None

    def run(self):
        """
        Start the application. This blocks the main thread.

        Starts the menubar app on the main thread (required by macOS)
        and creates the floating widget.
        """
        logger.info("Starting Claudia Chatterley v0.1.0")

        # Check accessibility permissions
        if not TextInjector.check_accessibility_permission():
            logger.warning(
                "Accessibility permission not granted. "
                "Claudia needs Accessibility access to paste text into other apps. "
                "Go to System Settings > Privacy & Security > Accessibility "
                "and add Claudia (or Terminal/Python)."
            )
            print(
                "\n⚠️  Claudia needs Accessibility permission to paste text.\n"
                "   Go to: System Settings > Privacy & Security > Accessibility\n"
                "   Add Terminal (or Python) to the allowed list.\n"
                "   Then restart Claudia.\n"
            )

        # Pre-load whisper model in background
        threading.Thread(
            target=self._preload_model,
            daemon=True,
            name="model-preloader",
        ).start()

        # Create and show the floating widget
        if self.config.ui.show_floating_widget:
            self.widget.show()
            logger.info("Floating mic widget shown at (%d, %d)", self.config.ui.widget_x, self.config.ui.widget_y)

        # Start the menubar app (blocks main thread)
        from claudia.ui.menubar import MenubarApp
        self._menubar = MenubarApp(
            on_toggle=self.toggle_recording,
            on_quit=self._on_quit,
        )

        print("🎤 Claudia Chatterley is running. Click the mic to start speaking!")
        print("   Menubar icon: 🎤 (idle) → 🔴 (recording) → ⏳ (transcribing)")
        print("   Quit: Ctrl+C or use the menubar menu.\n")

        self._menubar.run()

    def toggle_recording(self):
        """Toggle between recording and idle states."""
        if self._is_recording:
            self._stop_and_transcribe()
        else:
            self._start_recording()

    def _start_recording(self):
        """Begin capturing audio."""
        self._is_recording = True
        self.widget.set_state(WidgetState.RECORDING)
        if self._menubar:
            self._menubar.set_recording(True)

        self.recorder.start()
        logger.info("Recording started — speak now")

    def _stop_and_transcribe(self):
        """Stop recording and transcribe in background thread."""
        self._is_recording = False
        self.widget.set_state(WidgetState.PROCESSING)
        if self._menubar:
            self._menubar.set_processing()
            self._menubar.set_recording(False)

        # Run transcription in background to keep UI responsive
        threading.Thread(
            target=self._transcribe_and_inject,
            daemon=True,
            name="transcriber",
        ).start()

    def _transcribe_and_inject(self):
        """Background thread: stop recording, transcribe, and paste."""
        try:
            # Get audio from recorder
            audio_bytes = self.recorder.stop()

            if not audio_bytes:
                logger.info("No audio captured")
                self.widget.set_state(WidgetState.IDLE)
                return

            # Transcribe
            logger.info("Transcribing audio...")
            result = self.transcriber.transcribe(audio_bytes)

            if not result.text:
                logger.info("No speech detected in audio")
                self.widget.set_state(WidgetState.IDLE)
                return

            # Log result
            logger.info(
                "Transcribed (%.1fs audio → %.1fs processing, %s, confidence=%.2f): %s",
                result.duration_seconds,
                result.processing_time,
                result.engine,
                result.confidence,
                result.text[:100] + ("..." if len(result.text) > 100 else ""),
            )

            # Update stats
            self._transcription_count += 1
            self._total_audio_seconds += result.duration_seconds

            # Play chime if configured
            if self.config.ui.play_chime:
                play_chime()

            # Brief pause to let the chime play and user focus on target window
            time.sleep(0.1)

            # Inject text into active window
            success = self.injector.inject(result.text)

            if success:
                self.widget.set_state(WidgetState.DONE)
                logger.info("Text injected successfully")
            else:
                self.widget.set_state(WidgetState.IDLE)
                logger.warning("Text injection failed — text is on clipboard, paste manually")
                print(f"\n⚠️  Auto-paste failed. Text is on your clipboard — press Cmd+V to paste.")
                print(f"   Text: {result.text[:80]}...\n")

        except Exception as e:
            logger.error("Transcription pipeline failed: %s", e, exc_info=True)
            self.widget.set_state(WidgetState.IDLE)
            print(f"\n❌ Error: {e}\n")

    def _on_recorder_state_change(self, state: RecorderState):
        """Handle recorder state changes."""
        logger.debug("Recorder state: %s", state.value)

    def _on_audio_level(self, level: float):
        """Handle audio level updates (for the visual meter)."""
        self.widget.set_level(level)

    def _preload_model(self):
        """Pre-download and load the whisper model in background."""
        try:
            self.transcriber.preload_model()
        except Exception as e:
            logger.warning("Model preload failed (will retry on first transcription): %s", e)

    def _on_quit(self):
        """Clean up before quitting."""
        logger.info(
            "Claudia shutting down. Session stats: %d transcriptions, %.0f seconds of audio.",
            self._transcription_count,
            self._total_audio_seconds,
        )
        if self.recorder.state == RecorderState.RECORDING:
            self.recorder.cancel()

        # Save widget position for next launch
        self.config.first_run = False
        self.config.save()

    def get_stats(self) -> dict:
        """Get session statistics."""
        return {
            "transcriptions": self._transcription_count,
            "total_audio_seconds": self._total_audio_seconds,
            "engine": self.config.transcription.engine,
            "model": self.config.transcription.model_size,
        }
