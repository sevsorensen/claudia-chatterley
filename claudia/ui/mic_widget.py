"""
Floating microphone widget for macOS.

A small, always-on-top, draggable circular button that serves as the
primary interface for Claudia Chatterley. Click to start recording,
click again to stop. Color indicates state:

  Gray   = Idle (ready to record)
  Red    = Recording (listening to you)
  Blue   = Processing (transcribing your speech)
  Green  = Done (text has been pasted) — flashes briefly

Built with PyObjC for native macOS rendering. The widget floats above
all other windows and can be dragged to any position on screen.
"""

import logging
import math
import threading
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger(__name__)

try:
    import objc
    from AppKit import (
        NSApplication,
        NSWindow,
        NSView,
        NSColor,
        NSBezierPath,
        NSFont,
        NSAttributedString,
        NSFontAttributeName,
        NSForegroundColorAttributeName,
        NSMutableParagraphStyle,
        NSParagraphStyleAttributeName,
        NSCenterTextAlignment,
        NSWindowStyleMaskBorderless,
        NSBackingStoreBuffered,
        NSTimer,
        NSEvent,
        NSMakeRect,
    )
    from Quartz import (
        CGEventCreateKeyboardEvent,
        CGEventPost,
        CGEventSetFlags,
        kCGHIDEventTap,
        kCGEventFlagMaskCommand,
    )
    # NSFloatingWindowLevel constant
    NSFloatingWindowLevel = 3
    HAS_PYOBJC = True
except ImportError:
    HAS_PYOBJC = False
    logger.warning("PyObjC not available — falling back to terminal-only mode")


class WidgetState(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    PROCESSING = "processing"
    DONE = "done"


# Color palette
STATE_COLORS = {
    WidgetState.IDLE: (0.55, 0.55, 0.60, 0.85),       # Slate gray
    WidgetState.RECORDING: (0.90, 0.20, 0.20, 0.95),   # Vivid red
    WidgetState.PROCESSING: (0.20, 0.45, 0.90, 0.95),  # Blue
    WidgetState.DONE: (0.20, 0.80, 0.40, 0.95),        # Green
}

# Unicode mic symbols
STATE_ICONS = {
    WidgetState.IDLE: "\U0001F3A4",        # 🎤
    WidgetState.RECORDING: "\u23FA",        # ⏺ (record symbol)
    WidgetState.PROCESSING: "\u23F3",       # ⏳
    WidgetState.DONE: "\u2714",             # ✔
}


class MicWidgetController:
    """
    Controls the floating microphone widget.

    This is a high-level controller that manages the widget state
    and delegates to the actual PyObjC or fallback implementation.

    Usage:
        def on_toggle():
            if recording:
                stop_recording()
            else:
                start_recording()

        widget = MicWidgetController(on_toggle=on_toggle)
        widget.set_state(WidgetState.RECORDING)
        widget.set_level(0.5)  # Audio level meter
    """

    def __init__(
        self,
        on_toggle: Optional[Callable[[], None]] = None,
        x: int = 50,
        y: int = 200,
        size: int = 48,
    ):
        self.on_toggle = on_toggle or (lambda: None)
        self.x = x
        self.y = y
        self.size = size
        self._state = WidgetState.IDLE
        self._level = 0.0
        self._widget = None

    @property
    def state(self) -> WidgetState:
        return self._state

    def set_state(self, state: WidgetState):
        """Update widget visual state."""
        self._state = state
        if self._widget:
            self._widget.set_state(state)

        # Auto-revert from DONE to IDLE after 1 second
        if state == WidgetState.DONE:
            threading.Timer(1.0, lambda: self.set_state(WidgetState.IDLE)).start()

    def set_level(self, level: float):
        """Update audio level meter (0.0 to 1.0)."""
        self._level = max(0.0, min(1.0, level))
        if self._widget:
            self._widget.set_level(self._level)

    def show(self):
        """Show the floating widget."""
        if HAS_PYOBJC:
            self._create_native_widget()
        else:
            logger.info(
                "Floating widget not available (no PyObjC). "
                "Use menubar icon or global hotkey instead."
            )

    def hide(self):
        """Hide the floating widget."""
        if self._widget:
            self._widget.hide()

    def _create_native_widget(self):
        """Create the native PyObjC floating window."""
        # This will be created from the main app thread
        self._widget = NativeMicWidget(
            on_click=self.on_toggle,
            x=self.x,
            y=self.y,
            size=self.size,
        )


if HAS_PYOBJC:

    class MicView(NSView):
        """Custom NSView that draws the microphone button."""

        def initWithFrame_(self, frame):
            self = objc.super(MicView, self).initWithFrame_(frame)
            if self is not None:
                self._state = WidgetState.IDLE
                self._level = 0.0
                self._pulse_phase = 0.0
            return self

        def drawRect_(self, rect):
            """Draw the circular mic button with state-dependent colors."""
            bounds = self.bounds()
            cx = bounds.size.width / 2
            cy = bounds.size.height / 2
            radius = min(cx, cy) - 2

            # Draw shadow
            shadow_path = NSBezierPath.bezierPathWithOvalInRect_(
                NSMakeRect(cx - radius + 1, cy - radius - 1, radius * 2, radius * 2)
            )
            NSColor.colorWithCalibratedRed_green_blue_alpha_(0, 0, 0, 0.2).set()
            shadow_path.fill()

            # Draw main circle
            r, g, b, a = STATE_COLORS.get(self._state, STATE_COLORS[WidgetState.IDLE])
            circle_path = NSBezierPath.bezierPathWithOvalInRect_(
                NSMakeRect(cx - radius, cy - radius, radius * 2, radius * 2)
            )
            NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, a).set()
            circle_path.fill()

            # Draw pulse ring when recording (based on audio level)
            if self._state == WidgetState.RECORDING and self._level > 0.05:
                pulse_radius = radius + 4 + (self._level * 8)
                pulse_path = NSBezierPath.bezierPathWithOvalInRect_(
                    NSMakeRect(
                        cx - pulse_radius, cy - pulse_radius,
                        pulse_radius * 2, pulse_radius * 2,
                    )
                )
                pulse_path.setLineWidth_(2.0)
                alpha = 0.3 + (self._level * 0.4)
                NSColor.colorWithCalibratedRed_green_blue_alpha_(r, g, b, alpha).set()
                pulse_path.stroke()

            # Draw icon text
            icon = STATE_ICONS.get(self._state, STATE_ICONS[WidgetState.IDLE])
            font_size = radius * 0.8
            font = NSFont.systemFontOfSize_(font_size)

            paragraph = NSMutableParagraphStyle.alloc().init()
            paragraph.setAlignment_(NSCenterTextAlignment)

            attrs = {
                NSFontAttributeName: font,
                NSForegroundColorAttributeName: NSColor.whiteColor(),
                NSParagraphStyleAttributeName: paragraph,
            }
            attr_str = NSAttributedString.alloc().initWithString_attributes_(icon, attrs)
            text_size = attr_str.size()
            text_rect = NSMakeRect(
                cx - text_size.width / 2,
                cy - text_size.height / 2,
                text_size.width,
                text_size.height,
            )
            attr_str.drawInRect_(text_rect)

        def mouseDown_(self, event):
            """Handle click — toggle recording."""
            if hasattr(self, '_on_click') and self._on_click:
                self._on_click()

        def mouseDragged_(self, event):
            """Allow dragging the widget."""
            window = self.window()
            if window:
                screen_loc = NSEvent.mouseLocation()
                origin = NSPoint(
                    screen_loc.x - self.bounds().size.width / 2,
                    screen_loc.y - self.bounds().size.height / 2,
                )
                window.setFrameOrigin_(origin)

        def isFlipped(self):
            return False

        def acceptsFirstMouse_(self, event):
            return True

    class NativeMicWidget:
        """PyObjC floating window containing the mic button."""

        def __init__(self, on_click, x=50, y=200, size=48):
            self.size = size

            # Create borderless, transparent window
            frame = NSMakeRect(x, y, size + 8, size + 8)
            self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
                frame,
                NSWindowStyleMaskBorderless,
                NSBackingStoreBuffered,
                False,
            )

            self.window.setLevel_(3)  # Floating window level
            self.window.setOpaque_(False)
            self.window.setBackgroundColor_(NSColor.clearColor())
            self.window.setHasShadow_(False)
            self.window.setIgnoresMouseEvents_(False)
            self.window.setMovableByWindowBackground_(True)
            self.window.setCollectionBehavior_(
                1 << 0 | 1 << 1  # canJoinAllSpaces | participatesInCycle
            )

            # Create the mic view
            view_frame = NSMakeRect(0, 0, size + 8, size + 8)
            self.view = MicView.alloc().initWithFrame_(view_frame)
            self.view._on_click = on_click
            self.window.setContentView_(self.view)

            # Show it
            self.window.orderFront_(None)

        def set_state(self, state: WidgetState):
            """Update the visual state."""
            self.view._state = state
            self.view.setNeedsDisplay_(True)

        def set_level(self, level: float):
            """Update the audio level indicator."""
            self.view._level = level
            self.view.setNeedsDisplay_(True)

        def hide(self):
            """Hide the widget."""
            self.window.orderOut_(None)

        def show(self):
            """Show the widget."""
            self.window.orderFront_(None)
