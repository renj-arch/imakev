"""Concept Recognition Accuracy Benchmark.

Measures how well visual language communicates the intended emotional arc
without relying on narration text.

For each story, we compare:
  - Expected emotional signals (from archetype emotion_arc)
  - Actual visual signals (warmth, brightness, posture, gaze from directives)

Outputs a per-story clarity score + summary.
"""
import sys, os, random, json
sys.path.insert(0, os.path.dirname(__file__))

from src.narrative_engines import NarrativeEngine
from src.emotion_tracker import EmotionTracker
from src.relationship_tracker import RelationshipTracker
from src.concept_visuals import ConceptVisualsTranslator
from src.concept_extractor import extract_concepts
from src.director import Director, direct_narration_with_archetype
import re

OUT_DIR = os.path.join(os.path.dirname(__file__), "benchmark")
os.makedirs(OUT_DIR, exist_ok=True)

# ── Test stories (same as _benchmark.py) ──

STORIES = [
    ("curiosity_defeats_fear", (
        "Curiosity defeats fear. "
        "A child approached the dark cave. "
        "Something flickered inside. "
        "Heart pounded. "
        "But wonder pulled harder. "
        "She stepped forward and found light."
    )),
    ("cost_of_power", (
        "A young leader accepted the crown. "
        "The kingdom grew powerful. "
        "Armies conquered neighboring lands. "
        "But power demanded sacrifice. "
        "Allies became enemies. "
        "The throne grew cold. "
        "In the end, he sat alone."
    )),
    ("community_comes_together", (
        "The village was scattered after the storm. "
        "Families sheltered in ruins. "
        "A woman shared her food. "
        "Others began helping. "
        "They rebuilt a barn together. "
        "Strangers became neighbors. "
        "The village was stronger than before."
    )),
    ("knowledge_spreads", (
        "A scholar discovered a truth. "
        "She wrote it on parchment. "
        "Travelers carried the words. "
        "Villages heard the message. "
        "People began to understand. "
        "The knowledge crossed mountains. "
        "It changed how everyone thought."
    )),
    ("empire_declines", (
        "The great city was magnificent. "
        "Trade brought endless wealth. "
        "But corruption grew in shadows. "
        "The walls began to crack. "
        "Invaders came from the north. "
        "The empire crumbled. "
        "Only dust remained."
    )),
    ("hope_after_disaster", (
        "The volcano had destroyed everything. "
        "Ash covered the fields. "
        "Survivors wandered in grey silence. "
        "A child found a green sprout. "
        "Others began searching. "
        "Small flowers appeared. "
        "The people dared to plant again."
    )),
]

# Expected emotion models for each archetype
# Maps: archetype_name -> {emotion_dim -> [value_per_phase]}
# Values are 0-10 scale from ARCHETYPE_DEFS emotion_arc
ARCHETYPE_EMOTION_MODELS = {
    "transformation": {
        "curiosity": [5, 7, 6, 4],
        "trust":     [3, 2, 5, 8],
        "fear":      [5, 7, 4, 2],
    },
    "mystery": {
        "curiosity": [6, 8, 7, 5],
        "fear":      [7, 5, 6, 8],
        "hope":      [2, 3, 4, 8],
    },
    "disaster": {
        "fear":      [2, 4, 8, 8, 5],
        "hope":      [5, 3, 1, 1, 6],
        "despair":   [1, 2, 5, 7, 3],
    },
    "journey": {
        "hope":      [8, 4, 2, 5, 8],
        "fear":      [2, 6, 7, 4, 2],
        "curiosity": [5, 7, 6, 5, 4],
    },
    "rise_and_fall": {
        "hope":      [8, 7, 3, 1, 2],
        "trust":     [6, 5, 3, 1, 2],
        "fear":      [2, 3, 5, 7, 4],
        "satisfaction": [4, 8, 7, 1, 1],
    },
    "survival": {
        "fear":      [6, 8, 7, 4, 3],
        "hope":      [3, 2, 5, 7, 8],
        "despair":   [4, 6, 5, 3, 2],
    },
    "first_contact": {
        "fear":      [6, 8, 5, 3, 2],
        "curiosity": [7, 6, 8, 5, 4],
        "trust":     [1, 2, 5, 7, 8],
    },
    "discovery": {
        "curiosity": [7, 8, 6, 4, 3],
        "fear":      [4, 3, 2, 5, 3],
        "awe":       [2, 3, 6, 8, 7],
        "hope":      [3, 4, 5, 7, 8],
    },
    "migration": {
        "hope":      [7, 4, 3, 5, 8],
        "fear":      [3, 6, 7, 4, 2],
        "despair":   [1, 4, 5, 3, 2],
    },
    "war": {
        "fear":      [5, 8, 8, 6, 3],
        "anger":     [3, 6, 8, 7, 4],
        "despair":   [1, 3, 5, 7, 6],
        "hope":      [5, 3, 2, 1, 4],
    },
}

# How each concept maps to visual signals
# Range 0.0-1.0 for numeric; expected string values for posture/gaze
CONCEPT_VISUAL_SIGNATURES = {
    "fear":      {"warmth": 0.2, "brightness": 0.2, "posture": "closed", "gaze": "away", "elevation": 0.3, "prominence": 0.3},
    "trust":     {"warmth": 0.8, "brightness": 0.7, "posture": "open", "gaze": "toward", "elevation": 0.5, "prominence": 0.5},
    "curiosity": {"warmth": 0.5, "brightness": 0.5, "posture": "open", "gaze": "toward", "elevation": 0.5, "prominence": 0.5},
    "hope":      {"warmth": 0.8, "brightness": 0.85, "posture": "open", "gaze": "up", "elevation": 0.6, "prominence": 0.5},
    "despair":   {"warmth": 0.15, "brightness": 0.15, "posture": "slumped", "gaze": "down", "elevation": 0.2, "prominence": 0.2},
    "anger":     {"warmth": 0.2, "brightness": 0.4, "posture": "tense", "gaze": "forward", "elevation": 0.7, "prominence": 0.8},
    "awe":       {"warmth": 0.7, "brightness": 0.8, "posture": "open", "gaze": "up", "elevation": 0.5, "prominence": 0.5},
    "satisfaction": {"warmth": 0.7, "brightness": 0.7, "posture": "upright", "gaze": "forward", "elevation": 0.5, "prominence": 0.5},
    "confidence": {"warmth": 0.6, "brightness": 0.7, "posture": "upright", "gaze": "forward", "elevation": 0.7, "prominence": 0.8},
}


def compute_clarity_score(expected_emotions: list[dict],
                           actual_signals: list[dict]) -> dict:
    """Compare expected emotion sequence vs actual visual signals.

    expected_emotions: list of {dim: intensity} per beat, from archetype
    actual_signals: list of directorial visual_directives per beat

    Returns dict with per-dimension scores + overall clarity.
    """
    n = min(len(expected_emotions), len(actual_signals))
    if n == 0:
        return {"overall": 0.0, "dims": {}, "issues": ["no beats"]}

    dim_scores: dict[str, list[float]] = {}
    issues = []

    for beat_i in range(n):
        exp = expected_emotions[beat_i]
        act = actual_signals[beat_i]

        for dim, exp_intensity in exp.items():
            # Get expected visual signature for this emotion
            sig = CONCEPT_VISUAL_SIGNATURES.get(dim)
            if sig is None:
                continue

            # Score each visual dimension
            beat_scores = []
            for viz_key, exp_val in sig.items():
                if viz_key not in act:
                    continue
                actual_val = act[viz_key]
                if isinstance(exp_val, (int, float)):
                    # Numeric: score = 1 - |diff|
                    diff = abs(actual_val - exp_val)
                    score = max(0.0, 1.0 - diff * 2.0)
                else:
                    # String: score = 1 if exact match, 0.5 if close, 0 if wrong
                    if isinstance(actual_val, str):
                        if actual_val == exp_val:
                            score = 1.0
                        elif actual_val in ("upright", "open", "relaxed") and exp_val in ("upright", "open", "relaxed"):
                            score = 0.5  # close enough
                        elif actual_val in ("closed", "slumped", "tense") and exp_val in ("closed", "slumped", "tense"):
                            score = 0.5
                        elif actual_val in ("toward", "forward") and exp_val in ("toward", "forward"):
                            score = 0.5
                        else:
                            score = 0.0
                    else:
                        score = 0.0
                beat_scores.append(score)

            if beat_scores:
                dim_scores.setdefault(dim, []).append(sum(beat_scores) / len(beat_scores))

    # Aggregate per dimension
    dim_avg = {dim: round(sum(scores) / len(scores), 3) for dim, scores in dim_scores.items()}
    overall = round(sum(dim_avg.values()) / max(len(dim_avg), 1), 3)

    # Flag poor dimensions
    for dim, score in dim_avg.items():
        if score < 0.4:
            issues.append(f"{dim}: {score:.2f} (weak)")

    return {
        "overall": overall,
        "dims": dim_avg,
        "issues": issues,
    }


SEP = "=" * 70
all_results = {}

for story_id, narration in STORIES:
    print(f"\n{SEP}")
    print(f"BENCHMARK: {story_id}")
    print(f"{SEP}")

    # ── Step 1: Run pipeline ──
    rng = random.Random(42)
    result = direct_narration_with_archetype(narration)
    beat_sequences = result["beat_sequences"]
    archetype = result["archetype"]
    phases = result["phases"]

    print(f"  Archetype: {result['archetype_label']} ({archetype})")
    print(f"  Phases:    {', '.join(phases)}")
    print(f"  Beats:     {result['num_beats']}")

    # ── Step 2: Build expected emotion sequence per beat ──
    engine = NarrativeEngine(rng)
    config = engine.get_archetype_config(archetype)
    emotion_arc = config.get("emotion_arc", {})
    expected_emotions = []

    if emotion_arc:
        for si, seq in enumerate(beat_sequences):
            for bi, beat in enumerate(seq):
                # Map beat index to phase index
                phase_idx = phases.index(beat.narrative_phase) if beat.narrative_phase in phases else 0
                beat_emotions = {}
                for dim, arc in emotion_arc.items():
                    if phase_idx < len(arc):
                        # Scale from 0-10 to 0.0-1.0 and map to visual signature
                        beat_emotions[dim] = arc[phase_idx] / 10.0
                expected_emotions.append(beat_emotions)
    else:
        # Fallback: infer expected emotions from concept detection
        print("  (no emotion_arc defined, using concept-based inference)")

    # ── Step 3: Collect actual visual signals per beat ──
    actual_signals = []
    for si, seq in enumerate(beat_sequences):
        for bi, beat in enumerate(seq):
            dv = beat.visual_directives or {}
            actual_signals.append({
                "warmth": dv.get("warmth", 0.5),
                "brightness": dv.get("brightness", 0.5),
                "subject_elevation": dv.get("subject_elevation", 0.5),
                "subject_prominence": dv.get("subject_prominence", 0.5),
                "posture": dv.get("posture", "neutral"),
                "gaze": dv.get("gaze", "forward"),
                "negative_space": dv.get("negative_space", 0.3),
                "contrast": dv.get("contrast", 0.5),
            })

    # ── Step 4: Score ──
    if expected_emotions:
        score = compute_clarity_score(expected_emotions, actual_signals)
    else:
        score = {"overall": 0.0, "dims": {}, "issues": ["no emotion_arc available"]}

    all_results[story_id] = score

    # ── Step 5: Print diagnostic ──
    print(f"\n  Concept Clarity Score: {score['overall']:.3f}")
    for dim, s in sorted(score.get("dims", {}).items()):
        bar = "#" * int(s * 20)
        print(f"    {dim:<12s}: {s:.3f} |{bar}")
    for issue in score.get("issues", []):
        print(f"    ! {issue}")

    # Detail: per-beat expected vs actual
    print(f"\n  Per-beat detail:")
    for bi, (exp, act) in enumerate(zip(expected_emotions, actual_signals)):
        exp_dims = ", ".join(f"{d}={v:.2f}" for d, v in sorted(exp.items()))
        act_warm = act.get("warmth", "?")
        act_bright = act.get("brightness", "?")
        act_posture = act.get("posture", "?")
        print(f"    Beat {bi}: exp=[{exp_dims}] -> warmth={act_warm:.2f} bright={act_bright:.2f} pose={act_posture}")

print(f"\n{SEP}")
print("SUMMARY")
print(SEP)

avg_scores = [r["overall"] for r in all_results.values()]
print(f"\nAverage Concept Clarity: {sum(avg_scores)/len(avg_scores):.3f}")
print(f"Best:  {max(all_results, key=lambda k: all_results[k]['overall'])} ({max(avg_scores):.3f})")
print(f"Worst: {min(all_results, key=lambda k: all_results[k]['overall'])} ({min(avg_scores):.3f})")

print(f"\nPer-story breakdown:")
for story_id, score in sorted(all_results.items(), key=lambda x: -x[1]["overall"]):
    issues = "; ".join(score.get("issues", []))
    print(f"  {story_id:<30s} {score['overall']:.3f}  {issues}")

# Save report
report_path = os.path.join(OUT_DIR, "concept_clarity_report.json")
with open(report_path, "w") as f:
    json.dump(all_results, f, indent=2)
print(f"\nReport saved: {report_path}")
print(f"\n{SEP}")
