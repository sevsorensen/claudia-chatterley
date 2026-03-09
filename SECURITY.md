# Security Policy

## What Permissions Does Claudia Use?

Claudia Chatterley requests two macOS permissions, both requiring explicit user approval:

### Microphone Access
- **What it does:** Captures audio from your microphone while you hold the record button.
- **When it's active:** Only while you are recording (red mic button). Claudia does not listen in the background.
- **Where the audio goes:** Processed locally by Whisper on your Mac. Audio is held in memory during transcription, then discarded. No audio is saved to disk, transmitted over the network, or retained after transcription.

### Accessibility Permission
- **What it does:** Allows Claudia to simulate a single keystroke (Cmd+V) to paste transcribed text into your active application.
- **What it does NOT do:** Claudia does not read other applications' UI, simulate other keystrokes, log keystrokes, or perform any Accessibility action other than the paste operation.
- **Why it's needed:** macOS requires Accessibility permission for any application that simulates keyboard input. The same permission is used by TextExpander, Alfred, Raycast, Keyboard Maestro, and other automation tools.

## Data Handling

| Data | Where It Goes | How Long It Exists |
|------|--------------|-------------------|
| Audio from microphone | Memory only (RAM) | Deleted after transcription (~1-3 seconds) |
| Temporary WAV file | System temp directory | Deleted immediately after Whisper processes it |
| Transcribed text | Clipboard (2 seconds), then pasted into your app | Clipboard restored to original contents after 2 seconds |
| Whisper model | ~/.claudia/models/ | Persistent (read-only binary, no user data) |
| Configuration | ~/.claudia/config.json | Persistent (user preferences only) |

**When using Groq cloud engine (opt-in only):** Audio is sent to Groq's servers for transcription. This is clearly marked in the README and requires you to explicitly set `--engine groq` and provide an API key.

## Network Activity

- **Default (local engine):** No network activity after initial model download from Hugging Face.
- **Groq engine (opt-in):** HTTPS requests to Groq's API. Audio is sent to their servers.
- **No telemetry, analytics, or phone-home.** Claudia never contacts any server unless you explicitly enable Groq.
- **No open ports.** Claudia does not start any servers or listen for incoming connections.

## Reporting a Vulnerability

If you discover a security vulnerability in Claudia Chatterley, please report it responsibly:

1. **Email:** sev@epraxis.com
2. **Subject line:** "Claudia Chatterley Security Issue"
3. **Please include:** Description of the vulnerability, steps to reproduce, and potential impact.

I will acknowledge receipt within 48 hours and aim to release a fix within 7 days for critical issues.

**Please do NOT open a public GitHub issue for security vulnerabilities.** Responsible disclosure protects all users.

## Scope

This security policy covers the official Claudia Chatterley repository at `github.com/sevsorensen/claudia-chatterley`. Forks, modifications, or derivative works are the responsibility of their respective maintainers and are not endorsed by the original author.

## Dependencies

Claudia uses well-established, widely audited Python packages: faster-whisper, sounddevice, numpy, PyObjC, pyperclip. All are installed in an isolated virtual environment via pipx.
