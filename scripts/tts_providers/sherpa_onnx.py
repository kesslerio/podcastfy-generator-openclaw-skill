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
import shlex
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional

from podcastfy.tts.base import TTSProvider

WAV_HEADER_SIZE = 44
MIN_AUDIO_BYTES = 100
DEFAULT_TTS_BIN = Path(
    "~/.openclaw/tools/sherpa-onnx-tts/runtime/bin/sherpa-onnx-offline-tts"
).expanduser()


def _find_model_files(model_dir: str) -> dict:
    """Find .onnx, tokens.txt, and espeak-ng-data in a model directory."""
    p = Path(model_dir)
    if not p.is_dir():
        raise ValueError(f"Model directory not found: {model_dir}")

    onnx_files = sorted(p.glob("*.onnx"))
    if not onnx_files:
        raise ValueError(f"No .onnx file found in {model_dir}")
    onnx_file = next((path for path in onnx_files if path.is_file() and path.stat().st_size > 0), None)
    if onnx_file is None:
        raise ValueError(f"No non-empty .onnx file found in {model_dir}")

    tokens = p / "tokens.txt"
    if not tokens.is_file():
        raise ValueError(f"tokens.txt not found in {model_dir}")

    espeak_dir = p / "espeak-ng-data"
    if not espeak_dir.is_dir():
        raise ValueError(f"espeak-ng-data/ not found in {model_dir}")

    return {
        "model": onnx_file,
        "tokens": tokens,
        "data_dir": espeak_dir,
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
        return str(Path(parts[0]).expanduser()), int(parts[1])
    return str(Path(voice).expanduser()), 0


class SherpaTTS(TTSProvider):
    """Local TTS via sherpa-onnx-offline-tts binary.

    Class name is SherpaTTS (not SherpaOnnxTTS) because podcastfy resolves
    config keys via ClassName.lower().replace('tts','') → 'sherpa', which
    must match the 'sherpa:' section in conversation.yaml.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "sherpa"):
        """Initialize. api_key is ignored (local provider)."""
        self.model = model  # Required by podcastfy's text_to_speech.py
        self.tts_bin = Path(os.environ.get("SHERPA_ONNX_TTS_BIN", str(DEFAULT_TTS_BIN))).expanduser()
        if not self.tts_bin.exists():
            raise RuntimeError(
                f"sherpa-onnx-offline-tts not found at {self.tts_bin}. "
                "Install from https://github.com/k2-fsa/sherpa-onnx/releases "
                f"or set SHERPA_ONNX_TTS_BIN. Expected install path: {DEFAULT_TTS_BIN}"
            )
        if not os.access(self.tts_bin, os.X_OK):
            raise RuntimeError(
                f"sherpa-onnx-offline-tts is not executable: {self.tts_bin}. "
                f"Run: chmod +x {self.tts_bin}"
            )

    def _resolve_timeout_seconds(self, text: str) -> int:
        """Resolve process timeout from env or text length."""
        env_timeout = os.environ.get("SHERPA_TTS_TIMEOUT")
        if env_timeout:
            try:
                timeout = int(env_timeout)
                if timeout > 0:
                    return timeout
            except ValueError:
                pass

        # Estimate ~20 chars/sec synth speed, clamped for long inputs.
        dynamic_timeout = len(text) // 20
        return max(60, min(600, dynamic_timeout))

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
            tmp_path = Path(tmp.name)

        try:
            cmd = [
                str(self.tts_bin),
                f"--vits-model={files['model']}",
                f"--vits-tokens={files['tokens']}",
                f"--vits-data-dir={files['data_dir']}",
                f"--sid={sid}",
                f"--output-filename={tmp_path}",
                clean_text,
            ]
            # Log command args without text content to avoid leaking sensitive input
            cmd_args_str = " ".join(shlex.quote(str(part)) for part in cmd[:-1])
            timeout_seconds = self._resolve_timeout_seconds(clean_text)

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                )
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError(
                    f"sherpa-onnx-offline-tts timed out after {timeout_seconds}s "
                    f"(text length: {len(clean_text)} chars). Args: {cmd_args_str}"
                ) from exc

            if result.returncode != 0:
                raise RuntimeError(
                    f"sherpa-onnx-offline-tts failed (rc={result.returncode}): "
                    f"{result.stderr[:500]} | Args: {cmd_args_str}"
                )

            with tmp_path.open("rb") as f:
                wav_bytes = f.read()

            if len(wav_bytes) <= WAV_HEADER_SIZE or len(wav_bytes) < MIN_AUDIO_BYTES:
                raise RuntimeError(
                    "Generated audio file is suspiciously small "
                    f"({len(wav_bytes)} bytes, expected > {MIN_AUDIO_BYTES})"
                )

            return wav_bytes

        finally:
            try:
                tmp_path.unlink()
            except OSError:
                pass
