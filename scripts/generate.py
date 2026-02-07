#!/usr/bin/env python3
"""Generate AI podcast from URLs, text, PDFs, or YouTube videos.

Usage:
    generate.py --url https://example.com/article
    generate.py --url https://youtube.com/watch?v=abc123
    generate.py --text "Your content here"
    generate.py --pdf /path/to/document.pdf
    generate.py --url https://url1.com --url https://url2.com --lang de

    # Custom podcast identity
    generate.py --url https://... --podcast-name "Deep Dive" --host-name Alex --cohost-name Sam

    # Custom voices (ElevenLabs)
    generate.py --url https://... --elevenlabs --host-voice Daniel --cohost-voice Alice

Output: Prints path to generated OGG audio file.
"""

import argparse
import json
import os
import subprocess
import sys
import time
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


def cleanup_old_files(directory: Path, pattern: str, max_age_hours: int = 1) -> int:
    """Remove files matching pattern older than max_age_hours."""
    if not directory.exists():
        return 0

    removed = 0
    max_age_seconds = max_age_hours * 3600

    for file_path in directory.glob(pattern):
        try:
            age = time.time() - os.path.getctime(file_path)
            if age > max_age_seconds:
                file_path.unlink()
                removed += 1
        except Exception:
            pass

    return removed


def build_role(base_role: str, name: str | None) -> str:
    """Build a role string, optionally including the host name.

    Examples:
        build_role("host", None)    → "host"
        build_role("host", "Alex")  → "host named Alex"
    """
    if name:
        return f'{base_role} named {name}'
    return base_role


# Inner Python code executed inside the podcastfy venv.
# Receives config overrides as a JSON blob via --overrides.
VENV_CODE = '''
import json
import sys
import yaml
from pathlib import Path
from podcastfy.client import generate_podcast


def deep_merge(base, override):
    """Recursively merge override dict into base dict."""
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            deep_merge(base[k], v)
        else:
            base[k] = v
    return base


# Load base config
config_path = Path(sys.argv[1])
with open(config_path) as f:
    config = yaml.safe_load(f)

# Parse arguments
urls = []
text = None
pdf_path = None
overrides = {}
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
    elif sys.argv[i] == "--overrides" and i + 1 < len(sys.argv):
        try:
            overrides = json.loads(sys.argv[i + 1])
        except json.JSONDecodeError as e:
            print(f"Error: invalid --overrides JSON: {e}", file=sys.stderr)
            sys.exit(1)
        i += 2
    else:
        i += 1

# Apply overrides via recursive deep merge
deep_merge(config, overrides)

# Handle empty podcast_name: podcastfy hardcodes "Welcome to {name} - {tagline}"
# in its prompt, so empty string produces "Welcome to  - ...". Replace with a
# generic name that reads naturally if the user explicitly cleared it.
podcast_name = (config.get("podcast_name") or "").strip()
if not podcast_name:
    config["podcast_name"] = "the show"
    config["podcast_tagline"] = "Let's get into it"

tts_model = config.get("tts_model", "openai")

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


def generate_podcast(
    urls: list[str] | None = None,
    text: str | None = None,
    pdf_path: str | None = None,
    lang: str | None = None,
    output_path: str | None = None,
    tts_model: str = "openai",
    host_voice: str | None = None,
    cohost_voice: str | None = None,
    podcast_name: str | None = None,
    podcast_tagline: str | None = None,
    host_name: str | None = None,
    cohost_name: str | None = None,
) -> str | None:
    """Generate podcast using podcastfy.

    Returns path to generated OGG file, or None on failure.
    """
    config_path = SKILL_DIR / "config" / "conversation.yaml"

    # Build config overrides as a JSON blob
    overrides: dict = {}

    if lang:
        overrides["output_language"] = LANGUAGE_MAP.get(lang.lower(), lang)

    overrides["tts_model"] = tts_model

    if podcast_name is not None:
        overrides["podcast_name"] = podcast_name
    if podcast_tagline is not None:
        overrides["podcast_tagline"] = podcast_tagline

    # Build host roles with optional names
    if host_name:
        overrides["roles_person1"] = build_role("host", host_name)
    if cohost_name:
        overrides["roles_person2"] = build_role("co-host", cohost_name)

    # Voice overrides for the active TTS provider
    provider = "elevenlabs" if tts_model == "elevenlabs" else "openai"
    if host_voice or cohost_voice:
        # Explicit CLI voices take highest priority
        voices: dict = {}
        if host_voice:
            voices["question"] = host_voice
        if cohost_voice:
            voices["answer"] = cohost_voice
        overrides["text_to_speech"] = {provider: {"default_voices": voices}}
    elif lang:
        # Apply language-specific voice defaults from config (if no explicit voices)
        import yaml
        with open(config_path) as f:
            base_config = yaml.safe_load(f)
        lang_voices = base_config.get("language_voices", {})
        normalized_lang = LANGUAGE_MAP.get(lang.lower(), lang)
        provider_lang_voices = lang_voices.get(provider, {}).get(normalized_lang)
        if provider_lang_voices:
            overrides["text_to_speech"] = {provider: {"default_voices": provider_lang_voices}}

    # Build command
    cmd = [str(VENV_PYTHON), "-c", VENV_CODE, str(config_path)]

    if urls:
        for url in urls:
            cmd.extend(["--url", url])
    if text:
        cmd.extend(["--text", text])
    if pdf_path:
        cmd.extend(["--pdf", pdf_path])
    if overrides:
        cmd.extend(["--overrides", json.dumps(overrides)])

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
        print("⚠️ OGG conversion failed, using MP3", file=sys.stderr)
        return str(mp3_path)

    # Clean up MP3
    try:
        mp3_path.unlink()
    except Exception:
        pass

    # Clean up old transcript files (keep for 1 hour for debugging)
    transcripts_dir = SKILL_DIR / "data" / "transcripts"
    removed = cleanup_old_files(transcripts_dir, "transcript_*.txt", max_age_hours=1)
    if removed > 0:
        print(f"🧹 Cleaned up {removed} old transcript file(s)", file=sys.stderr)

    print("✅ Podcast generated!", file=sys.stderr)
    return str(ogg_path)


def main():
    parser = argparse.ArgumentParser(
        description="Generate AI podcast from content sources"
    )

    # Content sources
    source = parser.add_argument_group("content sources (at least one required)")
    source.add_argument(
        "--url", action="append", dest="urls",
        help="URL to process (can be repeated)",
    )
    source.add_argument("--text", help="Plain text content to convert")
    source.add_argument("--pdf", help="Path to PDF file")

    # Podcast identity
    identity = parser.add_argument_group("podcast identity")
    identity.add_argument(
        "--podcast-name",
        help='Podcast name (empty string = no name, hosts introduce topic naturally)',
    )
    identity.add_argument("--podcast-tagline", help="Podcast tagline")
    identity.add_argument("--host-name", help="Name for the host (Person1)")
    identity.add_argument("--cohost-name", help="Name for the co-host (Person2)")

    # TTS / voices
    voice_group = parser.add_argument_group("voice configuration")
    voice_group.add_argument(
        "--elevenlabs", action="store_true",
        help="Use ElevenLabs TTS instead of OpenAI (requires ELEVENLABS_API_KEY)",
    )
    voice_group.add_argument(
        "--host-voice",
        help="Voice for the host (e.g., 'Daniel', 'onyx')",
    )
    voice_group.add_argument(
        "--cohost-voice",
        help="Voice for the co-host (e.g., 'Alice', 'nova')",
    )
    # Legacy: --voice sets both host and co-host to the same voice
    voice_group.add_argument(
        "--voice",
        help=argparse.SUPPRESS,  # Hidden, kept for backwards compat
    )

    # Output
    parser.add_argument("--lang", help="Output language (en, de, fr, es)")
    parser.add_argument("--output", "-o", help="Output file path (default: auto)")

    args = parser.parse_args()

    # Validate inputs
    if not any([args.urls, args.text, args.pdf]):
        parser.error("At least one of --url, --text, or --pdf is required")

    check_environment(use_elevenlabs=args.elevenlabs)

    # Determine TTS model
    tts_model = "elevenlabs" if args.elevenlabs else "openai"

    # Handle legacy --voice (sets both, but new flags take precedence)
    host_voice = args.host_voice
    cohost_voice = args.cohost_voice
    if args.voice:
        if host_voice or cohost_voice:
            print(
                "⚠️ --voice ignored because --host-voice or --cohost-voice is set",
                file=sys.stderr,
            )
        else:
            host_voice = args.voice
            cohost_voice = args.voice

    # Generate podcast
    output = generate_podcast(
        urls=args.urls,
        text=args.text,
        pdf_path=args.pdf,
        lang=args.lang,
        output_path=args.output,
        tts_model=tts_model,
        host_voice=host_voice,
        cohost_voice=cohost_voice,
        podcast_name=args.podcast_name,
        podcast_tagline=args.podcast_tagline,
        host_name=args.host_name,
        cohost_name=args.cohost_name,
    )

    if output:
        print(output)
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
