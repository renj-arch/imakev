import subprocess, sys
from pathlib import Path
import config


VOICES = {
    "en-us-female": "en-US-AriaNeural",
    "en-us-male": "en-US-GuyNeural",
    "en-gb-female": "en-GB-SoniaNeural",
    "en-gb-male": "en-GB-RyanNeural",
    "en-au-female": "en-AU-NatashaNeural",
}


def generate_tts(text: str, output_path: Path, voice: str = "en-us-male") -> Path:
    if config.TTS_PROVIDER == "edge":
        return _generate_edge_cli(text, output_path, voice)
    elif config.TTS_PROVIDER == "elevenlabs":
        return _generate_elevenlabs(text, output_path, voice)
    raise ValueError(f"Unknown TTS provider: {config.TTS_PROVIDER}")


def _generate_edge_cli(text: str, output_path: Path, voice: str = "en-us-male") -> Path:
    voice_name = VOICES.get(voice, VOICES["en-us-male"])
    result = subprocess.run(
        [sys.executable, "-m", "edge_tts", "--text", text, "--voice", voice_name, "--write-media", str(output_path)],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"edge-tts failed: {result.stderr}")
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("edge-tts produced empty file")
    return output_path


def _generate_elevenlabs(text: str, output_path: Path, voice: str = "en-us-male") -> Path:
    try:
        from elevenlabs import generate, save, Voice, VoiceSettings
        audio = generate(
            text=text,
            voice=Voice(
                voice_id=config.ELEVENLABS_VOICE_ID,
                settings=VoiceSettings(stability=0.5, similarity_boost=0.75),
            ),
            api_key=config.ELEVENLABS_API_KEY,
        )
        save(audio, str(output_path))
        return output_path
    except ImportError:
        raise ImportError("Install elevenlabs: pip install elevenlabs")
