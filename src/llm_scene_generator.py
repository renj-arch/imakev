"""LLM Scene Generator — analyzes narration text and generates structured
scene descriptions for the SketchGenerator renderer.

Uses the configured LLM (local or cloud) to UNDERSTAND the narration and
produce a rich, context-appropriate visual scene with proper elements,
background, mood, and atmosphere.

Usage:
    from src.llm_scene_generator import describe_scene
    scene = describe_scene("A whale swimming through ancient oceans")
    # scene -> {"bg": {...}, "elements": [...], "atmosphere": {...}, "mood": "epic"}
"""

import re, json
from src.script_generator import _generate

SYSTEM_PROMPT = """You are a visual artist and scene composer. You create beautiful, full-color illustrations.
You read narration text, UNDERSTAND what is being described, and generate a structured scene.
You output ONLY valid JSON. You describe every visual detail with specific colors and positions."""

ELEMENT_TYPES = """mountain|tree|cloud|water|human|house|hill|sun|moon|star|circle|rect|polygon|line|text|label|ship|building|cannon|flag|x_mark|arrow|grass|path|bird|animal|fish|flower|fire|cave|volcano|wave|canoe|whale|shark|sea_serpent|totem|anchor|compass|globe|cliff|compass_rose|shadow_figure|moon_path|skeleton|crocodile|dinosaur|dna|island|rainbow|waterfall|book|scroll|lamp|key|crown|skull|gear|clock|lightbulb|telescope|map|hand|eye|coin|jar|shelf|astronaut|rocket|ufo|robot"""

MOODS = "peaceful|dramatic|somber|hopeful|epic|mysterious"

BACKGROUND_TYPES = "gradient|night|ocean|indoor|solid|sunset|forest|underwater"

ATMOSPHERE_TYPES = "stars|rain|snow|mist|sunbeams|sparkles|ash|none"

USER_PROMPT_TEMPLATE = """Create a beautiful full-color illustration for: "{prompt}"

Output a JSON scene description with this exact structure:
{{
  "bg": {{
    "type": "{bg_types}",
    "colors": [[R,G,B], [R,G,B], ...],
    "horizon": 0.0-1.0 or null,
    "ground_color": [R,G,B] or null,
    "water_color": [R,G,B] or null,
    "sky_color": [R,G,B] or null,
    "horizon_color": [R,G,B] or null
  }},
  "elements": [
    {{
      "type": "{element_types}",
      "x": 0.0-1.0,
      "y": 0.0-1.0,
      "scale": 0.5-2.0 or null,
      "fill": [R,G,B] or null,
      "stroke": [R,G,B] or null,
      "text": "text content" or null,
      "font_size": 14-60 or null,
      "width": 0.0-1.0 or null,
      "height": 0.0-1.0 or null,
      "radius": 0.0-1.0 or null,
      "label": "what this is" or null,
      "tree_style": "round|pine|palm" or null,
      "snow": true|false or null,
      "sail_color": [R,G,B] or null,
      "window_color": [R,G,B] or null,
      "roof_color": [R,G,B] or null,
      "skin_color": [R,G,B] or null
    }}
  ],
  "atmosphere": {{
    "particles": "{atmosphere_types}",
    "fog": true|false,
    "star_count": 0-100 or null
  }},
  "mood": "{moods}"
}}

RULES - READ CAREFULLY:
1. Choose background type and colors that match the narration's setting and mood
2. Place 3-8 elements to create a complete, beautiful composition
3. Use rich, harmonious colors (provide exact [R,G,B] values between 0-255)
4. For skeleton/bones/fossils: use "skeleton" type
5. For crocodiles/alligators/prehistoric reptiles: use "crocodile" type
6. For dinosaurs: use "dinosaur" type
7. For DNA/genetics: use "dna" type
8. For boats: use "ship" type with sail_color
9. For buildings: include window_color
10. For houses: include roof_color
11. For mountains: include "snow": true/false
12. For trees: include tree_style "round|pine|palm"
13. For people: use "human" type with optional skin_color
14. For evolution/timeline concepts: include "text" element with appropriate label
15. x,y coordinates are 0-1 on a portrait canvas (720x1280)
16. Choose mood to match the narration tone: epic for grand/evolutionary stories, mysterious for secrets/bones, somber for loss/leaving, hopeful for discovery/birth, peaceful for calm scenes, dramatic for action/change
17. Underwater scenes: bg type "underwater" with deep blues
18. Night scenes: bg type "night" with stars in atmosphere
19. Ocean scenes: bg type "ocean" with water_color

Respond with ONLY the JSON object, no other text."""


def describe_scene(narration: str) -> dict:
    """Generate a structured scene description from narration text.
    
    Uses the configured LLM to understand the narration and produce
    a rich visual scene. Falls back to a generic scene on failure.
    
    Args:
        narration: A sentence or paragraph describing a scene
        
    Returns:
        dict with keys: bg, elements, atmosphere, mood
    """
    prompt = USER_PROMPT_TEMPLATE.format(
        prompt=narration,
        bg_types=BACKGROUND_TYPES,
        element_types=ELEMENT_TYPES,
        atmosphere_types=ATMOSPHERE_TYPES,
        moods=MOODS,
    )
    
    try:
        raw = _generate(prompt, temperature=0.7, max_tokens=3000, system=SYSTEM_PROMPT)
        raw = re.sub(r'^```(?:json)?\s*', '', raw.strip())
        raw = re.sub(r'\s*```$', '', raw)
        data = json.loads(raw)
        if "bg" in data or "elements" in data:
            _validate_scene(data)
            return data
    except Exception as e:
        print(f"  LLM scene generation error: {e}")
    
    return None


def _validate_scene(scene: dict):
    """Ensure scene has all required fields with correct types."""
    if "bg" not in scene:
        scene["bg"] = {"type": "gradient", "colors": [[200, 210, 230], [140, 160, 200]]}
    if "elements" not in scene:
        scene["elements"] = []
    if "atmosphere" not in scene:
        scene["atmosphere"] = {"particles": "none", "fog": False}
    if "mood" not in scene:
        scene["mood"] = "peaceful"


def _fallback_scene(narration: str) -> dict:
    """Generic fallback scene when LLM is unavailable."""
    n = narration.lower()
    
    # Try to match environment from keywords
    bg = {"type": "gradient", "colors": [[200, 210, 230], [140, 160, 200]],
           "horizon": 0.6, "ground_color": [60, 90, 50]}
    mood = "peaceful"
    elements = [
        {"type": "hill", "x": 0.3, "y": 0.7, "width": 0.5, "height": 0.15, "fill": [60, 120, 60]},
        {"type": "tree", "x": 0.3, "y": 0.72, "scale": 0.8, "tree_style": "round", "fill": [50, 120, 50]},
        {"type": "cloud", "x": 0.5, "y": 0.2, "scale": 0.8},
    ]
    atmos = {"particles": "none", "fog": False}
    
    # Ocean/water scenes
    if any(w in n for w in ("ocean", "sea", "whale", "shark", "water", "beach", "wave")):
        bg = {"type": "ocean", "sky_color": [180, 210, 240], "horizon_color": [120, 170, 220],
              "horizon": 0.5, "water_color": [30, 70, 150]}
        elements = [{"type": "whale", "x": 0.5, "y": 0.5, "scale": 0.8, "fill": [60, 70, 100]}]
        mood = "epic" if any(w in n for w in ("giant", "huge", "largest", "enormous", "epic")) else "peaceful"
    
    # Night
    elif any(w in n for w in ("night", "dark", "moon", "star", "midnight")):
        bg = {"type": "night", "colors": [[10, 8, 30], [30, 25, 60]], "horizon": 0.6, "ground_color": [20, 30, 20]}
        elements = [{"type": "moon", "x": 0.7, "y": 0.2, "radius": 22}]
        atmos = {"particles": "stars", "fog": False, "star_count": 60}
        mood = "mysterious"
    
    # Prehistoric/evolution
    if any(w in n for w in ("evolution", "evolve", "prehistoric", "million years", "ancestor")):
        mood = "epic"
        elements.insert(0, {"type": "text", "x": 0.5, "y": 0.08, "text": "EVOLUTION", "font_size": 30, "fill": [200, 180, 60]})
    
    # Skeleton/bones
    if any(w in n for w in ("skeleton", "bone", "pelvic", "fossil", "skull")):
        elements.append({"type": "skeleton", "x": 0.5, "y": 0.65, "scale": 0.6, "fill": [220, 200, 180]})
        mood = "mysterious"
        atmos = {"particles": "none", "fog": True}
    
    return {
        "bg": bg,
        "elements": elements,
        "atmosphere": atmos,
        "mood": mood,
    }
