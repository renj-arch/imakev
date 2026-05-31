"""Wrapper that runs pipeline with retries and logging - for unattended operation."""

import sys, time, traceback
from pathlib import Path
from datetime import datetime

LOG_FILE = Path(__file__).parent / "pipeline_log.txt"
MAX_RETRIES = 3


def log(msg: str):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main():
    log("=" * 50)
    log("Pipeline started")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            import run_pipeline
            run_pipeline.main()
            log("Pipeline completed successfully")
            return
        except Exception as e:
            log(f"Attempt {attempt}/{MAX_RETRIES} FAILED: {e}")
            traceback.print_exc()
            if attempt < MAX_RETRIES:
                wait = attempt * 60
                log(f"Retrying in {wait}s...")
                time.sleep(wait)

    log("All attempts failed. Will retry on next schedule.")
    sys.exit(1)


if __name__ == "__main__":
    main()
