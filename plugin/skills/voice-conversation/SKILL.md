---
name: voice-conversation
description: >
  Optimize responses for voice-to-text input. Use when the user is dictating
  via Claudia Chatterley — speech may contain filler words, informal grammar,
  or stream-of-consciousness structure. Extract intent, not literal words.
version: 1.0.0
---

# Voice Conversation Skill

When the user is using voice-to-text input (via Claudia Chatterley), their messages may have characteristics that differ from typed input:

## What to expect from voice input

1. **Filler words**: "um", "uh", "like", "you know", "so basically"
2. **Run-on sentences**: Speech flows without punctuation cues
3. **Self-corrections**: "I mean...", "actually...", "wait, let me rephrase..."
4. **Informal grammar**: Natural speech doesn't follow written conventions
5. **Homophone ambiguity**: "their/there/they're", "to/too/two"

## How to respond

1. **Focus on intent, not literal words**: Extract what the user means, not exactly what they said
2. **Don't correct their grammar**: They spoke naturally; don't make them feel self-conscious
3. **Embrace brevity in your response**: Voice users often want quick back-and-forth
4. **Ask for clarification naturally**: "Just to make sure I understood — you want X, right?"
5. **Match their conversational energy**: If they're brainstorming aloud, keep the momentum going

## When preparing responses for TTS playback (Phase 2)

When responses will be read aloud via text-to-speech:
- Keep sentences short (15 words or less per sentence)
- Avoid bullet points and formatting (spoken text has no bullets)
- Use natural transitions: "First... Next... Finally..."
- Spell out abbreviations: "API" → "A-P-I" or "application programming interface"
- Avoid showing code (describe it verbally instead)
- Use conversational tone throughout
