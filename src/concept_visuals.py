"""Concept-to-Visual Translator — turns abstract narrative concepts into visual directives.

Sits between NarrativeEngine (archetype + phases) and Director (concrete beats).

The archetype tells the story SHAPE (rise, peak, fall).
The translator tells the story TEXTURE (how does "power" look? how does "fear" feel?).

Architecture:
  NarrativeEngine → (phase, tension, lighting_arc)
                        ↓
  ConceptTranslator → (visual directives per beat)
                        ↓
  Director → (concrete camera, lighting, positioning)
                        ↓
  Renderer
"""

import re, random
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional


# ── Concept definitions ──

@dataclass
class VisualDirectives:
    """Abstract visual parameters that the Director translates into concrete choices.

    Each value is 0.0-1.0 unless otherwise noted.
    The Director reads these when deciding camera, lighting, and character placement.
    """
    # Spatial
    subject_elevation: float = 0.5     # 0.0=ground level, 1.0=looming above
    subject_prominence: float = 0.5    # 0.0=tiny in frame, 1.0=dominates frame
    horizontal_bias: float = 0.5       # 0.0=far left, 0.5=center, 1.0=far right
    negative_space: float = 0.3        # 0.0=crowded, 1.0=mostly empty

    # Lighting quality
    warmth: float = 0.5                # 0.0=cold/blue, 0.5=neutral, 1.0=warm/orange
    brightness: float = 0.5            # 0.0=dark, 1.0=bright
    contrast: float = 0.5              # 0.0=flat, 1.0=high contrast

    # Character
    posture: str = "neutral"           # upright, slumped, tense, relaxed, open, closed, crouched
    gaze: str = "forward"              # forward, toward, away, down, up,回避
    movement: str = "still"            # still, approach, retreat, wander, circle, explore

    # Composition
    symmetry: float = 0.5              # 0.0=chaotic/asymmetric, 1.0=perfectly symmetric
    framing: str = "balanced"          # balanced, intimate, distant, isolated, crowded

    def to_dict(self) -> dict:
        return {
            "subject_elevation": self.subject_elevation,
            "subject_prominence": self.subject_prominence,
            "horizontal_bias": self.horizontal_bias,
            "negative_space": self.negative_space,
            "warmth": self.warmth,
            "brightness": self.brightness,
            "contrast": self.contrast,
            "posture": self.posture,
            "gaze": self.gaze,
            "movement": self.movement,
            "symmetry": self.symmetry,
            "framing": self.framing,
        }


# ── Concept → Visual mapping ──

# Each concept is defined by HOW IT LOOKS, not by what it means.
# Concepts can be combined (e.g., power + fear = elevated but guarded).

CONCEPT_VISUALS: dict[str, dict] = {
    # ── Power dynamics ──
    "power": {
        "subject_elevation": 0.8,
        "subject_prominence": 0.85,
        "horizontal_bias": 0.5,
        "negative_space": 0.2,
        "warmth": 0.8,
        "brightness": 0.7,
        "contrast": 0.4,
        "posture": "upright",
        "gaze": "forward",
        "movement": "still",
        "symmetry": 0.9,
        "framing": "balanced",
    },
    "powerless": {
        "subject_elevation": 0.2,
        "subject_prominence": 0.25,
        "horizontal_bias": 0.3,
        "negative_space": 0.7,
        "warmth": 0.2,
        "brightness": 0.3,
        "contrast": 0.7,
        "posture": "slumped",
        "gaze": "down",
        "movement": "still",
        "symmetry": 0.2,
        "framing": "isolated",
    },
    # ── Emotional states ──
    "fear": {
        "subject_elevation": 0.3,
        "subject_prominence": 0.4,
        "horizontal_bias": 0.3,
        "negative_space": 0.6,
        "warmth": 0.2,
        "brightness": 0.2,
        "contrast": 0.9,
        "posture": "closed",
        "gaze": "away",
        "movement": "retreat",
        "symmetry": 0.3,
        "framing": "isolated",
    },
    "trust": {
        "subject_elevation": 0.5,
        "subject_prominence": 0.6,
        "horizontal_bias": 0.5,
        "negative_space": 0.3,
        "warmth": 0.8,
        "brightness": 0.7,
        "contrast": 0.3,
        "posture": "open",
        "gaze": "toward",
        "movement": "approach",
        "symmetry": 0.7,
        "framing": "intimate",
    },
    "curiosity": {
        "subject_elevation": 0.5,
        "subject_prominence": 0.5,
        "horizontal_bias": 0.4,
        "negative_space": 0.4,
        "warmth": 0.6,
        "brightness": 0.6,
        "contrast": 0.5,
        "posture": "open",
        "gaze": "toward",
        "movement": "explore",
        "symmetry": 0.5,
        "framing": "balanced",
    },
    "danger": {
        "subject_elevation": 0.4,
        "subject_prominence": 0.7,
        "horizontal_bias": 0.5,
        "negative_space": 0.4,
        "warmth": 0.1,
        "brightness": 0.2,
        "contrast": 0.9,
        "posture": "tense",
        "gaze": "forward",
        "movement": "still",
        "symmetry": 0.4,
        "framing": "intimate",
    },
    # ── Social states ──
    "isolation": {
        "subject_elevation": 0.3,
        "subject_prominence": 0.2,
        "horizontal_bias": 0.2,
        "negative_space": 0.9,
        "warmth": 0.3,
        "brightness": 0.3,
        "contrast": 0.6,
        "posture": "closed",
        "gaze": "down",
        "movement": "still",
        "symmetry": 0.2,
        "framing": "isolated",
    },
    "community": {
        "subject_elevation": 0.5,
        "subject_prominence": 0.4,
        "horizontal_bias": 0.5,
        "negative_space": 0.1,
        "warmth": 0.8,
        "brightness": 0.8,
        "contrast": 0.3,
        "posture": "open",
        "gaze": "forward",
        "movement": "still",
        "symmetry": 0.6,
        "framing": "crowded",
    },
    # ── Change states ──
    "discovery": {
        "subject_elevation": 0.5,
        "subject_prominence": 0.5,
        "horizontal_bias": 0.5,
        "negative_space": 0.4,
        "warmth": 0.4,
        "brightness": 0.3,
        "contrast": 0.6,
        "posture": "open",
        "gaze": "toward",
        "movement": "explore",
        "symmetry": 0.4,
        "framing": "balanced",
    },
    "growth": {
        "subject_elevation": 0.6,
        "subject_prominence": 0.6,
        "horizontal_bias": 0.5,
        "negative_space": 0.3,
        "warmth": 0.7,
        "brightness": 0.7,
        "contrast": 0.4,
        "posture": "upright",
        "gaze": "up",
        "movement": "approach",
        "symmetry": 0.7,
        "framing": "balanced",
    },
    "decline": {
        "subject_elevation": 0.3,
        "subject_prominence": 0.3,
        "horizontal_bias": 0.4,
        "negative_space": 0.6,
        "warmth": 0.3,
        "brightness": 0.3,
        "contrast": 0.6,
        "posture": "slumped",
        "gaze": "down",
        "movement": "retreat",
        "symmetry": 0.3,
        "framing": "isolated",
    },
    # ── Relational ──
    "barrier": {
        "subject_elevation": 0.5,
        "subject_prominence": 0.5,
        "horizontal_bias": 0.3,
        "negative_space": 0.5,
        "warmth": 0.3,
        "brightness": 0.3,
        "contrast": 0.8,
        "posture": "tense",
        "gaze": "forward",
        "movement": "still",
        "symmetry": 0.3,
        "framing": "isolated",
    },
    "connection": {
        "subject_elevation": 0.5,
        "subject_prominence": 0.5,
        "horizontal_bias": 0.5,
        "negative_space": 0.2,
        "warmth": 0.8,
        "brightness": 0.7,
        "contrast": 0.3,
        "posture": "open",
        "gaze": "toward",
        "movement": "approach",
        "symmetry": 0.8,
        "framing": "intimate",
    },
    # ── Stability ──
    "control": {
        "subject_elevation": 0.7,
        "subject_prominence": 0.8,
        "horizontal_bias": 0.5,
        "negative_space": 0.2,
        "warmth": 0.6,
        "brightness": 0.7,
        "contrast": 0.4,
        "posture": "upright",
        "gaze": "forward",
        "movement": "still",
        "symmetry": 0.95,
        "framing": "balanced",
    },
    "chaos": {
        "subject_elevation": 0.4,
        "subject_prominence": 0.5,
        "horizontal_bias": 0.3,
        "negative_space": 0.5,
        "warmth": 0.3,
        "brightness": 0.4,
        "contrast": 0.9,
        "posture": "tense",
        "gaze": "away",
        "movement": "wander",
        "symmetry": 0.1,
        "framing": "isolated",
    },
    # ── Aspiration ──
    "hope": {
        "subject_elevation": 0.6,
        "subject_prominence": 0.5,
        "horizontal_bias": 0.5,
        "negative_space": 0.3,
        "warmth": 0.8,
        "brightness": 0.85,
        "contrast": 0.3,
        "posture": "open",
        "gaze": "up",
        "movement": "approach",
        "symmetry": 0.7,
        "framing": "balanced",
    },
    "despair": {
        "subject_elevation": 0.2,
        "subject_prominence": 0.2,
        "horizontal_bias": 0.3,
        "negative_space": 0.8,
        "warmth": 0.15,
        "brightness": 0.15,
        "contrast": 0.7,
        "posture": "slumped",
        "gaze": "down",
        "movement": "still",
        "symmetry": 0.2,
        "framing": "isolated",
    },
}

# Default neutral state (no concept active)
NEUTRAL_VISUALS = {
    "subject_elevation": 0.5,
    "subject_prominence": 0.5,
    "horizontal_bias": 0.5,
    "negative_space": 0.3,
    "warmth": 0.5,
    "brightness": 0.5,
    "contrast": 0.5,
    "posture": "neutral",
    "gaze": "forward",
    "movement": "still",
    "symmetry": 0.5,
    "framing": "balanced",
}


# ── Concept detection keywords ──

CONCEPT_KEYWORDS: dict[str, list[str]] = {
    "power": [
        "king", "queen", "emperor", "throne", "crown", "ruler", "lord",
        "commanded", "ruled", "dominion", "authority", "mighty",
        "powerful", "strongest", "commanded", "reigned",
    ],
    "powerless": [
        "lost power", "overthrown", "dethroned", "defeated", "surrendered",
        "begged", "pleaded", "weak", "helpless", "powerless", "broken",
        "fell from", "lost everything", "humbled", "stripped of",
        "empty throne", "walked alone", "nothing remained",
    ],
    "fear": [
        "afraid", "scared", "terrified", "fear", "fearful", "dread",
        "panicked", "fled", "ran away", "hid", "trembled", "shaking",
        "heart pounded", "frozen", "paralyzed", "horrified",
        "pounded", "heart raced", "breath caught",
    ],
    "trust": [
        "trust", "trusted", "trusting", "faith", "believed", "relied",
        "depended", "loyal", "loyalty", "bond", "friendship",
        "confidence", "comfortable with", "let its guard down",
        "stepped forward", "moved closer", "reached out",
    ],
    "curiosity": [
        "curious", "curiosity", "wondered", "fascinated", "intrigued",
        "drawn to", "pulled toward", "explored", "investigated",
        "leaned closer", "peered", "studied", "examined",
        "flickered inside", "pulled harder", "wonder",
    ],
    "danger": [
        "danger", "dangerous", "threat", "threatened", "predator",
        "hunted", "stalked", "poisonous", "deadly", "lethal",
        "warning", "alarm", "fierce", "savage", "lurking",
        "dark cave", "shadow moved", "something wrong",
    ],
    "isolation": [
        "alone", "lonely", "solitary", "isolated", "abandoned",
        "deserted", "empty", "only", "by itself", "separated",
        "cut off", "stranded", "left behind",
        "empty halls", "no one", "nobody",
    ],
    "community": [
        "together", "community", "village", "tribe", "settlement",
        "gathered", "crowd", "group", "family", "pack",
        "herd", "flock", "neighbors", "allied",
        "guards", "children", "people",
    ],
    "discovery": [
        "discovered", "found", "stumbled upon", "uncovered", "revealed",
        "breakthrough", "eureka", "realized", "understood",
        "came across", "noticed", "spotted",
        "found light", "flickered", "stepped into",
    ],
    "growth": [
        "grew", "expanded", "rose", "climbed", "flourished",
        "strengthened", "thrived", "prospered", "increased",
        "built", "developed", "advanced",
        "planted", "grew", "raised",
    ],
    "decline": [
        "declined", "weakened", "faded", "shrank", "deteriorated",
        "crumbled", "collapsed", "fell apart", "withered",
        "waned", "diminished", "decayed",
        "loses power", "loses strength", "fading",
    ],
    "barrier": [
        "blocked", "barrier", "wall", "fence", "obstacle",
        "separated", "divided", "closed off", "impassable",
        "guarded", "locked", "sealed", "forbidden",
        "looked away", "turned away",
    ],
    "connection": [
        "connected", "linked", "bridged", "joined", "united",
        "together", "met", "reunited", "bound", "tied",
        "alliance", "merged", "crossed to",
        "trade routes opened", "bridge", "highway",
    ],
    "control": [
        "controlled", "order", "discipline", "commanded", "organized",
        "planned", "deliberate", "calculated", "strategic",
        "mastered", "dominated", "regulated",
    ],
    "chaos": [
        "chaos", "chaotic", "disorder", "confusion", "pandemonium",
        "tumult", "turmoil", "unpredictable", "wild", "frenzy",
        "out of control", "spiraled", "descended into",
    ],
    "hope": [
        "hope", "hopeful", "optimistic", "dreamed", "longed",
        "wished", "prayed", "believed", "looked forward",
        "light at the end", "dawn of", "new beginning",
        "found light", "stepped forward", "pulled harder",
    ],
    "despair": [
        "despair", "hopeless", "gave up", "surrendered", "lost all",
        "nothing left", "pointless", "futile", "no way out",
        "abandoned hope", "consumed by darkness",
        "nothing remained", "empty", "lost everything",
    ],
}


# ── Opposing concept pairs for evolution tracking ──

OPPOSING_CONCEPTS: list[tuple[str, str]] = [
    ("power", "powerless"),
    ("fear", "trust"),
    ("curiosity", "fear"),
    ("growth", "decline"),
    ("hope", "despair"),
    ("control", "chaos"),
    ("isolation", "community"),
    ("barrier", "connection"),
]


# ── Phase-to-concept affinities ──

# Each archetype phase has natural concept affinities.
# Only concepts with weight >= 0.3 are used in blending (low-weight entries
# are noise and dilute per-sentence concept detection).

PHASE_AFFINITIES: dict[str, dict[str, float]] = {
    "rise":        {"power": 0.4, "growth": 0.3, "hope": 0.3},
    "peak":        {"power": 0.5, "control": 0.3, "community": 0.2},
    "decline":     {"decline": 0.5, "fear": 0.3, "despair": 0.2},
    "fall":        {"powerless": 0.5, "chaos": 0.3, "despair": 0.2},
    "aftermath":   {"isolation": 0.4, "despair": 0.3, "hope": 0.3},
    "threat":      {"danger": 0.6, "fear": 0.4},
    "desperation": {"despair": 0.5, "fear": 0.3, "isolation": 0.2},
    "adaptation":  {"growth": 0.4, "hope": 0.3, "trust": 0.3},
    "survival":    {"hope": 0.5, "trust": 0.3, "connection": 0.2},
    "isolation":   {"isolation": 0.7, "fear": 0.3},
    "encounter":   {"curiosity": 0.5, "fear": 0.3, "danger": 0.2},
    "tension":     {"fear": 0.5, "danger": 0.3, "barrier": 0.2},
    "understanding": {"connection": 0.5, "trust": 0.3, "curiosity": 0.2},
    "resolution":  {"connection": 0.5, "trust": 0.3, "hope": 0.2},
    "question":    {"curiosity": 0.5, "discovery": 0.3, "isolation": 0.2},
    "exploration": {"curiosity": 0.5, "discovery": 0.3, "growth": 0.2},
    "insight":     {"discovery": 0.6, "connection": 0.2, "curiosity": 0.2},
    "revelation":  {"discovery": 0.6, "hope": 0.2, "connection": 0.2},
    "impact":      {"growth": 0.3, "connection": 0.3, "curiosity": 0.2, "chaos": 0.2},
    "old_state":   {"control": 0.3, "community": 0.2, "trust": 0.2, "isolation": 0.1, "fear": 0.1, "power": 0.1},
    "pressure":    {"fear": 0.4, "danger": 0.3, "barrier": 0.2, "growth": 0.1},
    "change":      {"curiosity": 0.3, "growth": 0.3, "trust": 0.2, "discovery": 0.2},
    "new_state":   {"hope": 0.4, "trust": 0.3, "connection": 0.2, "growth": 0.1},
    "goal":        {"hope": 0.4, "growth": 0.3, "curiosity": 0.2, "power": 0.1},
    "obstacle":    {"barrier": 0.5, "fear": 0.3, "danger": 0.2},
    "progress":    {"growth": 0.4, "hope": 0.3, "connection": 0.2, "trust": 0.1},
    "arrival":     {"connection": 0.4, "hope": 0.3, "trust": 0.2, "community": 0.1},
    "home":        {"community": 0.4, "control": 0.2, "trust": 0.2, "isolation": 0.1, "connection": 0.1},
    "departure":   {"isolation": 0.3, "fear": 0.3, "hope": 0.2, "growth": 0.2},
    "journey":     {"growth": 0.3, "curiosity": 0.3, "discovery": 0.2, "connection": 0.2},
    "hardship":    {"despair": 0.4, "fear": 0.3, "danger": 0.2, "isolation": 0.1},
    "settlement":  {"community": 0.5, "connection": 0.2, "hope": 0.2, "trust": 0.1},
    "peace":       {"control": 0.3, "community": 0.3, "trust": 0.2, "hope": 0.2},
    "conflict":    {"chaos": 0.4, "fear": 0.3, "danger": 0.2, "anger": 0.1},
    "climax":      {"chaos": 0.4, "fear": 0.3, "despair": 0.2, "danger": 0.1},
}


def lerp(a: float, b: float, t: float) -> float:
    """Linearly interpolate between a and b."""
    return a + (b - a) * t


def blend_directives(a: dict, b: dict, weight_a: float = 0.5) -> dict:
    """Blend two visual directive dicts. weight_a=1.0 = use a entirely."""
    w = max(0.0, min(1.0, weight_a))
    result = {}
    for key in NEUTRAL_VISUALS:
        av = a.get(key, NEUTRAL_VISUALS[key])
        bv = b.get(key, NEUTRAL_VISUALS[key])
        if isinstance(av, (int, float)):
            result[key] = round(lerp(av, bv, 1.0 - w), 2)
        else:
            result[key] = av if w >= 0.5 else bv
    return result


# ── Translator Class ──

class ConceptVisualsTranslator:
    """Translates abstract narrative concepts into visual directives for each beat.

    Usage:
        translator = ConceptVisualsTranslator()
        directives = translator.translate(beats, sentences, full_text)
        # directives is a list of dicts, one per beat
    """

    def __init__(self, rng: random.Random = None):
        self.rng = rng or random.Random()

    # ── Concept Detection ──

    def detect_concepts(self, text: str) -> dict[str, float]:
        """Detect which concepts are present in a text and their intensities.

        Returns dict mapping concept_name -> intensity (0.0-1.0).
        """
        tl = text.lower()
        intensities: dict[str, float] = {}
        for concept, keywords in CONCEPT_KEYWORDS.items():
            score = 0
            for kw in keywords:
                if kw in tl:
                    score += 1
            if score > 0:
                intensities[concept] = min(1.0, score / 4.0)
        return intensities

    # ── Concept Evolution ──

    def compute_evolution(self, sentences: list[str]) -> list[dict[str, float]]:
        """Track how concept intensities evolve across the narrative.

        Returns list of concept dicts, one per sentence.
        """
        evolution: list[dict[str, float]] = []
        for sentence in sentences:
            evolution.append(self.detect_concepts(sentence))
        return evolution

    def get_phase_concepts(self, full_text: str, archetype: str,
                           phases: list[str], total_beats: int) -> list[list[str]]:
        """Assign which concepts are active for each phase of an archetype.

        Returns list of concept name lists, one per archetype phase.
        Phase concepts are based on phase affinity only — NOT full-text
        detection, which would contaminate early phases with concepts
        from later sentences.
        """
        result = []
        for phase in phases:
            affinities = PHASE_AFFINITIES.get(phase, {})
            # Only include high-affinity phase concepts (>= 0.3)
            high_affinity = {c for c, w in affinities.items() if w >= 0.3}
            result.append(list(high_affinity))
        return result

        return result

    # ── Visual Directive Generation ──

    def concepts_to_directives(self, concepts: list[str],
                                evolution_weight: float = 0.5) -> dict:
        """Blend multiple concepts into a single visual directive dict.

        For numeric fields: weighted average.
        For string fields: use the value from the concept with highest
        count among peer concepts (mode), falling back to neutral.
        """
        if not concepts:
            return dict(NEUTRAL_VISUALS)

        matched = [c for c in concepts if c in CONCEPT_VISUALS]
        if not matched:
            return dict(NEUTRAL_VISUALS)

        # Build result for numeric and string fields separately
        accumulated = {}
        for key in NEUTRAL_VISUALS:
            values = [CONCEPT_VISUALS[c][key] for c in matched]
            if isinstance(values[0], (int, float)):
                # Numeric: weighted average
                accumulated[key] = round(sum(values) / len(values), 2)
            else:
                # String: use the value that appears most frequently (mode)
                from collections import Counter
                counts = Counter(values)
                most_common = counts.most_common(1)
                accumulated[key] = most_common[0][0] if most_common else NEUTRAL_VISUALS[key]

        return accumulated

    # ── Main Translation ──

    def translate(self, beats: list, sentences: list[str],
                  archetype: str, phases: list[str]) -> list[dict]:
        """Translate narrative into visual directives per beat.

        Args:
            beats: list of ArchetypeBeat or similar with .phase and .beat_index
            sentences: list of sentence strings
            archetype: detected archetype name
            phases: list of phase names

        Returns:
            list of visual directive dicts, one per beat
        """
        if not beats:
            return []

        # Get concept evolution across sentences
        evolution = self.compute_evolution(sentences)

        # Get phase concept affinities
        full_text = " ".join(sentences)
        phase_concepts = self.get_phase_concepts(full_text, archetype, phases, len(beats))

        # Build a mapping from phase name to its concept list
        phase_to_concepts = dict(zip(phases, phase_concepts)) if len(phases) == len(phase_concepts) else {}

        directives_list = []
        for i, beat in enumerate(beats):
            phase = getattr(beat, "phase", "scene")
            beat_idx = getattr(beat, "beat_index", i)

            # Collect concepts active for this beat
            concepts_for_beat = set()

            # From sentence-level concept detection
            sent_idx = min(beat_idx, len(evolution) - 1) if evolution else 0
            if sent_idx < len(evolution):
                for concept, inten in evolution[sent_idx].items():
                    if inten > 0.2:
                        concepts_for_beat.add(concept)

            # From phase affinities
            if phase in phase_to_concepts:
                for c in phase_to_concepts[phase]:
                    concepts_for_beat.add(c)

            if not concepts_for_beat:
                # Check if phase name itself matches a concept
                if phase in CONCEPT_VISUALS:
                    concepts_for_beat.add(phase)

            # Generate directives
            directives = self.concepts_to_directives(list(concepts_for_beat))
            directives_list.append(directives)

        return directives_list


# ── Convenience ──

def translate_narrative(narration_text: str, beats: list,
                        archetype: str, phases: list[str]) -> list[dict]:
    """One-shot: translate a narrative into visual directives."""
    translator = ConceptVisualsTranslator()
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', narration_text.strip()) if s.strip()]
    return translator.translate(beats, sentences, archetype, phases)
