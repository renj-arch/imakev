"""Wrapper that alternates story/facts every run with retries and logging."""

import sys, time, traceback
from pathlib import Path
from datetime import datetime

LOG_FILE = Path(__file__).parent / "pipeline_log.txt"
MAX_RETRIES = 2
COUNTER_FILE = Path(__file__).parent / "run_counter.txt"


def log(msg: str):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


MODES = ["story", "facts", "what_if", "how_it_works", "riddles", "would_you_rather", "history_minute", "psychology", "life_hacks", "urban_legends", "coincidences", "unsolved_mysteries", "movie_trivia", "animal_kingdom", "space_wonders", "box_office", "upsc", "neet"]

def get_mode() -> str:
    count = 0
    if COUNTER_FILE.exists():
        count = int(COUNTER_FILE.read_text().strip() or "0")
    count += 1
    COUNTER_FILE.write_text(str(count))
    return MODES[(count - 1) % len(MODES)]


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else get_mode()
    log(f"=" * 50)
    log(f"Pipeline started - MODE: {mode}")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            sys.argv = [sys.argv[0], mode]
            import run_pipeline
            run_pipeline.main()
            log(f"Pipeline completed ({mode})")
            return
        except Exception as e:
            log(f"Attempt {attempt}/{MAX_RETRIES} FAILED: {e}")
            traceback.print_exc()
            if attempt < MAX_RETRIES:
                wait = attempt * 60
                log(f"Retrying in {wait}s...")
                time.sleep(wait)

    log(f"All attempts failed for {mode}. Will retry next run.")
    sys.exit(1)


if __name__ == "__main__":
    main()
