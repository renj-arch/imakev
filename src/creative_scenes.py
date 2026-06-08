"""Creative scene compositions for poetic, metaphorical, and transitional text.
Handles the segments that concept extraction can't — openings, closings,
reflective musings, philosophical asides. Maps them to symbolic visuals.
"""

import re

# ── Creative scene patterns ────────────────────────────────────
# Each entry: list of regex trigger patterns → visual composition

CREATIVE_SCENES = [

    # ── Book / Page metaphors ──
    {
        "id": "book_page_turn",
        "patterns": [
            r"turns?\s+the\s+page", r"turn\s+the\s+page",
            r"page\s+turns?", r"pag\w+\s*turn",
            r"chapter\s+ends?", r"new\s+chapter",
            r"close[sd]?\s+the\s+book", r"life\s+.*\bpage\b",
            r"write\w*\s+(your|our|a)\s+(own\s+)?story",
        ],
        "get_scene": lambda text, rng: {
            "bg": {"type": "gradient", "colors": [[210, 200, 180], [170, 155, 130]], "horizon": 0.5,
                   "ground_color": [140, 120, 100]},
            "elements": [
                {"type": "book", "x": 0.5, "y": 0.48, "scale": 4.5,
                 "fill": [160, 120, 80], "stroke": [100, 70, 40], "stroke_width": 2,
                 "title": "LIFE", "open": True, "shadow": True},
                {"type": "hand", "x": 0.68, "y": 0.42, "scale": 2.5,
                 "skin_color": [230, 200, 175], "pose": "pointing"},
                {"type": "circle", "x": 0.2, "y": 0.3, "radius": 3, "fill": [255, 230, 150, 60]},
                {"type": "circle", "x": 0.8, "y": 0.25, "radius": 2, "fill": [255, 230, 150, 40]},
            ],
            "atmosphere": {"particles": "sparkles", "star_count": 15},
            "mood": rng.choice(["hopeful", "peaceful", "epic"]),
        }
    },

    # ── Planet / Earth / World reflections ──
    {
        "id": "planet_serene",
        "patterns": [
            r"planet\s+doesn'?t\s+stop", r"world\s+(keeps?|continues?|goes?\s+on)",
            r"earth\s+(keeps?|continues?|turns?)", r"life\s+goes?\s+on",
            r"world\s+(keeps?|keeps?\s+on)\s+(moving|turning|spinning)",
            r"oceans?\s+continu",
        ],
        "get_scene": lambda text, rng: {
            "bg": {"type": "gradient", "colors": [[5, 5, 25], [15, 10, 40]], "horizon": 0.0},
            "elements": [
                {"type": "planet", "x": 0.5, "y": 0.45, "scale": 3.5,
                 "fill": [40, 100, 180], "shadow": True},
                {"type": "star", "x": 0.15, "y": 0.2, "scale": 0.5, "fill": [255, 255, 200]},
                {"type": "star", "x": 0.85, "y": 0.15, "scale": 0.4, "fill": [255, 255, 200]},
                {"type": "star", "x": 0.3, "y": 0.1, "scale": 0.3, "fill": [200, 200, 255]},
                {"type": "star", "x": 0.7, "y": 0.25, "scale": 0.35, "fill": [200, 200, 255]},
                {"type": "star", "x": 0.5, "y": 0.08, "scale": 0.5, "fill": [255, 230, 150]},
            ],
            "atmosphere": {"particles": "stars", "star_count": 20},
            "mood": rng.choice(["peaceful", "hopeful", "mysterious"]),
        }
    },

    # ── Heavy thought / Reflection ──
    {
        "id": "heavy_thought",
        "patterns": [
            r"heavy\s+thought", r"strange\s+part",
            r"unsettling\s+thing", r"that'?s?\s+(the\s+)?(heavy|strange|unsettling)",
            r"almost\s+worse\s+than", r"hardest\s+part",
        ],
        "get_scene": lambda text, rng: {
            "bg": {"type": "gradient", "colors": [[40, 35, 55], [25, 20, 40]], "horizon": 0.5,
                   "ground_color": [15, 12, 25]},
            "elements": [
                {"type": "human", "x": 0.3, "y": 0.55, "scale": 2.5, "pose": "thinking",
                 "fill": [80, 70, 100], "skin_color": [220, 190, 170]},
                {"type": "circle", "x": 0.55, "y": 0.32, "radius": 25,
                 "fill": [100, 90, 140, 80], "stroke": [140, 130, 180], "stroke_width": 2},
                {"type": "circle", "x": 0.55, "y": 0.32, "radius": 12, "fill": [140, 130, 180, 60]},
                {"type": "circle", "x": 0.55, "y": 0.32, "radius": 5, "fill": [200, 190, 230]},
            ],
            "atmosphere": {"particles": "none", "fog": True},
            "mood": rng.choice(["somber", "mysterious", "dramatic"]),
        }
    },

    # ── Extinction / Vanished / Gone ──
    {
        "id": "extinction_moment",
        "patterns": [
            r"something\s+ancient\s+had\s+vanished",
            r"gone\.?\s*(the\s+)?(way\s+of\s+)?(the\s+)?dinosaur",
            r"no\s+(more|longer|animal\s+knows)",
            r"(last|final)\s+(of\s+)?(its|their)\s+kind",
            r"vanished\w*", r"disappeared\w*",
            r"no\s+(ceremony|witness|one)\s+(marks?|records?|knows?)",
        ],
        "get_scene": lambda text, rng: {
            "bg": {"type": "gradient", "colors": [[60, 50, 60], [30, 25, 35]], "horizon": 0.5,
                   "ground_color": [20, 15, 25]},
            "elements": [
                {"type": "footprint", "x": 0.5, "y": 0.55, "scale": 3.0,
                 "fill": [80, 70, 80], "opacity": 100},
                {"type": "circle", "x": 0.5, "y": 0.48, "radius": 10,
                 "fill": [150, 140, 160, 30]},
                {"type": "circle", "x": 0.5, "y": 0.48, "radius": 4,
                 "fill": [200, 190, 210, 20]},
            ],
            "atmosphere": {"particles": "mist", "fog": True},
            "mood": rng.choice(["somber", "mysterious"]),
        }
    },

    # ── Imagine / Opening hook ──
    {
        "id": "imagine_opening",
        "patterns": [
            r"^imagine\s+being", r"^imagine\s+standing",
            r"^imagine\s+looking", r"^imagine\s+a\s+world",
            r"^picture\s+this", r"^what\s+if",
            r"^(have\s+you\s+ever\s+|have\s+you\s+|did\s+you\s+ever\s+|did\s+you\s+|ever\s+)wonder",
        ],
        "get_scene": lambda text, rng: {
            "bg": {"type": "gradient", "colors": [[20, 15, 35], [10, 8, 25]], "horizon": 0.0},
            "elements": [
                {"type": "star", "x": rng.uniform(0.2, 0.8), "y": rng.uniform(0.15, 0.35),
                 "scale": 1.5, "fill": [255, 240, 180]},
                {"type": "star", "x": rng.uniform(0.15, 0.85), "y": rng.uniform(0.25, 0.5),
                 "scale": 0.8, "fill": [200, 200, 255]},
                {"type": "star", "x": rng.uniform(0.1, 0.9), "y": rng.uniform(0.1, 0.2),
                 "scale": 0.5, "fill": [255, 200, 200]},
                {"type": "lightbulb", "x": 0.5, "y": 0.42, "scale": 3.0,
                 "fill": [255, 220, 80, 200]},
            ],
            "atmosphere": {"particles": "stars", "star_count": 15},
            "mood": rng.choice(["mysterious", "hopeful", "epic"]),
        }
    },

    # ── End / Closing ──
    {
        "id": "story_closing",
        "patterns": [
            r"that'?s?\s+(the\s+)?(story|end|ending)",
            r"and\s+(that'?s?|that\s+is)\s+(how|why|what)",
            r"and\s+(so|thus|therefore)",
            r"the\s+(end|ending)\s+of\s+the\s+(story|tale)",
            r"they\s+live\w*\s+(happily|ever\s+after)",
        ],
        "get_scene": lambda text, rng: {
            "bg": {"type": "gradient", "colors": [[180, 160, 130], [130, 110, 90]], "horizon": 0.5,
                   "ground_color": [100, 80, 60]},
            "elements": [
                {"type": "book", "x": 0.5, "y": 0.5, "scale": 3.5,
                 "fill": [150, 110, 70], "open": False, "shadow": True},
                {"type": "circle", "x": 0.5, "y": 0.45, "radius": 8,
                 "fill": [255, 200, 100, 40]},
            ],
            "atmosphere": {"particles": "sparkles", "star_count": 8},
            "mood": rng.choice(["peaceful", "hopeful", "somber"]),
        }
    },
]


def match_creative_scene(text: str, rng=None) -> dict | None:
    """Check if text matches any creative scene pattern.
    Returns the scene dict or None.
    """
    tl = text.lower()
    for scene_def in CREATIVE_SCENES:
        for pattern in scene_def["patterns"]:
            if re.search(pattern, tl):
                if rng is None:
                    import random
                    rng = random.Random(hash(text) & 0xFFFFFFFF)
                return scene_def["get_scene"](text, rng)
    return None


def extract_story_tone(text: str) -> str:
    """Detect if text is poetic/reflective vs factual/narrative."""
    poetic_signals = 0
    poetic_patterns = [
        r"\.{3,}", r"\b(just|simply|yet|still|perhaps|maybe)\b",
        r"\b(imagine|wonder|remember|feel|felt)\b",
        r"\b(heavy|strange|unsettling|ancient|endless)\b",
        r"\b(life|death|time|world|earth|soul|heart|mind)\b",
    ]
    tl = text.lower()
    for p in poetic_patterns:
        if re.search(p, tl):
            poetic_signals += 1
    # Short segments with ellipsis or abstract nouns
    words = tl.split()
    if len(words) <= 15 and poetic_signals >= 2:
        return "poetic"
    if poetic_signals >= 3:
        return "poetic"
    return "factual"
