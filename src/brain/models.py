"""Brain — statistical models that learn element patterns from training data."""
import json, math, re
from collections import Counter, defaultdict
from pathlib import Path

MODEL_PATH = Path(__file__).parent.parent.parent / "brain_model.json"

STOP_WORDS = {"the","a","an","and","or","but","in","on","at","to","for","of","with",
              "by","from","as","was","were","had","have","has","been","its","their",
              "them","they","this","that","these","those","it","is","are","not","no",
              "about","around","then","also","very","just","could","would","all",
              "some","each","every","into","over","after","before","between","when"}


class BrainModel:
    """Learns element composition patterns from training examples."""

    def __init__(self, path=None):
        self.path = Path(path) if path else MODEL_PATH
        self.model = self._load()

    def _load(self):
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return self._empty_model()

    def _empty_model(self):
        return {
            "keywords": {},           # keyword -> {element_type -> count}
            "element_stats": {},      # element_type -> {x_mean, x_std, y_mean, y_std, scale_mean, scale_std, count}
            "cooccurrence": {},       # element_type -> {other_type -> count}
            "mood_elements": {},      # mood -> {element_type -> count}
            "pair_sequences": [],     # [ (prev_type, next_type) ] for sequence learning
            "total_scenes": 0,
            "version": 1,
        }

    def _save(self):
        self.path.write_text(json.dumps(self.model, indent=2, ensure_ascii=False), encoding="utf-8")

    def extract_keywords(self, text):
        """Extract meaningful keywords from narration text."""
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        return [w for w in words if w not in STOP_WORDS]

    def train(self, examples):
        """Train on a list of scene examples from the dataset."""
        m = self.model
        for ex in examples:
            m["total_scenes"] += 1
            keywords = self.extract_keywords(ex.get("narration", ""))
            mood = ex.get("mood", "peaceful")
            elems = ex.get("elements", [])

            # Track which element types appeared
            appeared_types = set()

            for i, elem in enumerate(elems):
                etype = elem["type"]
                appeared_types.add(etype)
                x, y, s = elem.get("x", 0.5), elem.get("y", 0.5), elem.get("scale", 1.0)

                # Keyword → element mapping
                for kw in keywords:
                    if kw not in m["keywords"]:
                        m["keywords"][kw] = {}
                    m["keywords"][kw][etype] = m["keywords"][kw].get(etype, 0) + 1

                # Element position/scale statistics (online update)
                if etype not in m["element_stats"]:
                    m["element_stats"][etype] = {"count":0, "x_sum":0, "y_sum":0, "s_sum":0,
                                                  "x_ss":0, "y_ss":0, "s_ss":0}
                st = m["element_stats"][etype]
                st["count"] += 1
                st["x_sum"] += x
                st["y_sum"] += y
                st["s_sum"] += s

                # Sequence pairs
                if i > 0:
                    m["pair_sequences"].append([elems[i-1]["type"], etype])

            # Mood → element mapping
            if mood not in m["mood_elements"]:
                m["mood_elements"][mood] = {}
            for et in appeared_types:
                m["mood_elements"][mood][et] = m["mood_elements"][mood].get(et, 0) + 1

            # Co-occurrence
            for et1 in appeared_types:
                if et1 not in m["cooccurrence"]:
                    m["cooccurrence"][et1] = {}
                for et2 in appeared_types:
                    if et1 != et2:
                        m["cooccurrence"][et1][et2] = m["cooccurrence"][et1].get(et2, 0) + 1

        self._save()

    def keywords_for_type(self, etype, top=10):
        """Return keywords most associated with an element type."""
        scores = []
        for kw, types in self.model["keywords"].items():
            if etype in types:
                scores.append((types[etype], kw))
        return [(kw, cnt) for cnt, kw in sorted(scores, reverse=True)[:top]]

    def top_elements_for_keyword(self, keyword, top=5):
        """Return element types most associated with a keyword."""
        kw_data = self.model["keywords"].get(keyword, {})
        if not kw_data:
            return []
        total = sum(kw_data.values())
        return sorted([(et, cnt/total) for et, cnt in kw_data.items()], key=lambda x: -x[1])[:top]

    def predict_elements(self, narration, mood="peaceful", count_range=(2, 6)):
        """Predict scene elements from narration text — the core intelligence."""
        keywords = self.extract_keywords(narration)
        m = self.model

        # Score each potential element type
        scores = defaultdict(float)

        # 1. Keyword matching
        for kw in keywords:
            if kw in m["keywords"]:
                total = sum(m["keywords"][kw].values())
                for etype, cnt in m["keywords"][kw].items():
                    scores[etype] += cnt / total

        # 2. Mood prior
        mood_data = m["mood_elements"].get(mood, {})
        if mood_data:
            mood_total = sum(mood_data.values())
            for etype, cnt in mood_data.items():
                scores[etype] += 0.3 * cnt / mood_total

        # 3. Co-occurrence boost
        top_types = [et for et, _ in sorted(scores.items(), key=lambda x: -x[1])[:3]]
        for et in top_types:
            if et in m["cooccurrence"]:
                for other, cnt in m["cooccurrence"][et].items():
                    if other not in scores or scores[other] < 0.5:
                        scores[other] += 0.15 * cnt / (m["element_stats"].get(other, {}).get("count", 1) or 1)

        if not scores:
            return []

        # Sort and filter
        ranked = sorted(scores.items(), key=lambda x: -x[1])
        min_count, max_count = count_range

        # Pick top elements with score above threshold
        threshold = max(0.05, ranked[0][1] * 0.3) if ranked else 0
        selected = [(et, sc) for et, sc in ranked if sc >= threshold][:max_count]
        if len(selected) < min_count:
            selected = ranked[:min_count]

        # Assign positions and scales from learned distributions
        elements = []
        used_x = set()
        for etype, score in selected:
            stats = m["element_stats"].get(etype, {})

            x = stats.get("x_mean", 0.5) if stats.get("count", 0) > 0 else 0.5
            y = stats.get("y_mean", 0.7) if stats.get("count", 0) > 0 else 0.65
            scale = stats.get("s_mean", 2.5) if stats.get("count", 0) > 0 else 2.5

            attempts = 0
            while attempts < 20 and any(abs(x - ux) < 0.12 for ux in used_x):
                x = min(0.88, x + 0.12)
                attempts += 1
            used_x.add(round(x, 2))

            elements.append({
                "type": etype,
                "x": round(x, 2),
                "y": round(y, 2),
                "scale": round(scale, 1),
                "_confidence": round(score, 3),
            })

        return elements

    def get_prior(self, etype):
        """Get learned position/scale prior for an element type."""
        stats = self.model["element_stats"].get(etype)
        if not stats or stats["count"] == 0:
            return {"x": 0.5, "y": 0.6, "scale": 2.5}
        return {
            "x": round(stats["x_sum"] / stats["count"], 2),
            "y": round(stats["y_sum"] / stats["count"], 2),
            "scale": round(stats["s_sum"] / stats["count"], 1),
            "count": stats["count"],
        }

    def get_sequence(self, prev_type):
        """Given previous element type, predict the next."""
        pairs = self.model["pair_sequences"]
        if not pairs:
            return None
        counts = Counter()
        for a, b in pairs:
            if a == prev_type:
                counts[b] += 1
        if counts:
            return counts.most_common(1)[0][0]
        return None

    def summary(self):
        m = self.model
        return {
            "total_scenes": m["total_scenes"],
            "keywords_known": len(m["keywords"]),
            "element_types_learned": list(m["element_stats"].keys()),
            "cooccurrence_pairs": sum(len(v) for v in m["cooccurrence"].values()),
            "sequence_pairs": len(m["pair_sequences"]),
        }

    def learn_from_feedback(self, element_type, adjustment):
        """Adjust model weights based on feedback (simulated gradient update)."""
        stats = self.model["element_stats"].get(element_type)
        if not stats or stats["count"] == 0:
            return

        if "scale_max" in adjustment:
            # Reduce scale influence by adding a fake data point at smaller scale
            stats["s_sum"] = stats["s_sum"] * 0.9 + adjustment["scale_max"] * stats["count"] * 0.1

        if "y_min" in adjustment:
            stats["y_sum"] = stats["y_sum"] * 0.9 + adjustment["y_min"] * stats["count"] * 0.1

        self._save()


_brain = None


def get_brain(path=None):
    global _brain
    if _brain is None:
        _brain = BrainModel(path)
    return _brain


def train_from_dataset(dataset_path=None, brain_path=None):
    from .dataset import Dataset
    ds = Dataset(dataset_path)
    brain = BrainModel(brain_path)
    brain.train(ds.examples)
    return brain
