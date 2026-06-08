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


# ── Auto-layout engine ────────────────────────────────────────
# Positions elements on a 3-column grid with natural offsets

def compute_positions(concepts: dict, scene_type: str) -> list:
    """Place elements based on concept weights and scene type.
    
    Uses a priority system:
    - Primary concept → center (y=0.4)
    - Secondary → left/right (y=0.35-0.55)
    - Tertiary → foreground (y=0.6-0.75)
    - Decorative → background (y=0.1-0.25)
    """
    elements = []
    sorted_concepts = sorted(concepts.items(), key=lambda x: -x[1])

    # Filter non-visual concepts and get top visual elements
    visual_concepts = [c for c, _ in sorted_concepts if c in ELEMENT_DEFS]

    if not visual_concepts:
        return elements

    # Assign positions based on role
    primary_x, primary_y = 0.5, 0.4
    col_positions = [0.2, 0.5, 0.8]
    col_idx = 0

    for i, concept in enumerate(visual_concepts):
        base = ELEMENT_DEFS.get(concept, {"type": "circle", "radius": 10, "fill": [150, 150, 150]})

        # Determine position based on natural placement
        if concept in ("star", "cloud", "bird", "sun", "moon", "galaxy", "rainbow"):
            # Sky/background elements
            x = col_positions[col_idx % 3] + (i * 0.05)
            y = 0.12 + (i * 0.08)
        elif concept in ("mountain", "glacier", "planet", "dinosaur", "astronaut"):
            # Mid-ground elements
            x = col_positions[col_idx % 3] + (i * 0.02)
            y = 0.45 + (i * 0.03)
        elif concept in ("tree", "water", "flower", "grass", "path", "ocean", "wave",
                         "human", "animal", "dog", "cat", "horse", "ship", "car", "fire",
                         "building", "bear", "deer", "rabbit", "fox", "wolf", "frog",
                         "turtle", "monkey", "squirrel", "camel", "rhino", "hippo",
                         "giraffe", "dragon", "snake", "lizard", "goat", "sheep", "pig",
                         "cow", "rat", "beaver", "otter", "hedgehog", "bat", "kangaroo",
                         "sloth", "raccoon", "skunk", "zebra", "unicorn", "panda",
                         "moose", "bison", "mouse", "lion", "tiger", "elephant",
                          "chair", "table", "sofa", "bed", "cupboard", "fridge",
                          "oven", "sink", "toilet", "bathtub", "mirror", "curtain",
                            "pillow", "door", "window", "bike", "map", "world_map", "india_map", "globe",
                            "canoe", "kayak", "raft", "pirate_ship", "galleon", "train",
                            "planet", "blackhole", "galaxy", "snow", "rain", "lightning",
                            "storm", "fog", "desert", "computer", "network", "ai", "circuit",
                              "data", "microscope", "experiment", "alien", "artifact",
                              "cannon", "wall", "tent", "chain", "tower", "fortress",
                              "soldier"):
            # Foreground elements
            x = col_positions[col_idx % 3]
            y = 0.65 + (i * 0.04)
        elif concept in ("dna", "atom", "heart", "brain", "clock", "gear", "book",
                         "lightbulb", "target", "infinity", "puzzle"):
            # Center focus elements
            x = primary_x + (i - 1) * 0.15
            y = primary_y + (i * 0.05)
        else:
            x = col_positions[col_idx % 3]
            y = 0.5 + (i * 0.06)

        # Clamp positions
        x = max(0.05, min(0.95, x))
        y = max(0.05, min(0.85, y))

        element = base.copy()
        element["x"] = round(x, 3)
        element["y"] = round(y, 3)
        elements.append(element)

        col_idx += 1

    # Add text labels from concepts (filter non-visual)
    if visual_concepts:
        label_text = " ".join(concept.upper() for concept in visual_concepts[:3])
        elements.append({
            "type": "text", "x": 0.5, "y": 0.08,
            "text": label_text,
            "font_size": 22, "fill": [200, 200, 220]
        })

    # Fill thin scenes with context-appropriate decorative elements
    if len(elements) < 4:
        fillers = _get_filler_elements(visual_concepts[:1] if visual_concepts else None)
        elements.extend(fillers)

    return elements


def _get_filler_elements(primary_concepts: list | None) -> list:
    """Generate decorative filler elements when a scene is too sparse."""
    fillers = []
    # Determine theme from primary concept
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
        fillers = [
            {"type": "wave", "x": round(0.15 + i * 0.35, 3), "y": 0.75, "scale": 2.0, "fill": [60, 120, 190]}
            for i in range(3)
        ]
    elif theme == "space":
        fillers = [
            {"type": "star", "x": round(0.1 + i * 0.4, 3), "y": round(0.1 + (i % 2) * 0.08, 3), "radius": 1.5 + i * 0.5, "fill": [255, 255, 200]}
            for i in range(4)
        ]
    elif theme == "nature":
        fillers = [
            {"type": "circle", "x": round(0.1 + i * 0.3, 3), "y": round(0.7 + (i % 2) * 0.04, 3), "radius": 3, "fill": [50 + i * 20, 120 + i * 10, 50]}
            for i in range(3)
        ]
    elif theme == "city":
        fillers = [
            {"type": "building", "x": round(0.15 + i * 0.25, 3), "y": 0.6, "scale": 1.5 + i * 0.05, "fill": [140 + i * 15, 130 + i * 10, 120]}
            for i in range(3)
        ]
    else:
        fillers = [
            {"type": "circle", "x": round(0.2 + i * 0.3, 3), "y": round(0.3 + (i % 2) * 0.1, 3), "radius": 4 + i * 2, "fill": [150 + i * 20, 180, 210, 50 + i * 10]}
            for i in range(3)
        ]
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
    
    Works by:
    1. Extracting visual concepts from the text
    2. Selecting bg/atmosphere based on inferred scene type
    3. Auto-computing element positions
    4. Setting mood from emotional keywords
    5. Saving to memory for future recall
    """
    # Check memory first
    remembered = recall(text)
    if remembered:
        elements = remembered.get("elements", [])
        if elements and all(isinstance(e, dict) for e in elements):
            return remembered

    # Extract concepts
    concepts = extract_concepts(text)

    # If no concepts found, build a minimal scene from mood + bg type
    if not concepts:
        bg_type = detect_bg_type({"lightbulb": 1})  # Default to indoor/abstract
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
        bg_config["colors"] = [tuple(top), tuple(bot)]

    elements = compute_positions(concepts, scene_type)

    # Apply pose modifiers from original text
    tl = text.lower()
    if "sitting" in tl or "seated" in tl or "sits" in tl:
        for elem in elements:
            if elem.get("type") in ("human", "man", "woman", "child"):
                elem["pose"] = "sitting_chair"
        # Remove standalone chair element when human sits on it
        elements = [e for e in elements if not (
            e.get("type") in ("chair", "stool", "bench") and
            any(h.get("type") in ("human", "man", "woman", "child") for h in elements)
        )]
    if "sleeping" in tl or "asleep" in tl or "nap" in tl or "lying" in tl or "reclining" in tl or "laying" in tl:
        for elem in elements:
            if elem.get("type") in ("human", "man", "woman", "child"):
                elem["pose"] = "lying_back"
        # Remove standalone bed when human lies on it
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
        # Remove bike when riding
        elements = [e for e in elements if not (
            e.get("type") in ("bike", "motorcycle", "scooter") and
            any(h.get("type") in ("human", "man", "woman", "child") for h in elements)
        )]
    if "driving" in tl or "driver" in tl or "drives" in tl:
        for elem in elements:
            if elem.get("type") in ("human", "man", "woman", "child"):
                elem["pose"] = "sitting_chair"
        # Remove car when driving
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
