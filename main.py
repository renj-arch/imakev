import sys, re, time
from pathlib import Path
from datetime import datetime

from src.script_generator import generate_script, generate_title_from_script
from src.text_to_speech import generate_tts
from src.video_builder import build_shorts_video
from src.asset_manager import ensure_default_assets
import config


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


def generate_shorts_video(topic: str = "", niche: str = "general knowledge", voice: str = "en-us-male") -> Path:
    print(f"[1/4] Generating script... (niche: {niche})")
    script = _retry(generate_script, topic=topic, niche=niche)
    print(f"  Script: {_safe(script[:80])}...")

    print(f"[2/4] Generating title...")
    title = _retry(generate_title_from_script, script)
    safe_title = "".join(c for c in title if c.isalnum() or c in " _-").strip()[:40] or "shorts"
    print(f"  Title: {_safe(title)}")

    print(f"[3/4] Generating voiceover...")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_path = config.TEMP_DIR / f"audio_{ts}.mp3"
    _retry(generate_tts, script, audio_path, voice=voice)

    print(f"[4/4] Building video...")
    output_path = config.OUTPUT_DIR / f"{safe_title}_{ts}.mp4"
    build_shorts_video(audio_path, script, output_path, search_query=niche)

    audio_path.unlink(missing_ok=True)

    print(f"\nDone! Video saved to: {output_path}")
    print(f"  Title: {_safe(title)}")
    print(f"  Duration: ~{_get_duration(output_path)}s")
    return output_path


def _get_duration(video_path: Path) -> float:
    from moviepy import VideoFileClip
    with VideoFileClip(str(video_path)) as clip:
        return clip.duration


def main():
    ensure_default_assets()

    import argparse
    parser = argparse.ArgumentParser(description="AI YouTube Shorts Generator")
    parser.add_argument("--topic", "-t", default="", help="Specific topic for the video")
    parser.add_argument("--niche", "-n", default="general knowledge", help="Content niche")
    parser.add_argument("--voice", "-v", default="en-us-male", choices=["en-us-male", "en-us-female", "en-gb-male", "en-gb-female"], help="TTS voice")
    parser.add_argument("--batch", "-b", type=int, default=0, help="Generate multiple videos")

    args = parser.parse_args()

    if args.batch > 1:
        for i in range(args.batch):
            print(f"\n=== Video {i+1}/{args.batch} ===")
            generate_shorts_video(topic=args.topic, niche=args.niche, voice=args.voice)
    else:
        generate_shorts_video(topic=args.topic, niche=args.niche, voice=args.voice)


if __name__ == "__main__":
    main()
