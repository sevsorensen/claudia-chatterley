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
    1. User clicks mic widget → starts recording (saves frontmost app)
    2. User clicks again → stops recording
    3. Audio is transcribed by Whisper
    4. Focus is returned to the original app
    5. Transcribed text is pasted into that window

    Usage:
        config = ClaudiaConfig.load()
        app = ClaudiaApp(config)
        app.run()  # Blocks — runs the macOS event loop
    """

    # Bundle IDs that belong to Claudia's own process — never treat these as targets
    _OWN_BUNDLES = {"org.python.python", "com.apple.terminal", "com.googlecode.iterm2"}

    def __init__(self, config: ClaudiaConfig):
        self.config = config
        self._is_recording = False
        self._transcription_count = 0
        self._total_audio_seconds = 0.0

        # Continuous focus tracker: always knows the last non-Claudia app
        self._last_external_app = None  # NSRunningApplication
        self._target_app = None         # Frozen at recording start

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

        # CRITICAL: Initialize NSApplication FIRST — macOS requires this
        # before creating any windows or UI elements
        try:
            from AppKit import NSApplication
            NSApplication.sharedApplication()
            logger.info("NSApplication initialized")
        except ImportError:
            logger.warning("AppKit not available — UI may not work")

        # Start tracking which app has focus so we always know where to paste
        self._start_focus_tracker()

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

        # Create and show the floating widget (NSApplication must exist first)
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

    def _start_focus_tracker(self):
        """
        Register for macOS workspace notifications so we continuously track
        the last non-Claudia app that had focus. This runs on the main thread's
        run loop via NSNotificationCenter — no polling needed.
        """
        try:
            from AppKit import NSWorkspace, NSNotificationCenter

            center = NSWorkspace.sharedWorkspace().notificationCenter()
            center.addObserverForName_object_queue_usingBlock_(
                "NSWorkspaceDidActivateApplicationNotification",
                None,  # any object
                None,  # deliver on posting thread (main run loop)
                self._on_app_activated,
            )

            # Seed with whatever is frontmost right now
            front = NSWorkspace.sharedWorkspace().frontmostApplication()
            if front and not self._is_own_process(front):
                self._last_external_app = front

            logger.info("Focus tracker started — will remember last active app")
        except Exception as e:
            logger.warning("Could not start focus tracker: %s", e)

    def _on_app_activated(self, notification):
        """Called by macOS every time a different app comes to the foreground."""
        try:
            app = notification.userInfo()["NSWorkspaceApplicationKey"]
            if not self._is_own_process(app):
                self._last_external_app = app
                logger.debug("Focus tracker: now tracking %s (%s)",
                             app.localizedName(), app.bundleIdentifier())
        except Exception as e:
            logger.debug("Focus tracker notification error: %s", e)

    def _is_own_process(self, app) -> bool:
        """Return True if the given NSRunningApplication belongs to Claudia."""
        try:
            bundle = (app.bundleIdentifier() or "").lower()
            # Check known bundle IDs for Terminal, Python, iTerm
            if bundle in self._OWN_BUNDLES:
                return True
            # Also check by PID — if the app's PID matches ours, it's us
            import os
            if app.processIdentifier() == os.getpid():
                return True
            return False
        except Exception:
            return False

    def _restore_target_app(self):
        """Bring the target app back to front so paste lands in the right window."""
        if self._target_app is None:
            logger.debug("No target app to restore")
            return
        try:
            self._target_app.activateWithOptions_(1 << 1)  # NSApplicationActivateIgnoringOtherApps
            logger.debug("Restored focus to: %s", self._target_app.localizedName())
            time.sleep(0.2)  # Let the window come to front before pasting
        except Exception as e:
            logger.warning("Could not restore target app: %s", e)

    def _start_recording(self):
        """Begin capturing audio."""
        # Freeze the current external app as our paste target
        self._target_app = self._last_external_app
        if self._target_app:
            logger.info("Will paste into: %s", self._target_app.localizedName())
        else:
            logger.warning("No target app detected — text will go to clipboard only")

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

            # Restore focus to the app the user was in before clicking the mic
            self._restore_target_app()

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
