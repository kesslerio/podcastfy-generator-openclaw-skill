#!/usr/bin/env bash
# Install podcastfy in isolated uv environment
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$SKILL_DIR/.venv"

echo "🎙️ Installing Podcastfy Generator..."

# Check prerequisites
if ! command -v uv &> /dev/null; then
    echo "❌ uv not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

if ! command -v ffmpeg &> /dev/null; then
    echo "❌ ffmpeg not found. Install with: brew install ffmpeg (macOS) or apt install ffmpeg (Linux)"
    exit 1
fi

# Create venv if needed
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating Python environment..."
    uv venv "$VENV_DIR" --python 3.11
fi

# Install dependencies
echo "📥 Installing podcastfy..."
uv pip install --python "$VENV_DIR/bin/python" podcastfy

# Verify installation
"$VENV_DIR/bin/python" -c "import podcastfy; print(f'✅ Podcastfy {podcastfy.__version__} installed')" 2>/dev/null || \
"$VENV_DIR/bin/python" -c "import podcastfy; print('✅ Podcastfy installed')"

echo ""
echo "✅ Installation complete!"
echo ""
echo "Required environment variables:"
echo "  - OPENAI_API_KEY  (for TTS)"
echo "  - GEMINI_API_KEY  (for transcript generation)"
echo ""
echo "Test with:"
echo "  $SKILL_DIR/scripts/generate.py --text 'Hello world' --output /tmp/test.ogg"
