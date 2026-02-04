# Podcastfy Generator - OpenClaw Skill 🎙️

Generate AI podcast-style audio conversations from URLs, YouTube videos, PDFs, or text. Creates engaging two-host dialogues similar to Google NotebookLM's Audio Overview feature.

[![ClawHub](https://img.shields.io/badge/ClawHub-podcastfy--generator-blue)](https://clawhub.com/skills/podcastfy-generator)

## Features

- **Multi-source input**: URLs, YouTube, PDFs, plain text
- **Two-host dialogue**: Natural conversation between AI hosts
- **Multi-lingual**: English, German, French, Spanish
- **Short-form**: 2-5 minute podcasts (configurable)
- **Auto-delivery**: Sends OGG audio to Telegram/WhatsApp

## Quick Start

```bash
# Install (one-time)
./scripts/install.sh

# Generate from URL
./scripts/generate.py --url "https://example.com/article"

# Generate from text
./scripts/generate.py --text "Your content here"

# German output
./scripts/generate.py --url "https://example.com" --lang de
```

## Requirements

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) - Python package manager
- ffmpeg - Audio conversion
- OpenAI API key (`OPENAI_API_KEY`)
- Gemini API key (`GEMINI_API_KEY`)

## Installation

1. Clone or install via ClawHub:
   ```bash
   clawhub install podcastfy-generator
   ```

2. Run setup:
   ```bash
   ./scripts/install.sh
   ```

3. Set environment variables:
   ```bash
   export OPENAI_API_KEY="your-key"
   export GEMINI_API_KEY="your-key"
   ```

## Usage Examples

### With OpenClaw Agent

```
User: "Create a podcast about this article: https://..."
Agent: Generates podcast → sends audio to chat
```

### CLI

```bash
# Single URL
./scripts/generate.py --url "https://example.com/article"

# Multiple URLs
./scripts/generate.py --url "https://url1.com" --url "https://url2.com"

# YouTube video
./scripts/generate.py --url "https://youtube.com/watch?v=abc123"

# Plain text
./scripts/generate.py --text "The history of artificial intelligence..."

# Specify output path
./scripts/generate.py --url "https://..." --output /tmp/podcast.ogg

# Different language
./scripts/generate.py --url "https://..." --lang de
```

## Configuration

Edit `config/conversation.yaml` to customize:

- `word_count`: Target length (default: 500 words ≈ 3 min)
- `conversation_style`: Tone and approach
- `roles_person1/2`: Host personalities
- `dialogue_structure`: Podcast segments
- `creativity`: LLM temperature (0-1)

### Voice Selection

Default voices (OpenAI TTS):
- **Host 1**: `onyx` - Deep, authoritative male
- **Host 2**: `nova` - Bright, energetic female

## How It Works

1. **Content extraction**: Fetches and parses input sources
2. **Transcript generation**: Gemini LLM creates dialogue
3. **Audio synthesis**: OpenAI TTS with two voices
4. **Format conversion**: MP3 → OGG for messaging apps
5. **Delivery**: Returns file path for OpenClaw message tool

## Credits

Built on [Podcastfy](https://github.com/souzatharsis/podcastfy) - the open-source NotebookLM alternative.

## License

Apache 2.0
