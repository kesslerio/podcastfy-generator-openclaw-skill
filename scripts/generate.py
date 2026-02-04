#!/usr/bin/env python3
"""Generate AI podcast from URLs, text, PDFs, or YouTube videos.

Usage:
    generate.py --url https://example.com/article
    generate.py --url https://youtube.com/watch?v=abc123
    generate.py --text "Your content here"
    generate.py --pdf /path/to/document.pdf
    generate.py --url https://url1.com --url https://url2.com --lang de

Output: Prints path to generated OGG audio file.
"""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Ensure we use the skill's venv
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
VENV_DIR = SKILL_DIR / ".venv"
VENV_PYTHON = VENV_DIR / "bin" / "python"

# Language code mapping
LANGUAGE_MAP = {
    "en": "English",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "english": "English",
    "german": "German",
    "deutsch": "German",
    "french": "French",
    "français": "French",
    "spanish": "Spanish",
    "español": "Spanish",
}


def check_environment(use_elevenlabs: bool = False):
    """Verify environment is properly set up."""
    if not VENV_DIR.exists():
        print(f"❌ Virtual environment not found at {VENV_DIR}", file=sys.stderr)
        print(f"   Run: {SKILL_DIR}/scripts/install.sh", file=sys.stderr)
        sys.exit(1)

    if not os.environ.get("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    if not os.environ.get("GEMINI_API_KEY"):
        print("❌ GEMINI_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    if use_elevenlabs and not os.environ.get("ELEVENLABS_API_KEY"):
        print("❌ ELEVENLABS_API_KEY not set (required for --elevenlabs)", file=sys.stderr)
        sys.exit(1)


def convert_to_ogg(mp3_path: Path, ogg_path: Path) -> bool:
    """Convert MP3 to OGG using ffmpeg."""
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(mp3_path), "-c:a", "libopus", "-b:a", "128k", str(ogg_path)],
            check=True,
            capture_output=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ ffmpeg conversion failed: {e.stderr.decode()}", file=sys.stderr)
        return False
    except FileNotFoundError:
        print("❌ ffmpeg not found", file=sys.stderr)
        return False


def generate_podcast(
    urls: list[str] | None = None,
    text: str | None = None,
    pdf_path: str | None = None,
    lang: str | None = None,
    output_path: str | None = None,
    tts_model: str = "openai",
    voice: str | None = None,
) -> str | None:
    """Generate podcast using podcastfy.

    Returns path to generated OGG file, or None on failure.
    """
    # Load conversation config
    config_path = SKILL_DIR / "config" / "conversation.yaml"

    # Build the Python code to run in venv
    code = '''
import sys
import yaml
from pathlib import Path
from podcastfy.client import generate_podcast

# Load config
config_path = Path(sys.argv[1])
with open(config_path) as f:
    config = yaml.safe_load(f)

# Parse arguments
urls = []
text = None
pdf_path = None
lang = None
tts_model = "openai"
voice = None
i = 2
while i < len(sys.argv):
    if sys.argv[i] == "--url" and i + 1 < len(sys.argv):
        urls.append(sys.argv[i + 1])
        i += 2
    elif sys.argv[i] == "--text" and i + 1 < len(sys.argv):
        text = sys.argv[i + 1]
        i += 2
    elif sys.argv[i] == "--pdf" and i + 1 < len(sys.argv):
        pdf_path = sys.argv[i + 1]
        i += 2
    elif sys.argv[i] == "--lang" and i + 1 < len(sys.argv):
        lang = sys.argv[i + 1]
        i += 2
    elif sys.argv[i] == "--tts-model" and i + 1 < len(sys.argv):
        tts_model = sys.argv[i + 1]
        i += 2
    elif sys.argv[i] == "--voice" and i + 1 < len(sys.argv):
        voice = sys.argv[i + 1]
        i += 2
    else:
        i += 1

# Override language if specified
if lang:
    config["output_language"] = lang

# Set TTS model
config["tts_model"] = tts_model

# Set voice if specified (for ElevenLabs)
if voice:
    tts_config = config.setdefault("text_to_speech", {})
    el_config = tts_config.setdefault("elevenlabs", {"default_voices": {}})
    el_config["default_voices"]["question"] = voice
    el_config["default_voices"]["answer"] = voice

# Generate podcast
try:
    if urls:
        audio_file = generate_podcast(urls=urls, conversation_config=config, tts_model=tts_model)
    elif text:
        audio_file = generate_podcast(text=text, conversation_config=config, tts_model=tts_model)
    elif pdf_path:
        audio_file = generate_podcast(urls=[pdf_path], conversation_config=config, tts_model=tts_model)
    else:
        print("No input provided", file=sys.stderr)
        sys.exit(1)

    print(audio_file)
except Exception as e:
    print(f"Generation failed: {e}", file=sys.stderr)
    sys.exit(1)
'''

    # Build command
    cmd = [str(VENV_PYTHON), "-c", code, str(config_path)]

    if urls:
        for url in urls:
            cmd.extend(["--url", url])
    if text:
        cmd.extend(["--text", text])
    if pdf_path:
        cmd.extend(["--pdf", pdf_path])
    if tts_model:
        cmd.extend(["--tts-model", tts_model])
    if voice:
        cmd.extend(["--voice", voice])
    if lang:
        # Normalize language code
        normalized = LANGUAGE_MAP.get(lang.lower(), lang)
        cmd.extend(["--lang", normalized])

    # Run podcastfy
    print("🎙️ Generating podcast...", file=sys.stderr)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )
    except subprocess.TimeoutExpired:
        print("❌ Generation timed out (5 min limit)", file=sys.stderr)
        return None

    if result.returncode != 0:
        print(f"❌ Generation failed: {result.stderr}", file=sys.stderr)
        return None

    # Extract the MP3 path from stdout (last line, ignore warnings)
    stdout_lines = result.stdout.strip().split('\n')
    mp3_line = stdout_lines[-1].strip()

    # Handle relative paths from podcastfy
    if mp3_line.startswith('./'):
        mp3_line = mp3_line[2:]

    mp3_path = Path(mp3_line)
    if not mp3_path.exists():
        print(f"❌ Output file not found: {mp3_path}", file=sys.stderr)
        return None

    # Convert to OGG
    if output_path:
        ogg_path = Path(output_path)
    else:
        ogg_path = mp3_path.with_suffix(".ogg")

    print("🔄 Converting to OGG...", file=sys.stderr)
    if not convert_to_ogg(mp3_path, ogg_path):
        # Fall back to MP3 if conversion fails
        print("⚠️ OGG conversion failed, using MP3", file=sys.stderr)
        return str(mp3_path)

    # Clean up MP3
    try:
        mp3_path.unlink()
    except Exception:
        pass

    print("✅ Podcast generated!", file=sys.stderr)
    return str(ogg_path)


def main():
    parser = argparse.ArgumentParser(
        description="Generate AI podcast from content sources"
    )
    parser.add_argument(
        "--url",
        action="append",
        dest="urls",
        help="URL to process (can be repeated)"
    )
    parser.add_argument(
        "--text",
        help="Plain text content to convert"
    )
    parser.add_argument(
        "--pdf",
        help="Path to PDF file"
    )
    parser.add_argument(
        "--lang",
        help="Output language (en, de, fr, es)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path (default: auto-generated)"
    )
    parser.add_argument(
        "--elevenlabs",
        action="store_true",
        help="Use ElevenLabs TTS instead of OpenAI (requires ELEVENLABS_API_KEY)"
    )
    parser.add_argument(
        "--voice",
        help="Voice ID for TTS (e.g., 'Rachel', 'Adam' for ElevenLabs)"
    )

    args = parser.parse_args()

    # Validate inputs
    if not any([args.urls, args.text, args.pdf]):
        parser.error("At least one of --url, --text, or --pdf is required")

    check_environment(use_elevenlabs=args.elevenlabs)

    # Determine TTS model
    tts_model = "elevenlabs" if args.elevenlabs else "openai"

    # Generate podcast
    output = generate_podcast(
        urls=args.urls,
        text=args.text,
        pdf_path=args.pdf,
        lang=args.lang,
        output_path=args.output,
        tts_model=tts_model,
        voice=args.voice,
    )

    if output:
        # Print path for OpenClaw to pick up
        print(output)
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
