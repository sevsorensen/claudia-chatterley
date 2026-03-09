"""
macOS menubar integration for Claudia Chatterley.

Adds a microphone icon to the system menubar with a dropdown menu
for quick access to recording, settings, and quit.

Uses rumps for lightweight menubar app creation, with fallback to
PyObjC NSStatusBar if rumps is not available.
"""

import logging
import sys
import threading
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class MenubarApp:
    """
    Menubar icon with dropdown menu for Claudia Chatterley.

    The menubar icon serves as:
    1. Visual indicator of recording state (icon changes)
    2. Click target to toggle recording
    3. Dropdown menu for settings, device selection, quit
    """

    # Menu bar icon states (using SF Symbols or Unicode)
    ICON_IDLE = "\U0001F3A4"       # 🎤
    ICON_RECORDING = "\U0001F534"  # 🔴
    ICON_PROCESSING = "\u23F3"     # ⏳

    def __init__(
        self,
        on_toggle: Optional[Callable[[], None]] = None,
        on_quit: Optional[Callable[[], None]] = None,
        on_settings: Optional[Callable[[], None]] = None,
    ):
        self.on_toggle = on_toggle or (lambda: None)
        self.on_quit = on_quit or (lambda: None)
        self.on_settings = on_settings or (lambda: None)
        self._is_recording = False

    def run(self):
        """
        Start the menubar app. This blocks the main thread.

        Uses NSStatusBar directly via PyObjC for maximum control.
        """
        try:
            self._run_pyobjc()
        except ImportError:
            logger.error(
                "PyObjC is required for the menubar app. "
                "Install with: pip install pyobjc-framework-Cocoa"
            )
            sys.exit(1)

    def _run_pyobjc(self):
        """Run using PyObjC NSStatusBar."""
        from AppKit import (
            NSApplication,
            NSStatusBar,
            NSMenu,
            NSMenuItem,
            NSVariableStatusItemLength,
            NSImage,
            NSSize,
        )

        app = NSApplication.sharedApplication()

        # Create status bar item
        status_bar = NSStatusBar.systemStatusBar()
        self._status_item = status_bar.statusItemWithLength_(
            NSVariableStatusItemLength
        )
        self._status_item.setTitle_(self.ICON_IDLE)
        self._status_item.setHighlightMode_(True)

        # Build the dropdown menu
        menu = NSMenu.alloc().init()

        # Toggle recording item
        toggle_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Start Recording", "toggleRecording:", ""
        )
        toggle_item.setTarget_(self)
        self._toggle_item = toggle_item
        menu.addItem_(toggle_item)

        menu.addItem_(NSMenuItem.separatorItem())

        # Settings
        settings_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Settings...", "openSettings:", ","
        )
        settings_item.setTarget_(self)
        menu.addItem_(settings_item)

        # About
        about_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "About Claudia Chatterley", "showAbout:", ""
        )
        about_item.setTarget_(self)
        menu.addItem_(about_item)

        menu.addItem_(NSMenuItem.separatorItem())

        # Quit
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit Claudia", "quitApp:", "q"
        )
        quit_item.setTarget_(self)
        menu.addItem_(quit_item)

        self._status_item.setMenu_(menu)

        logger.info("Menubar app started")
        app.run()

    def toggleRecording_(self, sender):
        """Toggle recording state."""
        self.on_toggle()

    def openSettings_(self, sender):
        """Open settings."""
        self.on_settings()

    def showAbout_(self, sender):
        """Show about dialog."""
        from claudia import __version__
        logger.info("Claudia Chatterley v%s — Voice-to-text for Cowork", __version__)

    def quitApp_(self, sender):
        """Quit the application."""
        self.on_quit()
        from AppKit import NSApplication
        NSApplication.sharedApplication().terminate_(None)

    def set_recording(self, is_recording: bool):
        """Update menubar icon and menu text for recording state."""
        self._is_recording = is_recording
        if hasattr(self, "_status_item"):
            if is_recording:
                self._status_item.setTitle_(self.ICON_RECORDING)
                self._toggle_item.setTitle_("Stop Recording")
            else:
                self._status_item.setTitle_(self.ICON_IDLE)
                self._toggle_item.setTitle_("Start Recording")

    def set_processing(self):
        """Show processing indicator."""
        if hasattr(self, "_status_item"):
            self._status_item.setTitle_(self.ICON_PROCESSING)
