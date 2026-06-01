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

    print("\n[2/5] Uploading with viral SEO & thumbnail...")
    mp4s = sorted(Path("output").glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not mp4s:
        print("  No video!")
        return
    upload(str(mp4s[0]), mode="story", playlist_key="story", script_data=chapter)

    print(f"\n[3/5] Story Chapter {chapter['chapter']} done!")


def run_facts():
    print("=" * 55)
    print("  MODE: FACTS")
    print("=" * 55)

    from src.facts import generate_fact_script
    from upload_youtube import upload
    import fact_video

    out_path, fact_data = fact_video.main()

    print("\nUploading with viral SEO...")
    upload(str(out_path), mode="facts", playlist_key="facts", script_data=fact_data)
    print("Fact video done!")
    bank_manager.ensure_refilled("facts")


def run_what_if():
    print("=" * 55)
    print("  MODE: WHAT IF?")
    print("=" * 55)

    from upload_youtube import upload
    import what_if_video

    out_path, data = what_if_video.main()
    print("\nUploading with viral SEO...")
    upload(str(out_path), mode="what_if", playlist_key="what_if", script_data=data)
    print("What If video done!")
    bank_manager.ensure_refilled("what_if")


def run_how_it_works():
    print("=" * 55)
    print("  MODE: HOW IT WORKS")
    print("=" * 55)

    from upload_youtube import upload
    import how_it_works_video

    out_path, data = how_it_works_video.main()
    print("\nUploading with viral SEO...")
    upload(str(out_path), mode="how_it_works", playlist_key="how_it_works", script_data=data, made_for_kids=False)
    print("How It Works video done!")
    bank_manager.ensure_refilled("how_it_works")


def run_riddle():
    print("=" * 55)
    print("  MODE: RIDDLES")
    print("=" * 55)

    from upload_youtube import upload
    import riddle_video

    out_path, data = riddle_video.main()
    print("\nUploading with viral SEO...")
    upload(str(out_path), mode="riddles", playlist_key="riddles", script_data=data)
    print("Riddle video done!")
    bank_manager.ensure_refilled("riddles")


def run_wyr():
    print("=" * 55)
    print("  MODE: WOULD YOU RATHER")
    print("=" * 55)

    from upload_youtube import upload
    import would_you_rather_video

    out_path, data = would_you_rather_video.main()
    print("\nUploading with viral SEO...")
    upload(str(out_path), mode="would_you_rather", playlist_key="would_you_rather", script_data=data)
    print("Would You Rather video done!")
    bank_manager.ensure_refilled("would_you_rather")


def run_history_minute():
    print("=" * 55)
    print("  MODE: HISTORY MINUTE")
    print("=" * 55)

    from upload_youtube import upload
    import history_minute_video

    out_path, data = history_minute_video.main()
    print("\nUploading with viral SEO...")
    upload(str(out_path), mode="history_minute", playlist_key="history_minute", script_data=data, made_for_kids=False)
    print("History Minute video done!")
    bank_manager.ensure_refilled("history_minute")


def run_psychology():
    print("=" * 55)
    print("  MODE: PSYCHOLOGY HACKS")
    print("=" * 55)

    from upload_youtube import upload
    import psychology_video

    out_path, data = psychology_video.main()
    print("\nUploading with viral SEO...")
    upload(str(out_path), mode="psychology", playlist_key="psychology", script_data=data)
    print("Psychology video done!")
    bank_manager.ensure_refilled("psychology")


def run_life_hacks():
    print("=" * 55)
    print("  MODE: LIFE HACKS")
    print("=" * 55)

    from upload_youtube import upload
    import life_hacks_video

    out_path, data = life_hacks_video.main()
    print("\nUploading with viral SEO...")
    upload(str(out_path), mode="life_hacks", playlist_key="life_hacks", script_data=data)
    print("Life Hacks video done!")
    bank_manager.ensure_refilled("life_hacks")


def run_urban_legends():
    print("=" * 55)
    print("  MODE: URBAN LEGENDS")
    print("=" * 55)

    from upload_youtube import upload
    import urban_legends_video

    out_path, data = urban_legends_video.main()
    print("\nUploading with viral SEO...")
    upload(str(out_path), mode="urban_legends", playlist_key="urban_legends", script_data=data)
    print("Urban Legends video done!")
    bank_manager.ensure_refilled("urban_legends")


def run_coincidences():
    print("=" * 55)
    print("  MODE: COINCIDENCES")
    print("=" * 55)

    from upload_youtube import upload
    import coincidences_video

    out_path, data = coincidences_video.main()
    print("\nUploading with viral SEO...")
    upload(str(out_path), mode="coincidences", playlist_key="coincidences", script_data=data)
    print("Coincidences video done!")
    bank_manager.ensure_refilled("coincidences")


def run_unsolved_mysteries():
    print("=" * 55)
    print("  MODE: UNSOLVED MYSTERIES")
    print("=" * 55)

    from upload_youtube import upload
    import unsolved_mysteries_video

    out_path, data = unsolved_mysteries_video.main()
    print("\nUploading with viral SEO...")
    upload(str(out_path), mode="unsolved_mysteries", playlist_key="unsolved_mysteries", script_data=data)
    print("Unsolved Mysteries video done!")
    bank_manager.ensure_refilled("unsolved_mysteries")


def run_movie_trivia():
    print("=" * 55)
    print("  MODE: MOVIE TRIVIA")
    print("=" * 55)

    from upload_youtube import upload
    import movie_trivia_video

    out_path, data = movie_trivia_video.main()
    print("\nUploading with viral SEO...")
    upload(str(out_path), mode="movie_trivia", playlist_key="movie_trivia", script_data=data)
    print("Movie Trivia video done!")
    bank_manager.ensure_refilled("movie_trivia")


def run_animal_kingdom():
    print("=" * 55)
    print("  MODE: ANIMAL KINGDOM")
    print("=" * 55)

    from upload_youtube import upload
    import animal_kingdom_video

    out_path, data = animal_kingdom_video.main()
    print("\nUploading with viral SEO...")
    upload(str(out_path), mode="animal_kingdom", playlist_key="animal_kingdom", script_data=data)
    print("Animal Kingdom video done!")
    bank_manager.ensure_refilled("animal_kingdom")


def run_space_wonders():
    print("=" * 55)
    print("  MODE: SPACE WONDERS")
    print("=" * 55)

    from upload_youtube import upload
    import space_wonders_video

    out_path, data = space_wonders_video.main()
    print("\nUploading with viral SEO...")
    upload(str(out_path), mode="space_wonders", playlist_key="space_wonders", script_data=data)
    print("Space Wonders video done!")
    bank_manager.ensure_refilled("space_wonders")


def run_things():
    print("=" * 55)
    print("  MODE: THINGS THEY DON'T TEACH YOU")
    print("=" * 55)

    from upload_youtube import upload
    import things_they_dont_teach_video

    out_path, data = things_they_dont_teach_video.main()
    print("\nUploading with viral SEO...")
    upload(str(out_path), mode="things_they_dont_teach", playlist_key="things_they_dont_teach", script_data=data, made_for_kids=False)
    print("Things They Don't Teach You video done!")
    bank_manager.ensure_refilled("things_they_dont_teach")


def run_box_office():
    print("=" * 55)
    print("  MODE: BOX OFFICE")
    print("=" * 55)

    from upload_youtube import upload
    import box_office_video

    out_path, data = box_office_video.main()
    print("\nUploading with viral SEO...")
    upload(str(out_path), mode="box_office", playlist_key="box_office", script_data=data)
    print("Box Office video done!")
    bank_manager.ensure_refilled("box_office")


def run_challenges():
    print("=" * 55)
    print("  MODE: CHALLENGES & STUNTS")
    print("=" * 55)

    from upload_youtube import upload
    import challenges_video

    out_path, data = challenges_video.main()
    print("\nUploading with viral SEO...")
    upload(str(out_path), mode="challenges", playlist_key="challenges", script_data=data, made_for_kids=False)
    print("Challenges video done!")
    bank_manager.ensure_refilled("challenges")


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
    elif mode == "things_they_dont_teach":
        run_things()
    elif mode == "challenges":
        run_challenges()
    else:
        print(f"Unknown mode: {mode}. Use 'story', 'facts', 'what_if', 'how_it_works', 'riddles', 'would_you_rather', 'history_minute', 'psychology', 'life_hacks', 'urban_legends', 'coincidences', 'unsolved_mysteries', 'movie_trivia', 'animal_kingdom', 'space_wonders', 'box_office', 'things_they_dont_teach', or 'challenges'")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"PIPELINE CRASHED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
