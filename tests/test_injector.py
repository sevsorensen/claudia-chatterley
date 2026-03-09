"""Tests for the text injector module."""

import pytest

from claudia.injector import TextInjector


class TestTextInjector:
    """Tests for TextInjector."""

    def test_inject_empty_string(self):
        """Empty string returns False (nothing to inject)."""
        injector = TextInjector(auto_paste=False)
        result = injector.inject("")
        assert result is False

    def test_inject_copies_to_clipboard(self):
        """Text is copied to clipboard (auto_paste=False to avoid keystroke simulation)."""
        injector = TextInjector(auto_paste=False, restore_clipboard=False)
        result = injector.inject("Hello from Claudia!")
        assert result is True

        # Verify clipboard contents (macOS only)
        import subprocess
        clip = subprocess.run(
            ["pbpaste"], capture_output=True, text=True, timeout=2
        )
        assert clip.stdout == "Hello from Claudia!"

    def test_inject_unicode(self):
        """Unicode text is handled correctly."""
        injector = TextInjector(auto_paste=False, restore_clipboard=False)
        result = injector.inject("Héllo wörld! 日本語テスト")
        assert result is True

    def test_inject_multiline(self):
        """Multi-line text is handled correctly."""
        injector = TextInjector(auto_paste=False, restore_clipboard=False)
        text = "Line one.\nLine two.\nLine three."
        result = injector.inject(text)
        assert result is True

    def test_inject_long_text(self):
        """Long text (>1000 chars) is handled correctly."""
        injector = TextInjector(auto_paste=False, restore_clipboard=False)
        text = "A" * 5000
        result = injector.inject(text)
        assert result is True


class TestAccessibility:
    """Tests for accessibility permission check."""

    def test_check_returns_bool(self):
        """check_accessibility_permission returns a boolean."""
        result = TextInjector.check_accessibility_permission()
        assert isinstance(result, bool)
