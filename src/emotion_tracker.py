"""EmotionTracker — per-beat character emotion engine.

Reads narration sentences, detects action triggers, and evolves
character emotions in StoryState. Feeds into Concept Translator
so visual directives reflect the emotional arc.
"""

from __future__ import annotations

import re
import random
from typing import Optional

from src.story_state import StoryState, CharacterState

# ── Action triggers (reused from story_intelligence.py) ──
# Maps trigger word -> old-skool emotion deltas (1-10 scale)

ACTION_TRIGGERS: dict[str, dict] = {
    "notice":    {"type": "discovery", "emotion_delta": {"curiosity": 2, "alertness": 1}},
    "found":     {"type": "discovery", "emotion_delta": {"curiosity": 3, "trust": 1}},
    "discover":  {"type": "discovery", "emotion_delta": {"curiosity": 3, "alertness": 2}},
    "came":      {"type": "approach", "emotion_delta": {"curiosity": 1, "confidence": 1}},
    "approach":  {"type": "approach", "emotion_delta": {"curiosity": 2, "caution": 1}},
    "retreat":   {"type": "retreat", "emotion_delta": {"fear": 2, "caution": 1}},
    "run":       {"type": "escape", "emotion_delta": {"fear": 3, "alertness": 2}},
    "attack":    {"type": "conflict", "emotion_delta": {"aggression": 3, "fear": 2}},
    "fight":     {"type": "conflict", "emotion_delta": {"aggression": 4, "confidence": 1}},
    "eat":       {"type": "consume", "emotion_delta": {"hunger": -3, "trust": 1, "confidence": 1}},
    "feed":      {"type": "nurture", "emotion_delta": {"trust": 3, "hunger": -2, "curiosity": 1}},
    "help":      {"type": "aid", "emotion_delta": {"trust": 4, "confidence": 1}},
    "save":      {"type": "rescue", "emotion_delta": {"trust": 5, "fear": -3}},
    "hide":      {"type": "conceal", "emotion_delta": {"fear": 1, "caution": 2}},
    "wait":      {"type": "patience", "emotion_delta": {"caution": 1, "alertness": 2, "curiosity": 1}},
    "watch":     {"type": "observe", "emotion_delta": {"curiosity": 1, "alertness": 1}},
    "follow":    {"type": "pursuit", "emotion_delta": {"curiosity": 2, "confidence": 1}},
    "play":      {"type": "bond", "emotion_delta": {"trust": 2, "happiness": 2}},
    "sleep":     {"type": "rest", "emotion_delta": {"alertness": -2, "caution": -1}},
    "invite":    {"type": "welcome", "emotion_delta": {"trust": 3, "curiosity": 1}},
}

# Map old dim names -> new dim names
OLD_TO_NEW_DIM: dict[str, str] = {
    "curiosity": "curiosity",
    "fear": "fear",
    "trust": "trust",
    "anger": "anger",
    "aggression": "anger",
    "confidence": "confidence",
    "happiness": "satisfaction",
    "hope": "hope",
    "despair": "despair",
    "awe": "awe",
}

# Character-type baseline emotions (0.0-1.0)
CHARACTER_BASELINES: dict[str, dict[str, float]] = {
    "wolf":   {"caution": 0.7, "fear": 0.3, "trust": 0.2},
    "wildcat": {"caution": 0.7, "fear": 0.3, "trust": 0.2},
    "lion":   {"caution": 0.6, "fear": 0.2, "confidence": 0.5},
    "tiger":  {"caution": 0.6, "fear": 0.3, "confidence": 0.4},
    "rat":    {"fear": 0.6, "caution": 0.7, "trust": 0.1},
    "mouse":  {"fear": 0.6, "caution": 0.7, "trust": 0.1},
    "human":  {"confidence": 0.6, "curiosity": 0.4, "trust": 0.5},
    "dog":    {"trust": 0.7, "confidence": 0.6, "curiosity": 0.5},
    "rabbit": {"fear": 0.5, "caution": 0.6, "trust": 0.3},
    "fox":    {"curiosity": 0.6, "caution": 0.5, "confidence": 0.4},
    "bear":   {"confidence": 0.7, "anger": 0.3, "trust": 0.3},
    "bird":   {"curiosity": 0.6, "fear": 0.4, "hope": 0.3},
    "deer":   {"fear": 0.5, "caution": 0.6, "trust": 0.2},
}

# Dimensions that decay naturally when character is off-screen
DECAY_DIMS = ["fear", "trust", "curiosity", "hope", "despair", "anger", "awe", "satisfaction", "confidence"]
DECAY_RATE = 0.15  # per beat when character not present

# Irregular verb forms for word matching
IRREGULAR_FORMS: dict[str, list[str]] = {
    "feed": ["fed"],
    "run": ["ran", "runs"],
    "hide": ["hid", "hidden", "hides"],
    "fight": ["fought", "fights"],
    "eat": ["ate", "eaten", "eats"],
    "sleep": ["slept", "sleeps"],
    "save": ["saved", "saves"],
    "help": ["helped", "helps"],
    "play": ["played", "plays"],
    "invite": ["invited", "invites"],
    "approach": ["approached", "approaches", "approaching"],
    "retreat": ["retreated", "retreats", "retreating"],
    "notice": ["noticed", "notices", "noticing"],
    "follow": ["followed", "follows", "following"],
    "wait": ["waited", "waits", "waiting"],
    "watch": ["watched", "watches", "watching"],
    "attack": ["attacked", "attacks", "attacking"],
    "discover": ["discovered", "discovers", "discovering"],
    "come": ["came", "comes", "coming"],
}

CHARACTER_TYPE_SET = {
    "cat", "dog", "human", "bear", "rabbit", "fox", "wolf",
    "monkey", "horse", "elephant", "mouse", "rat", "lion", "tiger",
    "bird", "deer", "cow", "dinosaur", "dragon", "animal",
    "wildcat", "wildcats",
}


class EmotionTracker:
    """Evolves character emotions beat-by-beat from narration text.

    Call once per sentence during the Director pipeline.
    """

    def __init__(self, rng: random.Random = None):
        self.rng = rng or random.Random()

    def initialize_state(self, narration_text: str) -> StoryState:
        """Full-story analysis: detect characters, set baselines.

        Returns an initialized StoryState ready for per-beat updates.
        """
        state = StoryState()
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', narration_text.strip()) if s.strip()]

        # Extract characters across all sentences
        all_chars: set[str] = set()
        for s in sentences:
            concepts = _extract_concepts(s)
            for c in concepts:
                if c in CHARACTER_TYPE_SET:
                    all_chars.add(c)

        # Create characters with type-appropriate baseline emotions
        for i, ch in enumerate(sorted(all_chars)):
            baselines = dict(CHARACTER_BASELINES.get(ch, {}))
            new_dims = {}
            for old_dim, val in baselines.items():
                new_dim = OLD_TO_NEW_DIM.get(old_dim)
                if new_dim is not None:
                    new_dims[new_dim] = val * 0.1  # scale from heuristic → mild baseline
            state.characters[ch] = CharacterState(
                type=ch,
                first_seen=0,
                last_seen=0,
                importance=1.0 if i < 2 else 0.6,
            )
            for dim, val in new_dims.items():
                state.update_emotion(ch, dim, val)

        state.narrative.total_beats = len(sentences)
        return state

    def process_sentence(self, state: StoryState, sentence: str,
                         beat_index: int, narrative_phase: str = "",
                         all_chars_in_sentence: Optional[list[str]] = None) -> StoryState:
        """Process one sentence, updating character emotions in place.

        Returns the StoryState for chaining.
        """
        tl = sentence.lower()
        concepts = _extract_concepts(sentence)
        chars_in_s = all_chars_in_sentence or [c for c in concepts if c in CHARACTER_TYPE_SET]

        # Find matched trigger words (with inflection support)
        matched_triggers = []
        for word, trigger in ACTION_TRIGGERS.items():
            inflections = {word}
            if word.endswith("e"):
                inflections.add(word + "d")
                inflections.add(word[:-1] + "ing")
            elif word.endswith("y"):
                inflections.add(word[:-1] + "ied")
            else:
                inflections.add(word + "s")
                inflections.add(word + "ed")
                inflections.add(word + "ing")
            if word in IRREGULAR_FORMS:
                inflections.update(IRREGULAR_FORMS[word])
            pattern_str = r'\b(' + '|'.join(re.escape(w) for w in sorted(inflections, key=len, reverse=True)) + r')\b'
            if re.search(pattern_str, tl):
                matched_triggers.append(trigger)

        # Apply emotion deltas to characters in this sentence
        for ch_key in chars_in_s:
            if ch_key not in state.characters:
                state.ensure_character(ch_key, type=ch_key, first_seen=beat_index)
            state.characters[ch_key].last_seen = beat_index

            for trigger in matched_triggers:
                old_deltas = trigger.get("emotion_delta", {})
                for old_dim, delta in old_deltas.items():
                    new_dim = OLD_TO_NEW_DIM.get(old_dim)
                    if new_dim is None:
                        continue
                    # Scale from old 1-10 delta to 0.0-1.0 delta
                    scaled = delta / 20.0  # 1->0.05, 3->0.15, 5->0.25
                    state.blend_emotion(ch_key, new_dim, scaled)

            # Record event
            types = [t["type"] for t in matched_triggers]
            if types:
                state.record_event(
                    event_type=types[0],
                    detail=f"{ch_key} {types[0]}",
                    entities=[ch_key],
                )

        # Decay emotions for characters NOT in this sentence
        for ch_key, ch_state in state.characters.items():
            if ch_key not in chars_in_s and ch_state.last_seen < beat_index:
                for dim in DECAY_DIMS:
                    current = getattr(ch_state.emotions, dim, 0.0)
                    if current > 0:
                        decayed = current - DECAY_RATE * current
                        state.update_emotion(ch_key, dim, max(0.0, decayed))

        state.narrative.current_beat = beat_index
        return state

    def process_narrative(self, state: StoryState, sentences: list[str],
                          phases: Optional[list[str]] = None) -> StoryState:
        """Process all sentences sequentially, building emotional arc.

        Call after initialize_state.
        """
        if phases is None:
            phases = [""] * len(sentences)
        for i, (s, p) in enumerate(zip(sentences, phases)):
            self.process_sentence(state, s, i, narrative_phase=p)
        return state

    def get_dominant_emotions(self, state: StoryState, beat_index: int) -> dict[str, dict[str, float]]:
        """Return dominant emotions for all characters visible at a beat.

        Returns {character_key: {dim: intensity}} showing only non-zero dims.
        """
        result = {}
        for ch_key, ch_state in state.characters.items():
            if ch_state.last_seen >= beat_index:
                emo = ch_state.emotions
                dominant = {k: v for k, v in emo.__dict__.items() if isinstance(v, (int, float)) and v > 0.1}
                if dominant:
                    result[ch_key] = dominant
        return result


# ── Concept extraction helper (lightweight, no deps on director module) ──

CONCEPT_PATTERNS: list[tuple[str, str]] = [
    ("dragon", r'\bdragon\b'),
    ("dinosaurs", r'\bdinosaurs?\b'),
    ("dinosaur", r'\bdinosaurs?\b'),
    ("elephant", r'\belephants?\b'),
    ("horse", r'\bhor[rs]es?\b'),
    ("monkey", r'\bmonkeys?\b'),
    ("bear", r'\bbears?\b'),
    ("rabbit", r'\brabbits?\b'),
    ("fox", r'\bfox(es)?\b'),
    ("wolf", r'\b(wolf|wolves)\b'),
    ("wildcat", r'\bwildcats?\b'),
    ("deer", r'\bdeer\b'),
    ("mouse", r'\bm(i|o)ce\b|\bmouse\b'),
    ("rat", r'\brats?\b'),
    ("lion", r'\blions?\b'),
    ("tiger", r'\btigers?\b'),
    ("bird", r'\bbirds?\b'),
    ("cow", r'\bcows?\b'),
    ("dog", r'\bdogs?\b'),
    ("human", r'\bhumans?\b|\bman\b|\bwoman\b|\bperson\b|\bpeople\b|\bchild\b|\bboy\b|\bgirl\b'),
    ("animal", r'\banimals?\b|\bcreatures?\b'),
    ("cat", r'\bcats?\b'),
    ("cave", r'\bcave\b'),
    ("fire", r'\bfire\b'),
    ("water", r'\bwater\b|\briver\b|\blake\b|\bsea\b|\bocean\b'),
    ("forest", r'\bforeste?\b|\bwoods\b|\bwoodland\b'),
    ("mountain", r'\bmountains?\b'),
    ("valley", r'\bvalleys?\b'),
    ("darkness", r'\bdark\b|\bdarkness\b|\bshadow\b|\bshadowy\b'),
    ("light", r'\blight\b|\bbright\b|\bglow\b|\bsun\b|\bmoonlight\b'),
    ("food", r'\bfood\b|\bmeat\b|\bberry\b|\bbe?r?ies\b'),
    ("bone", r'\bbones?\b'),
    ("tree", r'\btrees?\b'),
    ("trap", r'\btraps?\b'),
    ("collar", r'\bcollar\b'),
    ("rope", r'\brope\b'),
    ("cage", r'\bcage\b'),
    ("river", r'\briver\b'),
    ("lake", r'\blake\b'),
    ("nest", r'\bnest\b'),
    ("den", r'\bden\b'),
    ("sky", r'\bsky\b'),
    ("moon", r'\bmoon\b'),
    ("star", r'\b(stars?|starlight)\b'),
    ("firelight", r'\bfirelight\b'),
    ("rock", r'\brocks?\b|\bstone\b'),
    ("shelter", r'\bshelter\b'),
    ("path", r'\bpath\b|\btrail\b|\broad\b'),
]


def _extract_concepts(text: str) -> list[str]:
    """Lightweight concept extractor that matches CONCEPT_PATTERNS."""
    tl = text.lower()
    found = []
    for concept, pattern_str in CONCEPT_PATTERNS:
        if re.search(pattern_str, tl):
            if concept not in found:
                found.append(concept)
    return found
