"""Creative scene composer — understands subjects, modifiers, expressions, clothing, and spatial relationships.

Parses a narration prompt into a rich scene description without external APIs.
The engine composes elements from atomic parts based on text understanding.
"""

import re
from src.concept_extractor import CONCEPTS, extract_concepts, detect_bg_type, detect_mood, infer_scene_type
from src.dynamic_scene import ELEMENT_DEFS, BG_CONFIGS, _scene_rng
import random

# ── Expression keywords ───────────────────────────────────────

EXPRESSIONS = {
    "happy":   ["happy", "joyful", "cheerful", "glad", "delighted", "pleased", "smiling", "grinning", "content"],
    "sad":     ["sad", "sadness", "sadly", "unhappy", "depressed", "gloomy", "miserable", "mournful",
                "crying", "tears", "cry", "weeping", "heartbroken", "lonely", "despair"],
    "angry":   ["angry", "anger", "furious", "mad", "enraged", "annoyed", "irritated",
                "frustrated", "grumpy", "cross"],
    "surprised": ["surprised", "shocked", "amazed", "astonished", "startled", "stunned"],
    "tired":   ["tired", "sleepy", "exhausted", "weary", "fatigued", "drowsy", "yawning"],
    "proud":   ["proud", "confident", "smug", "superior", "triumphant", "victorious"],
}

# ── Clothing keywords ─────────────────────────────────────────

CLOTHING = {
    "suit":     ["suit", "business suit", "formal wear", "work suit", "tuxedo"],
    "hat":      ["hat", "cap", "top hat", "fedora", "beret", "cowboy hat", "helmet"],
    "tie":      ["tie", "necktie", "bow tie", "bowtie"],
    "uniform":  ["uniform", "work uniform", "military uniform", "police uniform", "doctor coat"],
    "coat":     ["coat", "jacket", "blazer", "overcoat", "raincoat"],
    "dress":    ["dress", "gown", "robe", "cloak"],
    "apron":    ["apron", "overalls", "work apron"],
    "collar":   ["collar", "neck collar", "studded collar", "spike collar"],
    "shirt":    ["shirt", "t-shirt", "blouse", "polo"],
    "pants":    ["pants", "trousers", "jeans", "slacks", "shorts"],
    "shoes":    ["shoes", "boots", "sneakers", "loafers"],
}

# ── Accessories keywords ──────────────────────────────────────

ACCESSORIES = {
    "chain":       ["chain", "chain leash", "chain link", "metal chain"],
    "glasses":     ["glasses", "spectacles", "eyeglasses", "sunglasses", "monocle"],
    "crown":       ["crown", "tiara", "diadem"],
    "necklace":    ["necklace", "pendant", "locket", "medal"],
    "watch":       ["watch", "wristwatch"],
    "ring":        ["ring", "jewelry ring"],
    "cigar":       ["cigar", "cigarette", "pipe"],
    "belt":        ["belt", "belt buckle"],
    "scarf":       ["scarf", "muffler"],
    "backpack":    ["backpack", "bag", "satchel", "briefcase"],
}

# ── Spatial relationship keywords ─────────────────────────────

SPATIAL_RELATIONS = {
    "beside":     ["beside", "next to", "alongside", "adjacent", "by the side of", "near"],
    "behind":     ["behind", "in back of", "beyond", "past"],
    "in_front_of": ["in front of", "before", "ahead of", "facing"],
    "on":         ["on", "on top of", "above", "perched on", "sitting on", "upon"],
    "under":      ["under", "underneath", "beneath", "below"],
    "inside":     ["inside", "within", "in", "within"],
    "around":     ["around", "surrounding", "encircling"],
    "between":    ["between", "among", "amid", "amidst"],
    "across":     ["across", "opposite", "facing"],
}

# ── Action/Pose keywords ─────────────────────────────────────

ACTIONS = {
    "standing":  ["standing", "stands", "stood", "upright"],
    "sitting":   ["sitting", "sits", "sat", "seated", "perched"],
    "walking":   ["walking", "walks", "walked", "strolling", "pacing"],
    "lying":     ["lying", "laying", "reclining", "prone", "sleeping"],
    "kneeling":  ["kneeling", "kneels", "kneeled", "on knees"],
    "crouching": ["crouching", "crouches", "crouched", "hiding", "stalking"],
    "running":   ["running", "runs", "ran", "sprinting", "jogging"],
    "flying":    ["flying", "flies", "flew", "soaring", "hovering"],
}

# ── Body part references for accessory positioning ───────────

BODY_PARTS = {
    "neck":     ["neck", "throat", "collar"],
    "head":     ["head", "forehead", "crown of head", "top of head"],
    "waist":    ["waist", "hip", "hips", "belt line"],
    "wrist":    ["wrist", "writes"],
    "hand":     ["hand", "paw", "paws", "fist"],
    "foot":     ["foot", "feet", "ankle"],
    "ear":      ["ear", "ears"],
    "tail":     ["tail"],
    "back":     ["back", "shoulder", "shoulders"],
}

# ── Helper: find keywords in text ────────────────────────────

def _find_keywords_in_text(text: str, keyword_dict: dict) -> list:
    """Return list of (category, matched_word) for all matches found in text."""
    tl = text.lower()
    matches = []
    for category, keywords in keyword_dict.items():
        for kw in keywords:
            if re.search(r'\b' + re.escape(kw) + r'\b', tl):
                matches.append((category, kw))
                break  # one match per category
    return matches


def _find_expression(text: str) -> str | None:
    matches = _find_keywords_in_text(text, EXPRESSIONS)
    return matches[0][0] if matches else None


def _find_clothing(text: str) -> list[str]:
    return [c for c, _ in _find_keywords_in_text(text, CLOTHING)]


def _find_accessories(text: str) -> list[str]:
    return [a for a, _ in _find_keywords_in_text(text, ACCESSORIES)]


def _find_pose(text: str, concepts: dict) -> str:
    """Determine pose from text or concepts."""
    matches = _find_keywords_in_text(text, ACTIONS)
    if matches:
        return matches[0][0]
    # If "sitting" or similar is in concepts, use it
    for concept, count in concepts.items():
        if concept in ("sitting", "lying", "kneeling", "jogging", "running"):
            return concept
    return "standing"


def _find_spatial_relation(text: str) -> list[tuple[str, str, str]]:
    """Find spatial relationships. Returns [(subject_word, relation, object_word), ...]."""
    tl = text.lower()
    words = tl.split()
    results = []

    for rel_name, rel_kw in SPATIAL_RELATIONS.items():
        for kw in rel_kw:
            pattern = r'(\w+)\s+' + re.escape(kw) + r'\s+(\w+)'
            for m in re.finditer(pattern, tl):
                subj, obj = m.group(1), m.group(2)
                results.append((subj, rel_name, obj))
            # Also check "beside a/the" pattern
            pattern2 = r'(\w+)\s+' + re.escape(kw) + r'\s+(?:a|an|the)\s+(\w+)'
            for m in re.finditer(pattern2, tl):
                subj, obj = m.group(1), m.group(2)
                results.append((subj, rel_name, obj))
    return results


def _find_body_part_refs(text: str) -> list[tuple[str, str]]:
    """Find body part references. Returns [(part, word), ...]."""
    return _find_keywords_in_text(text, BODY_PARTS)


def _map_word_to_concept(word: str) -> str | None:
    """Map a word to its concept type using CONCEPTS dict."""
    wl = word.lower()
    for concept, keywords in CONCEPTS.items():
        if wl in keywords:
            return concept
    return None


def _resolve_elements_for_concepts(concepts: dict, pose: str, rng: random.Random) -> list[dict]:
    """Build element list from concepts, using ELEMENT_DEFS for defaults."""
    elements = []
    # Sort by count (most important first)
    sorted_c = sorted(concepts.items(), key=lambda x: -x[1])
    for cname, _ in sorted_c:
        if cname in ELEMENT_DEFS and ELEMENT_DEFS[cname].get("type") != "none":
            base = dict(ELEMENT_DEFS[cname])
            base["x"] = round(rng.uniform(0.2, 0.8), 3)
            base["y"] = round(rng.uniform(0.3, 0.75), 3)
            elements.append(base)
    return elements


def _apply_pose(elements: list, pose: str, text: str):
    """Apply pose to suitable elements (animals, humans)."""
    for e in elements:
        if e.get("type") in ("cat", "dog", "horse", "human", "bear", "rabbit", "fox", "wolf",
                            "monkey", "dinosaur", "dragon", "elephant"):
            if pose in ("sitting", "lying", "kneeling"):
                e["pose"] = pose


def _apply_expression(elements: list, expression: str | None, text: str):
    """Apply mood/expression to face-drawing elements."""
    if not expression:
        return
    for e in elements:
        if e.get("type") in ("cat", "dog", "human", "bear", "rabbit", "fox", "wolf",
                            "monkey", "horse", "elephant", "dragon"):
            e["mood"] = expression


def _apply_spatial_positions(elements: list, relations: list, text: str):
    """Reposition elements based on spatial relationships."""
    for subj_word, rel, obj_word in relations:
        subj_concept = _map_word_to_concept(subj_word)
        obj_concept = _map_word_to_concept(obj_word)
        if not subj_concept or not obj_concept:
            continue

        subj_elem = None
        obj_elem = None
        for e in elements:
            edef = ELEMENT_DEFS.get(subj_concept, {})
            if edef.get("type") == e.get("type"):
                subj_elem = e
            edef2 = ELEMENT_DEFS.get(obj_concept, {})
            if edef2.get("type") == e.get("type"):
                obj_elem = e

        if subj_elem and obj_elem:
            if rel == "beside":
                # Place subject to the left of object
                subj_elem["x"] = obj_elem["x"] - 0.2
                subj_elem["y"] = obj_elem["y"]
            elif rel == "behind":
                subj_elem["x"] = obj_elem["x"] - 0.1
                subj_elem["y"] = obj_elem["y"] - 0.08
            elif rel == "in_front_of":
                subj_elem["x"] = obj_elem["x"]
                subj_elem["y"] = obj_elem["y"] - 0.05
                subj_elem["_layer"] = 1  # draw on top
            elif rel == "on" or rel == "on top of":
                subj_elem["x"] = obj_elem["x"]
                subj_elem["y"] = obj_elem["y"] - 0.08
                subj_elem["pose"] = "sitting"
                subj_elem["_layer"] = 1


def _add_clothing(elements: list, clothing: list[str], rng: random.Random):
    """Add clothing overlay elements for subjects that wear them."""
    for c in clothing:
        # Find a subject to attach clothing to (first animal/human)
        target = None
        for e in elements:
            if e.get("type") in ("cat", "dog", "human", "bear", "rabbit", "fox", "wolf",
                                "monkey", "horse", "elephant", "dragon"):
                target = e
                break
        if not target:
            continue

        tx = target["x"]
        ty = target["y"]
        ts = target.get("scale", 2.0)

        if c == "suit":
            elements.append({
                "type": "rect", "x": tx, "y": ty - 0.02,
                "width": 0.08 * ts, "height": 0.10 * ts,
                "fill": [60, 60, 80, 220], "stroke": [40, 40, 60], "stroke_width": 2, "rx": 3,
                "_layer": 2
            })
        elif c == "hat":
            elements.append({
                "type": "rect", "x": tx + 0.02, "y": ty - 0.08,
                "width": 0.06 * ts, "height": 0.025 * ts,
                "fill": [80, 60, 50, 220], "stroke": [50, 35, 25], "stroke_width": 2,
                "_layer": 2
            })
        elif c == "tie":
            elements.append({
                "type": "polygon",
                "points": [[tx - 0.005, ty - 0.02], [tx + 0.005, ty - 0.02],
                           [tx + 0.008, ty + 0.04], [tx, ty + 0.045], [tx - 0.008, ty + 0.04]],
                "fill": [180, 40, 40, 220], "stroke": [120, 20, 20],
                "_layer": 2
            })
        elif c == "collar":
            elements.append({
                "type": "rect", "x": tx - 0.015, "y": ty - 0.035,
                "width": 0.03 * ts, "height": 0.008 * ts,
                "fill": [180, 30, 30, 230], "stroke": [80, 10, 10], "stroke_width": 2,
                "_layer": 2
            })
        elif c == "apron":
            elements.append({
                "type": "rect", "x": tx - 0.025, "y": ty - 0.01,
                "width": 0.05 * ts, "height": 0.07 * ts,
                "fill": [200, 200, 210, 200], "stroke": [150, 150, 160],
                "_layer": 2
            })


def _add_accessories(elements: list, accessories: list[str], rng: random.Random, text: str):
    """Add accessory elements."""
    # Find a subject to attach accessories
    target = None
    for e in elements:
        if e.get("type") in ("cat", "dog", "human", "bear", "rabbit", "fox", "wolf",
                            "monkey", "horse", "elephant", "dragon"):
            target = e
            break
    if not target:
        return

    tx = target["x"]
    ty = target["y"]
    ts = target.get("scale", 2.0)

    for a in accessories:
        if a == "chain":
            # Chain dangling from collar/neck
            chain_len = 0.12 * ts if ts else 0.2
            elements.append({
                "type": "line",
                "x1": tx, "y1": ty - 0.025,
                "x2": tx - 0.08, "y2": ty + 0.06,
                "color": [160, 150, 140, 220], "width": int(3 * max(ts / 3, 0.5)),
                "_layer": 2
            })
            # Chain links (small circles along line)
            for i in range(4):
                t = (i + 1) / 5
                lx = tx + (-0.08) * t
                ly = (ty - 0.025) + (0.085) * t
                elements.append({
                    "type": "circle",
                    "x": lx, "y": ly, "radius": 3,
                    "fill": [180, 170, 160, 200], "stroke": [120, 110, 100],
                    "_layer": 2
                })
        elif a == "glasses":
            elements.append({
                "type": "rect", "x": tx - 0.015, "y": ty - 0.03,
                "width": 0.05, "height": 0.02,
                "fill": None, "stroke": [40, 40, 40, 200], "stroke_width": 2, "rx": 2,
                "_layer": 2
            })
            elements.append({
                "type": "line",
                "x1": tx + 0.01, "y1": ty - 0.02,
                "x2": tx + 0.04, "y2": ty - 0.02,
                "color": [40, 40, 40, 200], "width": 2,
                "_layer": 2
            })


def _reorder_by_layer(elements: list[dict]) -> list[dict]:
    """Sort elements so lower _layer values draw first (behind)."""
    return sorted(elements, key=lambda e: e.get("_layer", 0))


def compose_creative_scene(text: str, rng: random.Random = None) -> dict | None:
    """Main entry point: compose a creative scene from narration text.

    Returns None if the text doesn't trigger creative composition
    (falls through to normal pipeline).
    """
    tl = text.lower()

    # Check if this text needs creative composition
    # (has clothing, accessories, expressions, or spatial relationships)
    clothing = _find_clothing(text)
    accessories = _find_accessories(text)
    expression = _find_expression(text)
    relations = _find_spatial_relation(text)
    pose = _find_pose(text, {})

    has_modifiers = bool(clothing or accessories or expression or relations)

    # Only activate for text that needs creative handling
    if not has_modifiers and not any(w in tl for w in ("wearing", "dressed", "holding", "carrying",
                                                        "expression", "mood", "feeling")):
        return None

    if rng is None:
        rng = random.Random(hash(tl) & 0xFFFFFFFF)

    # Extract concepts
    concepts = extract_concepts(text)
    if not concepts:
        return None

    # Build initial elements
    elements = _resolve_elements_for_concepts(concepts, pose, rng)
    if not elements:
        return None

    # Apply creative modifiers
    _apply_expression(elements, expression, text)
    _apply_pose(elements, pose, text)
    _apply_spatial_positions(elements, relations, text)

    # Add clothing and accessories
    _add_clothing(elements, clothing, rng)
    _add_accessories(elements, accessories, rng, text)

    # Reorder by layer
    elements = _reorder_by_layer(elements)

    # Detect scene properties
    bg_type = detect_bg_type(concepts)
    mood = detect_mood(text)
    if expression:
        mood = expression

    bg_config = dict(BG_CONFIGS.get(bg_type, BG_CONFIGS["gradient"]))
    from src.dynamic_scene import _apply_mood_colors
    bg_config = _apply_mood_colors(bg_config, mood, rng)
    atmos_config = {
        "particles": "none",
        "fog": False,
    }

    scene = {
        "bg": bg_config,
        "elements": elements,
        "atmosphere": atmos_config,
        "mood": mood,
    }

    return scene
