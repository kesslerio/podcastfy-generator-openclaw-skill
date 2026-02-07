"""Sherpa-ONNX local TTS provider for podcastfy.

Runs entirely offline using sherpa-onnx-offline-tts binary + Piper VITS models.
Zero API cost, unlimited usage, runs on CPU.

Requires:
    - SHERPA_ONNX_TTS_BIN: Path to sherpa-onnx-offline-tts binary
    - Model directories with .onnx, tokens.txt, and espeak-ng-data/

Voice format: "<model_dir>" or "<model_dir>:sid=<N>" for multi-speaker models.
Example voices:
    - "/path/to/vits-piper-en_US-lessac-high"
    - "/path/to/vits-piper-en_US-libritts_r-medium:sid=50"
"""

import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional

from podcastfy.tts.base import TTSProvider


def _find_model_files(model_dir: str) -> dict:
    """Find .onnx, tokens.txt, and espeak-ng-data in a model directory."""
    p = Path(model_dir)
    if not p.is_dir():
        raise ValueError(f"Model directory not found: {model_dir}")

    onnx_files = list(p.glob("*.onnx"))
    if not onnx_files:
        raise ValueError(f"No .onnx file found in {model_dir}")

    tokens = p / "tokens.txt"
    if not tokens.exists():
        raise ValueError(f"tokens.txt not found in {model_dir}")

    espeak_dir = p / "espeak-ng-data"
    if not espeak_dir.is_dir():
        raise ValueError(f"espeak-ng-data/ not found in {model_dir}")

    return {
        "model": str(onnx_files[0]),
        "tokens": str(tokens),
        "data_dir": str(espeak_dir),
    }


def _parse_voice(voice: str) -> tuple[str, int]:
    """Parse voice string into (model_dir, speaker_id).

    Supports:
        "/path/to/model"           → (path, 0)
        "/path/to/model:sid=50"    → (path, 50)
        "~/path/to/model:sid=50"   → (expanded, 50)
    """
    if ":sid=" in voice:
        parts = voice.rsplit(":sid=", 1)
        return os.path.expanduser(parts[0]), int(parts[1])
    return os.path.expanduser(voice), 0


class SherpaOnnxTTS(TTSProvider):
    """Local TTS via sherpa-onnx-offline-tts binary."""

    def __init__(self, api_key: Optional[str] = None, model: str = "sherpa"):
        """Initialize. api_key is ignored (local provider)."""
        self.tts_bin = os.environ.get(
            "SHERPA_ONNX_TTS_BIN",
            os.path.expanduser(
                "~/.openclaw/tools/sherpa-onnx-tts/runtime/bin/sherpa-onnx-offline-tts"
            ),
        )
        if not Path(self.tts_bin).exists():
            raise RuntimeError(
                f"sherpa-onnx-offline-tts not found at {self.tts_bin}. "
                "Set SHERPA_ONNX_TTS_BIN or install sherpa-onnx."
            )

    def get_supported_tags(self) -> List[str]:
        """No SSML support for local TTS."""
        return []

    def generate_audio(self, text: str, voice: str, model: str, voice2: str = None) -> bytes:
        """Generate audio using sherpa-onnx-offline-tts.

        Args:
            text: Text to synthesize.
            voice: Model directory path, optionally with ":sid=N" suffix.
            model: Ignored (model is determined by voice path).
            voice2: Ignored.

        Returns:
            WAV audio bytes.
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        if not voice:
            raise ValueError("Voice (model directory path) must be specified")

        model_dir, sid = _parse_voice(voice)
        files = _find_model_files(model_dir)

        # Strip any SSML tags that might have leaked through
        clean_text = re.sub(r"<[^>]+>", "", text).strip()
        if not clean_text:
            raise ValueError("Text is empty after stripping markup")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            cmd = [
                self.tts_bin,
                f"--vits-model={files['model']}",
                f"--vits-tokens={files['tokens']}",
                f"--vits-data-dir={files['data_dir']}",
                f"--sid={sid}",
                f"--output-filename={tmp_path}",
                clean_text,
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"sherpa-onnx-offline-tts failed (rc={result.returncode}): "
                    f"{result.stderr[:500]}"
                )

            with open(tmp_path, "rb") as f:
                wav_bytes = f.read()

            if len(wav_bytes) < 100:
                raise RuntimeError("Generated audio file is suspiciously small")

            return wav_bytes

        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
