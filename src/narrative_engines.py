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
            "mystery", "unknown", "secret", "hidden", "discovered", "revealed",
            "ancient", "lost", "why", "how", "puzzle", "strange", "unexplained",
            "mysterious", "legend", "myth", "rumor", "whisper", "forgotten",
            "found", "symbol", "carving", "hint", "temple", "ruin", "artifact",
            "nobody knows", "no one knows", "cannot explain", "buried secret",
            "cursed", "treasure", "map", "code", "cipher", "hieroglyph",
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
            "exploded", "buried", "ash", "lava", "melted", "burned",
            "sank", "drowned", "crumbled", "fell", "crashed", "shattered",
            "wave", "flooded", "drought", "blizzard", "wildfire",
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
            "migrated", "migration", "traveled", "travel", "moved",
            "move", "followed", "follow", "herd", "flock", "season",
            "seasonal", "across", "destination", "new home", "homeland",
            "trek", "exodus", "displaced", "refugee", "nomad",
            "nomadic", "caravan", "settlers", "pioneers", "crossing",
            "great journey", "long road", "search for", "new land",
            "left behind", "said goodbye", "departed", "set off",
            "stopped wandering", "settled", "built", "planted",
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


# ── Phase definitions per archetype ──

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

    # ── Archetype detection ──

    def detect_archetype(self, full_text: str) -> str:
        """Detect which story archetype this narrative follows.

        Returns one of: transformation, mystery, disaster, journey, unknown
        """
        tl = full_text.lower()

        scores = {}
        for archetype, config in ARCHETYPE_DEFS.items():
            score = 0
            for kw in config["keywords"]:
                if kw in tl:
                    score += 2
            # Bonus for matching phrase density
            words = tl.split()
            keyword_density = sum(1 for kw in config["keywords"] if kw in tl) / max(len(config["keywords"]), 1)
            score += keyword_density * 10
            scores[archetype] = score

        # Theme-specific heuristics
        if any(w in tl for w in ["became", "evolved", "transformed", "over generations",
                                  "turned into", "no longer", "gradually",
                                  "adapted", "over time", "eventually"]):
            scores["transformation"] = max(scores.get("transformation", 0), 6)
        if any(w in tl for w in ["mystery", "unknown", "secret", "why", "how",
                                  "ancient", "lost", "revealed", "found",
                                  "symbol", "hint", "temple", "ruin"]):
            scores["mystery"] = max(scores.get("mystery", 0), 6)
        if any(w in tl for w in ["eruption", "earthquake", "flood", "extinction",
                                  "disaster", "destroyed", "catastrophe",
                                  "exploded", "buried", "collapsed",
                                  "volcanic", "tsunami", "plague"]):
            scores["disaster"] = max(scores.get("disaster", 0), 6)
        if any(w in tl for w in ["journey", "traveled", "migrated", "expedition",
                                  "voyage", "crossed", "explored", "set out",
                                  "across the", "ocean crossing", "made landfall",
                                  "reached", "discovered island", "navigation"]):
            scores["journey"] = max(scores.get("journey", 0), 6)
        if any(w in tl for w in ["rose", "rose to", "golden age", "glory", "empire",
                                  "flourished", "peak", "declined", "crumbled",
                                  "fell from", "rise and fall", "achieved greatness",
                                  "reached its height", "slowly declined"]):
            scores["rise_and_fall"] = max(scores.get("rise_and_fall", 0), 6)
        if any(w in tl for w in ["stranded", "survive", "survival", "desperate",
                                  "alone", "endure", "endurance", "starving",
                                  "persist", "escaped", "rescued", "hunting for",
                                  "struggling to survive", "fighting to stay alive"]):
            scores["survival"] = max(scores.get("survival", 0), 6)
        if any(w in tl for w in ["first contact", "encountered", "approached",
                                  "face to face", "first meeting", "alien",
                                  "never seen before", "came across", "stumbled upon",
                                  "emerged from", "appeared before"]):
            scores["first_contact"] = max(scores.get("first_contact", 0), 6)
        if any(w in tl for w in ["curious", "discovery", "breakthrough", "eureka",
                                  "uncovered", "figured out", "experiment",
                                  "learned that", "realized that", "understood",
                                  "opened their eyes", "saw the truth",
                                  "fascinating", "astonishing"]):
            scores["discovery"] = max(scores.get("discovery", 0), 6)
        if any(w in tl for w in ["migrated", "exodus", "displaced", "refugee",
                                  "nomad", "set off", "new home", "search for",
                                  "left behind", "said goodbye", "departed",
                                  "great journey", "long road", "settlers",
                                  "pioneers", "crossing the"]):
            scores["migration"] = max(scores.get("migration", 0), 6)
        if any(w in tl for w in ["war", "battle", "invasion", "army", "enemy",
                                  "fought", "siege", "warrior", "soldier",
                                  "declared war", "went to war", "marched to",
                                  "battlefield", "surrendered", "ceasefire",
                                  "conflict", "attack", "defend"]):
            scores["war"] = max(scores.get("war", 0), 6)

        if not scores or max(scores.values()) < 3:
            # Second pass: check for phrase patterns
            for archetype, config in ARCHETYPE_DEFS.items():
                phrase_score = 0
                for kw in config["keywords"]:
                    if kw in tl:
                        phrase_score += 1
                if phrase_score >= 2:
                    scores[archetype] = max(scores.get(archetype, 0), phrase_score * 2)

        best = max(scores, key=scores.get)
        return best

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
                            full_text: Optional[str] = None) -> list[ArchetypeBeat]:
        """Generate a full archetype beat structure for the narrative.

        Args:
            sentences: list of sentence strings
            archetype: optional pre-detected archetype. If None, auto-detect.
            full_text: used for detection if archetype not provided

        Returns:
            list of ArchetypeBeats, one per sentence-phase assignment
        """
        if archetype is None:
            archetype = self.detect_archetype(full_text or " ".join(sentences))
        if archetype == "unknown":
            archetype = "transformation"  # best default

        config = self.get_archetype_config(archetype)
        phase_details = PHASE_DETAILS.get(archetype, {})
        tension_arc = config["tension_arc"]
        lighting_arc = config["lighting_arc"]
        emotion_arc = config.get("emotion_arc", {})

        assigned = self.map_sentences_to_phases(sentences, archetype)
        beats = []

        for i, (sentence, phase_name, phase_idx) in enumerate(assigned):
            details = phase_details.get(phase_name, {})
            tension = tension_arc[phase_idx] if phase_idx < len(tension_arc) else 5
            lighting = lighting_arc[phase_idx] if phase_idx < len(lighting_arc) else "day"

            # Get emotion values for this phase
            emotions_at_phase = {}
            for dim, arc in emotion_arc.items():
                if phase_idx < len(arc):
                    emotions_at_phase[dim] = arc[phase_idx]

            beat = ArchetypeBeat(
                phase=phase_name,
                archetype=archetype,
                beat_index=i,
                total_phases=len(config["phases"]),
                tension=tension,
                suggested_lighting=lighting,
                suggested_mood=details.get("mood", "neutral"),
                suggested_camera=details.get("camera", "medium"),
                suggested_animation=details.get("animation", "idle"),
                goal=details.get("goal", "advance story"),
                description=details.get("description", ""),
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
