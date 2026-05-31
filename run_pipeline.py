"""Full automated pipeline with 7-mode workflow rotation."""

from pathlib import Path
import config


def _get_mode_counter() -> int:
    counter_file = config.TEMP_DIR / "pipeline_counter.txt"
    if counter_file.exists():
        try:
            return int(counter_file.read_text().strip())
        except (ValueError, OSError):
            return 0
    return 0


def _save_mode_counter(val: int):
    counter_file = config.TEMP_DIR / "pipeline_counter.txt"
    counter_file.write_text(str(val))


MODES = [
    "cinematic",
    "shorts",
    "history_minute",
    "batch_shorts",
    "cinematic",
    "shorts",
    "history_minute",
]


def run():
    print("=" * 50)
    print("  AUTO PIPELINE - 7-Mode Daily Rotation")
    print("=" * 50)

    idx = _get_mode_counter()
    mode = MODES[idx % len(MODES)]
    print(f"  Mode #{idx + 1}: {mode}")
    print()

    if mode == "cinematic":
        print("[1/2] Generating cinematic video...")
        from cinematic_video import main as cinematic_main
        cinematic_main()

        print("\n[2/2] Uploading to YouTube...")
        from upload_youtube import upload
        mp4s = sorted(Path("output").glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
        if mp4s:
            video = str(mp4s[0])
            print(f"Uploading: {Path(video).name}")
            upload(
                video_path=video,
                title="AI Cinematic Short Film #shorts",
                description="Daily AI-generated cinematic short film.\n#shorts #aicinema",
                tags=["ai film", "cinematic", "shorts"],
                privacy="public",
            )

    elif mode == "shorts":
        print("[1/2] Generating shorts video...")
        from main import generate_shorts_video
        generate_shorts_video(niche="general knowledge")

        print("\n[2/2] Uploading to YouTube...")
        from upload_youtube import upload
        mp4s = sorted(Path("output").glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
        if mp4s:
            video = str(mp4s[0])
            print(f"Uploading: {Path(video).name}")
            upload(
                video_path=video,
                title="Daily Knowledge Shorts #shorts",
                description="Daily AI-generated knowledge shorts.\n#shorts #knowledge",
                tags=["shorts", "knowledge", "ai"],
                privacy="public",
            )

    elif mode == "history_minute":
        print("[1/2] Generating history minute video...")
        from history_minute_video import generate_history_video
        generate_history_video()

        print("\n[2/2] Uploading to YouTube...")
        from upload_youtube import upload
        mp4s = sorted(Path("output").glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
        if mp4s:
            video = str(mp4s[0])
            print(f"Uploading: {Path(video).name}")
            upload(
                video_path=video,
                title="History Minute #shorts",
                description="Daily history minute short.\n#shorts #history",
                tags=["history", "shorts", "ai"],
                privacy="public",
            )

    elif mode == "batch_shorts":
        print("[1/1] Generating batch shorts...")
        from main import generate_shorts_video
        for i in range(5):
            print(f"\n--- Batch video {i+1}/5 ---")
            generate_shorts_video(niche="general knowledge")

    _save_mode_counter(idx + 1)
    print("\nDone!")


if __name__ == "__main__":
    run()
