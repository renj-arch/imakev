"""Full automated pipeline: continuous story video generation + upload."""

import sys
from pathlib import Path
import config


def generate_next_video():
    """Generate the next chapter in the series."""
    from src.story import next_chapter
    chapter = next_chapter()

    print(f"\nGenerating Chapter {chapter['chapter']}: {chapter['title']}")

    # Update cinematic_video.py's scenes with the story content
    from cinematic_video import build_cinematic_video
    # Rebuild the scenes from chapter
    pass


def main():
    print("=" * 50)
    print("  IMAKEV - AI Cinematic Story Generator")
    print("  Continuous Story Pipeline")
    print("=" * 50)

    from src.story import next_chapter
    import cinematic_video as cv

    # Get next chapter
    chapter = next_chapter()

    # Patch the cinematic_video module with new chapter data
    cv.TITLE = f"Chapter {chapter['chapter']}: {chapter['title']}"
    cv.SCRIPT = ". ".join(chapter["subtitles"])
    cv.SUBTITLES = chapter["subtitles"]
    cv.SCENES = [(f"scene_{i}", s) for i, s in enumerate(chapter["scenes"])]

    print(f"\nChapter {chapter['chapter']}: {chapter['title']}")

    # Step 1: Generate video
    print("\n[1/2] Generating video...")
    cv.main()

    # Step 2: Upload to YouTube
    print("\n[2/2] Uploading to YouTube...")
    from upload_youtube import upload

    mp4s = sorted(Path("output").glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not mp4s:
        print("No video to upload!")
        return

    video = str(mp4s[0])
    title = f"Chapter {chapter['chapter']}: {chapter['title']} | AI Cinematic Series"
    print(f"Uploading: {Path(video).name}")
    print(f"Title: {title}")
    upload(
        video_path=video,
        title=title,
        description=f"Chapter {chapter['chapter']} of the Neon City Chronicles.\n\n{chapter['script']}\n\n#shorts #aicinema #series #neoncity",
        tags=["ai film", "cinematic", "series", "neon city", "ai series"],
        privacy="public",
    )

    print(f"\nChapter {chapter['chapter']} complete!")


if __name__ == "__main__":
    main()
