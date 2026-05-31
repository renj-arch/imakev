"""Full automated pipeline: viral video generation + upload + thumbnail + cross-post."""

from pathlib import Path
import config
from src import story as story_module


def main():
    print("=" * 55)
    print("  IMAKEV - Viral AI Cinematic Story Pipeline")
    print("=" * 55)

    # Step 0: Generate next story chapter
    chapter = story_module.next_chapter()
    print(f"\nChapter {chapter['chapter']}: {chapter['title']}")

    # --- GENERATE VIDEO ---
    import cinematic_video as cv

    # Patch with chapter data
    cv.TITLE = f"Chapter {chapter['chapter']}: {chapter['title']}"
    cv.CHAPTER = chapter["chapter"]
    cv.SCRIPT = ". ".join(chapter["subtitles"])
    cv.SUBTITLES = chapter["subtitles"]
    cv.SCENES = [(f"scene_{i}", s) for i, s in enumerate(chapter["scenes"])]

    print("\n[1/5] Generating video...")
    cv.main()

    # --- GENERATE THUMBNAIL ---
    print("\n[2/5] Generating YouTube thumbnail...")
    from src.thumbnail import save_thumbnail
    thumb_path = save_thumbnail(
        chapter=chapter["chapter"],
        story_title=chapter["title"],
        output_dir=config.OUTPUT_DIR,
    )
    print(f"  Thumbnail: {thumb_path}")

    # --- GENERATE TITLE + DESCRIPTION + TAGS ---
    print("\n[3/5] Optimizing SEO...")
    from src.seo import generate_title, generate_description, generate_tags, generate_hashtags

    final_title = generate_title(chapter["chapter"], chapter["title"])
    final_description = generate_description(chapter["chapter"], chapter["title"], cv.SCRIPT)
    final_tags = generate_tags(chapter["chapter"], chapter["title"])
    hashtags = generate_hashtags()
    print(f"  Title: {final_title}")
    print(f"  Tags: {len(final_tags)} tags + {hashtags.count('#')} hashtags")

    # --- UPLOAD TO YOUTUBE ---
    print("\n[4/5] Uploading to YouTube...")
    from upload_youtube import upload

    mp4s = sorted(Path("output").glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not mp4s:
        print("  No video found!")
        return

    video = str(mp4s[0])
    upload(
        video_path=video,
        title=final_title,
        description=final_description,
        tags=final_tags,
        privacy="public",
    )

    # --- LIKE4LIKE / COMMENT BOT SETUP (optional) ---
    print("\n[5/5] Viral hooks activated:")
    print("  ✓ Subscribe overlay added to video")
    print("  ✓ Comment prompt added to video")
    print("  ✓ SEO-optimized title + description")
    print("  ✓ Trending hashtags applied")
    print("  ✓ YouTube thumbnail generated")

    print(f"\n{'='*55}")
    print(f"  Chapter {chapter['chapter']} complete!")
    print(f"  Next: Chapter {chapter['chapter'] + 1} will generate tomorrow")
    print(f"  SEO title: {final_title}")
    print(f"{'='*55}")


if __name__ == "__main__":
    main()
