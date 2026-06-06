"""Narration → Sketch — an AI that generates illustrations from narration text.

Given any sentence, the AI analyzes what visuals it describes, creates a
structured scene description, and renders it as a full-color illustration.
Works with LLM (for any prompt) or keyword matching (when LLM is unavailable).

Usage:
    from src.narration_to_sketch import sketch_from_narration
    img = sketch_from_narration("A pirate with a parrot on his shoulder")
    img.save("output.png")
"""

import re, json
from PIL import Image
from src.sketch_generator import SketchGenerator
from src.script_generator import _generate

W, H = 720, 1280


def sketch_from_narration(narration: str, width=W, height=H, seed=None) -> Image.Image:
    """Generate an illustration from a narration sentence.
    
    The AI analyzes the narration, determines what visual elements it describes,
    and renders a full-color illustration. Uses LLM when available, falls back
    to intelligent keyword parsing.
    
    Args:
        narration: A sentence describing a scene
        width: Output image width
        height: Output image height
        seed: Random seed for reproducible output
        
    Returns:
        PIL Image of the illustration
    """
    scene_desc = _describe_scene(narration)
    gen = SketchGenerator(width, height, seed)
    return gen.render_scene(scene_desc)


def _describe_scene(narration: str) -> dict:
    """Convert narration to scene description. Tries LLM first, then keyword matching."""
    # Try LLM
    result = _llm_describe(narration)
    if result:
        return result
    # Fall back to keyword parsing
    result = _keyword_describe(narration)
    if result:
        return result
    # Ultimate fallback
    return _generic_fallback(narration)


def _llm_describe(narration: str) -> dict | None:
    """Use LLM to convert narration to scene description."""
    system = "You are a visual artist. Given a narration sentence, you describe a beautiful full-color illustration. Output ONLY valid JSON."

    prompt = f"""Create a full-color illustration for: "{narration}"

Output JSON:
{{
  "bg": {{"type": "gradient|night|ocean|indoor|solid|sunset", "colors": [[R,G,B], ...], "horizon": 0.55, "ground_color": [R,G,B]}},
  "elements": [{{"type": "mountain|tree|cloud|water|human|house|hill|sun|moon|star|ship|building|text|label|arrow|x_mark|circle|rect|line|polygon", "x": 0-1, "y": 0-1, "scale": 0.5-2, "fill": [R,G,B], "text": "...", "font_size": 14-60, "tree_style": "round|pine|palm", "snow": true|false}}],
  "atmosphere": {{"particles": "stars|rain|snow|none", "fog": true|false}},
  "mood": "peaceful|dramatic|somber|hopeful|epic|mysterious"
}}

ELEMENT TYPES:
- mountain: peak, snow cap
- tree: round/pine/palm crown
- cloud: fluffy
- human: simplified figure
- house: with roof
- hill: rolling
- sun/moon/star: sky objects
- ship: sailing vessel
- building: with windows
- text: on-screen label
- label: text in rounded box
- arrow: directional pointer
- x_mark: red cross-out

Place 3-8 elements matching the narration. Choose colors that fit the mood.
Respond with ONLY the JSON."""

    try:
        raw = _generate(prompt, temperature=0.8, max_tokens=3000, system=system)
        raw = re.sub(r'^```(?:json)?\s*', '', raw.strip())
        raw = re.sub(r'\s*```$', '', raw)
        data = json.loads(raw)
        if "bg" in data or "elements" in data:
            return data
    except Exception:
        pass
    return None


def _keyword_describe(narration: str) -> dict | None:
    """Parse narration for keywords and build a relevant scene description."""
    n = narration.lower()

    # ── Detect scene type from keywords ──
    scenes = []

    # Ocean / Ship / Pirate
    if any(w in n for w in ("pirate", "ship", "sail", "ocean", "sea", "sailor", "boat", "navy", "harbor")):
        scene = {
            "bg": {"type": "ocean", "sky_color": [180, 210, 240], "horizon_color": [120, 170, 220],
                   "horizon": 0.5, "water_color": [30, 70, 150]},
            "elements": [
                {"type": "ship", "x": 0.5, "y": 0.55, "scale": 1.0, "fill": [80, 60, 40], "sail_color": [220, 210, 190]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "dramatic" if any(w in n for w in ("storm", "danger", "battle", "war", "attack")) else "peaceful"
        }
        if "pirate" in n:
            scene["elements"].append({"type": "human", "x": 0.35, "y": 0.5, "scale": 0.7, "fill": [100, 60, 40]})
        if any(w in n for w in ("storm", "dark", "thunder")):
            scene["atmosphere"]["fog"] = True
            scene["bg"]["sky_color"] = [100, 100, 120]
            scene["bg"]["horizon_color"] = [80, 80, 100]
        scenes.append(scene)

    # Mountain / Hill / Valley
    if any(w in n for w in ("mountain", "hill", "valley", "peak", "cliff", "snow", "alps")):
        scene = {
            "bg": {"type": "gradient", "colors": [[180, 200, 220], [100, 150, 200]], "horizon": 0.55, "ground_color": [50, 80, 40]},
            "elements": [
                {"type": "mountain", "x": 0.5, "y": 0.65, "width": 0.5, "height": 0.3, "fill": [100, 110, 140], "snow": "snow" in n or True},
                {"type": "tree", "x": 0.2, "y": 0.72, "scale": 0.7, "tree_style": "pine", "fill": [30, 80, 30]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "epic"
        }
        if any(w in n for w in ("sun", "sunrise", "dawn")):
            scene["elements"].append({"type": "sun", "x": 0.5, "y": 0.28, "radius": 25, "fill": [255, 200, 50]})
            scene["mood"] = "hopeful"
        scenes.append(scene)

    # Forest / Tree / Woods
    if any(w in n for w in ("forest", "tree", "jungle", "woods", "wilderness")):
        scene = {
            "bg": {"type": "gradient", "colors": [[100, 160, 100], [40, 80, 40]], "horizon": 0.7, "ground_color": [30, 60, 30]},
            "elements": [
                {"type": "tree", "x": 0.2, "y": 0.7, "scale": 0.8, "tree_style": "round", "fill": [40, 100, 40]},
                {"type": "tree", "x": 0.5, "y": 0.72, "scale": 1.0, "tree_style": "pine", "fill": [30, 80, 30]},
                {"type": "tree", "x": 0.8, "y": 0.7, "scale": 0.7, "tree_style": "round", "fill": [50, 110, 50]},
            ],
            "atmosphere": {"particles": "none", "fog": True},
            "mood": "mysterious"
        }
        scenes.append(scene)

    # Night / Dark / Moon
    if any(w in n for w in ("night", "dark", "moon", "star", "midnight", "evening")):
        scene = {
            "bg": {"type": "night", "colors": [[10, 8, 30], [30, 25, 60]], "horizon": 0.6, "ground_color": [20, 30, 20]},
            "elements": [
                {"type": "moon", "x": 0.7, "y": 0.2, "radius": 22},
            ],
            "atmosphere": {"particles": "stars", "fog": False, "star_count": 60},
            "mood": "mysterious"
        }
        if "star" in n:
            scene["atmosphere"]["star_count"] = 80
        scenes.append(scene)

    # Sunset / Dawn / Dusk
    if any(w in n for w in ("sunset", "dawn", "dusk", "sunrise")):
        scene = {
            "bg": {"type": "sunset", "colors": [[200, 100, 60], [180, 80, 80], [100, 50, 80], [40, 50, 30]]},
            "elements": [
                {"type": "sun", "x": 0.5, "y": 0.35, "radius": 28, "fill": [255, 200, 50]},
                {"type": "cloud", "x": 0.3, "y": 0.2, "scale": 0.5},
                {"type": "cloud", "x": 0.7, "y": 0.25, "scale": 0.4},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "peaceful"
        }
        scenes.append(scene)

    # House / Home / Village / City
    if any(w in n for w in ("house", "home", "village", "town", "city", "building", "castle")):
        scene = {
            "bg": {"type": "gradient", "colors": [[200, 210, 220], [160, 170, 190]], "horizon": 0.55, "ground_color": [60, 80, 50]},
            "elements": [
                {"type": "house", "x": 0.5, "y": 0.7, "scale": 1.0, "fill": [180, 150, 120], "roof_color": [150, 50, 40]},
                {"type": "tree", "x": 0.25, "y": 0.72, "scale": 0.7, "tree_style": "round", "fill": [50, 120, 50]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "peaceful"
        }
        if any(w in n for w in ("castle", "king", "queen")):
            scene["elements"] = [
                {"type": "building", "x": 0.5, "y": 0.65, "width": 0.15, "height": 0.3, "fill": [120, 100, 80], "window_color": [255, 200, 100]},
            ]
            scene["mood"] = "epic"
        scenes.append(scene)

    # Desert
    if any(w in n for w in ("desert", "sand", "dune", "cactus")):
        scene = {
            "bg": {"type": "gradient", "colors": [[240, 220, 180], [200, 180, 140]], "horizon": 0.55, "ground_color": [180, 160, 100]},
            "elements": [
                {"type": "sun", "x": 0.7, "y": 0.25, "radius": 28, "fill": [255, 220, 80]},
                {"type": "hill", "x": 0.3, "y": 0.7, "width": 0.4, "height": 0.08, "fill": [200, 180, 120]},
                {"type": "hill", "x": 0.7, "y": 0.72, "width": 0.35, "height": 0.06, "fill": [190, 170, 110]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "epic"
        }
        scenes.append(scene)

    # People / Human / Character focus — only if no other scene matched
    if not scenes and any(w in n for w in ("man", "woman", "person", "people", "child", "king", "queen", "soldier", "pirate")):
        color_map = {"pirate": [100, 60, 40], "king": [120, 40, 60], "queen": [140, 60, 100],
                     "soldier": [60, 80, 100], "child": [80, 120, 80]}
        c = [80, 60, 120]
        for k, v in color_map.items():
            if k in n: c = v; break
        scene = {
            "bg": {"type": "gradient", "colors": [[200, 210, 230], [140, 160, 200]], "horizon": 0.6, "ground_color": [60, 90, 50]},
            "elements": [
                {"type": "human", "x": 0.5, "y": 0.55, "scale": 1.2, "fill": c},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "peaceful"
        }
        scenes.append(scene)

    # Choose best match (first match by priority order)
    if scenes:
        scene = scenes[0]
        # Add text label from narration
        words = n.split()
        label = " ".join(words[:5]).upper()
        scene["elements"].append({"type": "text", "x": 0.5, "y": 0.08, "text": label, "font_size": 26, "fill": [40, 35, 30]})
        return scene

    return None


def _generic_fallback(narration: str) -> dict:
    """Ultimate fallback: generic landscape with narration text."""
    return {
        "bg": {"type": "gradient", "colors": [[200, 210, 230], [140, 160, 200]],
               "horizon": 0.6, "ground_color": [60, 90, 50]},
        "elements": [
            {"type": "hill", "x": 0.5, "y": 0.7, "width": 0.5, "height": 0.15, "fill": [60, 120, 60]},
            {"type": "tree", "x": 0.3, "y": 0.72, "scale": 0.8, "tree_style": "round", "fill": [50, 120, 50]},
            {"type": "cloud", "x": 0.5, "y": 0.2, "scale": 0.6},
            {"type": "text", "x": 0.5, "y": 0.08, "text": narration[:40].upper(), "font_size": 28, "fill": [40, 35, 30]},
        ],
        "atmosphere": {"particles": "none", "fog": False},
        "mood": "peaceful"
    }


def batch_sketch_from_narrations(narrations: list[str], width=W, height=H) -> list[Image.Image]:
    """Generate illustrations for multiple narrations."""
    return [sketch_from_narration(n, width, height) for n in narrations]


if __name__ == "__main__":
    import sys
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "A pirate ship on a stormy sea with dark clouds"
    print(f"Narration: {text}")
    img = sketch_from_narration(text)
    import os
    os.makedirs("output", exist_ok=True)
    path = "output/narration_sketch.png"
    img.save(path)
    print(f"Saved: {path} ({img.size})")
