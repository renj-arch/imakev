import subprocess, sys, asyncio
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


def generate_tts_with_timestamps(text: str, output_path: Path, voice: str = "en-us-male") -> list[dict]:
    """Generate TTS audio and return word-level timestamps.
    
    Returns list of {text, start, end} dicts with times in seconds.
    Audio is saved to output_path."""
    voice_name = VOICES.get(voice, VOICES["en-us-male"])
    words = []

    async def _run():
        import edge_tts
        communicate = edge_tts.Communicate(
            text, voice_name,
            rate="+0%", volume="+0%", pitch="+0Hz",
            boundary="WordBoundary",
        )
        t0 = None
        with open(output_path, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "WordBoundary":
                    offset_s = chunk["offset"] / 1_000_0000
                    dur_s = chunk["duration"] / 1_000_0000
                    if t0 is None:
                        t0 = offset_s
                    words.append({
                        "text": chunk["text"],
                        "start": offset_s,
                        "end": offset_s + dur_s,
                    })
                elif chunk["type"] == "audio":
                    f.write(chunk["data"])

    asyncio.run(_run())

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("edge-tts produced empty file")
    return words


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
