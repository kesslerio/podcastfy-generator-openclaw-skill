---
name: podcastfy-generator
description: Generate AI podcast-style audio conversations from URLs, YouTube videos, PDFs, or text topics. Creates NotebookLM-style two-host dialogues. Use when user asks to "create a podcast", "make an audio summary", "turn this article into a podcast", or wants content converted to audio discussion format.
homepage: https://github.com/kesslerio/podcastfy-generator-openclaw-skill
metadata: {"openclaw": {"emoji": "🎙️", "requires": {"bins": ["ffmpeg", "uv"], "env": ["OPENAI_API_KEY", "GEMINI_API_KEY"]}, "primaryEnv": "OPENAI_API_KEY", "optionalEnv": ["ELEVENLABS_API_KEY"]}}
---

# Podcastfy Generator 🎙️

Generate AI podcast-style audio conversations from any content. Creates engaging two-host dialogues similar to Google NotebookLM's Audio Overview feature.

## Capabilities

- **URLs** → Fetch article content, generate podcast discussion
- **YouTube** → Extract transcript, create audio summary
- **PDFs** → Parse document, synthesize key points as dialogue
- **Text/Topics** → Generate podcast from plain text or topic prompts
- **Multi-lingual** → English, German, French, Spanish (auto-detect or specify)
- **Custom Identity** → Name the podcast, name the hosts, pick their voices

## Quick Examples

```
"Create a podcast about this article: https://example.com/tech-news"
"Turn this YouTube video into a podcast: https://youtube.com/watch?v=..."
"Generate a German podcast discussing quantum computing"
"Make a podcast called 'Deep Dive' with hosts Alex and Sam about this PDF"
```

## Usage

### Basic Generation

```bash
# From URL
<skill>/scripts/generate.py --url "https://example.com/article"

# From YouTube
<skill>/scripts/generate.py --url "https://youtube.com/watch?v=abc123"

# From text
<skill>/scripts/generate.py --text "Your content here..."

# From PDF
<skill>/scripts/generate.py --pdf "/path/to/document.pdf"

# Multiple sources
<skill>/scripts/generate.py --url "https://url1.com" --url "https://url2.com"
```

### Podcast Identity

```bash
# Name the podcast
<skill>/scripts/generate.py --url "https://..." --podcast-name "Deep Dive"

# Name the hosts (they'll use each other's names in conversation)
<skill>/scripts/generate.py --url "https://..." --host-name Alex --cohost-name Sam

# No podcast name (hosts introduce topic naturally, no show branding)
<skill>/scripts/generate.py --url "https://..." --podcast-name ""

# Full customization
<skill>/scripts/generate.py --url "https://..." \
  --podcast-name "Tech Talk" --podcast-tagline "Breaking down the future" \
  --host-name Alex --cohost-name Kiki
```

### Language Options

```bash
# Auto-detect (default)
<skill>/scripts/generate.py --url "https://example.de/artikel"

# Explicit language
<skill>/scripts/generate.py --url "https://example.com" --lang de
```

Supported: `en` (English), `de` (German), `fr` (French), `es` (Spanish)

### TTS Provider & Voice Options

Default: **OpenAI TTS** (`tts-1-hd` with onyx + nova voices)

Optional: **ElevenLabs** for higher quality, more natural voices:

```bash
# Use ElevenLabs with defaults (Daniel + Alice)
<skill>/scripts/generate.py --url "https://..." --elevenlabs

# Custom voices per host
<skill>/scripts/generate.py --url "https://..." --elevenlabs \
  --host-voice Daniel --cohost-voice Alice

# OpenAI custom voices
<skill>/scripts/generate.py --url "https://..." \
  --host-voice echo --cohost-voice shimmer
```

**OpenAI voices:** alloy, echo, fable, onyx, nova, shimmer

**ElevenLabs voices (premade):** Roger, Sarah, Laura, Charlie, George, Callum, River, Liam, Alice, Matilda, Will, Jessica, Eric, Bella, Chris, Brian, Daniel, Lily, Adam, Bill

Browse all: https://elevenlabs.io/voice-library

### All CLI Options

| Option | Description | Example |
|--------|-------------|---------|
| `--url` | URL to process (repeatable) | `--url https://...` |
| `--text` | Plain text content | `--text "AI is..."` |
| `--pdf` | Path to PDF file | `--pdf report.pdf` |
| `--lang` | Output language | `--lang de` |
| `--podcast-name` | Podcast name (empty = none) | `--podcast-name "Deep Dive"` |
| `--podcast-tagline` | Podcast tagline | `--podcast-tagline "..."` |
| `--host-name` | Host name (Person1) | `--host-name Alex` |
| `--cohost-name` | Co-host name (Person2) | `--cohost-name Kiki` |
| `--elevenlabs` | Use ElevenLabs TTS | `--elevenlabs` |
| `--host-voice` | Voice for host | `--host-voice Daniel` |
| `--cohost-voice` | Voice for co-host | `--cohost-voice Alice` |
| `--output`, `-o` | Output file path | `-o podcast.ogg` |

### Output

The script outputs an OGG audio file path. Use the OpenClaw `message` tool to send it:

```python
# Agent workflow
audio_path = exec("<skill>/scripts/generate.py --url 'https://...'")
message(action="send", media=audio_path, target=user_chat)
```

## Configuration

Default podcast style is configured in `<skill>/config/conversation.yaml`. CLI flags override config values.

Key config options:
- `podcast_name` — Show name (empty = content-driven intro)
- `roles_person1` / `roles_person2` — Host role descriptions
- `text_to_speech.{provider}.default_voices` — Default voice per provider
- `language_voices.{provider}.{Language}` — Per-language voice overrides (applied when no `--host-voice`/`--cohost-voice` is set)
- `conversation_style` — Style keywords (engaging, concise, etc.)
- `creativity` — 0-1 scale (higher = more creative dialogue)

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `OPENAI_API_KEY` | Yes | TTS audio generation (default) |
| `GEMINI_API_KEY` | Yes | Transcript/dialogue generation |
| `ELEVENLABS_API_KEY` | No | ElevenLabs TTS (required for `--elevenlabs`) |

Get your ElevenLabs API key at: https://elevenlabs.io/app/settings/api-keys

## Installation

First-time setup (run once):

```bash
<skill>/scripts/install.sh
```

## Requirements

- **ffmpeg** — Audio format conversion
- **uv** — Python environment management
- **Python 3.11+** — Runtime

## Troubleshooting

### "ffmpeg not found"
Install ffmpeg: `brew install ffmpeg` (macOS) or `apt install ffmpeg` (Linux)

### "API key not set"
Ensure `OPENAI_API_KEY` and `GEMINI_API_KEY` are in your environment or secrets.conf

### Hosts say "Quick Brief" or reference a show name
Set `podcast_name: ""` in config/conversation.yaml or use `--podcast-name ""`

### Generation takes too long
Podcastfy processes content through LLM + TTS. Expect 30-90 seconds for short podcasts.

### Audio quality issues
Try ElevenLabs (`--elevenlabs`) for more natural voices. OpenAI `tts-1-hd` is decent but synthetic.
