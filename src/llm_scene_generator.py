"""LLM Scene Generator — uses LLM to UNDERSTAND narration meaning,
then pipes structured intent into the dynamic scene engine for rendering.

Architecture:
  LLM (understanding) → structured intent (tiny JSON) → dynamic composer (rendering)

This hybrid approach means the LLM only needs ~50 tokens of output,
avoiding token limits while still giving genuine semantic understanding.
"""

import re, json
from src.script_generator import _generate
from src.dynamic_scene import compose_dynamic_scene, BG_CONFIGS, ATMOSPHERE_CONFIGS, ELEMENT_DEFS
from src.concept_extractor import extract_concepts, detect_bg_type, detect_mood

SYSTEM_PROMPT = "You analyze narration for illustration. Output ONLY a JSON object with scene type, mood, and subjects."

USER_PROMPT = '''Analyze this narration for a scene illustration.
Output JSON: {{"scene":"scene_type","mood":"mood","subjects":["subject1","subject2"],"era":"era_hint","tone":"tone"}}
scene_type one of: gradient|night|ocean|indoor|sunset|forest|underwater|space|desert
mood one of: peaceful|dramatic|somber|hopeful|epic|mysterious
subjects: 2-4 key visual concepts from the narration
era: ancient|medieval|modern|future|prehistoric|none
tone: wonder|awe|fear|sadness|joy|curiosity|none

Narration: "{prompt}"

JSON:'''


def describe_scene(narration: str) -> dict | None:
    """Analyze narration with LLM, then pipe intent into the scene engine.
    
    Returns a full scene dict (bg, elements, atmosphere, mood) or None.
    """
    prompt = USER_PROMPT.format(prompt=narration)
    
    try:
        raw = _generate(prompt, temperature=0.3, max_tokens=300, system=SYSTEM_PROMPT)
        if not raw:
            return None
        intent = _extract_json(raw)
        if not intent:
            return None
        return render_from_intent(narration, intent)
    except Exception as e:
        print(f"  LLM scene error: {e}")
        return None


def render_from_intent(narration: str, intent: dict) -> dict:
    """Convert LLM intent into a full rendered scene using the dynamic engine."""
    subjects = intent.get("subjects", [])
    scene_type = intent.get("scene", "gradient")
    mood = intent.get("mood", "peaceful")
    tone = intent.get("tone", "")
    era = intent.get("era", "")

    # Build concepts from LLM subjects (LLM understands meaning better than keywords)
    concepts = _subjects_to_concepts(subjects)

    # Merge with keyword-extracted concepts for robustness
    kw_concepts = extract_concepts(narration)
    for k, v in kw_concepts.items():
        concepts[k] = concepts.get(k, 0) + v

    # If no concepts at all, seed from scene type
    if not concepts:
        concepts = _seed_concepts_from_scene_type(scene_type, narration)

    bg_type = detect_bg_type(concepts)
    bg_config = BG_CONFIGS.get(bg_type, BG_CONFIGS.get(scene_type, BG_CONFIGS["gradient"])).copy()
    atmos_config = ATMOSPHERE_CONFIGS.get(bg_type, ATMOSPHERE_CONFIGS["gradient"]).copy()

    from src.dynamic_scene import compute_positions
    from src.concept_extractor import infer_scene_type
    elements = compute_positions(concepts, infer_scene_type(concepts))

    # Add atmosphere based on tone/era
    if mood == "mysterious" or tone == "awe":
        atmos_config["fog"] = True
    if scene_type in ("night", "space") or era == "prehistoric":
        atmos_config["particles"] = "stars"
        atmos_config["star_count"] = 40

    # Add an era text label if relevant
    if era and era != "none":
        elements.append({
            "type": "text", "x": 0.5, "y": 0.94,
            "text": era.upper(), "font_size": 16, "fill": [180, 180, 180, 120]
        })

    return {
        "bg": bg_config,
        "elements": elements,
        "atmosphere": atmos_config,
        "mood": mood,
    }


def _subjects_to_concepts(subjects: list) -> dict:
    """Map LLM subject words to our concept vocabulary."""
    concept_map = {
        "whale": "whale", "ocean": "ocean", "sea": "ocean", "water": "water",
        "coral": "ocean", "reef": "ocean", "fish": "fish", "shark": "shark",
        "dolphin": "dolphin", "jellyfish": "fish",
        "sun": "sun", "sunlight": "sun", "moon": "moon", "star": "star",
        "planet": "planet", "earth": "planet", "space": "star",
        "tree": "tree", "forest": "tree", "mountain": "mountain", "hill": "mountain",
        "flower": "flower", "grass": "grass", "plant": "plant", "garden": "flower",
        "desert": "desert", "sand": "desert", "dune": "desert",
        "snow": "snow", "ice": "glacier", "glacier": "glacier", "cold": "snow",
        "rain": "rain", "cloud": "cloud", "storm": "storm", "lightning": "lightning",
        "building": "building", "city": "building", "castle": "building",
        "house": "building", "pyramid": "building", "temple": "building",
        "human": "human", "person": "human", "people": "human", "king": "human",
        "queen": "human", "soldier": "human", "child": "human",
        "animal": "dog", "bird": "bird", "dinosaur": "dinosaur", "horse": "horse",
        "dog": "dog", "cat": "cat", "bear": "bear", "wolf": "wolf",
        "snake": "snake", "frog": "frog", "turtle": "turtle",
        "dna": "dna", "atom": "atom", "cell": "atom", "microscope": "microscope",
        "robot": "robot", "ai": "ai", "computer": "computer", "spaceship": "spaceship",
        "rocket": "spaceship", "astronaut": "astronaut",
        "fire": "fire", "volcano": "fire", "lava": "fire",
        "boat": "ship", "ship": "ship", "sail": "ship",
        "book": "book", "map": "map", "flag": "flag", "crown": "crown",
        "clock": "clock", "lightbulb": "lightbulb", "key": "key", "gear": "gear",
        "eye": "eye", "hand": "hand", "heart": "heart", "brain": "brain",
    }
    result = {}
    for s in subjects:
        s_lower = s.lower().strip()
        mapped = concept_map.get(s_lower)
        if mapped:
            result[mapped] = result.get(mapped, 0) + 1
        elif s_lower in ELEMENT_DEFS:
            result[s_lower] = result.get(s_lower, 0) + 1
    if not result:
        result["lightbulb"] = 1
    return result


def _seed_concepts_from_scene_type(scene_type: str, narration: str) -> dict:
    """Seed basic concepts when LLM subjects yield nothing."""
    seed_map = {
        "ocean": {"ocean": 1, "wave": 1},
        "night": {"moon": 1, "star": 2},
        "space": {"star": 2, "planet": 1},
        "forest": {"tree": 2, "grass": 1},
        "desert": {"desert": 1, "sun": 1},
        "sunset": {"sun": 1, "cloud": 1},
        "underwater": {"ocean": 1, "fish": 1},
        "indoor": {"lightbulb": 1, "book": 1},
        "gradient": {"lightbulb": 1},
    }
    return seed_map.get(scene_type, {"lightbulb": 1})


def _extract_json(raw: str) -> dict | None:
    """Extract first JSON object from string, handling markdown/extra text."""
    raw = raw.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    brace_depth = 0
    start = None
    for i, ch in enumerate(raw):
        if ch == '{':
            if start is None:
                start = i
            brace_depth += 1
        elif ch == '}':
            brace_depth -= 1
            if brace_depth == 0 and start is not None:
                try:
                    return json.loads(raw[start:i+1])
                except json.JSONDecodeError:
                    start = None
    return None
