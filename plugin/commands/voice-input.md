---
description: Dictate text using voice — speak instead of type for 3x faster input
argument-hint: "[optional: language code like 'en', 'fr', 'de']"
---

# Voice Input Mode

You are helping a user who wants to speak instead of type. The Claudia Chatterley companion app is running on their Mac and handles the actual audio capture and transcription.

## What to do

1. Tell the user to click the floating 🎤 mic button (or use their configured hotkey)
2. Explain that their speech will be transcribed and pasted into the input field
3. Remind them they can edit the text before pressing Enter

## If the companion app is not running

Tell the user:
- Open a terminal and run: `claudia`
- Or if not installed: `pip install claudia-chatterley && claudia`

## Language support

If the user specified a language code, note that they should configure it:
- `claudia --language <code>` (e.g., `claudia --language es` for Spanish)
- Or set `CLAUDIA_LANGUAGE=<code>` in their environment
