"""Dynamic Scene Composer — builds scenes algorithmically from ANY text.

Unlike the knowledge base (which returns pre-written scenes), this module
composes scenes on-the-fly by mapping extracted concepts to drawable
elements and auto-computing their layout. Handles novel topics that
no template covers.

Pipeline:
  text → concept_extractor → element selection → layout → final scene
"""

from src.concept_extractor import extract_concepts, detect_bg_type, detect_mood, infer_scene_type


# ── Concept-to-element mapping ─────────────────────────────────
# Maps concept names to element descriptions with visual parameters

ELEMENT_DEFS = {
    # Space
    "star":       {"type": "star", "radius": 2, "fill": [255, 255, 200]},
    "sun":        {"type": "sun", "radius": 22, "fill": [255, 230, 80]},
    "moon":       {"type": "moon", "radius": 14, "fill": [250, 245, 230]},
    "planet":     {"type": "planet", "scale": 2.5, "fill": [80, 140, 200]},
    "astronaut":  {"type": "astronaut", "scale": 3.5, "fill": [220, 220, 240]},
    "spaceship":  {"type": "spaceship", "scale": 3.0, "fill": [180, 190, 210]},
    "blackhole":  {"type": "blackhole", "scale": 2.5, "fill": [0, 0, 0]},
    "galaxy":     {"type": "galaxy", "scale": 2.5, "fill": [60, 20, 80]},
    "asteroid":   {"type": "asteroid", "scale": 3.0, "fill": [120, 110, 100]},

    # Nature
    "tree":       {"type": "tree", "scale": 3.5, "tree_style": "round", "fill": [45, 115, 45]},
    "mountain":   {"type": "mountain", "width": 0.4, "height": 0.3, "fill": [100, 130, 160]},
    "water":      {"type": "water", "width": 0.8, "height": 0.06, "fill": [60, 130, 200]},
    "ocean":      {"type": "wave", "scale": 3.0, "fill": [40, 100, 180]},
    "glacier":    {"type": "glacier", "scale": 2.5, "fill": [200, 220, 240]},
    "snow":       {"type": "snow", "scale": 3.0, "fill": [230, 240, 250]},
    "path":       {"type": "path", "scale": 3.0, "fill": [160, 140, 110]},

    # Weather
    "cloud":      {"type": "cloud", "scale": 3.0, "fill": [200, 210, 225]},
    "rain":       {"type": "rain", "scale": 3.0, "fill": [180, 200, 230]},
    "storm":      {"type": "storm", "scale": 2.5, "fill": [60, 60, 80]},
    "lightning":  {"type": "lightning", "scale": 2.5, "fill": [255, 230, 50]},
    "rainbow":    {"type": "rainbow", "scale": 3.0},
    "fog":        {"type": "fog", "scale": 3.0, "fill": [200, 210, 220]},
    "desert":     {"type": "desert", "scale": 2.0, "fill": [220, 190, 120]},

    # Animals
    "bird":       {"type": "bird", "scale": 1.5, "fill": [80, 60, 50]},
    "fish":       {"type": "fish", "scale": 2.0, "fill": [200, 150, 80]},
    "whale":      {"type": "whale", "scale": 3.0, "fill": [60, 70, 100]},
    "dolphin":    {"type": "fish", "scale": 2.5, "fill": [80, 130, 180]},
    "shark":      {"type": "shark", "scale": 2.5, "fill": [100, 110, 120]},
    "dinosaur":   {"type": "dinosaur", "scale": 2.5, "fill": [80, 110, 70]},
    "crocodile":  {"type": "crocodile", "scale": 2.5, "fill": [60, 100, 60]},
    "butterfly":  {"type": "bird", "scale": 1.25, "fill": [230, 150, 80]},
    "snake":      {"type": "snake", "scale": 2.0, "fill": [80, 130, 60]},
    "dog":        {"type": "dog", "scale": 2.5, "fill": [140, 100, 70]},
    "cat":        {"type": "cat", "scale": 2.0, "fill": [180, 140, 100]},
    "horse":      {"type": "horse", "scale": 3.0, "fill": [120, 90, 60]},
    "elephant":   {"type": "elephant", "scale": 3.5, "fill": [130, 130, 120]},
    "bear":       {"type": "bear", "scale": 2.5, "fill": [100, 70, 50]},
    "deer":       {"type": "deer", "scale": 2.5, "fill": [160, 130, 80]},
    "wolf":       {"type": "dog", "scale": 2.5, "fill": [110, 110, 110]},
    "fox":        {"type": "dog", "scale": 2.0, "fill": [200, 120, 60]},
    "rabbit":     {"type": "rabbit", "scale": 1.75, "fill": [200, 180, 160]},
    "frog":       {"type": "frog", "scale": 1.5, "fill": [80, 160, 60]},
    "turtle":     {"type": "turtle", "scale": 1.5, "fill": [80, 140, 80]},
    "monkey":     {"type": "monkey", "scale": 2.5, "fill": [140, 110, 80]},
    "squirrel":   {"type": "squirrel", "scale": 1.5, "fill": [160, 120, 80]},
    "lizard":     {"type": "lizard", "scale": 2.0, "fill": [100, 160, 80]},
    "goat":       {"type": "goat", "scale": 2.5, "fill": [200, 170, 140]},
    "sheep":      {"type": "sheep", "scale": 2.5, "fill": [240, 235, 230]},
    "pig":        {"type": "pig", "scale": 2.0, "fill": [240, 200, 180]},
    "cow":        {"type": "cow", "scale": 2.5, "fill": [240, 230, 220]},
    "rat":        {"type": "rat", "scale": 1.25, "fill": [160, 140, 130]},
    "beaver":     {"type": "beaver", "scale": 2.0, "fill": [140, 110, 80]},
    "otter":      {"type": "otter", "scale": 2.0, "fill": [140, 110, 100]},
    "hedgehog":   {"type": "hedgehog", "scale": 1.5, "fill": [150, 120, 90]},
    "bat":        {"type": "bat", "scale": 2.0, "fill": [60, 50, 45]},
    "kangaroo":   {"type": "kangaroo", "scale": 2.5, "fill": [180, 140, 100]},
    "sloth":      {"type": "sloth", "scale": 2.0, "fill": [140, 120, 100]},
    "raccoon":    {"type": "raccoon", "scale": 1.75, "fill": [150, 140, 130]},
    "skunk":      {"type": "skunk", "scale": 1.75, "fill": [40, 35, 30]},
    "camel":      {"type": "camel", "scale": 2.5, "fill": [190, 160, 120]},
    "rhino":      {"type": "rhino", "scale": 2.5, "fill": [130, 120, 110]},
    "hippo":      {"type": "hippo", "scale": 3.0, "fill": [150, 130, 140]},
    "giraffe":    {"type": "giraffe", "scale": 3.0, "fill": [220, 180, 100]},
    "dragon":     {"type": "dragon", "scale": 3.0, "fill": [60, 120, 60]},
    "mouse":      {"type": "rat", "scale": 1.0, "fill": [170, 150, 140]},
    "lion":       {"type": "cat", "scale": 2.5, "fill": [200, 160, 100]},
    "tiger":      {"type": "cat", "scale": 2.5, "fill": [220, 160, 80]},
    "zebra":      {"type": "horse", "scale": 2.5, "fill": [210, 210, 210]},
    "unicorn":    {"type": "horse", "scale": 2.5, "fill": [230, 230, 240]},
    "panda":      {"type": "bear", "scale": 2.5, "fill": [220, 220, 220]},
    "moose":      {"type": "deer", "scale": 3.0, "fill": [160, 130, 90]},
    "bison":      {"type": "cow", "scale": 3.0, "fill": [140, 120, 100]},

    # Human
    "human":      {"type": "human", "scale": 3.5, "fill": [180, 150, 130]},
    "eye":        {"type": "eye", "scale": 4.0, "fill": [255, 200, 50]},
    "hand":       {"type": "hand", "scale": 3.0, "fill": [200, 170, 140]},
    "heart":      {"type": "heart", "scale": 4.0, "fill": [220, 50, 50]},
    "brain":      {"type": "brain", "scale": 3.0, "fill": [200, 180, 200]},

    # Tech
    "computer":   {"type": "computer", "scale": 2.5, "fill": [30, 45, 80]},
    "network":    {"type": "network", "scale": 3.0, "fill": [60, 200, 120]},
    "robot":      {"type": "human", "scale": 3.0, "fill": [160, 165, 175]},
    "ai":         {"type": "ai", "scale": 3.0, "fill": [100, 200, 255]},
    "circuit":    {"type": "circuit", "scale": 2.5, "fill": [80, 220, 140]},
    "data":       {"type": "data", "scale": 3.0, "fill": [20, 25, 40]},

    # Science
    "dna":        {"type": "dna", "width": 80, "height": 120, "fill": [60, 140, 220]},
    "atom":       {"type": "atom", "radius": 30, "fill": [60, 140, 220]},
    "plant":      {"type": "plant", "scale": 2.5, "fill": [60, 140, 60]},
    "flower":     {"type": "flower", "scale": 2.5, "fill": [230, 80, 130]},
    "grass":      {"type": "grass", "scale": 3.0, "fill": [50, 130, 50]},
    "microscope": {"type": "microscope", "scale": 2.5, "fill": [180, 200, 230]},
    "telescope":  {"type": "telescope", "scale": 3.0, "fill": [120, 100, 80]},
    "experiment": {"type": "experiment", "scale": 3.0, "fill": [100, 200, 150]},
    "alien":      {"type": "alien", "scale": 3.0, "fill": [80, 200, 120]},
    "artifact":   {"type": "artifact", "scale": 3.0, "fill": [100, 255, 200]},

    # History
    "building":   {"type": "building", "scale": 2.5, "fill": [180, 160, 130]},
    "factory":    {"type": "factory", "scale": 2.5, "fill": [130, 110, 90], "window_color": [200, 180, 100]},
    "mill":       {"type": "factory", "scale": 2.5, "fill": [120, 100, 80], "window_color": [200, 180, 100]},
    "warehouse":  {"type": "factory", "scale": 2.5, "fill": [110, 95, 80], "window_color": [180, 160, 90]},
    "shop":       {"type": "shop", "scale": 2.5, "fill": [180, 150, 120], "window_color": [255, 240, 200]},
    "store":      {"type": "shop", "scale": 2.5, "fill": [170, 145, 115], "window_color": [255, 240, 200]},
    "cafe":       {"type": "shop", "scale": 2.5, "fill": [190, 160, 130], "window_color": [255, 240, 200]},
    "flag":       {"type": "flag", "scale": 2.0, "fill": [200, 50, 50]},
    "cannon":     {"type": "cannon", "scale": 2.5, "fill": [60, 60, 60]},
    "wall":       {"type": "wall", "scale": 2.0, "fill": [140, 120, 100]},
    "tower":      {"type": "tower", "scale": 2.0, "fill": [130, 110, 90]},
    "fortress":   {"type": "fortress", "scale": 2.0, "fill": [120, 100, 80]},
    "tent":       {"type": "tent", "scale": 2.5, "fill": [160, 140, 100]},
    "chain":      {"type": "chain", "scale": 2.0, "fill": [100, 90, 80]},
    "soldier":    {"type": "soldier", "scale": 3.0, "fill": [140, 60, 60]},
    "crown":      {"type": "crown", "scale": 2.5, "fill": [230, 200, 50]},
    "book":       {"type": "book", "scale": 3.5, "fill": [180, 120, 80]},
    "coin":       {"type": "coin", "scale": 2.5, "fill": [230, 200, 80]},
    "map":        {"type": "map", "scale": 3.0, "fill": [180, 170, 140]},
    "world_map":  {"type": "world_map", "scale": 3.0, "fill": [200, 180, 150]},
    "india_map":  {"type": "india_map", "scale": 3.0, "fill": [140, 180, 100]},
    "globe":      {"type": "globe", "scale": 2.5, "fill": [80, 130, 180]},
    "ship":       {"type": "ship", "scale": 2.0, "fill": [100, 80, 60]},
    "canoe":      {"type": "canoe", "scale": 2.5, "fill": [80, 55, 35]},
    "kayak":      {"type": "kayak", "scale": 2.5, "fill": [60, 80, 120]},
    "raft":       {"type": "raft", "scale": 2.5, "fill": [100, 80, 50]},
    "pirate_ship":{"type": "pirate_ship", "scale": 2.0, "fill": [60, 40, 30]},
    "galleon":    {"type": "galleon", "scale": 2.0, "fill": [70, 50, 35]},
    "train":      {"type": "train", "scale": 2.5, "fill": [80, 40, 40]},
    "car":        {"type": "car", "width": 0.15, "height": 0.06, "fill": [150, 80, 80]},
    "bike":       {"type": "bike", "scale": 3.0, "fill": [60, 60, 70]},
    "drive":      {"type": "none"},

    # Abstract
    "clock":      {"type": "clock", "scale": 4.0, "fill": [200, 200, 220]},
    "lightbulb":  {"type": "lightbulb", "scale": 3.5, "fill": [255, 240, 150]},
    "candle":     {"type": "candle", "scale": 3.0, "fill": [255, 220, 180]},
    "fire":       {"type": "fire", "scale": 3.0, "fill": [255, 100, 20]},
    "key":        {"type": "key", "scale": 2.5, "fill": [200, 180, 80]},
    "question":   {"type": "question_mark", "scale": 3.5, "fill": [200, 200, 200]},
    "target":     {"type": "target", "radius": 30, "fill": [200, 80, 80]},
    "infinity":   {"type": "infinity", "scale": 3.5, "fill": [100, 200, 200]},
    "puzzle":     {"type": "puzzle", "scale": 3.0, "fill": [200, 150, 80]},
    "scales":     {"type": "scales", "scale": 3.0, "fill": [180, 160, 120]},
    "gear":       {"type": "gear", "scale": 3.5, "fill": [180, 180, 200]},
    "hourglass":  {"type": "hourglass", "scale": 3.0, "fill": [180, 180, 200]},

    # Household items
    "chair":      {"type": "chair", "scale": 3.5, "fill": [120, 90, 60]},
    "table":      {"type": "table", "scale": 3.5, "fill": [140, 100, 60]},
    "sofa":       {"type": "sofa", "scale": 3.5, "fill": [160, 80, 80]},
    "bed":        {"type": "bed", "scale": 3.5, "fill": [180, 160, 140]},
    "cupboard":   {"type": "cupboard", "scale": 3.5, "fill": [160, 130, 100]},
    "fridge":     {"type": "fridge", "scale": 3.5, "fill": [240, 240, 245]},
    "oven":       {"type": "oven", "scale": 3.5, "fill": [220, 220, 225]},
    "sink":       {"type": "sink", "scale": 3.5, "fill": [220, 230, 240]},
    "toilet":     {"type": "toilet", "scale": 3.5, "fill": [240, 240, 245]},
    "bathtub":    {"type": "bathtub", "scale": 3.5, "fill": [230, 235, 240]},
    "mirror":     {"type": "mirror", "scale": 3.5, "fill": [200, 210, 225]},
    "curtain":    {"type": "curtain", "scale": 3.5, "fill": [180, 140, 160]},
    "pillow":     {"type": "pillow", "scale": 3.5, "fill": [255, 250, 240]},
    "door":       {"type": "door", "scale": 3.5, "fill": [160, 130, 100]},
    "window":     {"type": "window", "scale": 3.5, "fill": [200, 220, 240]},

    # Pose concepts (modifiers, not drawn)
    "sitting":    {"type": "none"},
    "lying":      {"type": "none"},
    "kneeling":   {"type": "none"},
    "jogging":    {"type": "none"},
    "running":    {"type": "none"},
}


# ── Scene background configs ──────────────────────────────────

BG_CONFIGS = {
    "space": {"type": "gradient", "colors": [[2, 2, 18], [10, 5, 30]], "horizon": 0.0},
    "ocean": {"type": "ocean", "sky_color": [160, 190, 220], "horizon_color": [100, 150, 200],
              "horizon": 0.4, "water_color": [20, 60, 130]},
    "forest": {"type": "forest", "colors": [[90, 150, 90], [60, 120, 60]], "horizon": 0.55, "ground_color": [40, 90, 35]},
    "mountain": {"type": "gradient", "colors": [[160, 190, 220], [120, 150, 190]], "horizon": 0.5, "ground_color": [80, 120, 80]},
    "desert": {"type": "desert", "colors": [[225, 195, 140], [195, 165, 115]], "horizon": 0.5, "ground_color": [185, 155, 100]},
    "city": {"type": "gradient", "colors": [[60, 70, 100], [30, 40, 70]], "horizon": 0.5, "ground_color": [25, 30, 50]},
    "industrial": {"type": "gradient", "colors": [[10, 15, 30], [22, 26, 50]], "horizon": 0.5, "ground_color": [15, 20, 40]},
    "indoor": {"type": "indoor", "colors": [[235, 230, 220], [220, 215, 205]], "horizon": 0.6, "ground_color": [200, 195, 185]},
    "weather": {"type": "gradient", "colors": [[60, 60, 80], [40, 40, 60]], "horizon": 0.5, "ground_color": [30, 30, 45]},
    "gradient": {"type": "gradient", "colors": [[200, 210, 230], [140, 160, 200]], "horizon": 0.6, "ground_color": [60, 90, 50]},
}

ATMOSPHERE_CONFIGS = {
    "space": {"particles": "stars", "star_count": 40, "fog": False},
    "ocean": {"particles": "none", "fog": False},
    "forest": {"particles": "mist", "fog": True},
    "mountain": {"particles": "none", "fog": False},
    "desert": {"particles": "none", "fog": False},
    "city": {"particles": "none", "fog": False},
    "industrial": {"particles": "none", "fog": False},
    "indoor": {"particles": "none", "fog": False},
    "weather": {"particles": "none", "fog": True},
    "gradient": {"particles": "none", "fog": False},
}


# ── Creative layout engine ────────────────────────────────────
# Uses seeded randomness for variety: different text → different layout

import math, random

def _scene_rng(text: str, scene_type: str = "") -> random.Random:
    """Deterministic RNG seeded from text content for reproducible creativity."""
    seed_str = text + scene_type
    seed_val = abs(hash(seed_str)) % (2**31)
    return random.Random(seed_val)


def _apply_palette_shift(element: dict, rng: random.Random):
    """Shift element fill color by a random hue rotation for palette variety."""
    fill = element.get("fill")
    if not fill or not isinstance(fill, (list, tuple)) or len(fill) < 3:
        return
    # Subtle shift: ±30 per channel
    shift = lambda c: max(0, min(255, c + rng.randint(-30, 30)))
    shifted = [shift(fill[0]), shift(fill[1]), shift(fill[2])]
    if len(fill) > 3:
        shifted.append(fill[3])
    element["fill"] = shifted


def compute_positions(concepts: dict, scene_type: str) -> list:
    """Place elements with creative variety using seeded randomness.
    
    Features:
    - Multiple layout patterns (3-col grid, diagonal, radial, clustered)
    - Position jitter to avoid grid-like appearance
    - Scale randomization
    - Palette shifting per element
    - Element subset selection (not all concepts become elements)
    """
    rng = _scene_rng(str(concepts), scene_type)
    elements = []
    sorted_concepts = sorted(concepts.items(), key=lambda x: -x[1])
    visual_concepts = [c for c, _ in sorted_concepts if c in ELEMENT_DEFS]

    if not visual_concepts:
        return elements

    # Randomly select a subset (80-100%) of concepts to include
    keep_ratio = rng.uniform(0.7, 1.0)
    n_keep = max(1, int(len(visual_concepts) * keep_ratio))
    if n_keep < len(visual_concepts):
        # Keep top concept always, randomly drop from rest
        keep = [visual_concepts[0]]
        rest = visual_concepts[1:]
        rng.shuffle(rest)
        keep.extend(rest[:n_keep - 1])
        visual_concepts = keep

    # Choose layout pattern
    layout = rng.choice(["grid", "diagonal", "clustered", "radial", "asymmetric"])
    primary_x, primary_y = 0.5, 0.4
    col_positions = [0.2, 0.5, 0.8]
    col_idx = 0

    # Define which concepts are sky vs mid vs foreground
    sky_set = {"star", "cloud", "bird", "sun", "moon", "galaxy", "rainbow"}
    mid_set = {"mountain", "glacier", "planet", "dinosaur", "astronaut"}
    center_set = {"dna", "atom", "heart", "brain", "clock", "gear", "book",
                  "lightbulb", "target", "infinity", "puzzle"}
    # Everything else is foreground

    for i, concept in enumerate(visual_concepts):
        base = ELEMENT_DEFS.get(concept,
            {"type": "circle", "radius": 10, "fill": [150, 150, 150]})
        element = base.copy()

        # Determine natural layer
        is_sky = concept in sky_set
        is_mid = concept in mid_set
        is_center = concept in center_set

        # ── Layout-specific position calculation ──
        if layout == "grid":
            # Standard 3-column but with jitter
            if is_sky:
                x = col_positions[col_idx % 3] + rng.uniform(-0.04, 0.04)
                y = 0.12 + (i * 0.08) + rng.uniform(-0.02, 0.02)
            elif is_mid:
                x = col_positions[col_idx % 3] + rng.uniform(-0.03, 0.03)
                y = 0.45 + (i * 0.03) + rng.uniform(-0.02, 0.02)
            elif is_center:
                x = primary_x + (i - 1) * 0.15 + rng.uniform(-0.03, 0.03)
                y = primary_y + (i * 0.05) + rng.uniform(-0.02, 0.02)
            else:
                x = col_positions[col_idx % 3] + rng.uniform(-0.04, 0.04)
                y = 0.65 + (i * 0.04) + rng.uniform(-0.03, 0.03)

        elif layout == "diagonal":
            # Elements cascade diagonally top-left to bottom-right
            t = i / max(1, len(visual_concepts))
            if is_sky:
                x = 0.1 + t * 0.7 + rng.uniform(-0.03, 0.03)
                y = 0.08 + t * 0.15 + rng.uniform(-0.02, 0.02)
            elif is_mid:
                x = 0.15 + t * 0.6 + rng.uniform(-0.03, 0.03)
                y = 0.3 + t * 0.2 + rng.uniform(-0.02, 0.02)
            elif is_center:
                x = 0.5 + rng.uniform(-0.05, 0.05)
                y = 0.4 + rng.uniform(-0.03, 0.03)
            else:
                x = 0.2 + t * 0.6 + rng.uniform(-0.03, 0.03)
                y = 0.55 + t * 0.25 + rng.uniform(-0.02, 0.02)

        elif layout == "clustered":
            # Elements grouped near center with spread
            if is_sky:
                x = 0.5 + rng.uniform(-0.2, 0.2)
                y = 0.1 + rng.uniform(0, 0.1)
            elif is_mid:
                x = 0.5 + rng.uniform(-0.15, 0.15)
                y = 0.4 + rng.uniform(-0.05, 0.05)
            elif is_center:
                x = 0.5 + rng.uniform(-0.08, 0.08)
                y = 0.4 + rng.uniform(-0.04, 0.04)
            else:
                x = 0.5 + rng.uniform(-0.2, 0.2)
                y = 0.65 + rng.uniform(-0.08, 0.08)

        elif layout == "radial":
            # Elements spread outward from center
            angle = (i / max(1, len(visual_concepts))) * 2 * math.pi + rng.uniform(-0.3, 0.3)
            if is_sky:
                dist = 0.3 + rng.uniform(0, 0.05)
            elif is_mid:
                dist = 0.2 + rng.uniform(0, 0.05)
            elif is_center:
                dist = rng.uniform(0, 0.08)
            else:
                dist = 0.25 + rng.uniform(0, 0.08)
            x = 0.5 + math.cos(angle) * dist
            y = 0.45 + math.sin(angle) * dist * 0.7

        elif layout == "asymmetric":
            # Rule-of-thirds inspired asymmetric placement
            thirds_x = [0.2, 0.7, 0.3, 0.8, 0.15, 0.75]
            thirds_y = [0.55, 0.6, 0.7, 0.5, 0.65, 0.75]
            sky_thirds_x = [0.2, 0.6, 0.3, 0.8]
            sky_thirds_y = [0.1, 0.08, 0.18, 0.12]
            if is_sky:
                idx = i % len(sky_thirds_x)
                x = sky_thirds_x[idx] + rng.uniform(-0.03, 0.03)
                y = sky_thirds_y[idx] + rng.uniform(-0.02, 0.02)
            elif is_mid:
                x = 0.5 + rng.uniform(-0.1, 0.1)
                y = 0.45 + rng.uniform(-0.03, 0.03)
            elif is_center:
                x = 0.5 + rng.uniform(-0.05, 0.05)
                y = 0.4 + rng.uniform(-0.03, 0.03)
            else:
                idx = i % len(thirds_x)
                x = thirds_x[idx] + rng.uniform(-0.03, 0.03)
                y = thirds_y[idx] + rng.uniform(-0.03, 0.03)

        # Clamp positions
        x = max(0.05, min(0.95, x))
        y = max(0.05, min(0.88, y))

        element["x"] = round(x, 3)
        element["y"] = round(y, 3)

        # Scale randomization
        base_scale = element.get("scale", 1.0)
        scale_jitter = rng.uniform(0.75, 1.3)
        element["scale"] = round(base_scale * scale_jitter, 2)

        # Palette shift
        _apply_palette_shift(element, rng)

        elements.append(element)
        col_idx += 1

    # Add text label (always at top center)
    if visual_concepts:
        label_text = " ".join(c.upper() for c in visual_concepts[:3])
        elements.append({
            "type": "text", "x": 0.5, "y": 0.08,
            "text": label_text,
            "font_size": 22, "fill": [200, 200, 220]
        })

    # Fill thin scenes with context-appropriate decorative elements
    if len(elements) < 4:
        fillers = _get_filler_elements(visual_concepts[:1] if visual_concepts else None, rng)
        elements.extend(fillers)

    return elements


def _get_filler_elements(primary_concepts: list | None, rng=None) -> list:
    """Generate decorative filler elements."""
    if rng is None:
        rng = random.Random()
    fillers = []
    theme = "general"
    if primary_concepts:
        p = primary_concepts[0]
        if p in ("ocean", "whale", "fish", "shark", "dolphin", "water"):
            theme = "ocean"
        elif p in ("space", "star", "planet", "moon", "sun", "galaxy"):
            theme = "space"
        elif p in ("forest", "tree", "mountain", "flower", "grass"):
            theme = "nature"
        elif p in ("building", "city", "castle", "house"):
            theme = "city"

    if theme == "ocean":
        for i in range(3):
            fillers.append({
                "type": "wave",
                "x": round(rng.uniform(0.1, 0.85), 3),
                "y": round(rng.uniform(0.7, 0.82), 3),
                "scale": round(rng.uniform(1.5, 2.5), 1),
                "fill": [60, 120 + rng.randint(-20, 20), 190]
            })
    elif theme == "space":
        for i in range(rng.randint(3, 6)):
            fillers.append({
                "type": "star",
                "x": round(rng.uniform(0.05, 0.95), 3),
                "y": round(rng.uniform(0.05, 0.3), 3),
                "radius": round(rng.uniform(1, 3), 1),
                "fill": [255, 255, rng.randint(180, 230)]
            })
    elif theme == "nature":
        for i in range(rng.randint(2, 4)):
            fillers.append({
                "type": "flower",
                "x": round(rng.uniform(0.1, 0.9), 3),
                "y": round(rng.uniform(0.65, 0.8), 3),
                "scale": round(rng.uniform(1.5, 2.5), 1),
                "fill": [rng.randint(180, 255), rng.randint(60, 200), rng.randint(60, 200)]
            })
    elif theme == "city":
        for i in range(rng.randint(2, 4)):
            fillers.append({
                "type": "building",
                "x": round(rng.uniform(0.1, 0.85), 3),
                "y": round(rng.uniform(0.55, 0.7), 3),
                "scale": round(rng.uniform(1.2, 2.2), 1),
                "fill": [rng.randint(120, 180), rng.randint(110, 160), rng.randint(100, 140)]
            })
    else:
        # General decorative: floating ambient shapes
        for i in range(rng.randint(2, 4)):
            fillers.append({
                "type": "circle",
                "x": round(rng.uniform(0.1, 0.9), 3),
                "y": round(rng.uniform(0.15, 0.5), 3),
                "radius": round(rng.uniform(3, 8), 1),
                "fill": [rng.randint(130, 200), rng.randint(150, 210), rng.randint(190, 240), 60]
            })

    return fillers


# ── Memory / Learning ──────────────────────────────────────────
# Simple file-based cache: saves query→scene pairs so the engine
# "remembers" what it generated for similar texts.

import json
import os
import hashlib

LEARNING_FILE = os.path.join(os.path.dirname(__file__), "..", "memory.json")


def _text_hash(text: str) -> str:
    return hashlib.md5(text.lower().encode()).hexdigest()


def _load_memory() -> dict:
    if os.path.exists(LEARNING_FILE):
        try:
            with open(LEARNING_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def _save_memory(memory: dict):
    try:
        with open(LEARNING_FILE, "w") as f:
            json.dump(memory, f, indent=2)
    except IOError:
        pass  # Silently fail if can't write


def remember(text: str, scene: dict):
    """Save a generated scene to memory."""
    memory = _load_memory()
    h = _text_hash(text)
    # Store scene type, element types, mood for recall
    memory[h] = {
        "text": text[:100],
        "scene_type": scene.get("scene_type", "story"),
        "elements": [e.get("type") for e in scene.get("elements", [])],
        "bg_type": scene.get("bg", {}).get("type", "gradient"),
        "mood": scene.get("mood", "peaceful"),
        "hits": memory.get(h, {}).get("hits", 0) + 1
    }
    _save_memory(memory)


def recall(text: str) -> dict | None:
    """Check if a similar query was answered before."""
    memory = _load_memory()
    h = _text_hash(text)
    if h in memory:
        entry = memory[h]
        # Increment hit count
        entry["hits"] = entry.get("hits", 0) + 1
        memory[h] = entry
        _save_memory(memory)
        return entry
    return None


# ── Dynamic composition ───────────────────────────────────────

def compose_dynamic_scene(text: str) -> dict | None:
    """Compose a scene from scratch for ANY narration text.
    
    Now with creative variety:
    - Multiple layout patterns (grid, diagonal, radial, clustered, asymmetric)
    - Position jitter + scale randomization
    - Palette shifting per element
    - Subset concept selection (not all concepts become elements)
    - Ambient decorative particles
    - HSL hue rotation for overall color mood
    """
    # Check memory first
    remembered = recall(text)
    if remembered:
        elements = remembered.get("elements", [])
        if elements and all(isinstance(e, dict) for e in elements):
            return remembered

    rng = _scene_rng(text)

    # Extract concepts
    concepts = extract_concepts(text)

    # If no concepts found, build a minimal scene from mood + bg type
    if not concepts:
        bg_type = detect_bg_type({"lightbulb": 1})
        mood = detect_mood(text)
        scene = {
            "bg": BG_CONFIGS.get(bg_type, BG_CONFIGS["gradient"]).copy(),
            "elements": [
                {"type": "text", "x": 0.5, "y": 0.08,
                 "text": text[:40].upper(), "font_size": 24, "fill": [80, 80, 100]},
                {"type": "circle", "x": 0.5, "y": 0.4, "radius": 30,
                 "fill": [100, 140, 200, 40], "stroke": [80, 120, 180], "stroke_width": 2},
                {"type": "circle", "x": 0.5, "y": 0.4, "radius": 15, "fill": [140, 180, 230, 60]},
                {"type": "circle", "x": 0.5, "y": 0.4, "radius": 5, "fill": [200, 220, 255]},
            ],
            "atmosphere": ATMOSPHERE_CONFIGS.get(bg_type, ATMOSPHERE_CONFIGS["gradient"]).copy(),
            "mood": mood,
        }
        remember(text, scene)
        return scene

    # Infer scene properties
    scene_type = infer_scene_type(concepts)
    bg_type = detect_bg_type(concepts)
    mood = detect_mood(text)

    # Sometimes override mood for variety (20% chance)
    if rng.random() < 0.2 and mood != "dramatic":
        alt_moods = [m for m in ("peaceful", "somber", "hopeful", "mysterious", "epic", "dramatic") if m != mood]
        mood = rng.choice(alt_moods)

    # Build scene
    bg_config = BG_CONFIGS.get(bg_type, BG_CONFIGS["gradient"]).copy()
    atmos_config = ATMOSPHERE_CONFIGS.get(bg_type, ATMOSPHERE_CONFIGS["gradient"]).copy()

    # Apply mood-based color shifts and atmosphere effects
    if "colors" in bg_config:
        top, bot = list(bg_config["colors"][0]), list(bg_config["colors"][1])
        if mood == "somber":
            top = [max(0, c - 30) for c in top]
            bot = [max(0, c - 20) for c in bot]
            atmos_config["fog"] = True
        elif mood == "hopeful":
            top = [min(255, c + 30) for c in top]
            bot = [min(255, c + 15) for c in bot]
            if atmos_config.get("particles") == "none":
                atmos_config["particles"] = "sparkles"
                atmos_config["star_count"] = 20
        elif mood == "dramatic":
            top = [min(255, top[0] + 20), max(0, top[1] - 30), max(0, top[2] - 30)]
            bot = [max(0, bot[0] - 10), max(0, bot[1] - 20), max(0, bot[2] - 20)]
        elif mood == "mysterious":
            top = [max(0, c - 20) for c in top]
            bot = [max(0, c - 10) for c in bot]
            atmos_config["fog"] = True
        elif mood == "epic":
            top = [min(255, top[0] + 20), min(255, top[1] + 10), min(255, top[2] + 10)]
            bot = [max(0, bot[0] - 10), max(0, bot[1] - 10), max(0, bot[2] - 10)]

        # Apply subtle random hue rotation for creative variety within mood
        hue_shift = rng.randint(-15, 15)
        top = [max(0, min(255, c + hue_shift)) for c in top]
        bot = [max(0, min(255, c + hue_shift)) for c in bot]

        bg_config["colors"] = [tuple(top), tuple(bot)]

    # Randomly add ambient particles for depth
    if rng.random() < 0.3 and atmos_config.get("particles", "none") == "none":
        atmos_config["particles"] = rng.choice(["stars", "mist", "dust", "sparkles"])
        atmos_config["star_count"] = rng.randint(8, 20)

    elements = compute_positions(concepts, scene_type)

    # Add ambient decorative elements (floating dust, sparkles, etc.)
    if rng.random() < 0.4 and len(elements) < 8:
        n_ambient = rng.randint(1, 3)
        for _ in range(n_ambient):
            amb = {
                "type": "circle",
                "x": round(rng.uniform(0.1, 0.9), 3),
                "y": round(rng.uniform(0.2, 0.6), 3),
                "radius": round(rng.uniform(2, 5), 1),
                "fill": [rng.randint(200, 255), rng.randint(200, 255), rng.randint(200, 255), 40],
            }
            elements.append(amb)

    # Apply pose modifiers from original text
    tl = text.lower()
    if "sitting" in tl or "seated" in tl or "sits" in tl:
        for elem in elements:
            if elem.get("type") in ("human", "man", "woman", "child"):
                elem["pose"] = "sitting_chair"
        elements = [e for e in elements if not (
            e.get("type") in ("chair", "stool", "bench") and
            any(h.get("type") in ("human", "man", "woman", "child") for h in elements)
        )]
    if "sleeping" in tl or "asleep" in tl or "nap" in tl or "lying" in tl or "reclining" in tl or "laying" in tl:
        for elem in elements:
            if elem.get("type") in ("human", "man", "woman", "child"):
                elem["pose"] = "lying_back"
        elements = [e for e in elements if not (
            e.get("type") in ("bed", "bunk", "cot") and
            any(h.get("type") in ("human", "man", "woman", "child") for h in elements)
        )]
    if "kneeling" in tl or "kneels" in tl:
        for elem in elements:
            if elem.get("type") in ("human", "man", "woman", "child"):
                elem["pose"] = "kneeling"
    if "jogging" in tl or "jogs" in tl:
        for elem in elements:
            if elem.get("type") in ("human", "man", "woman", "child"):
                elem["pose"] = "jogging"
    if "running" in tl or "runs" in tl or "sprinting" in tl:
        for elem in elements:
            if elem.get("type") in ("human", "man", "woman", "child"):
                elem["pose"] = "running"
    if "gazing" in tl or "gazing at" in tl or "looks up" in tl or "looking up" in tl or "staring" in tl or "stares" in tl:
        for elem in elements:
            if elem.get("type") in ("human", "man", "woman", "child", "astronaut"):
                elem["pose"] = "standing_arms_up"
    if "reading" in tl or "reads" in tl or "newspaper" in tl:
        for elem in elements:
            if elem.get("type") in ("human", "man", "woman", "child"):
                if "pose" not in elem:
                    elem["pose"] = "reading"
    if "riding" in tl or "rider" in tl or "cycling" in tl or "cyclist" in tl:
        for elem in elements:
            if elem.get("type") in ("human", "man", "woman", "child"):
                elem["pose"] = "sitting_chair"
        elements = [e for e in elements if not (
            e.get("type") in ("bike", "motorcycle", "scooter") and
            any(h.get("type") in ("human", "man", "woman", "child") for h in elements)
        )]
    if "driving" in tl or "driver" in tl or "drives" in tl:
        for elem in elements:
            if elem.get("type") in ("human", "man", "woman", "child"):
                elem["pose"] = "sitting_chair"
        elements = [e for e in elements if not (
            e.get("type") in ("car", "vehicle", "truck", "bus") and
            any(h.get("type") in ("human", "man", "woman", "child") for h in elements)
        )]

    # Add atmosphere particles for space
    if bg_type == "space":
        atmos_config["particles"] = "stars"
        atmos_config["star_count"] = 40

    # Spatial relationship: astronaut/alien on planet surface
    has_astronaut = any(e.get("type") in ("astronaut", "alien") for e in elements)
    has_planet = any(e.get("type") == "planet" for e in elements)
    if has_astronaut and has_planet:
        for e in elements:
            if e.get("type") == "planet":
                e["y"] = 0.72
                e["scale"] = 1.5
            if e.get("type") in ("astronaut", "alien"):
                e["y"] = 0.45

    scene = {
        "bg": bg_config,
        "elements": elements,
        "atmosphere": atmos_config,
        "mood": mood,
    }

    # Save to memory
    remember(text, scene)

    return scene
