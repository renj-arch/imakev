"""Narrative Engines — story archetype detection and archetype-driven beat structuring.

The engine that sits above the Director. Instead of generating beats per-sentence,
it recognizes the story's archetype and applies a canonical narrative structure.

Once the AI knows "this is a transformation story", every production choice
pulls in the same direction — lighting, reveals, emotional arcs, pacing.

Archetypes:
  Transformation:   Old State → Pressure → Change → New State
  Mystery:          Question → Hint → Contradiction → Reveal
  Disaster:         Normal → Warning → Impact → Chaos → Aftermath
  Journey:          Goal → Obstacle → Adaptation → Progress → Arrival
"""

import re, math, random
from dataclasses import dataclass, field
from typing import Optional

from src.concept_extractor import extract_concepts


# ── Archetype definitions ──

ARCHETYPE_DEFS: dict[str, dict] = {
    "transformation": {
        "label": "Transformation Story",
        "phases": ["old_state", "pressure", "change", "new_state"],
        "keywords": [
            "became", "changed", "evolved", "transformed", "over generations",
            "gradually", "slowly", "turned into", "no longer", "used to be",
            "began to", "started to", "eventually", "over time", "adapted",
            "shifted", "mutated", "emerged as", "developed into",
            "rebuilt", "reborn", "restored", "recovered", "renewed",
            "reopened", "reclaimed",
        ],
        "tension_arc": [2, 4, 6, 2],
        "lighting_arc": ["dusk", "night", "dawn", "day"],
        "emotion_arc": {
            "curiosity": [5, 7, 6, 4],
            "trust":     [3, 2, 5, 8],
            "fear":      [5, 7, 4, 2],
        },
        "description": "Something gradually becomes something else. Evolution, domestication, growth.",
    },
    "mystery": {
        "label": "Mystery Story",
        "phases": ["question", "hint", "contradiction", "reveal"],
        "keywords": [
            "mystery", "mysterious", "unexplained", "enigma", "perplexing",
            "ancient", "lost", "forgotten", "puzzle", "riddle",
            "whisper", "rumor", "legend", "myth", "forbidden",
            "symbol", "carving", "hint", "temple", "ruin", "artifact",
            "nobody knows", "no one knows", "cannot explain", "buried secret",
            "cursed", "treasure", "code", "cipher", "hieroglyph",
            "disappearance", "vanished", "without a trace",
            "strange markings", "impossible to understand", "cannot be read",
            "secret passage", "hidden chamber", "ancient door",
            "hidden", "unknown language", "stone door",
            "cannot decipher", "could not decipher", "unreadable",
        ],
        "tension_arc": [3, 5, 7, 9],
        "lighting_arc": ["shadow", "moonlight", "dark", "dawn"],
        "emotion_arc": {
            "curiosity": [8, 9, 9, 7],
            "fear":      [3, 5, 7, 4],
            "trust":     [4, 3, 2, 6],
        },
        "description": "A question drives the narrative. Hints build, contradictions deepen, then the truth emerges.",
    },
    "disaster": {
        "label": "Disaster Story",
        "phases": ["normal", "warning", "impact", "chaos", "aftermath"],
        "keywords": [
            "eruption", "earthquake", "flood", "plague", "extinction", "destroyed",
            "collapsed", "struck", "impact", "devastated", "obliterated", "wiped out",
            "catastrophe", "cataclysmic", "crisis", "fatal", "deadly", "disaster",
            "volcanic", "tsunami", "hurricane", "famine", "pestilence",
            "exploded", "ash", "lava", "melted", "burned",
            "sank", "drowned", "crumbled", "fell", "crashed", "shattered",
            "wave", "flooded", "drought", "blizzard", "wildfire",
            "illness", "sickness", "disease", "infected", "contagious",
            "epidemic", "pandemic", "symptom",
        ],
        "tension_arc": [2, 4, 9, 10, 5],
        "lighting_arc": ["day", "dusk", "dark", "firelight", "dawn"],
        "emotion_arc": {
            "fear":      [2, 5, 9, 10, 4],
            "curiosity": [3, 4, 2, 1, 5],
            "trust":     [5, 3, 1, 1, 4],
        },
        "description": "Normal life breaks apart. Warning signs, impact, chaos, then fragile recovery.",
    },
    "journey": {
        "label": "Journey Story",
        "phases": ["goal", "obstacle", "adaptation", "progress", "arrival"],
        "keywords": [
            "traveled", "crossed", "migrated", "explored", "voyage", "journey",
            "expedition", "trek", "sailed", "walked", "roamed", "wandered",
            "set out", "departed", "headed", "toward", "destination", "quest",
            "adventure", "odyssey", "pilgrimage", "crusade",
            "ocean", "sea", "across", "horizon", "land appeared",
            "followed", "navigation", "stars", "current", "wind",
            "discovered island", "reached shore", "made landfall",
            "voyagers", "explorers", "pioneers", "settlers",
        ],
        "tension_arc": [3, 7, 5, 4, 2],
        "lighting_arc": ["dawn", "dusk", "night", "dawn", "day"],
        "emotion_arc": {
            "curiosity":    [8, 5, 6, 7, 5],
            "confidence":   [7, 3, 4, 6, 9],
            "fear":         [2, 6, 4, 3, 1],
        },
        "description": "A goal drives movement. Obstacles force adaptation. Progress and eventual arrival.",
    },
    "rise_and_fall": {
        "label": "Rise & Fall Story",
        "phases": ["rise", "peak", "decline", "fall", "aftermath"],
        "keywords": [
            "rose", "climbed", "reached", "golden age", "glory", "empire",
            "prosperity", "flourished", "expanded", "conquered", "power",
            "wealthy", "declined", "weakened", "crumbled", "fell",
            "collapsed", "faded", "vanished", "remnant", "ruin",
            "legacy", "rise", "peak", "achieved greatness", "built",
            "grew stronger", "reached its height", "reached its peak",
            "began to fall", "slowly declined", "inevitable",
            "throne", "crown", "king", "queen", "emperor",
            "loses power", "lost power", "overthrown", "dethroned",
            "empty throne", "fell from power", "stripped of",
        ],
        "tension_arc": [2, 4, 7, 10, 5],
        "lighting_arc": ["dawn", "day", "dusk", "dark", "dawn"],
        "emotion_arc": {
            "confidence": [3, 8, 6, 2, 4],
            "fear":       [2, 3, 5, 9, 6],
            "trust":      [5, 7, 4, 1, 3],
        },
        "description": "Something rises to greatness, then falls. Empire, glory, decline, and what remains.",
    },
    "survival": {
        "label": "Survival Story",
        "phases": ["threat", "desperation", "adaptation", "hope", "survival"],
        "keywords": [
            "stranded", "lost", "alone", "survive", "survival", "hunger",
            "starving", "thirst", "dehydrated", "cold", "shelter",
            "hunt", "hiding", "pursued", "chased", "predator",
            "dangerous", "desperate", "endure", "endurance", "persist",
            "persistence", "rescue", "rescued", "saved", "escape",
            "escaped", "refuge", "safe", "found", "limited resources",
            "injured", "wounded", "bleeding", "alone", "isolated",
            "fending for", "struggling to survive", "fighting to stay alive",
            "sank", "shipwreck", "no food", "no water", "fresh water",
            "caught fish", "built a shelter",
        ],
        "tension_arc": [7, 10, 8, 5, 2],
        "lighting_arc": ["dusk", "dark", "night", "moonlight", "dawn"],
        "emotion_arc": {
            "fear":  [8, 10, 6, 4, 2],
            "hope":  [1, 2, 5, 7, 9],
            "trust": [2, 1, 3, 5, 7],
        },
        "description": "A character fights to survive. Threats close in, resources dwindle, then resilience wins.",
    },
    "first_contact": {
        "label": "First Contact Story",
        "phases": ["isolation", "encounter", "tension", "understanding", "resolution"],
        "keywords": [
            "first", "contact", "encountered", "discovered", "strange",
            "alien", "unknown", "unfamiliar", "different", "meeting",
            "approached", "approach", "cautiously", "communication",
            "communicate", "language", "sign", "understanding",
            "understand", "peaceful", "hostile", "wary", "curious",
            "foreign", "visitor", "arrived", "appeared", "emerged",
            "face to face", "first meeting", "first encounter",
            "never seen before", "came across", "stumbled upon",
        ],
        "tension_arc": [2, 5, 8, 6, 3],
        "lighting_arc": ["day", "moonlight", "shadow", "dusk", "dawn"],
        "emotion_arc": {
            "curiosity": [5, 8, 6, 7, 4],
            "fear":      [2, 6, 9, 5, 3],
            "trust":     [3, 2, 1, 5, 8],
        },
        "description": "Two worlds meet. Curiosity, fear, misunderstanding — then breakthrough or breaking point.",
    },
    "discovery": {
        "label": "Discovery Story",
        "phases": ["question", "exploration", "insight", "revelation", "impact"],
        "keywords": [
            "curious", "curiosity", "explored", "exploration", "wondered",
            "wonder", "discovered", "discovery", "found", "revealed",
            "revelation", "understood", "understanding", "learned",
            "learning", "experiment", "research", "breakthrough",
            "eureka", "fascinating", "amazed", "astonishing",
            "uncover", "hidden", "secret", "knowledge", "unknown",
            "figured out", "realized", "it meant", "suddenly understood",
            "opened their eyes", "saw the truth",
        ],
        "tension_arc": [2, 4, 6, 7, 3],
        "lighting_arc": ["shadow", "moonlight", "dawn", "day", "day"],
        "emotion_arc": {
            "curiosity":    [7, 9, 8, 6, 4],
            "awe":          [3, 5, 8, 9, 6],
            "satisfaction": [1, 2, 4, 7, 9],
        },
        "description": "The unknown becomes known. Questioning, seeking, finding, and the consequences of knowledge.",
    },
    "migration": {
        "label": "Migration Story",
        "phases": ["home", "departure", "journey", "hardship", "arrival", "settlement"],
        "keywords": [
            "migrated", "migration", "exodus", "displaced", "refugee",
            "nomad", "nomadic", "caravan", "moved", "followed",
            "herd", "flock", "season", "seasonal",
            "trek", "settlers", "pioneers", "crossing",
            "destination", "new home", "homeland",
            "great journey", "long road", "search for", "new land",
            "left behind", "said goodbye", "departed", "set off",
            "stopped wandering", "settled", "settlement", "wandered",
            "valley", "arrived", "found a place", "made their home",
            "no longer wandered", "put down roots",
        ],
        "tension_arc": [2, 4, 6, 8, 3, 1],
        "lighting_arc": ["day", "dawn", "dusk", "night", "dawn", "day"],
        "emotion_arc": {
            "hope": [7, 6, 4, 2, 5, 8],
            "fear": [2, 3, 5, 8, 4, 1],
            "trust":[5, 4, 3, 2, 6, 8],
        },
        "description": "A group moves from one place to another. Leaving, crossing, struggling, and finding new ground.",
    },
    "war": {
        "label": "War Story",
        "phases": ["peace", "tension", "conflict", "climax", "aftermath"],
        "keywords": [
            "war", "battle", "fought", "fight", "enemy", "army",
            "invasion", "defend", "attack", "strategy", "victory",
            "defeat", "peace", "warrior", "soldier", "combat",
            "conflict", "siege", "assault", "charge", "retreat",
            "ambush", "ally", "front line", "ceasefire",
            "declared war", "went to war", "marched to", "battlefield",
            "surrendered", "truce", "fallen soldiers", "wounded",
        ],
        "tension_arc": [1, 4, 8, 10, 3],
        "lighting_arc": ["day", "dusk", "firelight", "dark", "dawn"],
        "emotion_arc": {
            "fear":  [2, 5, 8, 10, 4],
            "anger": [3, 4, 9, 10, 3],
            "hope":  [6, 4, 2, 1, 7],
        },
        "description": "Conflict erupts and resolves. Peace, rising tension, battle, climax, and what peace costs.",
    },
}

# ── Event patterns for narrative event detection ──
# Strong multi-word signals that heavily bias toward a specific archetype.
# Event matches get +4 each (vs +2 for single keywords).

ARCHETYPE_EVENTS: dict[str, list[str]] = {
    "disaster": [
        "volcano erupted", "earthquake struck", "tsunami hit", "plague spread",
        "city burned", "mountain exploded", "ash buried", "fire consumed",
        "wave crashed", "flood destroyed", "lava flowed", "eruption buried",
        "giant wave", "tidal wave", "wildfire spread", "the ground shook",
        "the sky fell", "it destroyed", "swept away", "rained down",
        "the remains of", "survivors searched", "picked through the rubble",
        "plague spread", "disease spread", "fell ill", "infected with",
        "sickness spread", "illness appeared", "strange illness",
    ],
    "discovery": [
        "discovered that", "found a way", "figured out", "came to understand",
        "learned the truth", "experiment showed", "discovered how",
        "realized that", "understood why", "stumbled upon",
        "opened their eyes to", "saw the truth",
    ],
    "transformation": [
        "turned into", "became something", "evolved from", "over generations",
        "gradually changed", "no longer was", "began to change",
        "started to become", "slowly transformed", "mutated into",
        "emerged as a", "developed into",
    ],
    "journey": [
        "set out", "crossed the", "made their way", "arrived at",
        "sailed across", "trekked through", "traveled across",
        "journeyed to", "headed toward", "made landfall",
        "reached the", "departed from",
    ],
    "mystery": [
        "no one knew", "could not explain", "cannot explain",
        "mysterious disappearance", "ancient secret", "cursed treasure",
        "nobody understood", "remained a mystery", "was never found",
        "vanished without", "disappeared into",
        "could not read", "cannot read", "cannot decipher",
        "could not decipher", "impossible to read", "unknown language",
    ],
    "rise_and_fall": [
        "rose to power", "reached its peak", "began to decline",
        "fell from grace", "crumbled to dust", "rose from nothing",
        "reached its height", "slowly declined", "inevitable decline",
        "golden age", "built an empire", "conquered everything",
        "lost everything", "stripped of power",
    ],
    "survival": [
        "fighting to survive", "struggled to stay alive", "running out of",
        "barely survived", "just barely", "fought to survive",
        "escaped from", "managed to survive", "fought for survival",
        "limited resources", "running low on",
    ],
    "migration": [
        "left their home", "moved across", "settled in", "built a new",
        "made their way", "said goodbye to", "departed from their",
        "crossed the plains", "crossed the desert", "crossed the sea",
        "search for a new", "in search of", "put down roots",
        "found a new home", "built a settlement",
    ],
    "first_contact": [
        "first encounter", "face to face", "never seen before",
        "came across", "emerged from", "appeared before",
        "first meeting", "encountered a strange", "approached cautiously",
        "made contact with", "first communication",
    ],
    "war": [
        "declared war", "went to war", "marched to battle",
        "surrounded by enemies", "army advanced", "invasion began",
        "battle raged", "fought fiercely", "laid siege",
        "retreated from", "surrendered to",
    ],
}

# ── Concept-to-archetype affinities for concept_score blending ──
# When concepts_visuals detects these concepts in text, boost the related archetype.
# Weight 0.0-1.0: how strongly this concept suggests this archetype.

ARCHETYPE_CONCEPT_AFFINITIES: dict[str, dict[str, float]] = {
    "discovery":     {"discovery": 0.8, "curiosity": 0.5},
    "mystery":       {"curiosity": 0.3, "isolation": 0.2, "fear": 0.2},
    "disaster":      {"chaos": 0.7, "fear": 0.5, "danger": 0.5, "despair": 0.3},
    "survival":      {"fear": 0.6, "danger": 0.5, "despair": 0.4, "isolation": 0.3, "hope": 0.2},
    "journey":       {"curiosity": 0.5, "discovery": 0.3, "hope": 0.2, "growth": 0.2},
    "migration":     {"isolation": 0.3, "hope": 0.3, "community": 0.3, "connection": 0.2},
    "rise_and_fall":  {"power": 0.6, "powerless": 0.4, "growth": 0.4, "decline": 0.5, "control": 0.3, "chaos": 0.3},
    "transformation": {"growth": 0.4, "discovery": 0.3, "curiosity": 0.3, "hope": 0.2},
    "first_contact":  {"curiosity": 0.5, "fear": 0.4, "danger": 0.3, "trust": 0.3, "connection": 0.3},
    "war":           {"chaos": 0.6, "fear": 0.5, "danger": 0.4, "anger": 0.3, "control": 0.2},
}

@dataclass
class ArchetypeBeat:
    """A single beat within a narrative archetype structure."""
    phase: str = ""
    archetype: str = ""
    beat_index: int = 0
    total_phases: int = 4
    tension: int = 5
    suggested_lighting: str = "day"
    suggested_mood: str = "neutral"
    suggested_camera: str = "medium"
    suggested_animation: str = "idle"
    goal: str = "advance story"
    description: str = ""
    archetype_probs: Optional[dict[str, float]] = None  # probability distribution over archetypes


# ── Phase details ──

PHASE_DETAILS: dict[str, dict[str, dict]] = {
    "transformation": {
        "old_state": {
            "goal": "establish what existed before",
            "mood": "neutral",
            "camera": "wide",
            "animation": "idle",
            "lighting": "dusk",
            "description": "Show the original state. Calm, stable, familiar.",
        },
        "pressure": {
            "goal": "introduce force of change",
            "mood": "cautious",
            "camera": "closeup",
            "animation": "freeze",
            "lighting": "night",
            "description": "Something pushes against the old state. Tension builds.",
        },
        "change": {
            "goal": "show transformation beginning",
            "mood": "focused",
            "camera": "extreme_closeup",
            "animation": "freeze",
            "lighting": "dawn",
            "description": "The shift begins. Small differences appear.",
        },
        "new_state": {
            "goal": "reveal what emerged",
            "mood": "triumphant",
            "camera": "medium",
            "animation": "proud_pose",
            "lighting": "day",
            "description": "The result of transformation. Different, evolved.",
        },
    },
    "mystery": {
        "question": {
            "goal": "pose the central question",
            "mood": "mysterious",
            "camera": "wide",
            "animation": "freeze",
            "lighting": "shadow",
            "description": "Something is off. A question forms in the audience's mind.",
        },
        "hint": {
            "goal": "offer a clue",
            "mood": "mysterious",
            "camera": "closeup",
            "animation": "freeze",
            "lighting": "moonlight",
            "description": "A detail appears. Not enough to answer, enough to intrigue.",
        },
        "contradiction": {
            "goal": "deepen the mystery",
            "mood": "cautious",
            "camera": "dutch",
            "animation": "freeze",
            "lighting": "dark",
            "description": "New information contradicts the hint. The mystery deepens.",
        },
        "reveal": {
            "goal": "answer the question",
            "mood": "surprised",
            "camera": "extreme_wide",
            "animation": "freeze_then_step",
            "lighting": "dawn",
            "description": "The truth emerges. Everything clicks into place.",
        },
    },
    "disaster": {
        "normal": {
            "goal": "establish peaceful normalcy",
            "mood": "neutral",
            "camera": "wide",
            "animation": "idle",
            "lighting": "day",
            "description": "Life as usual. No one knows what is coming.",
        },
        "warning": {
            "goal": "show the first sign",
            "mood": "cautious",
            "camera": "closeup",
            "animation": "freeze",
            "lighting": "dusk",
            "description": "A subtle warning. Dismissed or unnoticed.",
        },
        "impact": {
            "goal": "the disaster strikes",
            "mood": "surprised",
            "camera": "handheld",
            "animation": "run",
            "lighting": "dark",
            "description": "Full impact. Chaos erupts. Everything changes instantly.",
        },
        "chaos": {
            "goal": "show the aftermath in motion",
            "mood": "cautious",
            "camera": "dutch",
            "animation": "freeze",
            "lighting": "firelight",
            "description": "The world is broken. Survival mode.",
        },
        "aftermath": {
            "goal": "show what remains",
            "mood": "tired",
            "camera": "extreme_wide",
            "animation": "sleep",
            "lighting": "dawn",
            "description": "Quiet after the storm. Fragile new beginning.",
        },
    },
    "journey": {
        "goal": {
            "goal": "establish the destination",
            "mood": "hopeful",
            "camera": "extreme_wide",
            "animation": "idle",
            "lighting": "dawn",
            "description": "The goal is set. Motion begins.",
        },
        "obstacle": {
            "goal": "introduce the first barrier",
            "mood": "cautious",
            "camera": "closeup",
            "animation": "freeze",
            "lighting": "dusk",
            "description": "The path is blocked. Doubt creeps in.",
        },
        "adaptation": {
            "goal": "show solving the obstacle",
            "mood": "focused",
            "camera": "medium",
            "animation": "walk",
            "lighting": "night",
            "description": "The traveler adapts. A new approach.",
        },
        "progress": {
            "goal": "movement toward goal",
            "mood": "hopeful",
            "camera": "wide",
            "animation": "walk",
            "lighting": "dawn",
            "description": "Forward motion resumes. The goal feels closer.",
        },
        "arrival": {
            "goal": "reaching the destination",
            "mood": "triumphant",
            "camera": "extreme_wide",
            "animation": "proud_pose",
            "lighting": "day",
            "description": "The journey ends. The destination is reached.",
        },
    },
    "rise_and_fall": {
        "rise": {
            "goal": "show the beginning of ascent",
            "mood": "hopeful",
            "camera": "wide",
            "animation": "walk",
            "lighting": "dawn",
            "description": "Humble beginnings. Small but growing.",
        },
        "peak": {
            "goal": "show the height of power",
            "mood": "triumphant",
            "camera": "low_angle",
            "animation": "proud_pose",
            "lighting": "day",
            "description": "The peak. Everything works. Glory achieved.",
        },
        "decline": {
            "goal": "show the first cracks",
            "mood": "cautious",
            "camera": "closeup",
            "animation": "freeze",
            "lighting": "dusk",
            "description": "Small problems ignored. The foundation weakens.",
        },
        "fall": {
            "goal": "show the collapse",
            "mood": "sad",
            "camera": "dutch",
            "animation": "freeze",
            "lighting": "dark",
            "description": "Everything crumbles. What was built is lost.",
        },
        "aftermath": {
            "goal": "show what survives",
            "mood": "tired",
            "camera": "extreme_wide",
            "animation": "sleep",
            "lighting": "dawn",
            "description": "Quiet after destruction. Seeds of something new.",
        },
    },
    "survival": {
        "threat": {
            "goal": "introduce the danger",
            "mood": "cautious",
            "camera": "wide",
            "animation": "freeze",
            "lighting": "dusk",
            "description": "Something is wrong. The danger approaches.",
        },
        "desperation": {
            "goal": "show resources running out",
            "mood": "cautious",
            "camera": "closeup",
            "animation": "freeze",
            "lighting": "dark",
            "description": "Hope fades. Options narrow. The character is pushed to the edge.",
        },
        "adaptation": {
            "goal": "show the character adapting",
            "mood": "focused",
            "camera": "medium",
            "animation": "crouch",
            "lighting": "night",
            "description": "Survival instinct kicks in. A new approach emerges.",
        },
        "hope": {
            "goal": "show a breakthrough",
            "mood": "hopeful",
            "camera": "wide",
            "animation": "walk",
            "lighting": "moonlight",
            "description": "A sign of hope. Resources found. Path forward appears.",
        },
        "survival": {
            "goal": "show the outcome",
            "mood": "triumphant",
            "camera": "extreme_wide",
            "animation": "proud_pose",
            "lighting": "dawn",
            "description": "The character made it. Changed, but alive.",
        },
    },
    "first_contact": {
        "isolation": {
            "goal": "establish the isolated world",
            "mood": "neutral",
            "camera": "extreme_wide",
            "animation": "idle",
            "lighting": "day",
            "description": "A world that has never seen the other. Peaceful ignorance.",
        },
        "encounter": {
            "goal": "show the first meeting",
            "mood": "mysterious",
            "camera": "silhouette",
            "animation": "freeze",
            "lighting": "moonlight",
            "description": "Something appears on the horizon. First glimpse of the other.",
        },
        "tension": {
            "goal": "show uncertainty and fear",
            "mood": "cautious",
            "camera": "closeup",
            "animation": "freeze",
            "lighting": "shadow",
            "description": "Fear of the unknown. Misunderstanding threatens conflict.",
        },
        "understanding": {
            "goal": "show a bridge forming",
            "mood": "focused",
            "camera": "medium",
            "animation": "freeze_then_step",
            "lighting": "dusk",
            "description": "A gesture. A word. The first hint of connection.",
        },
        "resolution": {
            "goal": "show the new relationship",
            "mood": "hopeful",
            "camera": "wide",
            "animation": "idle",
            "lighting": "dawn",
            "description": "Two worlds now know each other. Changed forever.",
        },
    },
    "discovery": {
        "question": {
            "goal": "pose the question",
            "mood": "mysterious",
            "camera": "wide",
            "animation": "freeze",
            "lighting": "shadow",
            "description": "Something doesn't fit. Why? How?",
        },
        "exploration": {
            "goal": "show the search",
            "mood": "focused",
            "camera": "closeup",
            "animation": "walk",
            "lighting": "moonlight",
            "description": "Looking. Testing. Following clues into the unknown.",
        },
        "insight": {
            "goal": "show the first understanding",
            "mood": "surprised",
            "camera": "extreme_closeup",
            "animation": "freeze_then_step",
            "lighting": "dawn",
            "description": "The pieces connect. A flash of understanding.",
        },
        "revelation": {
            "goal": "show the full truth",
            "mood": "surprised",
            "camera": "extreme_wide",
            "animation": "freeze",
            "lighting": "day",
            "description": "The full picture emerges. Everything makes sense now.",
        },
        "impact": {
            "goal": "show how the truth changes things",
            "mood": "neutral",
            "camera": "medium",
            "animation": "idle",
            "lighting": "day",
            "description": "Knowledge has consequences. The world is different now.",
        },
    },
    "migration": {
        "home": {
            "goal": "establish the homeland",
            "mood": "neutral",
            "camera": "extreme_wide",
            "animation": "idle",
            "lighting": "day",
            "description": "Familiar ground. The place that must be left.",
        },
        "departure": {
            "goal": "show the leaving",
            "mood": "sad",
            "camera": "wide",
            "animation": "walk",
            "lighting": "dawn",
            "description": "Saying goodbye. The journey begins.",
        },
        "journey": {
            "goal": "show movement across distance",
            "mood": "focused",
            "camera": "extreme_wide",
            "animation": "walk",
            "lighting": "dusk",
            "description": "Open road or open ocean. The group moves forward.",
        },
        "hardship": {
            "goal": "show the cost of the journey",
            "mood": "cautious",
            "camera": "closeup",
            "animation": "freeze",
            "lighting": "night",
            "description": "Storms, hunger, loss. The journey demands sacrifice.",
        },
        "arrival": {
            "goal": "show reaching the destination",
            "mood": "hopeful",
            "camera": "extreme_wide",
            "animation": "proud_pose",
            "lighting": "dawn",
            "description": "Land appears. The promised place is real.",
        },
        "settlement": {
            "goal": "show the new beginning",
            "mood": "triumphant",
            "camera": "wide",
            "animation": "idle",
            "lighting": "day",
            "description": "Building a home. The journey is complete.",
        },
    },
    "war": {
        "peace": {
            "goal": "establish peace before the storm",
            "mood": "neutral",
            "camera": "extreme_wide",
            "animation": "idle",
            "lighting": "day",
            "description": "Normal life. No one knows what is coming.",
        },
        "tension": {
            "goal": "show rising conflict",
            "mood": "cautious",
            "camera": "closeup",
            "animation": "freeze",
            "lighting": "dusk",
            "description": "Rumors. Threats. The first skirmish.",
        },
        "conflict": {
            "goal": "show the battle",
            "mood": "angry",
            "camera": "handheld",
            "animation": "run",
            "lighting": "firelight",
            "description": "Full engagement. Chaos, strategy, courage, fear.",
        },
        "climax": {
            "goal": "show the turning point",
            "mood": "surprised",
            "camera": "dutch",
            "animation": "freeze",
            "lighting": "dark",
            "description": "The moment everything hangs in the balance.",
        },
        "aftermath": {
            "goal": "show what peace costs",
            "mood": "tired",
            "camera": "extreme_wide",
            "animation": "sleep",
            "lighting": "dawn",
            "description": "Silence after the storm. Counting the cost.",
        },
    },
}


class NarrativeEngine:
    """Detects story archetype and generates archetype-driven narrative structure.

    Usage:
        engine = NarrativeEngine()
        archetype = engine.detect_archetype(full_text)
        beats = engine.structure_narrative(sentences, archetype)
        for sentence, phase in beats:
            # sentence gets visual treatment matching its narrative role
    """

    def __init__(self, rng: random.Random = None):
        self.rng = rng or random.Random()

    # ── Text matching helpers ──

    def _text_contains(self, text: str, phrase: str) -> bool:
        """Check if phrase appears in text as a distinct word (or with common
        inflections like s/es/ed/ing/ies). Multi-word phrases use substring match.

        Prevents false matches like 'war' inside 'forward' or 'warmth',
        while allowing 'whisper' to match 'whispers' and 'ash' to match 'ashes'.
        """
        if " " in phrase:
            return phrase in text
        # Exact whole-word match
        pattern = r"\b" + re.escape(phrase) + r"\b"
        if re.search(pattern, text):
            return True
        # Common inflections for single words
        if len(phrase) > 2:
            forms = [
                phrase + "s",       # regular plural
                phrase + "ed",      # past tense (for non-e-ending words)
                phrase + "ing",     # gerund (for non-e-ending words)
                phrase + "es",      # es plural (churches, ashes)
            ]
            # Y→IES: mystery → mysteries
            if phrase.endswith("y"):
                forms.append(phrase[:-1] + "ies")
            # Drop-e rule: explore → explored/exploring
            if phrase.endswith("e") and len(phrase) > 3:
                stem = phrase[:-1]
                forms.extend([stem + "ed", stem + "ing"])
            for form in forms:
                if re.search(r"\b" + re.escape(form) + r"\b", text):
                    return True
        return False

    # ── Concept detection (shared with concept_visuals) ──

    def _detect_concepts(self, text: str) -> dict[str, float]:
        """Detect abstract concepts from vocabulary-level signals.

        Returns dict of concept_name -> intensity (0.0-1.0).
        Mirrors ConceptVisualsTranslator.detect_concepts to avoid circular import.
        """
        tl = text.lower()
        intensities: dict[str, float] = {}
        concept_keywords = {
            "power": ["king", "queen", "emperor", "throne", "crown", "ruler", "lord",
                       "commanded", "ruled", "dominion", "authority", "mighty",
                       "powerful", "strongest", "reigned"],
            "powerless": ["lost power", "overthrown", "dethroned", "defeated", "surrendered",
                          "begged", "pleaded", "weak", "helpless", "powerless", "broken",
                          "fell from", "lost everything", "humbled", "stripped of",
                          "empty throne", "walked alone", "nothing remained"],
            "fear": ["afraid", "scared", "terrified", "fear", "fearful", "dread",
                     "panicked", "fled", "ran away", "hid", "trembled", "shaking",
                     "heart pounded", "frozen", "paralyzed", "horrified",
                     "pounded", "heart raced", "breath caught"],
            "trust": ["trust", "trusted", "trusting", "faith", "believed", "relied",
                      "depended", "loyal", "loyalty", "bond", "friendship",
                      "confidence", "comfortable with", "let its guard down",
                      "stepped forward", "moved closer", "reached out"],
            "curiosity": ["curious", "curiosity", "wondered", "fascinated", "intrigued",
                          "drawn to", "pulled toward", "explored", "investigated",
                          "leaned closer", "peered", "studied", "examined",
                          "flickered inside", "pulled harder", "wonder"],
            "danger": ["danger", "dangerous", "threat", "threatened", "predator",
                       "hunted", "stalked", "poisonous", "deadly", "lethal",
                       "warning", "alarm", "fierce", "savage", "lurking",
                       "dark cave", "shadow moved", "something wrong"],
            "isolation": ["alone", "lonely", "solitary", "isolated", "abandoned",
                          "deserted", "empty", "only", "by itself", "separated",
                          "cut off", "stranded", "left behind",
                          "empty halls", "no one", "nobody"],
            "community": ["together", "community", "village", "tribe", "settlement",
                          "gathered", "crowd", "group", "family", "pack",
                          "herd", "flock", "neighbors", "allied",
                          "guards", "children", "people"],
            "discovery": ["discovered", "found", "stumbled upon", "uncovered", "revealed",
                          "breakthrough", "eureka", "realized", "understood",
                          "came across", "noticed", "spotted",
                          "found light", "flickered", "stepped into"],
            "growth": ["grew", "expanded", "rose", "climbed", "flourished",
                       "strengthened", "thrived", "prospered", "increased",
                       "built", "developed", "advanced", "raised"],
            "decline": ["declined", "weakened", "faded", "shrank", "deteriorated",
                        "crumbled", "collapsed", "fell apart", "withered",
                        "waned", "diminished", "decayed",
                        "loses power", "loses strength", "fading"],
            "barrier": ["blocked", "barrier", "wall", "fence", "obstacle",
                        "separated", "divided", "closed off", "impassable",
                        "guarded", "locked", "sealed", "forbidden",
                        "looked away", "turned away"],
            "connection": ["connected", "linked", "bridged", "joined", "united",
                           "together", "met", "reunited", "bound", "tied",
                           "alliance", "merged", "crossed to",
                           "trade routes opened", "bridge", "highway"],
            "control": ["controlled", "order", "discipline", "commanded", "organized",
                        "planned", "deliberate", "calculated", "strategic",
                        "mastered", "dominated", "regulated"],
            "chaos": ["chaos", "chaotic", "disorder", "confusion", "pandemonium",
                      "tumult", "turmoil", "unpredictable", "wild", "frenzy",
                      "out of control", "spiraled", "descended into"],
            "hope": ["hope", "hopeful", "optimistic", "dreamed", "longed",
                     "wished", "prayed", "believed", "looked forward",
                     "light at the end", "dawn of", "new beginning",
                     "found light", "stepped forward", "pulled harder"],
            "despair": ["despair", "hopeless", "gave up", "surrendered", "lost all",
                        "nothing left", "pointless", "futile", "no way out",
                        "abandoned hope", "consumed by darkness",
                        "nothing remained", "empty", "lost everything"],
        }
        for concept, keywords in concept_keywords.items():
            score = 0
            for kw in keywords:
                if self._text_contains(tl, kw):
                    score += 1
            if score > 0:
                intensities[concept] = min(1.0, score / 4.0)
        return intensities

    # ── Three-component archetype detection ──

    def detect_archetype(self, full_text: str) -> str:
        """Detect which story archetype this narrative follows.

        Uses three-component scoring:
          1. keyword_score  — single-word/phrase vocabulary matches
          2. event_score    — multi-word narrative event patterns
          3. concept_score  — abstract concept signals blended via affinities

        Returns one of the 10 archetype names.
        """
        tl = full_text.lower()
        scores = {}

        # ── 1. Keyword score (word-boundary aware) ──
        for archetype, config in ARCHETYPE_DEFS.items():
            score = 0
            for kw in config["keywords"]:
                if self._text_contains(tl, kw):
                    score += 2
            matched_count = sum(1 for kw in config["keywords"] if self._text_contains(tl, kw))
            keyword_density = matched_count / max(len(config["keywords"]), 1)
            score += keyword_density * 10
            scores[archetype] = score

        # ── 2. Event score ──
        for archetype, events in ARCHETYPE_EVENTS.items():
            for event in events:
                if event in tl:
                    scores[archetype] = scores.get(archetype, 0) + 4

        # ── 3. Concept score ──
        detected = self._detect_concepts(tl)
        for archetype, affinities in ARCHETYPE_CONCEPT_AFFINITIES.items():
            concept_bonus = 0
            for concept, weight in affinities.items():
                intensity = detected.get(concept, 0.0)
                if intensity > 0:
                    concept_bonus += intensity * weight
            if concept_bonus > 0:
                scores[archetype] = scores.get(archetype, 0) + concept_bonus * 5

        # ── 4. Targeted heuristics (additive, not floor) ──
        heuristic_map = {
            "transformation": ["became", "evolved", "transformed",
                               "over generations",
                               "turned into", "no longer", "gradually",
                               "adapted", "over time", "eventually",
                               "rebuilt", "reborn", "restored", "reopened"],
            "mystery": ["mystery", "mysterious", "unexplained", "enigma",
                        "puzzle", "cannot explain", "nobody knows",
                        "riddle", "cursed", "forbidden", "hidden",
                        "legend of", "myth of", "without a trace",
                        "strange markings", "cannot be read",
                        "impossible to understand"],
            "disaster": ["eruption", "earthquake", "flood", "extinction",
                         "disaster", "destroyed", "catastrophe",
                         "exploded", "collapsed",
                         "volcanic", "tsunami", "plague", "wildfire",
                         "volcano", "erupted", "devastated",
                         "illness", "disease", "epidemic"],
            "journey": ["journey", "traveled", "voyage", "expedition",
                        "crossed", "set out", "made landfall",
                        "trekked", "sailed", "wandered"],
            "rise_and_fall": ["rose to", "golden age", "glory", "empire",
                              "flourished", "declined", "crumbled",
                              "fell from", "rise and fall", "achieved greatness",
                              "reached its height", "slowly declined",
                              "built an empire", "lost everything"],
            "survival": ["stranded", "survive", "survival", "desperate",
                         "endure", "endurance", "starving",
                         "persist", "escaped", "rescued",
                         "struggling to survive", "fighting to stay alive",
                         "shelter", "sank", "shipwreck", "no food",
                         "no water", "fresh water", "caught fish"],
            "first_contact": ["first contact", "encountered", "approached",
                              "face to face", "first meeting", "alien",
                              "never seen before", "came across", "stumbled upon",
                              "emerged from", "appeared before"],
            "discovery": ["curious", "curiosity", "discovery", "breakthrough",
                          "eureka", "uncovered", "figured out", "experiment",
                          "learned that", "realized that", "understood",
                          "understand", "learning", "knowledge", "truth",
                          "opened their eyes", "saw the truth",
                          "fascinating", "astonishing"],
            "migration": ["migrated", "exodus", "displaced", "refugee",
                          "nomad", "set off",
                          "left behind", "said goodbye", "departed",
                          "great journey", "long road", "settlers",
                          "pioneers", "crossing the",
                          "wandered", "followed", "valley", "herd"],
            "war": ["war", "battle", "invasion", "enemy",
                    "fought", "siege",
                    "declared war", "went to war", "marched to",
                    "battlefield", "surrendered", "ceasefire",
                    "attack", "defend"],
        }
        for archetype, words in heuristic_map.items():
            for w in words:
                if self._text_contains(tl, w):
                    scores[archetype] = scores.get(archetype, 0) + 4
                    break

        # ── Fallback for very low scores ──
        if max(scores.values()) < 3:
            for archetype, config in ARCHETYPE_DEFS.items():
                phrase_score = 0
                for kw in config["keywords"]:
                    if self._text_contains(tl, kw):
                        phrase_score += 1
                if phrase_score >= 2:
                    scores[archetype] = max(scores.get(archetype, 0), phrase_score * 2)

        best = max(scores, key=scores.get)
        return best

    def detect_archetype_probs(self, full_text: str) -> dict[str, float]:
        """Return a probability distribution over all archetypes.

        Uses the same three-component scoring as detect_archetype(),
        then normalizes via softmax (temperature=2 for reasonable spread).
        """
        tl = full_text.lower()
        scores: dict[str, float] = {}

        # ── 1. Keyword score ──
        for archetype, config in ARCHETYPE_DEFS.items():
            score = 0
            for kw in config["keywords"]:
                if self._text_contains(tl, kw):
                    score += 2
            matched_count = sum(1 for kw in config["keywords"] if self._text_contains(tl, kw))
            keyword_density = matched_count / max(len(config["keywords"]), 1)
            score += keyword_density * 10
            scores[archetype] = score

        # ── 2. Event score ──
        for archetype, events in ARCHETYPE_EVENTS.items():
            for event in events:
                if event in tl:
                    scores[archetype] = scores.get(archetype, 0) + 4

        # ── 3. Concept score ──
        detected = self._detect_concepts(tl)
        for archetype, affinities in ARCHETYPE_CONCEPT_AFFINITIES.items():
            concept_bonus = 0
            for concept, weight in affinities.items():
                intensity = detected.get(concept, 0.0)
                if intensity > 0:
                    concept_bonus += intensity * weight
            if concept_bonus > 0:
                scores[archetype] = scores.get(archetype, 0) + concept_bonus * 5

        # ── 4. Targeted heuristics ──
        heuristic_map = {
            "transformation": ["became", "evolved", "transformed",
                               "over generations", "turned into", "no longer",
                               "gradually", "adapted", "over time", "eventually",
                               "rebuilt", "reborn", "restored", "reopened"],
            "mystery": ["mystery", "mysterious", "unexplained", "enigma",
                        "puzzle", "cannot explain", "nobody knows",
                        "riddle", "cursed", "forbidden", "hidden",
                        "legend of", "myth of", "without a trace",
                        "strange markings", "cannot be read", "impossible to understand"],
            "disaster": ["eruption", "earthquake", "flood", "extinction",
                         "disaster", "destroyed", "catastrophe",
                         "exploded", "collapsed", "volcanic", "tsunami",
                         "plague", "wildfire", "volcano", "erupted", "devastated",
                         "illness", "disease", "epidemic"],
            "journey": ["journey", "traveled", "voyage", "expedition",
                        "crossed", "set out", "made landfall",
                        "trekked", "sailed", "wandered"],
            "rise_and_fall": ["rose to", "golden age", "glory", "empire",
                              "flourished", "declined", "crumbled",
                              "fell from", "rise and fall", "achieved greatness",
                              "reached its height", "slowly declined",
                              "built an empire", "lost everything"],
            "survival": ["stranded", "survive", "survival", "desperate",
                         "endure", "endurance", "starving",
                         "persist", "escaped", "rescued",
                         "struggling to survive", "fighting to stay alive",
                         "shelter", "sank", "shipwreck", "no food",
                         "no water", "fresh water", "caught fish"],
            "first_contact": ["first contact", "encountered", "approached",
                              "face to face", "first meeting", "alien",
                              "never seen before", "came across", "stumbled upon",
                              "emerged from", "appeared before"],
            "discovery": ["curious", "curiosity", "discovery", "breakthrough",
                          "eureka", "uncovered", "figured out", "experiment",
                          "learned that", "realized that", "understood",
                          "understand", "learning", "knowledge", "truth",
                          "opened their eyes", "saw the truth",
                          "fascinating", "astonishing"],
            "migration": ["migrated", "exodus", "displaced", "refugee",
                          "nomad", "set off",
                          "left behind", "said goodbye", "departed",
                          "great journey", "long road", "settlers",
                          "pioneers", "crossing the",
                          "wandered", "followed", "valley", "herd"],
            "war": ["war", "battle", "invasion", "enemy",
                    "fought", "siege",
                    "declared war", "went to war", "marched to",
                    "battlefield", "surrendered", "ceasefire",
                    "attack", "defend"],
        }
        for archetype, words in heuristic_map.items():
            for w in words:
                if self._text_contains(tl, w):
                    scores[archetype] = scores.get(archetype, 0) + 4
                    break

        # Normalize via softmax (temperature=2 for moderate spread)
        import math as _math
        temp = 2.0
        max_score = max(scores.values()) if scores else 0
        if max_score <= 0:
            return {k: 1.0 / len(ARCHETYPE_DEFS) for k in ARCHETYPE_DEFS}
        exp_scores = {k: _math.exp((v - max_score) / temp) for k, v in scores.items()}
        total = sum(exp_scores.values())
        if total <= 0:
            return {k: 1.0 / len(ARCHETYPE_DEFS) for k in ARCHETYPE_DEFS}
        return {k: round(v / total, 3) for k, v in exp_scores.items()}

    def get_archetype_config(self, archetype: str) -> dict:
        """Get full config for an archetype."""
        return ARCHETYPE_DEFS.get(archetype, ARCHETYPE_DEFS["transformation"])

    # ── Sentence-to-phase mapping ──

    def map_sentences_to_phases(self, sentences: list[str], archetype: str) -> list[tuple[str, str, int]]:
        """Map each sentence to its narrative phase.

        Returns list of (sentence, phase_name, phase_index).
        """
        config = self.get_archetype_config(archetype)
        phases = config["phases"]
        n_phases = len(phases)
        n_sentences = len(sentences)

        if n_sentences == 0:
            return []

        if archetype == "unknown" or n_phases == 0:
            # Fallback: evenly distribute as generic narrative
            return [(s, "scene", min(i, 3)) for i, s in enumerate(sentences)]

        # Distribute sentences across archetype phases
        assigned = []
        for i, sentence in enumerate(sentences):
            # Calculate which phase this sentence belongs to
            phase_position = i / max(n_sentences - 1, 1)  # 0.0 to 1.0
            phase_idx = min(int(phase_position * n_phases), n_phases - 1)
            phase_name = phases[phase_idx]
            assigned.append((sentence, phase_name, phase_idx))

        return assigned

    # ── Archetype-powered beat generation ──

    def structure_narrative(self, sentences: list[str],
                            archetype: Optional[str] = None,
                            full_text: Optional[str] = None,
                            archetype_probs: Optional[dict[str, float]] = None
                            ) -> list[ArchetypeBeat]:
        """Generate a full archetype beat structure for the narrative.

        If archetype_probs is given, parameters from multiple archetypes
        are blended proportionally (archetype blending).

        Args:
            sentences: list of sentence strings
            archetype: optional pre-detected archetype. If None, auto-detect.
            full_text: used for detection if archetype not provided
            archetype_probs: probability dict from detect_archetype_probs().

        Returns:
            list of ArchetypeBeats, one per sentence-phase assignment
        """
        if archetype_probs is None:
            if archetype is None:
                archetype = self.detect_archetype(full_text or " ".join(sentences))
            if archetype == "unknown":
                archetype = "transformation"
            # Build a single-point probability distribution
            archetype_probs = {archetype: 1.0}
        else:
            # Use the highest-prob archetype for phase mapping
            archetype = max(archetype_probs, key=archetype_probs.get)

        config = self.get_archetype_config(archetype)
        phase_details = PHASE_DETAILS.get(archetype, {})

        # Collect configs for all archetypes with significant probability
        active_archetypes = [(a, p) for a, p in archetype_probs.items() if p > 0.05]
        active_configs = [(a, p, self.get_archetype_config(a)) for a, p in active_archetypes]

        assigned = self.map_sentences_to_phases(sentences, archetype)
        beats = []

        n_sentences = len(sentences)

        for i, (sentence, phase_name, phase_idx) in enumerate(assigned):
            details = phase_details.get(phase_name, {})

            # Blend tension: weighted average across active archetypes
            blended_tension = 0.0
            tension_weight = 0.0
            # Blend lighting/mood/camera: weighted vote
            lighting_votes: dict[str, float] = {}
            mood_votes: dict[str, float] = {}
            camera_votes: dict[str, float] = {}
            animation_votes: dict[str, float] = {}

            for arch, prob, cfg in active_configs:
                n_phases = len(cfg["phases"])
                idx = min(phase_idx, n_phases - 1)

                # Tension
                t_arc = cfg["tension_arc"]
                t_val = t_arc[idx] if idx < len(t_arc) else 5
                blended_tension += prob * t_val
                tension_weight += prob

                # Lighting
                l_arc = cfg["lighting_arc"]
                l_val = l_arc[idx] if idx < len(l_arc) else "day"
                lighting_votes[l_val] = lighting_votes.get(l_val, 0.0) + prob

                # Mood / camera / animation from phase details
                arch_details = PHASE_DETAILS.get(arch, {})
                # Find the closest phase name in this archetype
                arch_phases = cfg["phases"]
                closest_phase = arch_phases[idx] if idx < len(arch_phases) else arch_phases[-1]
                phase_info = arch_details.get(closest_phase, {})
                mood_votes[phase_info.get("mood", "neutral")] = mood_votes.get(phase_info.get("mood", "neutral"), 0.0) + prob
                camera_votes[phase_info.get("camera", "medium")] = camera_votes.get(phase_info.get("camera", "medium"), 0.0) + prob
                animation_votes[phase_info.get("animation", "idle")] = animation_votes.get(phase_info.get("animation", "idle"), 0.0) + prob

            tension = round(blended_tension / max(tension_weight, 0.01))
            lighting = max(lighting_votes, key=lighting_votes.get) if lighting_votes else "day"
            mood = max(mood_votes, key=mood_votes.get) if mood_votes else "neutral"
            camera = max(camera_votes, key=camera_votes.get) if camera_votes else "medium"
            anim = max(animation_votes, key=animation_votes.get) if animation_votes else "idle"

            beat = ArchetypeBeat(
                phase=phase_name,
                archetype=archetype,
                beat_index=i,
                total_phases=len(config["phases"]),
                tension=tension,
                suggested_lighting=lighting,
                suggested_mood=mood,
                suggested_camera=camera,
                suggested_animation=anim,
                goal=details.get("goal", "advance story"),
                description=details.get("description", ""),
                archetype_probs=archetype_probs,
            )
            beats.append(beat)

        return beats

    # ── Archetype-aware reveal planning ──

    def get_reveal_strategy(self, archetype: str) -> dict:
        """Get the reveal strategy for an archetype.

        Controls how characters and objects are introduced over time.
        """
        strategies = {
            "transformation": {
                "character_reveal": "slow",
                "object_reveal": "normal",
                "first_appearance": "hint",
                "pacing": "gradual",
            },
            "mystery": {
                "character_reveal": "very_slow",
                "object_reveal": "slow",
                "first_appearance": "silhouette",
                "pacing": "delayed",
            },
            "disaster": {
                "character_reveal": "fast",
                "object_reveal": "fast",
                "first_appearance": "full",
                "pacing": "rapid",
            },
            "journey": {
                "character_reveal": "normal",
                "object_reveal": "slow",
                "first_appearance": "partial",
                "pacing": "moderate",
            },
            "rise_and_fall": {
                "character_reveal": "normal",
                "object_reveal": "normal",
                "first_appearance": "full",
                "pacing": "slow_burn",
            },
            "survival": {
                "character_reveal": "fast",
                "object_reveal": "slow",
                "first_appearance": "full",
                "pacing": "rapid",
            },
            "first_contact": {
                "character_reveal": "very_slow",
                "object_reveal": "slow",
                "first_appearance": "silhouette",
                "pacing": "delayed",
            },
            "discovery": {
                "character_reveal": "slow",
                "object_reveal": "very_slow",
                "first_appearance": "partial",
                "pacing": "moderate",
            },
            "migration": {
                "character_reveal": "normal",
                "object_reveal": "slow",
                "first_appearance": "full",
                "pacing": "moderate",
            },
            "war": {
                "character_reveal": "fast",
                "object_reveal": "fast",
                "first_appearance": "full",
                "pacing": "rapid",
            },
        }
        return strategies.get(archetype, strategies["transformation"])

    def get_liturgical_beat(self, archetype: str, phase_name: str, beat_idx: int) -> Optional[dict]:
        """Get a specific micro-beat within a phase for finer granularity.

        Some archetypes support sub-beats within each phase for richer storytelling.
        """
        sub_beats = {
            "transformation": {
                "old_state": [
                    {"goal": "establish calm", "camera": "extreme_wide", "duration": 2.0},
                    {"goal": "show daily life", "camera": "medium", "duration": 1.5},
                ],
                "pressure": [
                    {"goal": "first sign of change", "camera": "closeup", "duration": 1.5},
                    {"goal": "tension rises", "camera": "dutch", "duration": 2.0},
                ],
                "change": [
                    {"goal": "difference appears", "camera": "extreme_closeup", "duration": 1.5},
                    {"goal": "change accelerates", "camera": "handheld", "duration": 1.5},
                ],
                "new_state": [
                    {"goal": "reveal the result", "camera": "wide", "duration": 2.0},
                    {"goal": "show new normal", "camera": "medium", "duration": 1.5},
                ],
            },
            "mystery": {
                "question": [
                    {"goal": "strange detail", "camera": "closeup", "duration": 2.0},
                ],
                "hint": [
                    {"goal": "clue appears", "camera": "extreme_closeup", "duration": 1.5},
                ],
                "contradiction": [
                    {"goal": "clue doesn't fit", "camera": "dutch", "duration": 2.0},
                ],
                "reveal": [
                    {"goal": "truth emerges", "camera": "extreme_wide", "duration": 2.5},
                ],
            },
        }
        archetype_sub = sub_beats.get(archetype, {})
        phase_sub = archetype_sub.get(phase_name, [])
        if 0 <= beat_idx < len(phase_sub):
            return phase_sub[beat_idx]
        return None


# ── Convenience: one-shot narrative analysis ──

def analyze_narrative(full_text: str) -> dict:
    """Full narrative analysis: detect archetype, structure beats."""
    engine = NarrativeEngine()
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', full_text.strip()) if s.strip()]
    archetype = engine.detect_archetype(full_text)
    beats = engine.structure_narrative(sentences, archetype)
    config = engine.get_archetype_config(archetype)

    return {
        "archetype": archetype,
        "archetype_label": config.get("label", "Unknown"),
        "description": config.get("description", ""),
        "num_sentences": len(sentences),
        "num_phases": len(config["phases"]),
        "phases": config["phases"],
        "tension_arc": config.get("tension_arc", []),
        "lighting_arc": config.get("lighting_arc", []),
        "beats": beats,
        "sentences": sentences,
        "reveal_strategy": engine.get_reveal_strategy(archetype),
    }
