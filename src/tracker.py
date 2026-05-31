"""Tracks which items have been used across runs via JSON file. Resets when exhausted."""

import json, random
from pathlib import Path
import config

TRACKER_DIR = config.TEMP_DIR / "trackers"

def pick(name: str, items: list, count: int = 5) -> list:
    """Pick `count` unused items from `items`. Resets when all used."""
    TRACKER_DIR.mkdir(exist_ok=True)
    path = TRACKER_DIR / f"{name}.json"
    used: set[int] = set()
    if path.exists():
        used = set(json.loads(path.read_text()))
    available = [i for i in range(len(items)) if i not in used]
    if len(available) < count:
        used = set()
        available = list(range(len(items)))
    chosen = random.sample(available, min(count, len(available)))
    used.update(chosen)
    path.write_text(json.dumps(list(used)))
    return [items[i] for i in chosen]


def reset(name: str):
    path = TRACKER_DIR / f"{name}.json"
    if path.exists():
        path.unlink()
