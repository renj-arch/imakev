"""Full automated pipeline: story / facts / what_if modes."""

import sys
from pathlib import Path
import config
import bank_manager


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
    from upload_youtube import upload
    import fact_video

    out_path, fact_data = fact_video.main()

    hashtags = generate_hashtags(8)
    desc = f"{fact_data['hook']}\n\n"
    for i, f in enumerate(fact_data["facts"], 1):
        desc += f"{i}. {f}\n"
    desc += f"\n#facts #shorts\n{hashtags}"
    tags = ["facts", fact_data["niche"], "shorts", "did you know", "fun facts"]

    print("\nUploading...")
    upload(str(out_path), fact_data["title"], desc, tags, "public", "facts")
    print("Fact video done!")
    bank_manager.ensure_refilled("facts")


def run_what_if():
    print("=" * 55)
    print("  MODE: WHAT IF?")
    print("=" * 55)

    from upload_youtube import upload
    import what_if_video

    out_path, data = what_if_video.main()

    desc = f"{data['hook']}\n\n"
    for s, e in zip(data["scenarios"], data["explanations"]):
        desc += f"What if {s}? {e}\n\n"
    desc += "#whatif #imagination #kidsshorts #shorts"
    tags = ["what if", "imagination", "kids shorts", "curiosity", "wonder", "fun"]

    print("\nUploading...")
    upload(str(out_path), data["title"], desc, tags, "public", "what_if")
    print("What If video done!")
    bank_manager.ensure_refilled("what_if")


def run_how_it_works():
    print("=" * 55)
    print("  MODE: HOW IT WORKS")
    print("=" * 55)

    from upload_youtube import upload
    import how_it_works_video

    out_path, data = how_it_works_video.main()

    desc = "Ever wondered how everyday things work?\n\n"
    for t, e in zip(data["topics"], data["explanations"]):
        desc += f"{t.capitalize()}: {e}\n\n"
    desc += "#howitworks #science #shorts #engineering"
    tags = ["how it works", "science", "engineering", "shorts", "education", "explained"]

    print("\nUploading...")
    upload(str(out_path), data["title"], desc, tags, "public", "how_it_works", made_for_kids=False)
    print("How It Works video done!")
    bank_manager.ensure_refilled("how_it_works")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "story"
    if mode == "story":
        run_story()
    elif mode == "facts":
        run_facts()
    elif mode == "what_if":
        run_what_if()
    elif mode == "how_it_works":
        run_how_it_works()
    else:
        print(f"Unknown mode: {mode}. Use 'story', 'facts', 'what_if', or 'how_it_works'")


if __name__ == "__main__":
    main()
