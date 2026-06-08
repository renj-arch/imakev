"""Brain — training data collector. Records every scene as a learning example."""
import json, os, time, hashlib
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent.parent / "brain_data.json"


class Dataset:
    """Records and manages training examples (scene compositions)."""

    def __init__(self, path=None):
        self.path = Path(path) if path else DATA_PATH
        self.examples = self._load()

    def _load(self):
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                return []
        return []

    def _save(self):
        self.path.write_text(json.dumps(self.examples, indent=2, ensure_ascii=False), encoding="utf-8")

    def add_scene(self, narration, elements, mood="peaceful", camera="LONG", duration=3.0, source="manual"):
        """Record a scene composition as a training example."""
        example = {
            "id": hashlib.md5(f"{narration}{time.time()}".encode()).hexdigest()[:8],
            "narration": narration,
            "mood": mood,
            "camera": camera,
            "duration": duration,
            "element_count": len(elements),
            "elements": [dict(e) for e in elements],
            "source": source,
            "timestamp": time.time(),
        }
        self.examples.append(example)
        self._save()
        return example["id"]

    def add_feedback(self, example_id, text, action):
        """Attach feedback to a training example."""
        for ex in self.examples:
            if ex["id"] == example_id:
                ex.setdefault("feedback", []).append({"text": text, "action": action})
                break
        self._save()

    def get_by_narration(self, keyword):
        """Find examples containing keyword in narration."""
        return [ex for ex in self.examples if keyword.lower() in ex["narration"].lower()]

    @property
    def count(self):
        return len(self.examples)

    def summary(self):
        """Return aggregate statistics across all examples."""
        from collections import Counter
        type_counts = Counter()
        total_elements = 0
        for ex in self.examples:
            for e in ex["elements"]:
                type_counts[e["type"]] += 1
                total_elements += 1
        moods = Counter(ex.get("mood", "unknown") for ex in self.examples)
        return {
            "total_scenes": self.count,
            "total_elements": total_elements,
            "element_types": dict(type_counts.most_common(20)),
            "moods": dict(moods),
            "avg_elements_per_scene": round(total_elements / max(self.count, 1), 1),
        }


_dataset = None


def get_dataset(path=None):
    global _dataset
    if _dataset is None:
        _dataset = Dataset(path)
    return _dataset


def record_scene(narration, elements, **kw):
    return get_dataset().add_scene(narration, elements, **kw)
