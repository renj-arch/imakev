"""History Minute video generator — bank/LLM script + TTS + video assembly."""

import re, sys, time, random
from pathlib import Path
from datetime import datetime

from src.history_minute import generate_history_script
from src.text_to_speech import generate_tts
from src.video_builder import build_shorts_video
from src.asset_manager import ensure_default_assets
import config

USED_TOPICS_FILE = config.TEMP_DIR / "history_used_topics.txt"


def _load_used_topics() -> set[str]:
    if not USED_TOPICS_FILE.exists():
        return set()
    return {line.strip() for line in USED_TOPICS_FILE.read_text().splitlines() if line.strip()}


def _save_used_topic(topic: str):
    with open(USED_TOPICS_FILE, "a", encoding="utf-8") as f:
        f.write(topic + "\n")


def _safe(text: str) -> str:
    return re.sub(r"[^\x00-\x7F]+", "", text) if text else ""


def _retry(fn, *args, retries=3, delay=5, **kwargs):
    for i in range(retries):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                wait = delay * (2 ** i)
                print(f"  Rate limited, retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise
    raise Exception(f"Failed after {retries} retries")


def generate_history_video(voice: str = "en-us-male") -> Path:
    print("=" * 50)
    print("  HISTORY MINUTE GENERATOR")
    print("=" * 50)

    used = _load_used_topics()

    print(f"\n[1/4] Generating history script...")
    script = _retry(generate_history_script, used_topics=used)
    print(f"  Script: {_safe(script[:80])}...")

    topic_match = re.search(r'^(.*?):', script)
    topic = topic_match.group(1).strip() if topic_match else script.split(".")[0].strip()
    safe_title = "".join(c for c in topic if c.isalnum() or c in " _-").strip()[:40] or "history_minute"
    safe_title = re.sub(r'\s+', '_', safe_title)

    print(f"[2/4] Generating voiceover...")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_path = config.TEMP_DIR / f"hist_audio_{ts}.mp3"
    _retry(generate_tts, script, audio_path, voice=voice)

    print(f"[3/4] Building video...")
    output_path = config.OUTPUT_DIR / f"History_{safe_title}_{ts}.mp4"
    build_shorts_video(audio_path, script, output_path, search_query="history documentary")

    audio_path.unlink(missing_ok=True)
    _save_used_topic(topic)

    print(f"\n[4/4] Done! Video saved to: {output_path}")
    print(f"  Duration: ~{_get_duration(output_path)}s")
    return output_path


def _get_duration(video_path: Path) -> float:
    from moviepy import VideoFileClip
    with VideoFileClip(str(video_path)) as clip:
        return clip.duration


def main():
    ensure_default_assets()

    import argparse
    parser = argparse.ArgumentParser(description="History Minute Video Generator")
    parser.add_argument("--voice", "-v", default="en-us-male", choices=["en-us-male", "en-us-female", "en-gb-male", "en-gb-female"], help="TTS voice")
    args = parser.parse_args()

    generate_history_video(voice=args.voice)


if __name__ == "__main__":
    main()
