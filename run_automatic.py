"""Wrapper that alternates modes every run with retries, logging, and analytics."""

import sys, time, traceback, json
from pathlib import Path
from datetime import datetime

LOG_FILE = Path(__file__).parent / "pipeline_log.txt"
MAX_RETRIES = 2
COUNTER_FILE = Path(__file__).parent / "run_counter.txt"
PERF_FILE = Path(__file__).parent / "performance.json"


def log(msg: str):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


MODES = ["how_it_works", "facts"]

def get_mode() -> str:
    count = 0
    if COUNTER_FILE.exists():
        count = int(COUNTER_FILE.read_text().strip() or "0")
    count += 1
    COUNTER_FILE.write_text(str(count))
    return MODES[(count - 1) % len(MODES)]


def print_report():
    """Print performance analytics from performance.json."""
    if not PERF_FILE.exists():
        log("No performance data yet. Run the pipeline first.")
        return
    data = json.loads(PERF_FILE.read_text())
    videos = data.get("videos", [])
    if not videos:
        log("No videos recorded.")
        return
    mode_counts = {}
    for v in videos:
        m = v.get("mode", "unknown")
        mode_counts[m] = mode_counts.get(m, 0) + 1
    log(f"Total videos uploaded: {len(videos)}")
    log("Per mode:")
    for mode, count in sorted(mode_counts.items(), key=lambda x: -x[1]):
        log(f"  {mode}: {count}")
    log(f"Latest video: https://youtu.be/{videos[-1]['video_id']} ({videos[-1]['title']})")
    log(f"Uploaded at: {videos[-1]['uploaded_at']}")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--report":
        print_report()
        return
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
