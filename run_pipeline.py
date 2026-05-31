"""Full automated pipeline: switches between story video and fact video each run."""

import sys, random
from pathlib import Path
import config


def run_story():
    print("=" * 55)
    print("  MODE: CINEMATIC STORY")
    print("=" * 55)

    from src import story as story_module
    import cinematic_video as cv
    from src.thumbnail import save_thumbnail
    from src.seo import generate_title, generate_description, generate_tags, generate_hashtags
    from upload_youtube import upload

    chapter = story_module.next_chapter()
    print(f"\nChapter {chapter['chapter']}: {chapter['title']}")

    cv.TITLE = f"Chapter {chapter['chapter']}: {chapter['title']}"
    cv.CHAPTER = chapter["chapter"]
    cv.SCRIPT = ". ".join(chapter["subtitles"])
    cv.SUBTITLES = chapter["subtitles"]
    cv.SCENES = [(f"scene_{i}", s) for i, s in enumerate(chapter["scenes"])]

    print("\n[1/5] Generating video...")
    cv.main()

    print("\n[2/5] Thumbnail...")
    save_thumbnail(chapter["chapter"], chapter["title"], config.OUTPUT_DIR)

    print("\n[3/5] SEO...")
    final_title = generate_title(chapter["chapter"], chapter["title"])
    hashtags = generate_hashtags()
    final_description = generate_description(chapter["chapter"], chapter["title"], cv.SCRIPT, hashtags)
    final_tags = generate_tags(chapter["chapter"], chapter["title"])

    print("\n[4/5] Uploading...")
    mp4s = sorted(Path("output").glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not mp4s:
        print("  No video!")
        return
    upload(str(mp4s[0]), final_title, final_description, final_tags, "public", "story")

    print(f"\n[5/5] Story Chapter {chapter['chapter']} done!")


def run_facts():
    print("=" * 55)
    print("  MODE: FACTS")
    print("=" * 55)

    from src.facts import generate_fact_script
    from src.seo import generate_hashtags
    import fact_video
    from upload_youtube import upload

    # Generate and render
    out_path, fact_data = fact_video.main()

    # SEO
    hashtags = generate_hashtags()
    desc = f"{fact_data['hook']}\n\n"
    for i, f in enumerate(fact_data["facts"], 1):
        desc += f"{i}. {f}\n"
    desc += f"\n#facts #{fact_data['niche'].replace(' ', '')} #shorts\n{hashtags}"

    tags = ["facts", fact_data["niche"], "shorts", "did you know", "mind blowing"] + fact_data["niche"].split()

    print("\nUploading...")
    upload(str(out_path), fact_data["title"], desc, tags, "public", "facts")
    print("Fact video done!")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "story"
    if mode == "story":
        run_story()
    elif mode == "facts":
        run_facts()
    else:
        print(f"Unknown mode: {mode}. Use 'story' or 'facts'")


if __name__ == "__main__":
    main()
