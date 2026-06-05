"""Piper TTS wrapper — fast, local, high-quality text-to-speech (completely free, no API)."""

import subprocess, sys, os, json, urllib.request, zipfile
from pathlib import Path

VOICE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx"
VOICE_JSON_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json"

def _ensure_voice(voice_dir: Path) -> Path:
    onnx_path = voice_dir / "en_US-amy-medium.onnx"
    json_path = voice_dir / "en_US-amy-medium.onnx.json"
    if onnx_path.exists() and json_path.exists():
        return onnx_path
    voice_dir.mkdir(parents=True, exist_ok=True)
    print(f"  Downloading Piper voice (Amy medium)...")
    for url, dest in [(VOICE_URL, onnx_path), (VOICE_JSON_URL, json_path)]:
        urllib.request.urlretrieve(url, dest)
    print(f"  Voice downloaded")
    return onnx_path

def generate_speech(text: str, output_path: str | Path) -> bool:
    output_path = Path(output_path)
    voice_dir = Path(__file__).parent.parent / "assets" / "piper_voices"
    try:
        model = _ensure_voice(voice_dir)
        cmd = [
            sys.executable, "-m", "piper",
            "--model", str(model),
            "--output_file", str(output_path),
        ]
        proc = subprocess.run(
            cmd,
            input=text.encode("utf-8"),
            capture_output=True,
            timeout=120,
        )
        if proc.returncode != 0:
            print(f"  Piper error: {proc.stderr.decode()[:200]}")
            return False
        sz = output_path.stat().st_size
        print(f"  Piper TTS: {sz/1024:.0f}KB, {len(text.split())} words")
        return sz > 1000
    except Exception as e:
        print(f"  Piper TTS error: {e}")
        return False
