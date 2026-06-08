"""Visual treatment system — each segment gets ONE dominant visual treatment.

Treatments are mutually exclusive. The engine selects the best treatment based on
text content, then applies it as overrides to the scene description (camera,
particles, mood, palette, effects, layout).
"""

import re

TREATMENTS = {

    "cinematic": {
        "label": "Cinematic",
        "moods": ["dramatic", "epic"],
        "camera_zoom": (1.08, 1.35),       # (start, end) Ken Burns zoom
        "camera_pan": (0.02, 0.06),         # pan drift range
        "vignette": 0.7,                    # heavy dark edges
        "particles": "none",
        "fog": False,
        "palette": "cool",
        "element_count": "many",
        "grain": 0.02,
        "triggers": [
            r"\b(cinematic|epic|battle|charge|march|vast|sweep\w*)\b",
            r"\b(enormous|titanic|colossal|monumental)\b",
            r"\b(army|fleet|legion|hoarde|migration)\b",
        ],
    },

    "atmospheric": {
        "label": "Atmospheric",
        "moods": ["mysterious", "somber"],
        "camera_zoom": (1.0, 1.06),
        "camera_pan": (0.01, 0.03),
        "vignette": 0.3,
        "particles": "mist",
        "fog": True,
        "palette": "neutral",
        "element_count": "moderate",
        "grain": 0.06,
        "triggers": [
            r"\b(mist|fog|gloom|shadow|dark\w*)\b",
            r"\b(mystery|unknown|ancient|old)\b",
            r"\b(quiet|silence|still|hush)\b",
            r"\b(slow\w*|gradual\w*)\b",
        ],
    },

    "dynamic": {
        "label": "Dynamic",
        "moods": ["epic", "dramatic"],
        "camera_zoom": (1.0, 1.45),
        "camera_pan": (0.04, 0.10),
        "vignette": 0.4,
        "particles": "sparkles",
        "fog": False,
        "palette": "warm",
        "element_count": "many",
        "grain": 0.03,
        "triggers": [
            r"\b(sudden\w*|burst|flash|explos\w*)\b",
            r"\b(rapid\w*|fast|quick|rush|surge)\b",
            r"\b(energy|power|force|lightning)\b",
            r"\b(transform\w*|erupt\w*|ignite)\b",
        ],
    },

    "intimate": {
        "label": "Intimate",
        "moods": ["peaceful", "hopeful"],
        "camera_zoom": (1.0, 1.03),
        "camera_pan": (0.0, 0.02),
        "vignette": 0.2,
        "particles": "none",
        "fog": False,
        "palette": "warm",
        "element_count": "single",
        "grain": 0.04,
        "triggers": [
            r"\b(one|single|alone|lone\w*|only)\b",
            r"\b(intimate|close|personal|private)\b",
            r"\b(feel|thought|heart|soul|mind)\b",
            r"\b(individual|unique|special)\b",
        ],
    },

    "epic_scale": {
        "label": "Epic Scale",
        "moods": ["epic", "hopeful"],
        "camera_zoom": (1.0, 1.25),
        "camera_pan": (0.03, 0.08),
        "vignette": 0.5,
        "particles": "stars",
        "fog": False,
        "palette": "cool",
        "element_count": "moderate",
        "grain": 0.02,
        "triggers": [
            r"\b(planet|world|earth|universe|cosmos)\b",
            r"\b(galaxy|star|nebula|space|sky)\b",
            r"\b(ocean|horizon|mountain|continent)\b",
            r"\b(ages|eons|forever|eternal)\b",
        ],
    },

    "moody": {
        "label": "Moody",
        "moods": ["somber", "mysterious"],
        "camera_zoom": (1.0, 1.12),
        "camera_pan": (0.01, 0.04),
        "vignette": 0.6,
        "particles": "ash",
        "fog": True,
        "palette": "dark",
        "element_count": "few",
        "grain": 0.08,
        "triggers": [
            r"\b(dark|night|shadow|gloom|despair)\b",
            r"\b(sad|solemn|mourn|grief|loss)\b",
            r"\b(rain|storm|thunder|lightning|ash)\b",
            r"\b(extinct|vanish\w*|disappear\w*|died)\b",
        ],
    },

    "dreamy": {
        "label": "Dreamy",
        "moods": ["hopeful", "peaceful"],
        "camera_zoom": (1.0, 1.04),
        "camera_pan": (0.0, 0.02),
        "vignette": 0.15,
        "particles": "sparkles",
        "fog": False,
        "palette": "pastel",
        "element_count": "few",
        "grain": 0.05,
        "triggers": [
            r"\b(dream|imagine|wonder|magic\w*)\b",
            r"\b(gentle|soft|peaceful|serene|calm)\b",
            r"\b(beautiful|lovely|hope|wish)\b",
            r"\b(float\w*|drift\w*|fade\w*)\b",
        ],
    },

    "documentary": {
        "label": "Documentary",
        "moods": ["peaceful", "hopeful"],
        "camera_zoom": (1.0, 1.0),           # static
        "camera_pan": (0.0, 0.0),
        "vignette": 0.0,
        "particles": "none",
        "fog": False,
        "palette": "neutral",
        "element_count": "moderate",
        "grain": 0.01,
        "triggers": [
            r"\b(fact|history|document|record|account)\b",
            r"\b(research|study|observe\w*)\b",
            r"\b(discover\w*|find|found|unearth)\b",
            r"\b(evidence|proof|exhibit)\b",
        ],
    },

    "minimal": {
        "label": "Minimal",
        "moods": ["peaceful", "hopeful"],
        "camera_zoom": (1.0, 1.02),
        "camera_pan": (0.0, 0.01),
        "vignette": 0.1,
        "particles": "none",
        "fog": False,
        "palette": "neutral",
        "element_count": "single",
        "grain": 0.03,
        "triggers": [
            r"\b(simple|just|only|merely|bare)\b",
            r"\b(empty|void|space|blank|nothing)\b",
            r"\b(still|quiet|calm|peace)\b",
            r"^.{0,60}$",                    # very short text
        ],
    },

    "dramatic_reveal": {
        "label": "Dramatic Reveal",
        "moods": ["dramatic", "mysterious"],
        "camera_zoom": (1.15, 1.0),          # zoom out (reverse Ken Burns)
        "camera_pan": (0.05, 0.12),
        "vignette": 0.6,
        "particles": "sunbeams",
        "fog": False,
        "palette": "cool",
        "element_count": "single",
        "grain": 0.04,
        "triggers": [
            r"\b(reveal|unveil|emerge|appear)\b",
            r"\b(sudden\w*|finally|at\s+last|then)\b",
            r"\b(reveal|uncover|expose|show)\b",
            r"\b(turn\w*\s+the\s+page|chapter\s+ends?|new\s+chapter)\b",
        ],
    },
}


def select_treatment(segment_text: str, story_mood: str = "", rng=None) -> dict:
    """Select a visual treatment for a segment.
    
    Returns a TREATMENTS entry dict with all parameters.
    Falls back to 'atmospheric' for poetic text, 'documentary' for factual,
    or a mood-matched default.
    """
    tl = segment_text.lower()
    scores = {}

    for name, tx in TREATMENTS.items():
        score = 0
        for pat in tx.get("triggers", []):
            matches = re.findall(pat, tl)
            score += len(matches)
        scores[name] = score

    # Find best treatment by score
    best = max(scores, key=lambda k: scores[k])

    # Tiebreaker: if no triggers matched, use mood or random
    if scores[best] == 0:
        if rng is None:
            import random
            rng = random.Random(hash(segment_text) & 0xFFFFFFFF)

        # Map story moods to default treatments
        mood_map = {
            "dramatic": "cinematic",
            "somber": "moody",
            "mysterious": "atmospheric",
            "hopeful": "dreamy",
            "epic": "epic_scale",
            "peaceful": "minimal",
            "informational": "documentary",
        }
        best = mood_map.get(story_mood, "atmospheric")
        # Still use RNG to add variety
        if rng.random() < 0.3:
            candidates = [k for k in TREATMENTS if k != best]
            best = rng.choice(candidates)

    return TREATMENTS[best]


def apply_treatment(scene: dict, treatment: dict, rng) -> dict:
    """Apply a visual treatment as overrides on the scene description.
    
    Modifies: camera zoom/pan, particles, mood, fog, vignette, etc.
    The element list is kept but the treatment can add/remove atmosphere.
    """
    scene = dict(scene)  # shallow copy

    # ── Mood override ──
    scene["mood"] = rng.choice(treatment["moods"])

    # ── Atmosphere ──
    atmos = dict(scene.get("atmosphere", {}))
    particles = treatment.get("particles", "none")
    if particles and particles != "none":
        atmos["particles"] = particles
        if particles in ("stars", "sparkles"):
            atmos["star_count"] = rng.randint(15, 40)
    else:
        atmos["particles"] = "none"
    fog = treatment.get("fog", False)
    if fog:
        atmos["fog"] = True
    scene["atmosphere"] = atmos

    # ── Camera / Ken Burns ──
    zoom_start, zoom_end = treatment["camera_zoom"]
    pan = (
        round(rng.uniform(*treatment["camera_pan"]), 3),
        round(rng.uniform(*treatment["camera_pan"]), 3),
    )
    scene["_camera"] = {
        "zoom_start": zoom_start,
        "zoom_end": zoom_end,
        "pan_x": pan[0] * rng.choice([-1, 1]),
        "pan_y": pan[1] * rng.choice([-1, 1]),
    }

    # ── Vignette ──
    scene.setdefault("style", {})["vignette"] = treatment.get("vignette", 0.3)
    scene["style"]["grain"] = treatment.get("grain", 0.04)

    # ── Element count filter ──
    count_mode = treatment.get("element_count", "moderate")
    elements = scene.get("elements", [])
    if count_mode == "single" and len(elements) > 1:
        # Keep only the most relevant element (largest or first non-circle)
        non_circle = [e for e in elements if e.get("type") != "circle"]
        if non_circle:
            best_elem = max(non_circle, key=lambda e: e.get("scale", 1))
            elements = [best_elem]
        else:
            elements = [elements[0]]
    elif count_mode == "few" and len(elements) > 3:
        rng.shuffle(elements)
        elements = elements[:3]
    elif count_mode == "many":
        pass  # keep all
    scene["elements"] = elements

    # ── Palette / color bias ──
    palette = treatment.get("palette", "neutral")
    if palette == "warm":
        scene["_palette_bias"] = (1.1, 0.95, 0.85)  # boost R, reduce B
    elif palette == "cool":
        scene["_palette_bias"] = (0.85, 0.95, 1.1)
    elif palette == "dark":
        scene["_palette_bias"] = (0.7, 0.7, 0.8)
    elif palette == "pastel":
        scene["_palette_bias"] = (1.15, 1.1, 1.2)
    else:
        scene["_palette_bias"] = (1.0, 1.0, 1.0)

    return scene
