# 🎤 Claudia Chatterley

**Voice-to-text companion for Claude Cowork and any macOS app.**

Speak instead of type. Click the floating mic, talk naturally, and your words appear as text wherever your cursor is — Cowork, Chrome, Terminal, anywhere on macOS.

**3–3.5× faster than typing. Zero cognitive load on spelling and grammar.**

---

## The Problem

Research shows that prompting by speaking is **3× to 3.5× more efficient** than typing. Typing forces dual-tasking — language production *and* motor execution — that reduces creative bandwidth. Voice-to-text tools like Dictanote work beautifully in Chrome, but they don't work inside **Claude Cowork**, which runs in a sandboxed environment.

Going back to typing after experiencing voice input is drudgery.

## The Solution

Claudia Chatterley is a lightweight macOS companion that works at the **operating system level**. It captures your voice, transcribes it locally using Whisper, and pastes the text into whatever app has focus. No cloud required. No API keys needed. Fully private.

```
Click 🎤 → Speak → Click 🎤 → Text appears → Edit if needed → Press Enter
```

## How It Works

```
┌──────────────────────────────┐
│  Floating Mic Button         │
│  Gray ● = Ready              │
│  Red  ● = Recording          │
│  Blue ● = Transcribing       │
│  Green ● = Done              │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  Whisper (local, private)    │
│  ~140MB model, Apple Silicon │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  Paste into active window    │
│  Works everywhere on macOS   │
└──────────────────────────────┘
```

## Quick Start

### Recommended: One-Command Install

This handles everything — Homebrew, Python, portaudio, and Claudia itself. It will ask before installing each piece.

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/sevsorensen/claudia-chatterley/main/setup.sh)"
```

### From Source (developers)

```bash
git clone https://github.com/severinsorensen/claudia-chatterley.git
cd claudia-chatterley
chmod +x setup.sh && ./setup.sh
```

### Manual Install (if you already have Python 3.10+ and Homebrew)

```bash
brew install portaudio
pip3 install claudia-chatterley
claudia
```

On first run, Claudia downloads the Whisper base model (~140MB). After that, everything runs locally.

## Requirements

The setup script installs these automatically, but for reference:

- **macOS** (Apple Silicon recommended for fastest transcription)
- **Homebrew** — free package manager for macOS ([brew.sh](https://brew.sh))
- **Python 3.10+** — the system Python on most Macs is 3.9; the installer adds 3.12 via Homebrew without touching your system Python
- **portaudio** — audio library for microphone access (installed via `brew install portaudio`)
- **Accessibility permission** — System Settings > Privacy & Security > Accessibility (required for auto-paste)

## Usage

### Basic

```bash
claudia                    # Start with floating mic widget
claudia --devices          # List available microphones
claudia --device 2         # Use a specific microphone
claudia --no-widget        # Menubar only (no floating button)
```

### Transcription Options

```bash
claudia --model small      # Use a larger model (more accurate, slower)
claudia --model tiny       # Use a smaller model (faster, less accurate)
claudia --language auto    # Auto-detect language
claudia --language es      # Transcribe in Spanish
```

### Cloud Transcription (Optional)

For faster, more accurate transcription, use the Groq Whisper API:

```bash
export CLAUDIA_GROQ_API_KEY=your-key-here
claudia --engine groq
```

Groq transcribes at 216× real-time — essentially instant. Get a free API key at [console.groq.com](https://console.groq.com).

## Configuration

Settings are stored in `~/.claudia/config.json`:

```json
{
  "transcription": {
    "engine": "local",
    "model_size": "base",
    "language": "en",
    "groq_api_key": null
  },
  "audio": {
    "sample_rate": 16000,
    "input_device": null
  },
  "ui": {
    "show_floating_widget": true,
    "widget_x": 50,
    "widget_y": 200,
    "play_chime": true,
    "auto_paste": true
  }
}
```

Environment variables override config file settings:

| Variable | Description |
|----------|-------------|
| `CLAUDIA_ENGINE` | `local` or `groq` |
| `CLAUDIA_MODEL_SIZE` | `tiny`, `base`, `small`, `medium`, `large-v3` |
| `CLAUDIA_LANGUAGE` | Language code (`en`, `fr`, `de`, etc.) |
| `CLAUDIA_GROQ_API_KEY` | Groq API key for cloud transcription |
| `CLAUDIA_AUTO_PASTE` | `true` or `false` |

## Whisper Model Sizes

| Model | Size | Speed | Accuracy | Best For |
|-------|------|-------|----------|----------|
| tiny | 39MB | Fastest | Basic | Quick notes, simple dictation |
| **base** | **140MB** | **Fast** | **Good** | **Default — best balance** |
| small | 461MB | Moderate | Better | Important documents |
| medium | 1.5GB | Slower | Great | Professional transcription |
| large-v3 | 3GB | Slowest | Best | Maximum accuracy |

## How It Compares

| Feature | Claudia Chatterley | Dictanote (Chrome) | macOS Dictation |
|---------|-------------------|-------------------|-----------------|
| Works in Cowork | ✅ | ❌ | ⚠️ Limited |
| Works system-wide | ✅ | ❌ (Chrome only) | ✅ |
| Fully local/private | ✅ | ❌ (cloud) | ✅ (on Apple Silicon) |
| Click-to-toggle mic | ✅ | ✅ | ❌ (keyboard shortcut) |
| Whisper accuracy | ✅ | N/A | Comparable |
| Open source | ✅ | ❌ | ❌ |
| Cloud option | ✅ (Groq) | Built-in | ❌ |

## Troubleshooting

### "Auto-paste failed"
Claudia needs Accessibility permission. Go to System Settings > Privacy & Security > Accessibility and add Terminal (or your Python environment) to the allowed list.

### "No input devices found"
Install portaudio: `brew install portaudio`

### Transcription is slow
- Use the `tiny` or `base` model for speed
- Or switch to Groq cloud: `claudia --engine groq`
- Apple Silicon Macs are significantly faster than Intel

### Text appears in wrong window
Claudia pastes into whatever window has focus when transcription finishes. Make sure your target window (Cowork, etc.) is focused before clicking the mic.

## Roadmap

- [x] **v0.1** — Voice-to-text with floating mic widget
- [ ] **v0.2** — Global hotkey support (Cmd+Shift+Space)
- [ ] **v0.3** — Cowork plugin integration (MCP server)
- [ ] **v0.4** — Two-way voice conversation ("Claudia Chatterley Mode")
- [ ] **v0.5** — Voice selection (accent, gender, speed) for TTS
- [ ] **v1.0** — Stable release with full Cowork plugin

## Philosophy

> "Typing forces the prefrontal cortex into dual-tasking when it should be free for ideation. What AI truly needs is the *intent* of the prompter — then be set free to do the work."

Claudia Chatterley is built on the conviction that the interface between human thought and AI capability should be as frictionless as possible. Voice is the most natural human output modality. Typing is a 150-year-old mechanical workaround. It's time to let it go.

## License

MIT License — Free to use, modify, and distribute.

## Author

**Severin Sorensen** — CEO & Executive Coach at [ePraxis LLC](https://epraxis.com), author of *The AI Whisperer* series. Built with Claude (Anthropic).

---

*Named affectionately after years of calling Claude "Claudia Chatterley" — because every good AI deserves a proper name.*
