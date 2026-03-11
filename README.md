# 🎤 Claudia Chatterley (Voice-to-Text)

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
│  Whisper "small" (local)     │
│  ~460MB model, Apple Silicon │
│  + vocabulary hints for      │
│    your proper nouns         │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  Focus restored to your app  │
│  Text pasted automatically   │
│  Works everywhere on macOS   │
└──────────────────────────────┘
```

## Quick Start

### Recommended: One-Command Install

This handles everything — Homebrew, Python 3.12, portaudio, pipx, and Claudia itself. It asks before installing each piece.

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/sevsorensen/claudia-chatterley/main/setup.sh)"
```

> **Why this format?** The `/bin/bash -c "$(curl ...)"` pattern downloads the script as a string *first*, then runs it. This keeps your keyboard input working so the installer can ask you yes/no questions. (This is the same pattern Homebrew's own installer uses.)

### From Source (developers)

```bash
git clone https://github.com/sevsorensen/claudia-chatterley.git
cd claudia-chatterley
chmod +x setup.sh && ./setup.sh
```

### Manual Install (if you already have Python 3.10+ and Homebrew)

```bash
brew install portaudio pipx
pipx install git+https://github.com/sevsorensen/claudia-chatterley.git
claudia
```

> **Note:** Claudia is installed via `pipx` (not `pip`) because Homebrew's Python 3.12 uses PEP 668 "externally managed environments" that block system-wide pip installs. pipx creates an isolated virtual environment automatically.

On first run, Claudia downloads the Whisper "small" model (~460MB). After that, everything runs locally.

## What the Installer Actually Does

We tested the installer on a stock MacBook Pro with only Python 3.9 and no Homebrew. Here's exactly what it checks and installs:

| Step | What It Checks | If Missing… |
|------|---------------|-------------|
| 1 | Homebrew | Installs it (requires your Mac password, takes 2–5 min) |
| 2 | Python 3.10+ | Installs Python 3.12 via Homebrew (your old 3.9 stays untouched) |
| 3 | portaudio | Installs via Homebrew (a few seconds) |
| 4 | pipx | Installs via Homebrew (the safe way to install Python CLI apps) |
| 5 | Claudia | Installs from GitHub via pipx into its own virtual environment |

**After Homebrew installs:** If you see "command not found: brew", close Terminal completely (Cmd+Q) and open a new window. Homebrew needs a fresh shell to be recognized.

## Requirements

- **macOS** (Apple Silicon recommended for fastest transcription)
- **Homebrew** — free package manager for macOS ([brew.sh](https://brew.sh))
- **Python 3.10+** — your Mac probably has 3.9; the installer adds 3.12 alongside it
- **portaudio** — audio library for microphone access
- **Accessibility permission** — System Settings > Privacy & Security > Accessibility (required for auto-paste into other apps)

## Accessibility Permission (Important!)

Claudia needs Accessibility permission to simulate Cmd+V and paste text into other apps. Without it, transcription works but the text only goes to your clipboard — it won't auto-paste.

1. Open **System Settings** → **Privacy & Security** → **Accessibility**
2. Click the **+** button
3. Add **Terminal** (or whatever terminal app you use to launch `claudia`)
4. Make sure the toggle is **ON** (blue)

**How you'll know it's missing:** Claudia will transcribe your speech (you'll see it in the terminal log) but the text won't appear in your target app. The terminal will say "Auto-paste failed."

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
claudia --model small      # Default — good accuracy, good speed
claudia --model base       # Faster, less accurate
claudia --model medium     # Slower, more accurate
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

> **Privacy note:** When using Groq, your audio is sent to their servers. If you do sensitive work and want everything local, stick with the default `local` engine.

## Vocabulary Hints (Teach Claudia Your Words)

Whisper sometimes misspells proper nouns it hasn't seen before. Claudia lets you seed a vocabulary list so the model expects your specific words.

Default vocabulary (ships with Claudia):
```
Severin, Sorensen, ePraxis, Arete, AreteCoach, AIWhisperer, Claudia Chatterley, Cowork, Vistage
```

**To add your own words:** Edit `~/.claudia/config.json` and add to the `"vocabulary"` array:

```json
{
  "transcription": {
    "vocabulary": [
      "Severin", "Sorensen", "ePraxis", "Arete", "AreteCoach",
      "AIWhisperer", "Claudia Chatterley", "Cowork", "Vistage",
      "YourCompany", "YourProduct", "AnyProperNoun"
    ]
  }
}
```

No reinstall needed — just restart `claudia`.

## Configuration

Settings are stored in `~/.claudia/config.json`:

```json
{
  "transcription": {
    "engine": "local",
    "model_size": "small",
    "language": "en",
    "vocabulary": ["Severin", "Sorensen", "ePraxis", "..."],
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
| base | 140MB | Fast | Good | Fast drafts where speed matters most |
| **small** | **461MB** | **Moderate** | **Better** | **Default — best balance of speed and accuracy** |
| medium | 1.5GB | Slower | Great | Professional transcription |
| large-v3 | 3GB | Slowest | Best | Maximum accuracy |

## How It Compares

| Feature | Claudia Chatterley | Dictanote (Chrome) | macOS Dictation |
|---------|-------------------|-------------------|-----------------|
| Works in Cowork | ✅ | ❌ | ⚠️ Limited |
| Works system-wide | ✅ | ❌ (Chrome only) | ✅ |
| Fully local/private | ✅ | ❌ (cloud) | ✅ (on Apple Silicon) |
| Click-to-toggle mic | ✅ | ✅ | ❌ (keyboard shortcut) |
| Custom vocabulary | ✅ | N/A | ❌ |
| Open source | ✅ | ❌ | ❌ |
| Cloud option | ✅ (Groq) | Built-in | ❌ |

## Troubleshooting

These are real problems we hit during installation and testing, with real fixes.

### "command not found: brew" after Homebrew installs
Close Terminal completely (Cmd+Q) and open a new window. Homebrew adds itself to your PATH, but only in new shell sessions. Then re-run the install command.

### "externally-managed-environment" error from pip
Homebrew's Python 3.12 blocks system-wide pip installs (PEP 668). This is by design. Use `pipx` instead, which creates an isolated environment:
```bash
brew install pipx
pipx install git+https://github.com/sevsorensen/claudia-chatterley.git
```

### "Auto-paste failed" or text goes to Terminal instead of your app
Two things to check:
1. **Accessibility permission** — System Settings > Privacy & Security > Accessibility. Add Terminal and toggle it ON.
2. **Focus tracking** — Claudia remembers which app you were in *before* clicking the mic and returns focus there after transcription. Make sure you click into your target app (Chrome, Cowork, etc.) before clicking the mic.

### Whisper misspells your name or company
Add your proper nouns to the vocabulary list in `~/.claudia/config.json` (see "Vocabulary Hints" section above). Restart `claudia` to pick up the changes.

### "No input devices found"
Install portaudio: `brew install portaudio`

### Transcription is slow
- The `small` model (default) takes 1–3 seconds on Apple Silicon for a 10-second clip
- Use `base` or `tiny` for faster results: `claudia --model base`
- Or switch to Groq cloud: `claudia --engine groq`
- Apple Silicon Macs are significantly faster than Intel

### "Python 3.10+ required" (found 3.9)
Your Mac has the old system Python. Install a newer one alongside it:
```bash
brew install python@3.12
```
This does NOT replace your old Python — it adds a new one. Then reinstall Claudia.

### Updating Claudia
To get the latest version from GitHub:
```bash
pipx install --force git+https://github.com/sevsorensen/claudia-chatterley.git
```

If you changed the default model size or other settings, and the old `config.json` is overriding your new defaults:
```bash
rm ~/.claudia/config.json
claudia
```
This triggers first-run setup with the latest defaults.

## Privacy & Security

Claudia Chatterley is designed with privacy as a core principle.

**What Claudia records:** Audio from your microphone, only while you hold the record button (red mic). Claudia does not listen in the background.

**Where your audio goes:** Processed locally on your Mac by Whisper. Audio is held in memory during transcription (~1-3 seconds), then permanently discarded. No audio is saved to disk, transmitted over the network, or retained in any form.

**What Claudia does NOT do:**
- Does not record continuously or in the background
- Does not send data to any server (unless you opt into Groq cloud)
- Does not open any network ports or listen for connections
- Does not collect telemetry, analytics, or usage data
- Does not access other applications' content, URLs, or documents

**Permissions:** Claudia requires Microphone access (to hear you) and Accessibility permission (to paste text via Cmd+V). Both require your explicit approval in System Settings. See [SECURITY.md](SECURITY.md) for full details.

**Groq cloud option:** If you choose `--engine groq`, audio is sent to Groq's servers for transcription. This is opt-in only and clearly marked. The default engine is fully local.

## Roadmap

- [x] **v0.1** — Voice-to-text with floating mic widget
- [x] **v0.1.1** — Focus tracking, vocabulary hints, "small" model default
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
