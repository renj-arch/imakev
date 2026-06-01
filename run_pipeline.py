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


def run_riddle():
    print("=" * 55)
    print("  MODE: RIDDLES")
    print("=" * 55)

    from upload_youtube import upload
    import riddle_video

    out_path, data = riddle_video.main()

    desc = f"{data['hook']}\n\n{data['riddle']}\n\nAnswer: {data['answer']}\n\n{data.get('explanation', '')}\n\n#riddles #brainteaser #shorts"
    tags = ["riddles", "brain teaser", "puzzle", "shorts", "fun", "challenge"]

    print("\nUploading...")
    upload(str(out_path), data["title"], desc, tags, "public", "riddles")
    print("Riddle video done!")
    bank_manager.ensure_refilled("riddles")


def run_wyr():
    print("=" * 55)
    print("  MODE: WOULD YOU RATHER")
    print("=" * 55)

    from upload_youtube import upload
    import would_you_rather_video

    out_path, data = would_you_rather_video.main()

    desc = f"{data['hook']} {data['option_a']} or {data['option_b']}?\n\nComment which one you'd pick! ⬇️\n\n#wouldyourather #shorts #fun"
    tags = ["would you rather", "fun", "shorts", "choose", "challenge"]

    print("\nUploading...")
    upload(str(out_path), data["title"], desc, tags, "public", "would_you_rather")
    print("Would You Rather video done!")
    bank_manager.ensure_refilled("would_you_rather")


def run_history_minute():
    print("=" * 55)
    print("  MODE: HISTORY MINUTE")
    print("=" * 55)

    from upload_youtube import upload
    import history_minute_video

    out_path, data = history_minute_video.main()

    desc = f"{data['hook']}\n\n{data['script']}\n\n#history #shorts #historyfacts"
    tags = ["history", "history facts", "shorts", "did you know", "history lesson", "educational"]

    print("\nUploading...")
    upload(str(out_path), data["title"], desc, tags, "public", "history_minute", made_for_kids=False)
    print("History Minute video done!")
    bank_manager.ensure_refilled("history_minute")


def run_psychology():
    print("=" * 55)
    print("  MODE: PSYCHOLOGY HACKS")
    print("=" * 55)

    from upload_youtube import upload
    import psychology_video

    out_path, data = psychology_video.main()

    desc = "Mind-blowing psychology hacks your brain doesn't want you to know.\n\n"
    for h, e in zip(data["hacks"], data["explanations"]):
        desc += f"{h}: {e}\n\n"
    desc += "#psychology #brainhacks #shorts #mindtricks"
    tags = ["psychology", "brain hacks", "mind tricks", "shorts", "self improvement", "mental health"]

    print("\nUploading...")
    upload(str(out_path), data["title"], desc, tags, "public", "psychology")
    print("Psychology video done!")
    bank_manager.ensure_refilled("psychology")


def run_life_hacks():
    print("=" * 55)
    print("  MODE: LIFE HACKS")
    print("=" * 55)

    from upload_youtube import upload
    import life_hacks_video

    out_path, data = life_hacks_video.main()

    desc = "Life hacks that actually work.\n\n"
    for h, e in zip(data["hacks"], data["explanations"]):
        desc += f"{h}: {e}\n\n"
    desc += "#lifehacks #shorts #tips #hacks"
    tags = ["life hacks", "tips", "shorts", "diy", "household hacks", "clever"]

    print("\nUploading...")
    upload(str(out_path), data["title"], desc, tags, "public", "life_hacks")
    print("Life Hacks video done!")
    bank_manager.ensure_refilled("life_hacks")


def run_urban_legends():
    print("=" * 55)
    print("  MODE: URBAN LEGENDS")
    print("=" * 55)

    from upload_youtube import upload
    import urban_legends_video

    out_path, data = urban_legends_video.main()

    desc = f"{data['hook']}\n\n{data['legend']}\n\nTHE MYTH:\n{data['myth']}\n\nTHE TRUTH:\n{data['truth']}\n\n#urbanlegends #shorts #mythsdebunked"
    tags = ["urban legends", "myths", "debunked", "shorts", "creepy", "truth"]

    print("\nUploading...")
    upload(str(out_path), data["title"], desc, tags, "public", "urban_legends")
    print("Urban Legends video done!")
    bank_manager.ensure_refilled("urban_legends")


def run_coincidences():
    print("=" * 55)
    print("  MODE: COINCIDENCES")
    print("=" * 55)

    from upload_youtube import upload
    import coincidences_video

    out_path, data = coincidences_video.main()

    desc = "Real coincidences that sound fake but are 100% true.\n\n"
    for title, story in zip(data["coincidences"], data["stories"]):
        desc += f"{title}: {story}\n\n"
    desc += "#coincidences #truestories #shorts #mindblown #didyouknow"
    tags = ["coincidences", "true stories", "shorts", "mind blown", "amazing", "unbelievable", "did you know"]

    print("\nUploading...")
    upload(str(out_path), data["title"], desc, tags, "public", "coincidences")
    print("Coincidences video done!")
    bank_manager.ensure_refilled("coincidences")


def run_unsolved_mysteries():
    print("=" * 55)
    print("  MODE: UNSOLVED MYSTERIES")
    print("=" * 55)

    from upload_youtube import upload
    import unsolved_mysteries_video

    out_path, data = unsolved_mysteries_video.main()

    desc = "Real unsolved mysteries that still baffle investigators.\n\n"
    for title, story in zip(data["mysteries"], data["stories"]):
        desc += f"{title}: {story}\n\n"
    desc += "What do you think happened? Comment below.\n\n#unsolvedmysteries #truecrime #shorts #mystery"
    tags = ["unsolved mysteries", "true crime", "shorts", "mystery", "cold case", "creepy", "unsolved"]

    print("\nUploading...")
    upload(str(out_path), data["title"], desc, tags, "public", "unsolved_mysteries")
    print("Unsolved Mysteries video done!")
    bank_manager.ensure_refilled("unsolved_mysteries")


def run_movie_trivia():
    print("=" * 55)
    print("  MODE: MOVIE TRIVIA")
    print("=" * 55)

    from upload_youtube import upload
    import movie_trivia_video

    out_path, data = movie_trivia_video.main()

    desc = "Real behind-the-scenes movie secrets you never knew.\n\n"
    for title, story in zip(data["trivia_titles"], data["stories"]):
        desc += f"{title}: {story}\n\n"
    desc += "#movietrivia #behindthescenes #shorts #hollywood #moviefacts"
    tags = ["movie trivia", "behind the scenes", "shorts", "hollywood", "movie facts", "cinema", "did you know"]

    print("\nUploading...")
    upload(str(out_path), data["title"], desc, tags, "public", "movie_trivia")
    print("Movie Trivia video done!")
    bank_manager.ensure_refilled("movie_trivia")


def run_animal_kingdom():
    print("=" * 55)
    print("  MODE: ANIMAL KINGDOM")
    print("=" * 55)

    from upload_youtube import upload
    import animal_kingdom_video

    out_path, data = animal_kingdom_video.main()

    desc = "Incredible animal facts from around the world.\n\n"
    for title, story in zip(data["animal_facts"], data["stories"]):
        desc += f"{title}: {story}\n\n"
    desc += "#animals #animalfacts #shorts #nature #wildlife"
    tags = ["animals", "animal facts", "shorts", "nature", "wildlife", "amazing animals", "did you know"]

    print("\nUploading...")
    upload(str(out_path), data["title"], desc, tags, "public", "animal_kingdom")
    print("Animal Kingdom video done!")
    bank_manager.ensure_refilled("animal_kingdom")


def run_space_wonders():
    print("=" * 55)
    print("  MODE: SPACE WONDERS")
    print("=" * 55)

    from upload_youtube import upload
    import space_wonders_video

    out_path, data = space_wonders_video.main()

    desc = "Incredible space facts from NASA and astronomy.\n\n"
    for title, story in zip(data["space_facts"], data["stories"]):
        desc += f"{title}: {story}\n\n"
    desc += "#space #astronomy #shorts #nasa #universe"
    tags = ["space", "astronomy", "shorts", "nasa", "universe", "space facts", "mind blown"]

    print("\nUploading...")
    upload(str(out_path), data["title"], desc, tags, "public", "space_wonders")
    print("Space Wonders video done!")
    bank_manager.ensure_refilled("space_wonders")


def run_box_office():
    print("=" * 55)
    print("  MODE: BOX OFFICE")
    print("=" * 55)

    from upload_youtube import upload
    import box_office_video

    out_path, data = box_office_video.main()

    desc = "Incredible box office facts and movie earnings records.\n\n"
    for title, story in zip(data["box_office_titles"], data["stories"]):
        desc += f"{title}: {story}\n\n"
    desc += "#boxoffice #movies #shorts #hollywood #moviefacts"
    tags = ["box office", "movies", "shorts", "hollywood", "movie facts", "earnings", "film records"]

    print("\nUploading...")
    upload(str(out_path), data["title"], desc, tags, "public", "box_office")
    print("Box Office video done!")
    bank_manager.ensure_refilled("box_office")


def run_upsc():
    print("=" * 55)
    print("  MODE: UPSC CONCEPTS")
    print("=" * 55)

    from upload_youtube import upload
    import upsc_video

    out_path, data = upsc_video.main()

    desc = "UPSC concept explained in 60 seconds.\n\n"
    for t, e in zip(data["topics"], data["explanations"]):
        desc += f"{t}: {e}\n\n"
    desc += "#upsc #upscpreparation #upscexam #shorts #cse #ias #upscconcepts #competitiveexams"
    tags = ["upsc", "upsc preparation", "upsc exam", "shorts", "ias", "civil services", "upsc concepts", "competitive exams", "upsc syllabus", "upsc prelims"]

    print("\nUploading...")
    upload(str(out_path), data["title"], desc, tags, "public", "upsc", made_for_kids=False)
    print("UPSC video done!")
    bank_manager.ensure_refilled("upsc")


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
    elif mode == "riddles":
        run_riddle()
    elif mode == "would_you_rather":
        run_wyr()
    elif mode == "history_minute":
        run_history_minute()
    elif mode == "psychology":
        run_psychology()
    elif mode == "life_hacks":
        run_life_hacks()
    elif mode == "urban_legends":
        run_urban_legends()
    elif mode == "coincidences":
        run_coincidences()
    elif mode == "unsolved_mysteries":
        run_unsolved_mysteries()
    elif mode == "movie_trivia":
        run_movie_trivia()
    elif mode == "animal_kingdom":
        run_animal_kingdom()
    elif mode == "space_wonders":
        run_space_wonders()
    elif mode == "box_office":
        run_box_office()
    elif mode == "upsc":
        run_upsc()
    else:
        print(f"Unknown mode: {mode}. Use 'story', 'facts', 'what_if', 'how_it_works', 'riddles', 'would_you_rather', 'history_minute', 'psychology', 'life_hacks', 'urban_legends', 'coincidences', 'unsolved_mysteries', 'movie_trivia', 'animal_kingdom', 'space_wonders', 'box_office', or 'upsc'")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"PIPELINE CRASHED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
