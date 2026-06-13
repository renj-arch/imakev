"""RelationshipTracker — evolves dyadic character relationships per beat.

Reads action triggers (from EmotionTracker-compatible dicts) and updates
trust / fear / familiarity between character pairs in StoryState.
"""

from __future__ import annotations

import re
import random
from typing import Optional

from src.story_state import StoryState

# ── Trigger type → relationship deltas (0.0-1.0) ──

RELATIONSHIP_RULES: dict[str, dict[str, float]] = {
    "discovery": {"familiarity": 0.08},
    "approach":  {"familiarity": 0.08, "trust": 0.04},
    "retreat":   {"fear": 0.08},
    "escape":    {"fear": 0.12, "trust": -0.06},
    "conflict":  {"fear": 0.15, "trust": -0.10},
    "consume":   {"trust": 0.06, "familiarity": 0.04},
    "nurture":   {"trust": 0.12, "familiarity": 0.08},
    "aid":       {"trust": 0.15, "familiarity": 0.08},
    "rescue":    {"trust": 0.20, "fear": -0.08, "familiarity": 0.12},
    "conceal":   {"fear": 0.06, "trust": -0.04},
    "patience":  {"familiarity": 0.04},
    "observe":   {"familiarity": 0.04},
    "pursuit":   {"fear": 0.08, "trust": -0.05},
    "bond":      {"trust": 0.12, "familiarity": 0.12},
    "rest":      {},
    "welcome":   {"trust": 0.15, "familiarity": 0.08},
}

# Same triggers as EmotionTracker for detecting action types per sentence
ACTION_TRIGGERS: dict[str, str] = {
    "notice":    "discovery",
    "found":     "discovery",
    "discover":  "discovery",
    "came":      "approach",
    "approach":  "approach",
    "retreat":   "retreat",
    "run":       "escape",
    "attack":    "conflict",
    "fight":     "conflict",
    "eat":       "consume",
    "feed":      "nurture",
    "help":      "aid",
    "save":      "rescue",
    "hide":      "conceal",
    "wait":      "patience",
    "watch":     "observe",
    "follow":    "pursuit",
    "play":      "bond",
    "sleep":     "rest",
    "invite":    "welcome",
}

CHARACTER_TYPE_SET = {
    "cat", "dog", "human", "bear", "rabbit", "fox", "wolf",
    "monkey", "horse", "elephant", "mouse", "rat", "lion", "tiger",
    "bird", "deer", "cow", "dinosaur", "dragon", "animal",
    "wildcat", "wildcats",
}

DECAY_RATE = 0.05  # familiarity decay per beat when pair doesn't interact


class RelationshipTracker:
    """Updates dyadic relationships based on shared action triggers.

    Call per sentence after EmotionTracker has processed the sentence.
    """

    def __init__(self, rng: random.Random = None):
        self.rng = rng or random.Random()

    def process_sentence(self, state: StoryState, sentence: str,
                         beat_index: int,
                         chars_in_sentence: Optional[list[str]] = None) -> StoryState:
        """Detect action triggers and update relationships between characters.

        If only one character is present, the action is treated as
        self-directed (no relationship change).
        If multiple characters are present, each pair's relationship
        is updated according to RELATIONSHIP_RULES.
        """
        tl = sentence.lower()
        concepts = _extract_concepts(sentence)
        chars = chars_in_sentence or [c for c in concepts if c in CHARACTER_TYPE_SET]

        if len(chars) < 2:
            # Single character or no characters — no relationship to update
            return state

        # Find active trigger types
        trigger_types: list[str] = []
        for word, action_type in ACTION_TRIGGERS.items():
            if _word_in_text(tl, word):
                if action_type not in trigger_types:
                    trigger_types.append(action_type)

        # Update relationship for each character pair
        for i in range(len(chars)):
            for j in range(i + 1, len(chars)):
                a, b = chars[i], chars[j]
                rel = state.ensure_relationship(a, b)

                for ttype in trigger_types:
                    rules = RELATIONSHIP_RULES.get(ttype, {})
                    for dim, delta in rules.items():
                        current = getattr(rel, dim, 0.0)
                        clamped = max(0.0, min(1.0, current + delta))
                        setattr(rel, dim, clamped)

        # Decay familiarity for non-interacting pairs
        all_pairs = set()
        for i in range(len(chars)):
            for j in range(i + 1, len(chars)):
                all_pairs.add(tuple(sorted((chars[i], chars[j]))))

        for (a, b), rel in list(state.relationships.items()):
            if (a, b) not in all_pairs and rel.familiarity > 0:
                rel.familiarity = max(0.0, rel.familiarity - DECAY_RATE)

        return state

    def get_relationship_concepts(self, state: StoryState,
                                  chars_on_screen: list[str]) -> list[str]:
        """Derive concepts from relationships between on-screen characters.

        Returns concept names that should be active (e.g., 'trust',
        'fear', 'connection') based on relationship thresholds.
        """
        concepts: list[str] = []
        if len(chars_on_screen) < 2:
            return concepts

        for i in range(len(chars_on_screen)):
            for j in range(i + 1, len(chars_on_screen)):
                a, b = chars_on_screen[i], chars_on_screen[j]
                key = tuple(sorted((a, b)))
                rel = state.relationships.get(key)
                if rel is None:
                    continue
                if rel.trust >= 0.05:
                    concepts.append("trust")
                if rel.fear >= 0.05:
                    concepts.append("fear")
                if rel.familiarity >= 0.08:
                    concepts.append("connection")
        return concepts


# ── Helpers (mirrors emotion_tracker's approach) ──

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


def _word_in_text(text: str, word: str) -> bool:
    """Check if word (with inflections) appears in text."""
    inflections = set([word])
    # Add standard inflections
    if word.endswith("e"):
        inflections.add(word + "d")
        inflections.add(word[:-1] + "ing")
    elif word.endswith("y"):
        inflections.add(word[:-1] + "ied")
    else:
        inflections.add(word + "s")
        inflections.add(word + "ed")
        inflections.add(word + "ing")
    # Add irregular forms
    if word in IRREGULAR_FORMS:
        inflections.update(IRREGULAR_FORMS[word])
    pattern = r'\b(' + '|'.join(re.escape(w) for w in sorted(inflections, key=len, reverse=True)) + r')\b'
    return bool(re.search(pattern, text))


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
]


def _extract_concepts(text: str) -> list[str]:
    tl = text.lower()
    found = []
    for concept, pattern_str in CONCEPT_PATTERNS:
        if re.search(pattern_str, tl):
            if concept not in found:
                found.append(concept)
    return found
