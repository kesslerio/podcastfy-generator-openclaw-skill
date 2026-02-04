---
name: podcastfy-generator
description: Generate AI podcast-style audio conversations from URLs, YouTube videos, PDFs, or text topics. Creates NotebookLM-style two-host dialogues. Use when user asks to "create a podcast", "make an audio summary", "turn this article into a podcast", or wants content converted to audio discussion format.
homepage: https://github.com/kesslerio/podcastfy-generator-openclaw-skill
metadata: {"openclaw": {"emoji": "🎙️", "requires": {"bins": ["ffmpeg", "uv"], "env": ["OPENAI_API_KEY", "GEMINI_API_KEY"]}, "primaryEnv": "OPENAI_API_KEY"}}
---

# Podcastfy Generator 🎙️

Generate AI podcast-style audio conversations from any content. Creates engaging two-host dialogues similar to Google NotebookLM's Audio Overview feature.

## Capabilities

- **URLs** → Fetch article content, generate podcast discussion
- **YouTube** → Extract transcript, create audio summary
- **PDFs** → Parse document, synthesize key points as dialogue
- **Text/Topics** → Generate podcast from plain text or topic prompts
- **Multi-lingual** → English, German, French, Spanish (auto-detect or specify)

## Quick Examples

```
"Create a podcast about this article: https://example.com/tech-news"
"Turn this YouTube video into a podcast: https://youtube.com/watch?v=..."
"Generate a German podcast discussing quantum computing"
"Make an audio summary of these meeting notes: [paste text]"
```

## Usage

### Basic Generation

Run the generate script with content sources:

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

### Language Options

```bash
# Auto-detect (default)
<skill>/scripts/generate.py --url "https://example.de/artikel"

# Explicit language
<skill>/scripts/generate.py --url "https://example.com" --lang de
<skill>/scripts/generate.py --url "https://example.com" --lang fr
```

Supported: `en` (English), `de` (German), `fr` (French), `es` (Spanish)

### Output

The script outputs an OGG audio file path. Use the OpenClaw `message` tool to send it:

```python
# Agent workflow
audio_path = exec("<skill>/scripts/generate.py --url 'https://...'")
message(action="send", media=audio_path, target=user_chat)
```

## Workflow

1. **Parse request** — Extract URLs, text, PDFs, or topic from user message
2. **Detect language** — Auto-detect from content or use explicit `--lang`
3. **Generate transcript** — Podcastfy creates dialogue via Gemini LLM
4. **Synthesize audio** — OpenAI TTS with two distinct voices (onyx + nova)
5. **Convert format** — MP3 → OGG for Telegram/WhatsApp compatibility
6. **Deliver** — Send audio file to user's chat

## Configuration

Default podcast style is configured in `<skill>/config/conversation.yaml`:

- **Length:** 2-5 minutes (short format)
- **Style:** Engaging, concise, informative
- **Hosts:** Onyx (male anchor) + Nova (female co-host)
- **Structure:** Hook → Key Points → Takeaway

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `OPENAI_API_KEY` | Yes | TTS audio generation |
| `GEMINI_API_KEY` | Yes | Transcript/dialogue generation |

## Installation

First-time setup (run once):

```bash
<skill>/scripts/install.sh
```

This creates an isolated Python environment with podcastfy and dependencies.

## Requirements

- **ffmpeg** — Audio format conversion
- **uv** — Python environment management
- **Python 3.11+** — Runtime

## Troubleshooting

### "ffmpeg not found"
Install ffmpeg: `brew install ffmpeg` (macOS) or `apt install ffmpeg` (Linux)

### "API key not set"
Ensure `OPENAI_API_KEY` and `GEMINI_API_KEY` are in your environment or secrets.conf

### Generation takes too long
Podcastfy processes content through LLM + TTS. Expect 30-90 seconds for short podcasts.

### Audio quality issues
The skill uses `tts-1-hd` model for high quality. If issues persist, check source content quality.
