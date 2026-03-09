---
description: View and configure Claudia Chatterley voice settings
---

# Voice Settings

Display the current Claudia Chatterley configuration and help the user modify settings.

## Configuration file

Settings are stored in `~/.claudia/config.json`. Show the user their current settings and explain each option.

## Key settings

### Transcription Engine
- `local` (default): Uses Whisper locally. Private, no API key needed.
- `groq`: Uses Groq Whisper API. Faster and more accurate but requires API key.

### Whisper Model Size
- `tiny` (39MB): Fastest, basic accuracy
- `base` (140MB): Good balance (default)
- `small` (461MB): Better accuracy
- `medium` (1.5GB): Great accuracy
- `large-v3` (3GB): Best accuracy

### Language
- `en` (default): English
- `auto` or `null`: Auto-detect language
- Any ISO language code: `fr`, `de`, `es`, `ja`, etc.

### UI Options
- `show_floating_widget`: Show/hide the floating mic button
- `play_chime`: Play a sound when transcription is ready
- `auto_paste`: Automatically paste text (vs. clipboard only)

## How to modify

Tell the user they can either:
1. Edit `~/.claudia/config.json` directly
2. Use CLI flags: `claudia --engine groq --model small --language auto`
3. Set environment variables: `export CLAUDIA_ENGINE=groq`
