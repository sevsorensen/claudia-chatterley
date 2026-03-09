"""
Text injector — pastes transcribed text into the active application.

Uses the macOS clipboard (pasteboard) and simulates Cmd+V to paste text
into whatever window has focus. This works universally across all macOS apps
including Cowork, Chrome, Terminal, Notes, etc.

The approach:
  1. Save the user's current clipboard contents
  2. Place transcribed text on the clipboard
  3. Simulate Cmd+V keystroke via CGEvent
  4. Restore the original clipboard contents (after a brief delay)
"""

import logging
import subprocess
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)


# CGEvent key codes
_K_V = 0x09  # 'v' key
_K_CMD = 0x37  # Command key

# Event types
_KEY_DOWN = 0x0A  # kCGEventKeyDown
_KEY_UP = 0x0B  # kCGEventKeyUp


class TextInjector:
    """
    Injects text into the active application via clipboard + Cmd+V.

    Usage:
        injector = TextInjector()
        injector.inject("Hello, this is transcribed text!")
    """

    def __init__(self, auto_paste: bool = True, restore_clipboard: bool = True):
        """
        Args:
            auto_paste: If True, simulate Cmd+V after copying. If False, only copy to clipboard.
            restore_clipboard: If True, restore original clipboard after a delay.
        """
        self.auto_paste = auto_paste
        self.restore_clipboard = restore_clipboard
        self._restore_delay = 2.0  # seconds to wait before restoring clipboard

    def inject(self, text: str) -> bool:
        """
        Inject text into the active application.

        Args:
            text: The text to inject.

        Returns:
            True if injection succeeded, False otherwise.
        """
        if not text:
            logger.debug("Empty text, nothing to inject")
            return False

        try:
            # Save current clipboard if we'll restore it later
            original_clipboard = None
            if self.restore_clipboard:
                original_clipboard = self._get_clipboard()

            # Place text on clipboard
            self._set_clipboard(text)
            logger.debug("Text copied to clipboard (%d chars)", len(text))

            if self.auto_paste:
                # Brief pause to ensure clipboard is ready
                time.sleep(0.05)

                # Simulate Cmd+V
                self._simulate_paste()
                logger.info("Text pasted into active window (%d chars)", len(text))

            # Restore original clipboard in background after delay
            if self.restore_clipboard and original_clipboard is not None:
                threading.Timer(
                    self._restore_delay,
                    self._set_clipboard,
                    args=[original_clipboard],
                ).start()

            return True

        except Exception as e:
            logger.error("Text injection failed: %s", e)
            return False

    def _get_clipboard(self) -> Optional[str]:
        """Get current clipboard text content."""
        try:
            result = subprocess.run(
                ["pbpaste"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            return result.stdout if result.returncode == 0 else None
        except Exception:
            return None

    def _set_clipboard(self, text: str):
        """Set clipboard text content using pbcopy."""
        try:
            subprocess.run(
                ["pbcopy"],
                input=text,
                text=True,
                timeout=2,
                check=True,
            )
        except Exception as e:
            logger.error("Failed to set clipboard: %s", e)
            raise

    def _simulate_paste(self):
        """
        Simulate Cmd+V keystroke using PyObjC CGEvent API.

        This is the most reliable way to simulate keyboard input on macOS,
        as it works with all applications including Electron apps (Cowork).
        """
        try:
            import Quartz

            # Create a Cmd+V key down event
            event_down = Quartz.CGEventCreateKeyboardEvent(None, _K_V, True)
            Quartz.CGEventSetFlags(event_down, Quartz.kCGEventFlagMaskCommand)

            # Create a Cmd+V key up event
            event_up = Quartz.CGEventCreateKeyboardEvent(None, _K_V, False)
            Quartz.CGEventSetFlags(event_up, Quartz.kCGEventFlagMaskCommand)

            # Post the events
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, event_down)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, event_up)

            logger.debug("Cmd+V keystroke simulated via CGEvent")

        except ImportError:
            # Fallback: use AppleScript if PyObjC Quartz is not available
            logger.debug("PyObjC Quartz not available, falling back to AppleScript")
            self._simulate_paste_applescript()

    def _simulate_paste_applescript(self):
        """Fallback: simulate Cmd+V using AppleScript."""
        script = 'tell application "System Events" to keystroke "v" using command down'
        try:
            subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                timeout=5,
                check=True,
            )
            logger.debug("Cmd+V keystroke simulated via AppleScript")
        except subprocess.CalledProcessError as e:
            logger.error("AppleScript paste failed: %s", e.stderr)
            raise RuntimeError(
                "Could not simulate paste. Ensure Claudia has Accessibility permissions "
                "in System Settings > Privacy & Security > Accessibility."
            )

    @staticmethod
    def check_accessibility_permission() -> bool:
        """
        Check if the app has macOS Accessibility permission.
        This is required for simulating keystrokes.
        """
        try:
            import Quartz
            # Try to create a test event — this will succeed even without permission,
            # but posting it will silently fail without Accessibility access.
            # The reliable check is via the Accessibility API:
            from ApplicationServices import AXIsProcessTrusted
            return AXIsProcessTrusted()
        except ImportError:
            # If we can't import, assume we need to check via AppleScript
            try:
                result = subprocess.run(
                    ["osascript", "-e", 'tell application "System Events" to return ""'],
                    capture_output=True,
                    timeout=5,
                )
                return result.returncode == 0
            except Exception:
                return False


def play_chime():
    """Play a subtle system chime to indicate transcription is ready."""
    try:
        # Use macOS built-in sound
        subprocess.Popen(
            ["afplay", "/System/Library/Sounds/Tink.aiff"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass  # Non-critical, silently skip if sound not available
