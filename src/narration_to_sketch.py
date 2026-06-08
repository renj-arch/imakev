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


def _detect_visual_type(text: str) -> str:
    """Classify narration into visual type: story, diagram, flowchart, timeline, etc.
    
    Uses keyword matching to determine the best visual format for the narration.
    The engine uses this to route to the right renderer.
    """
    t = text.lower()
    
    # Non-story visual types with their keyword triggers
    types = [
        ("timeline",     ["timeline", "over millions of years", "over thousands", "generation after",
                          "over time", "evolved", "gradually", "era", "epoch",
                          "began", "eventually", "slowly", "century after century",
                          "year after year", "millennium", "over millions"]),
        ("flowchart",    ["leads to", "results in", "because of this", "chain reaction",
                          "step", "stage", "phase", "process", "sequence", "progression",
                          "first", "second", "third", "then", "next", "finally"]),
        ("cycle_diagram", ["cycle", "repeats", "circular", "loop", "recurring",
                          "comes back", "goes around", "rotates"]),
        ("venn_diagram",  ["both", "in common", "shared", "similarities", "differences",
                          "compare and contrast", "unlike", "on one hand", "on the other"]),
        ("diagram",       ["how it works", "structure", "anatomy", "labeled",
                          "diagram", "cross section", "layers"]),
        ("map",           ["across the world", "continent across", "region across",
                           "journey across", "migration across", "spread across"]),
        ("tree_diagram",  ["classification", "category", "divided into", "branches",
                          "subgroup", "hierarchy", "descends from", "evolved from"]),
        ("network_diagram", ["connected", "linked", "network", "relation", "connection",
                            "interconnected", "web of", "links to", "nodes"]),
    ]
    
    best_type, best_score = "story", 0
    for vtype, keywords in types:
        score = sum(1 for w in keywords if w in t)
        if score > best_score:
            best_type, best_score = vtype, score
    
    # Require at least 3 keyword matches for non-story types
    # (single accidental word matches like "network", "across", "cycle" should not override story)
    if best_type != "story" and best_score < 3:
        return "story"
    return best_type


def _describe_scene(narration: str, story_context: dict = None,
                     voice: str = None, camera: str = "medium") -> dict:
    """Convert narration to scene description using the engine's built-in intelligence.
    
    Pipeline:
      1. Scene type detection (story/diagram/timeline/etc.)
      2. Scene composition (creative → knowledge → dynamic → keyword → fallback)
      3. Visual treatment — ONE dominant treatment per segment (camera, particles, mood, etc.)
    """
    
    # Detect what kind of visual this narration needs
    visual_type = _detect_visual_type(narration)
    
    # Non-story types: route to auto_story's specialized generators (no treatment applied)
    if visual_type != "story":
        try:
            from auto_story import _infer_visuals_local
            result = _infer_visuals_local(narration, 1, 1)
            if result and "visual" in result:
                scene = result["visual"]
                scene["mood"] = result.get("mood", "peaceful")
                return scene
        except Exception:
            pass
    
    # Build scene through compositon pipeline
    scene = _compose_scene(narration, story_context, voice, camera)
    
    # Apply visual treatment — ONE dominant look per segment
    import random
    rng = random.Random(hash(narration) & 0xFFFFFFFF)
    from src.visual_treatments import select_treatment, apply_treatment
    treatment = select_treatment(narration, scene.get("mood", ""), rng)
    scene = apply_treatment(scene, treatment, rng)
    
    return scene


def _compose_scene(narration: str, story_context: dict = None,
                    voice: str = None, camera: str = "medium") -> dict:
    """Scene composition pipeline (no treatment applied here)."""
    
    # PRIMARY: Creative scene — poetic/reflective/philosophical text
    from src.creative_scenes import match_creative_scene
    result = match_creative_scene(narration)
    if result:
        return result
    
    # SECONDARY: Knowledge base — curated scene templates for known topics.
    from src.scene_knowledge import semantic_scene
    result = semantic_scene(narration, threshold=0.3)
    if result:
        return result
    
    # TERTIARY: Dynamic scene composer — context-aware
    from src.dynamic_scene import compose_context_scene
    result = compose_context_scene(narration, story_context=story_context, voice=voice, camera=camera)
    if result:
        return result
    
    # QUATERNARY: Keyword parsing (fast path for common topics)
    result = _keyword_describe(narration)
    if result:
        return result
    
    # ULTIMATE FALLBACK
    return _generic_fallback(narration)


def _llm_describe(narration: str) -> dict | None:
    """LLM scene generation (disabled — no external API dependency).
    
    The engine is fully self-contained. Intelligence comes from the
    concept extractor + dynamic scene composer, not external APIs.
    """
    return None


def _keyword_describe(narration: str) -> dict | None:
    """Parse narration for keywords and build a relevant scene description."""
    n = narration.lower()

    # ── Detect scene type from keywords ──
    scenes = []

    # ═══════════════════════════════════════════════════════════════
    #  ANTARCTICA / FROZEN CONTINENT (checked first — 11 scenes)
    # ═══════════════════════════════════════════════════════════════

    # Opening Hook — Antarctica with forests (ice meets greenery)
    if any(w in n for w in ("antarctica", "antarctic", "south pole", "frozen continent",
                             "endless ice", "world of ice")) and \
       any(w in n for w in ("forest", "trees", "green", "plants", "forests", "rivers flow")):
        scene = {
            "bg": {"type": "gradient", "colors": [[200, 220, 240], [160, 200, 230]], "horizon": 0.55, "ground_color": [80, 130, 80]},
            "elements": [
                {"type": "tree", "x": 0.2, "y": 0.68, "scale": 3.5, "tree_style": "round", "fill": [40, 110, 40]},
                {"type": "tree", "x": 0.5, "y": 0.7, "scale": 4.5, "tree_style": "pine", "fill": [35, 95, 35]},
                {"type": "tree", "x": 0.8, "y": 0.69, "scale": 3.75, "tree_style": "round", "fill": [45, 115, 45]},
                {"type": "glacier", "x": 0.5, "y": 0.4, "scale": 2.5, "fill": [200, 220, 240]},
                {"type": "water", "x": 0.05, "y": 0.75, "width": 0.9, "height": 0.08, "fill": [60, 130, 200]},
                {"type": "bird", "x": 0.4, "y": 0.25, "scale": 2.0},
                {"type": "bird", "x": 0.6, "y": 0.28, "scale": 1.75},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "hopeful"
        }
        if any(w in n for w in ("impossible", "contradiction", "strange")):
            scene["mood"] = "mysterious"
        scenes.append(scene)

    # Ch 1: Ancient Antarctica — 100 million years ago, warm, dinosaurs, forests, no ice
    if any(w in n for w in ("100 million", "million years ago", "100 million years",
                             "warm climate", "dinosaur", "dinosaurs", "warmer",
                             "not buried", "vast forests", "ancient trees")):
        scene = {
            "bg": {"type": "gradient", "colors": [[120, 190, 230], [90, 150, 200]], "horizon": 0.6, "ground_color": [50, 100, 50]},
            "elements": [
                {"type": "tree", "x": 0.2, "y": 0.7, "scale": 4.0, "tree_style": "round", "fill": [50, 130, 50]},
                {"type": "tree", "x": 0.5, "y": 0.72, "scale": 5.0, "tree_style": "round", "fill": [40, 110, 40]},
                {"type": "tree", "x": 0.8, "y": 0.71, "scale": 4.25, "tree_style": "pine", "fill": [35, 100, 35]},
                {"type": "dinosaur", "x": 0.5, "y": 0.6, "scale": 2.5, "fill": [80, 110, 70]},
                {"type": "water", "x": 0.05, "y": 0.78, "width": 0.9, "height": 0.08, "fill": [40, 130, 190]},
                {"type": "sun", "x": 0.7, "y": 0.15, "radius": 22, "fill": [255, 230, 80]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "epic"
        }
        scenes.append(scene)

    # Ch 2: Endless Sunlight — 24-hour daylight, midnight sun
    if any(w in n for w in ("endless sunlight", "constant daylight", "months of sunlight",
                             "24-hour", "midnight sun", "months of darkness",
                             "unusual seasons", "long summer", "summer days",
                             "polar day", "polar night", "sunlight in summer",
                             "months of")):
        scene = {
            "bg": {"type": "sunset", "colors": [[255, 220, 120], [200, 180, 140], [150, 150, 200], [80, 100, 180]], "horizon": 0.5, "ground_color": [50, 80, 40]},
            "elements": [
                {"type": "sun", "x": 0.5, "y": 0.05, "radius": 35, "fill": [255, 240, 150]},
                {"type": "tree", "x": 0.25, "y": 0.7, "scale": 3.5, "tree_style": "round", "fill": [50, 130, 50]},
                {"type": "tree", "x": 0.75, "y": 0.72, "scale": 4.0, "tree_style": "pine", "fill": [40, 110, 40]},
                {"type": "hill", "x": 0.5, "y": 0.75, "width": 0.7, "height": 0.12, "fill": [60, 120, 60]},
                {"type": "text", "x": 0.5, "y": 0.12, "text": "ENDLESS DAY", "font_size": 28, "fill": [200, 180, 60]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "hopeful"
        }
        if any(w in n for w in ("darkness", "night", "winter")):
            scene["bg"] = {"type": "night", "colors": [[10, 8, 30], [30, 25, 60]], "horizon": 0.55, "ground_color": [20, 30, 20]}
            scene["elements"] = [{"type": "moon", "x": 0.7, "y": 0.2, "radius": 14},
                                 {"type": "text", "x": 0.5, "y": 0.12, "text": "MONTHS OF DARKNESS", "font_size": 26, "fill": [150, 150, 200]}]
            scene["atmosphere"] = {"particles": "stars", "fog": False, "star_count": 80}
            scene["mood"] = "mysterious"
        scenes.append(scene)

    # Ch 3: Lost Forests — fossilized wood, leaves, pollen, roots beneath ice
    if any(w in n for w in ("fossilized", "fossils beneath", "pollen", "fossilized wood",
                             "fossil leaves", "ancient roots", "fossil roots",
                             "fossils tell", "entire ecosystem", "fossils beneath ice")):
        scene = {
            "bg": {"type": "snow", "colors": [[200, 210, 220], [160, 180, 200]], "horizon": 0.5, "ground_color": [180, 190, 200]},
            "elements": [
                {"type": "iceberg", "x": 0.25, "y": 0.4, "scale": 2.5, "fill": [210, 225, 245]},
                {"type": "skeleton", "x": 0.5, "y": 0.7, "scale": 2.5, "fill": [200, 180, 150]},
                {"type": "tree", "x": 0.5, "y": 0.7, "scale": 2.0, "tree_style": "round", "fill": [80, 60, 40]},
                {"type": "text", "x": 0.5, "y": 0.1, "text": "LOST FORESTS", "font_size": 26, "fill": [180, 190, 200]},
            ],
            "atmosphere": {"particles": "snow", "fog": True},
            "mood": "mysterious"
        }
        scenes.append(scene)

    # Ch 4: Moving Planet — tectonic plates, continents drifting
    if any(w in n for w in ("tectonic", "continents drift", "continents moving",
                             "plates move", "plates drift", "isolated position",
                             "south pole position", "moved south",
                             "giant tectonic", "slowly drift",
                             "centimeters each year", "moved into position",
                             "separated from")):
        scene = {
            "bg": {"type": "space", "colors": [[2, 2, 15], [5, 3, 25]], "horizon": 0.0},
            "elements": [
                {"type": "globe", "x": 0.5, "y": 0.45, "scale": 5.0, "fill": [80, 140, 200]},
                {"type": "arrow", "x": 0.55, "y": 0.35, "x2": 0.6, "y2": 0.5, "fill": [255, 200, 50]},
                {"type": "text", "x": 0.5, "y": 0.08, "text": "CONTINENTAL DRIFT", "font_size": 24, "fill": [200, 200, 220]},
                {"type": "star", "x": 0.2, "y": 0.2, "radius": 2},
                {"type": "star", "x": 0.8, "y": 0.15, "radius": 1.5},
                {"type": "star", "x": 0.3, "y": 0.75, "radius": 2},
                {"type": "star", "x": 0.7, "y": 0.8, "radius": 1.5},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "epic"
        }
        scenes.append(scene)

    # Ch 5: Ocean Barrier — Circumpolar Current, cold water moat
    if any(w in n for w in ("ocean current", "circumpolar", "giant moat",
                             "cold water", "separated antarctica", "powerful current",
                             "isolated antarctica", "current around",
                             "ocean barrier", "moat of cold", "antarctic circumpolar",
                             "heat stopped", "warmer oceans")):
        scene = {
            "bg": {"type": "ocean", "sky_color": [160, 190, 220], "horizon_color": [100, 150, 200],
                   "horizon": 0.5, "water_color": [20, 60, 130]},
            "elements": [
                {"type": "iceberg", "x": 0.3, "y": 0.45, "scale": 2.5, "fill": [210, 225, 245]},
                {"type": "iceberg", "x": 0.7, "y": 0.5, "scale": 2.0, "fill": [200, 220, 240]},
                {"type": "arrow", "x": 0.2, "y": 0.5, "x2": 0.8, "y2": 0.5, "fill": [100, 180, 255]},
                {"type": "text", "x": 0.5, "y": 0.12, "text": "CIRCUMPOLAR CURRENT", "font_size": 22, "fill": [180, 210, 240]},
            ],
            "atmosphere": {"particles": "none", "fog": True},
            "mood": "dramatic"
        }
        if any(w in n for w in ("moat", "isolated", "barrier")):
            scene["mood"] = "somber"
        scenes.append(scene)

    # Ch 6: Long Freeze — temperatures dropping, snow, glaciers expanding
    if any(w in n for w in ("long freeze", "temperatures dropped", "temperatures falling",
                             "temperatures slowly", "cooling", "snow lasted",
                             "glaciers expanded",
                             "cooling wasn't instant", "retreating",
                             "forests began retreating", "year after year",
                             "cold crept", "ice advanced")):
        scene = {
            "bg": {"type": "snow", "colors": [[200, 210, 220], [160, 180, 200]], "horizon": 0.5, "ground_color": [180, 190, 200]},
            "elements": [
                {"type": "glacier", "x": 0.35, "y": 0.45, "scale": 3.0, "fill": [190, 210, 230]},
                {"type": "glacier", "x": 0.65, "y": 0.5, "scale": 2.5, "fill": [200, 215, 235]},
                {"type": "tree", "x": 0.2, "y": 0.7, "scale": 2.25, "tree_style": "pine", "fill": [30, 70, 30]},
                {"type": "tree", "x": 0.7, "y": 0.72, "scale": 1.75, "tree_style": "pine", "fill": [25, 60, 25]},
                {"type": "text", "x": 0.5, "y": 0.1, "text": "THE LONG FREEZE", "font_size": 26, "fill": [160, 180, 200]},
            ],
            "atmosphere": {"particles": "snow", "fog": True},
            "mood": "somber"
        }
        scenes.append(scene)

    # Ch 7: Ice Takes Control — ice sheets spreading, reflection, cooling acceleration
    if any(w in n for w in ("ice takes control", "ice formed", "ice sheets spread",
                             "sunlight reflected", "cooling accelerated",
                             "trees disappeared", "rivers froze",
                             "green world faded", "expanding glaciers",
                             "less heat", "ice across", "glaciers took over")):
        scene = {
            "bg": {"type": "snow", "colors": [[190, 200, 215], [150, 170, 195]], "horizon": 0.5, "ground_color": [170, 185, 200]},
            "elements": [
                {"type": "glacier", "x": 0.5, "y": 0.4, "scale": 4.0, "fill": [190, 210, 235]},
                {"type": "glacier", "x": 0.2, "y": 0.55, "scale": 2.5, "fill": [200, 215, 240]},
                {"type": "glacier", "x": 0.8, "y": 0.5, "scale": 2.75, "fill": [195, 210, 230]},
                {"type": "sun", "x": 0.5, "y": 0.18, "radius": 20, "fill": [255, 250, 220]},
            ],
            "atmosphere": {"particles": "snow", "fog": True},
            "mood": "dramatic"
        }
        scenes.append(scene)

    # Ch 8: Last Forest — forests gone, frozen deserts
    if any(w in n for w in ("last forest", "forests were gone", "forests gone",
                             "suddenly died", "frozen desert",
                             "green valleys became", "ecosystems vanished",
                             "climate no longer", "forest disappeared",
                             "last trees", "final forest")):
        scene = {
            "bg": {"type": "snow", "colors": [[180, 190, 200], [150, 170, 190]], "horizon": 0.5, "ground_color": [160, 175, 190]},
            "elements": [
                {"type": "iceberg", "x": 0.3, "y": 0.45, "scale": 3.0, "fill": [200, 215, 235]},
                {"type": "tree", "x": 0.7, "y": 0.7, "scale": 2.0, "tree_style": "pine", "fill": [20, 50, 20]},
                {"type": "x_mark", "x": 0.7, "y": 0.7, "scale": 2.0, "fill": [200, 100, 80]},
                {"type": "text", "x": 0.5, "y": 0.1, "text": "THE LAST FOREST", "font_size": 26, "fill": [150, 170, 190]},
            ],
            "atmosphere": {"particles": "snow", "fog": True},
            "mood": "somber"
        }
        scenes.append(scene)

    # Ch 9: Modern Antarctica / Ending — ice sheet, hidden fossils, lost green world
    if any(w in n for w in ("largest ice sheet", "kilometers thick",
                             "beneath that ice", "hidden beneath",
                             "clues to another world", "ancient roots",
                             "continent that once", "evidence of a continent",
                             "fossil forest", "fossil forests",
                             "lost green world", "hidden beneath the ice",
                             "beneath antarctica", "memory of a lost",
                             "continent of change", "planet of change")):
        scene = {
            "bg": {"type": "snow", "colors": [[200, 210, 225], [170, 190, 210]], "horizon": 0.5, "ground_color": [185, 200, 215]},
            "elements": [
                {"type": "glacier", "x": 0.25, "y": 0.4, "scale": 2.75, "fill": [200, 220, 240]},
                {"type": "glacier", "x": 0.75, "y": 0.45, "scale": 2.5, "fill": [210, 225, 245]},
                {"type": "skeleton", "x": 0.5, "y": 0.72, "scale": 2.25, "fill": [200, 180, 150]},
                {"type": "tree", "x": 0.3, "y": 0.7, "scale": 1.75, "tree_style": "round", "fill": [60, 40, 30]},
                {"type": "tree", "x": 0.7, "y": 0.72, "scale": 1.5, "tree_style": "pine", "fill": [50, 35, 25]},
                {"type": "text", "x": 0.5, "y": 0.08, "text": "BENEATH THE ICE", "font_size": 24, "fill": [180, 200, 220]},
            ],
            "atmosphere": {"particles": "snow", "fog": True},
            "mood": "mysterious"
        }
        if any(w in n for w in ("memory", "hidden beneath", "lost green", "beneath antarctica",
                                 "world of change", "planet of change")):
            scene["mood"] = "hopeful"
        scenes.append(scene)

    # Antarctica general catch-all (only if no specific section matched above)
    if not scenes and any(w in n for w in ("antarctica", "antarctic", "south pole", "ice sheet",
                                            "continent of ice", "frozen continent", 
                                            "wilderness of ice", "endless white")):
        scene = {
            "bg": {"type": "snow", "colors": [[220, 230, 240], [180, 200, 220]], "horizon": 0.5, "ground_color": [200, 210, 220]},
            "elements": [
                {"type": "glacier", "x": 0.3, "y": 0.5, "scale": 3.5, "fill": [200, 220, 240]},
                {"type": "glacier", "x": 0.7, "y": 0.55, "scale": 2.5, "fill": [210, 225, 245]},
                {"type": "cloud", "x": 0.5, "y": 0.2, "scale": 3.0, "fill": [230, 235, 240]},
            ],
            "atmosphere": {"particles": "snow", "fog": True},
            "mood": "mysterious"
        }
        if any(w in n for w in ("memory", "hidden", "beneath", "under", "clues", "evidence", "fossil")):
            scene["elements"].append({"type": "skeleton", "x": 0.5, "y": 0.72, "scale": 2.0, "fill": [220, 200, 180]})
            scene["mood"] = "mysterious"
        scenes.append(scene)

    # ═══════════════════════════════════════════════════════════════
    #  SPACE / COSMOS / BLACK HOLE
    # ═══════════════════════════════════════════════════════════════
    if any(w in n for w in ("black hole", "cosmos", "universe", "solar system",
                             "planet", "galaxy", "nebula", "asteroid",
                             "star collapses", "gravitational", "space",
                             "astronaut", "spaceship", "rocket", "orbit",
                             "jupiter", "saturn", "mars", "venus", "mercury",
                             "alien", "extraterrestrial", "constellation",
                             "big bang", "dark matter", "supernova")):
        scene = {
            "bg": {"type": "gradient", "colors": [[2, 2, 15], [10, 5, 30]], "horizon": 0.0},
            "elements": [
                {"type": "star", "x": 0.2, "y": 0.15, "radius": 2.5, "fill": [255, 255, 200]},
                {"type": "star", "x": 0.7, "y": 0.1, "radius": 1.5, "fill": [200, 200, 255]},
                {"type": "star", "x": 0.8, "y": 0.3, "radius": 2, "fill": [255, 200, 200]},
                {"type": "star", "x": 0.15, "y": 0.5, "radius": 1.5, "fill": [200, 255, 200]},
                {"type": "star", "x": 0.9, "y": 0.6, "radius": 2, "fill": [255, 255, 255]},
                {"type": "astronaut", "x": 0.5, "y": 0.4, "scale": 3.5, "fill": [220, 220, 240]},
            ],
            "atmosphere": {"particles": "stars", "star_count": 60, "fog": False},
            "mood": "epic"
        }
        if any(w in n for w in ("black hole", "collapses", "gravitational", "singularity",
                                 "event horizon", "spaghettification")):
            scene["elements"] = [
                {"type": "circle", "x": 0.5, "y": 0.4, "radius": 60, "fill": [0, 0, 0]},
                {"type": "circle", "x": 0.5, "y": 0.4, "radius": 80, "fill": [80, 30, 80, 40], "stroke": [255, 100, 200], "stroke_width": 3},
                {"type": "circle", "x": 0.5, "y": 0.4, "radius": 100, "fill": [40, 10, 50, 20], "stroke": [150, 80, 200], "stroke_width": 1},
                {"type": "star", "x": 0.2, "y": 0.15, "radius": 1.5, "fill": [255, 255, 200]},
                {"type": "star", "x": 0.7, "y": 0.1, "radius": 1, "fill": [200, 200, 255]},
                {"type": "star", "x": 0.8, "y": 0.3, "radius": 1.5, "fill": [255, 200, 200]},
                {"type": "text", "x": 0.5, "y": 0.08, "text": "BLACK HOLE", "font_size": 28, "fill": [200, 100, 200]},
            ]
            scene["mood"] = "mysterious"
        if any(w in n for w in ("astronaut", "spaceship", "rocket", "alien")):
            scene["mood"] = "hopeful"
        if any(w in n for w in ("solar system", "planet orbit", "jupiter", "saturn",
                                 "mercury", "venus", "mars", "eight planets")):
            scene["elements"] = [
                {"type": "sun", "x": 0.5, "y": 0.08, "radius": 18, "fill": [255, 230, 80]},
                {"type": "circle", "x": 0.5, "y": 0.35, "radius": 50, "fill": None, "stroke": [100, 100, 150, 40], "stroke_width": 1},
                {"type": "circle", "x": 0.5, "y": 0.35, "radius": 75, "fill": None, "stroke": [100, 100, 150, 30], "stroke_width": 1},
                {"type": "circle", "x": 0.5, "y": 0.35, "radius": 100, "fill": None, "stroke": [100, 100, 150, 25], "stroke_width": 1},
                {"type": "star", "x": 0.5, "y": 0.35, "radius": 4, "fill": [200, 100, 50]},
                {"type": "star", "x": 0.55, "y": 0.32, "radius": 3, "fill": [180, 120, 60]},
                {"type": "star", "x": 0.48, "y": 0.3, "radius": 2.5, "fill": [100, 150, 200]},
                {"type": "star", "x": 0.6, "y": 0.38, "radius": 2, "fill": [200, 180, 100]},
                {"type": "text", "x": 0.5, "y": 0.75, "text": "SOLAR SYSTEM", "font_size": 24, "fill": [200, 200, 220]},
            ]
            scene["mood"] = "hopeful"
        scenes.append(scene)

    # ═══════════════════════════════════════════════════════════════
    #  TECHNOLOGY / COMPUTER / INTERNET
    # ═══════════════════════════════════════════════════════════════
    if any(w in n for w in ("internet", "computer", "technology", "digital",
                             "chip", "circuit", "transistor", "silicon",
                             "processor", "server", "data", "algorithm",
                             "program", "software", "code", "binary",
                             "robot", "robotics", "automation", "AI",
                             "artificial intelligence", "machine learning",
                             "neural network", "computer processes",
                             "fiber optic", "billion devices",
                             "information travels", "world wide web",
                             "cyber", "quantum computer")):
        scene = {
            "bg": {"type": "gradient", "colors": [[10, 15, 30], [20, 30, 50]], "horizon": 0.6, "ground_color": [15, 20, 40]},
            "elements": [
                {"type": "rect", "x": 0.2, "y": 0.35, "width": 0.25, "height": 0.3, "fill": [30, 40, 70, 180], "stroke": [60, 120, 200], "stroke_width": 2},
                {"type": "rect", "x": 0.55, "y": 0.4, "width": 0.25, "height": 0.2, "fill": [30, 40, 70, 180], "stroke": [60, 120, 200], "stroke_width": 2},
                {"type": "line", "x1": 0.45, "y1": 0.5, "x2": 0.55, "y2": 0.5, "fill": [60, 200, 120], "stroke_width": 2},
                {"type": "line", "x1": 0.2, "y1": 0.55, "x2": 0.45, "y2": 0.55, "fill": [60, 180, 200], "stroke_width": 2},
                {"type": "line", "x1": 0.55, "y1": 0.45, "x2": 0.8, "y2": 0.45, "fill": [60, 180, 200], "stroke_width": 2},
                {"type": "circle", "x": 0.45, "y": 0.5, "radius": 3, "fill": [100, 255, 150]},
                {"type": "circle", "x": 0.55, "y": 0.5, "radius": 3, "fill": [100, 255, 150]},
                {"type": "circle", "x": 0.55, "y": 0.45, "radius": 3, "fill": [100, 200, 255]},
                {"type": "text", "x": 0.5, "y": 0.12, "text": "TECHNOLOGY", "font_size": 24, "fill": [100, 200, 230]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "hopeful"
        }
        if any(w in n for w in ("robot", "robotics", "automation", "AI",
                                 "artificial intelligence", "machine")):
            scene["elements"] = [
                {"type": "human", "x": 0.35, "y": 0.5, "scale": 4.5, "fill": [150, 150, 160]},
                {"type": "gear", "x": 0.65, "y": 0.45, "scale": 5.0, "fill": [180, 180, 200]},
                {"type": "circle", "x": 0.35, "y": 0.35, "radius": 4, "fill": [100, 200, 255]},
                {"type": "circle", "x": 0.35, "y": 0.35, "radius": 2, "fill": [255, 255, 255]},
                {"type": "text", "x": 0.5, "y": 0.08, "text": "ARTIFICIAL INTELLIGENCE", "font_size": 22, "fill": [100, 200, 230]},
            ]
        if any(w in n for w in ("binary", "code", "program", "software", "algorithm")):
            scene["elements"].append({"type": "text", "x": 0.5, "y": 0.72, "text": "01001  10110  01011", "font_size": 18, "fill": [60, 200, 120]})
        scenes.append(scene)

    # ═══════════════════════════════════════════════════════════════
    #  HUMAN BODY / HEART / BRAIN / ANATOMY
    # ═══════════════════════════════════════════════════════════════
    if any(w in n for w in ("human heart", "human brain", "human body",
                             "blood vessel", "blood cells", "heart beats",
                             "pumping blood", "heart pumps", "86 billion",
                             "neurons", "nerve", "brain contains",
                             "brain has", "brain uses", "brain weighs",
                             "human anatomy", "organs", "skeleton",
                             "muscle", "lungs", "kidney", "liver",
                             "dna", "gene", "chromosome", "cell",
                             "genetic", "blueprint of life",
                             "immune system", "digestive",
                             "neural", "synapse", "cortex")):
        scene = {
            "bg": {"type": "indoor", "colors": [[235, 230, 220], [220, 215, 205]], "horizon": 0.6, "ground_color": [200, 195, 185]},
            "elements": [
                {"type": "heart", "x": 0.3, "y": 0.4, "scale": 4.5, "fill": [200, 60, 60]},
                {"type": "dna", "x": 0.7, "y": 0.45, "width": 80, "height": 120, "fill": [60, 120, 200]},
                {"type": "text", "x": 0.5, "y": 0.08, "text": "HUMAN BODY", "font_size": 28, "fill": [60, 60, 80]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "peaceful"
        }
        if any(w in n for w in ("brain", "neuron", "neural", "86 billion",
                                 "cortex", "synapse", "cerebrum")):
            scene["elements"] = [
                {"type": "ellipse", "x": 0.3, "y": 0.4, "width": 120, "height": 90, "fill": [200, 180, 200]},
                {"type": "ellipse", "x": 0.6, "y": 0.4, "width": 120, "height": 90, "fill": [190, 170, 190]},
                {"type": "line", "x1": 0.3, "y1": 0.4, "x2": 0.6, "y2": 0.4, "fill": [100, 100, 100], "stroke_width": 2},
                {"type": "line", "x1": 0.3, "y1": 0.4, "x2": 0.25, "y2": 0.65, "fill": [160, 140, 160], "stroke_width": 1},
                {"type": "line", "x1": 0.6, "y1": 0.4, "x2": 0.65, "y2": 0.65, "fill": [160, 140, 160], "stroke_width": 1},
                {"type": "circle", "x": 0.3, "y": 0.4, "radius": 2, "fill": [100, 100, 100]},
                {"type": "circle", "x": 0.6, "y": 0.4, "radius": 2, "fill": [100, 100, 100]},
                {"type": "text", "x": 0.5, "y": 0.08, "text": "THE HUMAN BRAIN", "font_size": 28, "fill": [60, 60, 80]},
            ]
        if any(w in n for w in ("heart", "pumping blood", "heart beats",
                                 "blood vessel", "heart pumps")):
            scene["elements"] = [
                {"type": "heart", "x": 0.5, "y": 0.4, "scale": 6.5, "fill": [220, 50, 50]},
                {"type": "line", "x1": 0.35, "y1": 0.45, "x2": 0.2, "y2": 0.6, "fill": [200, 50, 50], "stroke_width": 3},
                {"type": "line", "x1": 0.65, "y1": 0.45, "x2": 0.8, "y2": 0.6, "fill": [50, 100, 200], "stroke_width": 3},
                {"type": "circle", "x": 0.2, "y": 0.6, "radius": 3, "fill": [220, 60, 60]},
                {"type": "circle", "x": 0.8, "y": 0.6, "radius": 3, "fill": [60, 100, 200]},
                {"type": "text", "x": 0.5, "y": 0.08, "text": "THE HUMAN HEART", "font_size": 28, "fill": [60, 60, 80]},
            ]
        if any(w in n for w in ("dna", "gene", "genetic", "chromosome",
                                 "blueprint of life", "cell")):
            scene["elements"] = [
                {"type": "dna", "x": 0.3, "y": 0.5, "width": 100, "height": 160, "fill": [60, 140, 220]},
                {"type": "dna", "x": 0.7, "y": 0.5, "width": 100, "height": 160, "fill": [60, 180, 120]},
                {"type": "circle", "x": 0.3, "y": 0.3, "radius": 5, "fill": [200, 200, 60]},
                {"type": "circle", "x": 0.7, "y": 0.3, "radius": 5, "fill": [60, 200, 200]},
                {"type": "text", "x": 0.5, "y": 0.08, "text": "DNA - BLUEPRINT OF LIFE", "font_size": 24, "fill": [60, 60, 80]},
            ]
        scenes.append(scene)

    # ═══════════════════════════════════════════════════════════════
    #  WEATHER / STORM / VOLCANO / HURRICANE
    # ═══════════════════════════════════════════════════════════════
    if any(w in n for w in ("hurricane", "tornado", "volcano", "earthquake",
                             "storm", "thunderstorm", "lightning",
                             "thunder", "flood", "tsunami",
                             "molten lava", "volcanic", "eruption",
                             "erupts with", "lava flows", "volcanic ash",
                             "devastating wind", "storm surge",
                             "ocean waters", "warm waters",
                             "whirlwind", "cyclone", "typhoon",
                             "avalanche", "landslide",
                             "seismic", "tremor", "tectonic shift")):
        scene = {
            "bg": {"type": "gradient", "colors": [[100, 100, 120], [60, 60, 80]], "horizon": 0.5, "ground_color": [40, 40, 50]},
            "elements": [
                {"type": "cloud", "x": 0.25, "y": 0.2, "scale": 4.5, "fill": [60, 60, 80]},
                {"type": "cloud", "x": 0.75, "y": 0.15, "scale": 4.0, "fill": [50, 50, 70]},
                {"type": "line", "x1": 0.3, "y1": 0.2, "x2": 0.3, "y2": 0.45, "fill": [255, 220, 50], "stroke_width": 4},
                {"type": "line", "x1": 0.7, "y1": 0.15, "x2": 0.7, "y2": 0.35, "fill": [255, 220, 50], "stroke_width": 3},
                {"type": "line", "x1": 0.28, "y1": 0.35, "x2": 0.32, "y2": 0.35, "fill": [255, 220, 50], "stroke_width": 2},
                {"type": "line", "x1": 0.68, "y1": 0.25, "x2": 0.72, "y2": 0.25, "fill": [255, 220, 50], "stroke_width": 2},
                {"type": "text", "x": 0.5, "y": 0.08, "text": "NATURE'S POWER", "font_size": 26, "fill": [200, 200, 220]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "dramatic"
        }
        if any(w in n for w in ("volcano", "volcanic", "eruption", "molten lava",
                                 "lava flows", "volcanic ash", "erupts with")):
            scene["bg"] = {"type": "gradient", "colors": [[100, 70, 50], [60, 40, 30]], "horizon": 0.55, "ground_color": [40, 25, 20]}
            scene["elements"] = [
                {"type": "mountain", "x": 0.5, "y": 0.55, "width": 0.5, "height": 0.35, "fill": [80, 50, 35]},
                {"type": "circle", "x": 0.5, "y": 0.25, "radius": 12, "fill": [255, 150, 30]},
                {"type": "circle", "x": 0.5, "y": 0.25, "radius": 8, "fill": [255, 200, 50]},
                {"type": "fire", "x": 0.5, "y": 0.55, "scale": 5.0, "fill": [255, 100, 20]},
                {"type": "text", "x": 0.5, "y": 0.08, "text": "VOLCANIC ERUPTION", "font_size": 26, "fill": [255, 180, 100]},
            ]
        if any(w in n for w in ("hurricane", "tornado", "cyclone", "typhoon",
                                 "whirlwind", "storm surge")):
            scene["elements"] = [
                {"type": "ellipse", "x": 0.5, "y": 0.4, "width": 160, "height": 100, "fill": [80, 80, 100, 40], "stroke": [150, 150, 180], "stroke_width": 2},
                {"type": "ellipse", "x": 0.5, "y": 0.4, "width": 100, "height": 60, "fill": [60, 60, 80, 60], "stroke": [200, 200, 220], "stroke_width": 1},
                {"type": "ellipse", "x": 0.5, "y": 0.4, "width": 40, "height": 25, "fill": [200, 200, 220]},
                {"type": "cloud", "x": 0.3, "y": 0.15, "scale": 3.5, "fill": [50, 50, 70]},
                {"type": "cloud", "x": 0.7, "y": 0.18, "scale": 3.0, "fill": [50, 50, 70]},
                {"type": "text", "x": 0.5, "y": 0.08, "text": "HURRICANE", "font_size": 26, "fill": [200, 200, 220]},
            ]
        scenes.append(scene)

    # ═══════════════════════════════════════════════════════════════
    #  HISTORY / ANCIENT CIVILIZATIONS
    # ═══════════════════════════════════════════════════════════════
    if any(w in n for w in ("ancient", "civilization", "empire", "pharaoh",
                             "pyramid", "roman", "roman empire", "greek",
                             "greece", "egypt", "egyptian",
                             "medieval", "kingdom", "caesar",
                             "colosseum", "temple", "monument",
                             "archaeology", "archaeologist",
                             "industrial revolution", "steam engine",
                             "factory", "industrial", "manufacturing",
                             "renaissance", "colony", "colonial",
                             "mongol", "viking", "celtic",
                             "byzantine", "ottoman", "persian")):
        scene = {
            "bg": {"type": "gradient", "colors": [[200, 180, 150], [160, 140, 110]], "horizon": 0.5, "ground_color": [140, 120, 90]},
            "elements": [
                {"type": "building", "x": 0.3, "y": 0.45, "scale": 3.5, "fill": [180, 160, 130]},
                {"type": "building", "x": 0.7, "y": 0.48, "scale": 2.5, "fill": [170, 150, 120]},
                {"type": "sun", "x": 0.8, "y": 0.12, "radius": 18, "fill": [255, 220, 120]},
                {"type": "text", "x": 0.5, "y": 0.08, "text": "ANCIENT WORLD", "font_size": 26, "fill": [80, 60, 40]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "epic"
        }
        if any(w in n for w in ("egypt", "egyptian", "pharaoh", "pyramid")):
            scene["bg"] = {"type": "desert", "colors": [[220, 190, 140], [190, 160, 110]], "horizon": 0.5, "ground_color": [180, 150, 100]}
            scene["elements"] = [
                {"type": "polygon", "points": [0.3, 0.5, 0.4, 0.2, 0.5, 0.5], "fill": [180, 140, 80]},
                {"type": "polygon", "points": [0.55, 0.55, 0.65, 0.25, 0.75, 0.55], "fill": [170, 130, 70]},
                {"type": "sun", "x": 0.8, "y": 0.12, "radius": 20, "fill": [255, 220, 80]},
                {"type": "text", "x": 0.5, "y": 0.08, "text": "ANCIENT EGYPT", "font_size": 26, "fill": [120, 90, 50]},
            ]
        if any(w in n for w in ("roman", "roman empire", "caesar", "colosseum")):
            scene["bg"] = {"type": "gradient", "colors": [[210, 190, 160], [170, 150, 120]], "horizon": 0.5, "ground_color": [150, 130, 100]}
            scene["elements"] = [
                {"type": "building", "x": 0.25, "y": 0.4, "scale": 4.0, "fill": [190, 170, 140]},
                {"type": "building", "x": 0.55, "y": 0.42, "scale": 3.0, "fill": [180, 160, 130]},
                {"type": "building", "x": 0.75, "y": 0.45, "scale": 2.5, "fill": [170, 150, 120]},
                {"type": "flag", "x": 0.3, "y": 0.15, "scale": 3.0, "fill": [200, 50, 50]},
                {"type": "text", "x": 0.5, "y": 0.08, "text": "ROMAN EMPIRE", "font_size": 26, "fill": [120, 90, 60]},
            ]
        if any(w in n for w in ("industrial revolution", "steam engine", "factory", "industrial")):
            scene["bg"] = {"type": "gradient", "colors": [[150, 140, 130], [100, 90, 80]], "horizon": 0.5, "ground_color": [80, 70, 60]}
            scene["elements"] = [
                {"type": "building", "x": 0.3, "y": 0.4, "scale": 3.5, "fill": [120, 100, 80]},
                {"type": "building", "x": 0.65, "y": 0.42, "scale": 3.0, "fill": [110, 90, 70]},
                {"type": "fire", "x": 0.3, "y": 0.25, "scale": 4.0, "fill": [255, 150, 50]},
                {"type": "fire", "x": 0.65, "y": 0.28, "scale": 3.0, "fill": [255, 150, 50]},
                {"type": "text", "x": 0.5, "y": 0.08, "text": "INDUSTRIAL REVOLUTION", "font_size": 24, "fill": [200, 180, 150]},
            ]
        scenes.append(scene)

    # ═══════════════════════════════════════════════════════════════
    #  SCIENCE / DISCOVERY / EVOLUTION
    # ═══════════════════════════════════════════════════════════════
    if any(w in n for w in ("science", "discovery", "scientific", "experiment",
                             "laboratory", "microscope", "telescope",
                             "research", "scientist", "discover",
                             "molecule", "atom", "particle",
                             "evolution", "natural selection",
                             "species evolve", "theory of",
                             "fossil record", "carbon dating",
                             "microscopic", "invisible",
                             "magnetic field", "radiation",
                             "physics", "chemistry", "biology",
                             "chemical reaction", "element")):
        scene = {
            "bg": {"type": "gradient", "colors": [[220, 225, 235], [180, 190, 210]], "horizon": 0.6, "ground_color": [160, 170, 190]},
            "elements": [
                {"type": "atom", "x": 0.35, "y": 0.35, "radius": 40, "fill": [60, 140, 220]},
                {"type": "dna", "x": 0.7, "y": 0.45, "width": 80, "height": 130, "fill": [60, 180, 120]},
                {"type": "text", "x": 0.5, "y": 0.08, "text": "SCIENCE & DISCOVERY", "font_size": 24, "fill": [40, 60, 100]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "hopeful"
        }
        if any(w in n for w in ("evolution", "natural selection", "species evolve")):
            scene["bg"] = {"type": "gradient", "colors": [[200, 220, 200], [140, 180, 150]], "horizon": 0.5, "ground_color": [100, 140, 100]}
            scene["elements"] = [
                {"type": "animal", "x": 0.2, "y": 0.55, "scale": 2.5, "fill": [120, 100, 80]},
                {"type": "animal", "x": 0.4, "y": 0.53, "scale": 3.0, "fill": [100, 80, 60]},
                {"type": "animal", "x": 0.6, "y": 0.5, "scale": 3.5, "fill": [80, 70, 50]},
                {"type": "animal", "x": 0.8, "y": 0.48, "scale": 4.0, "fill": [60, 50, 40]},
                {"type": "arrow", "x": 0.25, "y": 0.5, "x2": 0.35, "y2": 0.5, "fill": [100, 100, 100]},
                {"type": "arrow", "x": 0.45, "y": 0.48, "x2": 0.55, "y2": 0.48, "fill": [100, 100, 100]},
                {"type": "arrow", "x": 0.65, "y": 0.45, "x2": 0.75, "y2": 0.45, "fill": [100, 100, 100]},
                {"type": "text", "x": 0.5, "y": 0.08, "text": "EVOLUTION", "font_size": 28, "fill": [40, 80, 40]},
            ]
        scenes.append(scene)

    # ═══════════════════════════════════════════════════════════════
    #  WATER / OCEAN / SEA / UNDERWATER
    # ═══════════════════════════════════════════════════════════════
    if any(w in n for w in ("ocean", "sea", "underwater", "marine",
                             "coral reef", "deep sea", "ocean floor",
                             "creatures of the deep", "sea creature",
                             "coral", "jellyfish", "octopus",
                             "whale shark", "manta ray", "seahorse",
                             "tidal wave", "high tide", "low tide",
                             "coastline", "beach", "shore",
                             "lighthouse", "fishing", "sailor",
                             "pirate", "shipwreck", "sunken",
                             "submarine", "diving", "scuba")):
        bg = {"type": "ocean", "sky_color": [180, 210, 240], "horizon_color": [100, 160, 210],
              "horizon": 0.4, "water_color": [20, 60, 130]}
        if any(w in n for w in ("deep sea", "underwater", "ocean floor",
                                 "submarine", "sunken", "coral", "jellyfish",
                                 "marine creature", "creatures of the deep")):
            bg = {"type": "ocean", "sky_color": [5, 10, 30], "horizon_color": [10, 20, 50],
                  "horizon": 0.1, "water_color": [5, 15, 50]}
        scene = {
            "bg": bg,
            "elements": [
                {"type": "wave", "x": 0.2, "y": 0.45, "scale": 3.0, "fill": [40, 100, 180]},
                {"type": "wave", "x": 0.6, "y": 0.48, "scale": 2.5, "fill": [40, 100, 180]},
                {"type": "ship", "x": 0.5, "y": 0.35, "scale": 2.5, "fill": [100, 80, 60]},
                {"type": "bird", "x": 0.3, "y": 0.15, "scale": 1.5},
                {"type": "bird", "x": 0.6, "y": 0.18, "scale": 1.25},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "peaceful"
        }
        if any(w in n for w in ("pirate", "shipwreck", "sunken", "treasure")):
            scene["elements"] = [
                {"type": "ship", "x": 0.5, "y": 0.35, "scale": 2.5, "fill": [80, 50, 30]},
                {"type": "wave", "x": 0.3, "y": 0.4, "scale": 3.5, "fill": [30, 60, 120]},
                {"type": "wave", "x": 0.7, "y": 0.42, "scale": 3.0, "fill": [30, 60, 120]},
                {"type": "cloud", "x": 0.5, "y": 0.12, "scale": 4.0, "fill": [100, 100, 120]},
                {"type": "text", "x": 0.5, "y": 0.08, "text": "PIRATE SHIP", "font_size": 28, "fill": [40, 40, 60]},
            ]
            scene["mood"] = "dramatic"
        if any(w in n for w in ("deep sea", "underwater", "coral", "jellyfish", "octopus")):
            scene["elements"] = [
                {"type": "fish", "x": 0.3, "y": 0.4, "scale": 3.0, "fill": [200, 150, 80]},
                {"type": "fish", "x": 0.7, "y": 0.5, "scale": 2.5, "fill": [80, 150, 200]},
                {"type": "fish", "x": 0.5, "y": 0.6, "scale": 2.0, "fill": [200, 80, 80]},
                {"type": "flower", "x": 0.2, "y": 0.7, "scale": 2.5, "fill": [200, 100, 150]},
                {"type": "flower", "x": 0.8, "y": 0.68, "scale": 2.0, "fill": [150, 200, 100]},
                {"type": "text", "x": 0.5, "y": 0.08, "text": "UNDER THE SEA", "font_size": 26, "fill": [100, 180, 220]},
            ]
            scene["mood"] = "mysterious"
        scenes.append(scene)

    # ═══════════════════════════════════════════════════════════════
    #  PRE-WHALE / LAND ANCESTOR context
    # ═══════════════════════════════════════════════════════════════
    pre_whale = any(w in n for w in ("no whales", "before whales", "weren't whales", "there were no whales",
                                      "before there were whales", "pre-whale", "deer-like"))
    if pre_whale and any(w in n for w in ("land", "walk", "legs", "river", "rivers", "mammal", "deer", "dog")):
        scene = {
            "bg": {"type": "gradient", "colors": [[180, 210, 200], [120, 170, 150]], "horizon": 0.6, "ground_color": [60, 100, 50]},
            "elements": [
                {"type": "animal", "x": 0.4, "y": 0.65, "scale": 3.5, "fill": [130, 100, 70]},
                {"type": "water", "x": 0.05, "y": 0.72, "width": 0.9, "height": 0.1, "fill": [60, 130, 180]},
                {"type": "tree", "x": 0.8, "y": 0.74, "scale": 3.0, "tree_style": "round", "fill": [50, 120, 50]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "peaceful"
        }
        scenes.append(scene)

    # Whale / Ocean Evolution — high priority
    if any(w in n for w in ("whale", "whales", "whale's", "blue whale", "humpback", "orca",
                             "ambulocetus", "pakicetus", "basilosaurus", "walking whale",
                             "ancient whale", "early whale", "whale ancestor",
                             "cetacean", "cetaceans")):
        scene = {
            "bg": {"type": "ocean", "sky_color": [180, 210, 240], "horizon_color": [120, 170, 220],
                   "horizon": 0.5, "water_color": [30, 70, 150]},
            "elements": [
                {"type": "whale", "x": 0.5, "y": 0.5, "scale": 4.0, "fill": [60, 70, 100]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "epic" if any(w in n for w in ("largest", "giant", "biggest", "enormous", "ocean giant")) else "peaceful"
        }
        if any(w in n for w in ("skeleton", "bone", "bones", "pelvic", "fossil", "hidden")):
            scene["elements"].append({"type": "skeleton", "x": 0.5, "y": 0.65, "scale": 3.0, "fill": [220, 200, 180]})
            scene["mood"] = "mysterious"
        if any(w in n for w in ("walk on land", "walked on land", "walk across", "four legs on land",
                                 "walking on the ground", "on land and", "lived on land",
                                 "move on land", "on land but")):
            scene["elements"] = [
                {"type": "animal", "x": 0.4, "y": 0.65, "scale": 3.5, "fill": [100, 80, 60]},
                {"type": "water", "x": 0.05, "y": 0.7, "width": 0.9, "height": 0.15, "fill": [60, 120, 200]},
            ]
            scene["bg"] = {"type": "gradient", "colors": [[180, 210, 240], [100, 160, 200]], "horizon": 0.6, "ground_color": [60, 90, 50]}
            scene["mood"] = "hopeful"
        if any(w in n for w in ("breathe", "air", "lungs", "mammal", "milk", "nurse")):
            scene["elements"].append({"type": "text", "x": 0.5, "y": 0.15, "text": "MAMMAL", "font_size": 30, "fill": [200, 180, 60]})
        if any(w in n for w in ("largest", "biggest", "blue whale", "dinosaur", "enormous")):
            scene["mood"] = "epic"
            scene["bg"]["water_color"] = [20, 60, 140]
        scenes.append(scene)

    # Ocean evolution / seas / ancestors
    if any(w in n for w in ("descendants", "spread across", "seas", "filter feeders",
                             "hunters", "ocean giant", "ruling the oceans",
                             "abandoned the land", "took to the water",
                             "shoreline", "coastline", "rivers and shallow")):
        scene = {
            "bg": {"type": "ocean", "sky_color": [180, 210, 240], "horizon_color": [120, 170, 220],
                   "horizon": 0.5, "water_color": [30, 70, 150]},
            "elements": [
                {"type": "whale", "x": 0.5, "y": 0.5, "scale": 4.0, "fill": [60, 70, 100]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "epic"
        }
        if any(w in n for w in ("filter", "giant", "largest", "biggest", "enormous")):
            scene["mood"] = "epic"
            scene["bg"]["water_color"] = [20, 60, 140]
        scenes.append(scene)

    # Skeleton / Bones / Hidden
    if any(w in n for w in ("skeleton", "pelvic", "bones", "hind legs", "hindlimb",
                             "remnants", "remnant", "fossil", "fossils", "fossilized",
                             "vestigial", "evidence", "clue", "clues", "trace", "traces",
                             "hidden inside", "secret hidden")):
        scene = {
            "bg": {"type": "ocean", "sky_color": [80, 100, 130], "horizon_color": [60, 80, 110],
                   "horizon": 0.5, "water_color": [20, 50, 100]},
            "elements": [
                {"type": "whale", "x": 0.5, "y": 0.45, "scale": 3.5, "fill": [60, 70, 100]},
                {"type": "skeleton", "x": 0.5, "y": 0.65, "scale": 3.0, "fill": [220, 200, 180]},
                {"type": "text", "x": 0.5, "y": 0.12, "text": "HIDDEN EVIDENCE", "font_size": 24, "fill": [200, 200, 220]},
            ],
            "atmosphere": {"particles": "none", "fog": True},
            "mood": "mysterious"
        }
        scenes.append(scene)

    # Ocean / Ship / Pirate
    if any(w in n for w in ("pirate", "ship", "sail", "ocean", "sea", "sailor", "boat", "navy", "harbor")):
        scene = {
            "bg": {"type": "ocean", "sky_color": [180, 210, 240], "horizon_color": [120, 170, 220],
                   "horizon": 0.5, "water_color": [30, 70, 150]},
            "elements": [
                {"type": "ship", "x": 0.5, "y": 0.55, "scale": 5.0, "fill": [80, 60, 40], "sail_color": [220, 210, 190]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "dramatic" if any(w in n for w in ("storm", "danger", "battle", "war", "attack")) else "peaceful"
        }
        if "pirate" in n:
            scene["elements"].append({"type": "human", "x": 0.35, "y": 0.5, "scale": 3.5, "fill": [100, 60, 40]})
        if any(w in n for w in ("storm", "dark", "thunder")):
            scene["atmosphere"]["fog"] = True
            scene["bg"]["sky_color"] = [100, 100, 120]
            scene["bg"]["horizon_color"] = [80, 80, 100]
        scenes.append(scene)

    # Evolution / Body Change (legs, tails, bodies growing, etc.)
    if any(w in n for w in ("evolution", "evolve", "evolved", "generation", "generations",
                             "legs became", "bodies became", "tails grew", "shrank",
                             "transformed into", "adapted", "adaptation", "mutation",
                             "accumulated", "small changes", "generation after",
                             "change", "changes", "transformation")):
        # Don't match if it's just "hind legs" in a skeleton context
        if any(w in n for w in ("pelvic", "skeleton", "bones", "fossil")):
            pass  # skeleton section will handle
        scene = {
            "bg": {"type": "gradient", "colors": [[180, 210, 240], [120, 170, 220]], "horizon": 0.6, "ground_color": [40, 80, 60]},
            "elements": [
                {"type": "animal", "x": 0.4, "y": 0.65, "scale": 3.5, "fill": [100, 80, 60]},
                {"type": "water", "x": 0.05, "y": 0.72, "width": 0.9, "height": 0.12, "fill": [60, 120, 200]},
                {"type": "text", "x": 0.5, "y": 0.1, "text": "EVOLUTION", "font_size": 28, "fill": [60, 60, 80]},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "epic"
        }
        if any(w in n for w in ("tail", "tails", "flipper", "flippers", "fin", "fins")):
            scene["elements"].append({"type": "whale", "x": 0.65, "y": 0.5, "scale": 3.0, "fill": [60, 70, 100]})
        scenes.append(scene)

    # Mountain / Hill / Valley
    if any(w in n for w in ("mountain", "hill", "valley", "peak", "cliff", "snow", "alps")):
        scene = {
            "bg": {"type": "gradient", "colors": [[180, 200, 220], [100, 150, 200]], "horizon": 0.55, "ground_color": [50, 80, 40]},
            "elements": [
                {"type": "mountain", "x": 0.5, "y": 0.65, "width": 0.5, "height": 0.3, "fill": [100, 110, 140], "snow": "snow" in n or True},
                {"type": "tree", "x": 0.2, "y": 0.72, "scale": 3.5, "tree_style": "pine", "fill": [30, 80, 30]},
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
                {"type": "tree", "x": 0.2, "y": 0.7, "scale": 4.0, "tree_style": "round", "fill": [40, 100, 40]},
                {"type": "tree", "x": 0.5, "y": 0.72, "scale": 5.0, "tree_style": "pine", "fill": [30, 80, 30]},
                {"type": "tree", "x": 0.8, "y": 0.7, "scale": 3.5, "tree_style": "round", "fill": [50, 110, 50]},
            ],
            "atmosphere": {"particles": "none", "fog": True},
            "mood": "mysterious"
        }
        scenes.append(scene)

    # Eclipse / Solar Eclipse
    if any(w in n for w in ("eclipse", "solar eclipse", "lunar eclipse")):
        scene = {
            "bg": {"type": "gradient", "colors": [[60, 60, 90], [20, 15, 40]], "horizon": 0.6, "ground_color": [30, 35, 40]},
            "elements": [
                {"type": "sun", "x": 0.5, "y": 0.35, "radius": 30, "fill": [80, 80, 80]},
                {"type": "moon", "x": 0.5, "y": 0.35, "radius": 16, "fill": [200, 200, 220]},
                {"type": "circle", "x": 0.5, "y": 0.35, "radius": 60, "fill": [200, 200, 220, 15], "stroke": [255, 255, 200, 30], "stroke_width": 1},
                {"type": "star", "x": 0.2, "y": 0.1, "radius": 2},
                {"type": "star", "x": 0.8, "y": 0.15, "radius": 1.5},
                {"type": "star", "x": 0.35, "y": 0.05, "radius": 1},
            ],
            "atmosphere": {"particles": "stars", "fog": False, "star_count": 30},
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
                {"type": "cloud", "x": 0.3, "y": 0.2, "scale": 2.5},
                {"type": "cloud", "x": 0.7, "y": 0.25, "scale": 2.0},
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
                {"type": "house", "x": 0.5, "y": 0.7, "scale": 5.0, "fill": [180, 150, 120], "roof_color": [150, 50, 40]},
                {"type": "tree", "x": 0.25, "y": 0.72, "scale": 3.5, "tree_style": "round", "fill": [50, 120, 50]},
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
                {"type": "human", "x": 0.5, "y": 0.55, "scale": 6.0, "fill": c},
            ],
            "atmosphere": {"particles": "none", "fog": False},
            "mood": "peaceful"
        }
        scenes.append(scene)

    # Ice Age / Mammoth / Prehistoric
    if any(w in n for w in ("mammoth", "woolly mammoth", "ice age", "prehistoric",
                             "tundra", "glacier", "frozen steppe", "megafauna",
                             "winter storm", "snowstorm", "blizzard", "frozen plain",
                             "extinct giant", "last mammoth")):
        scene = {
            "bg": {"type": "gradient", "colors": [[180, 200, 220], [120, 150, 190]], "horizon": 0.55, "ground_color": [180, 190, 210]},
            "elements": [
                {"type": "mountain", "x": 0.2, "y": 0.45, "width": 0.35, "height": 0.35, "fill": [140, 150, 170], "snow": True},
                {"type": "mountain", "x": 0.75, "y": 0.5, "width": 0.3, "height": 0.25, "fill": [120, 130, 150], "snow": True},
                {"type": "snow", "x": 0.5, "y": 0.58, "width": 0.5, "height": 0.06, "fill": [200, 210, 220]},
                {"type": "tree", "x": 0.3, "y": 0.7, "scale": 3.0, "tree_style": "pine", "fill": [40, 80, 60]},
                {"type": "tree", "x": 0.7, "y": 0.72, "scale": 2.5, "tree_style": "pine", "fill": [35, 75, 55]},
                {"type": "bird", "x": 0.4, "y": 0.18, "scale": 1.5, "fill": [60, 60, 70]},
                {"type": "bird", "x": 0.55, "y": 0.2, "scale": 1.25, "fill": [70, 70, 80]},
            ],
            "atmosphere": {"particles": "mist", "fog": True},
            "mood": "somber"
        }
        # If narration explicitly mentions mammoth, add one
        if any(w in n for w in ("mammoth", "woolly mammoth", "tusk", "herd", "megafauna", "last mammoth")):
            scene["elements"].insert(0, {"type": "mammoth", "x": 0.5, "y": 0.6, "scale": 3.5, "fill": [150, 130, 100]})
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
            {"type": "tree", "x": 0.3, "y": 0.72, "scale": 4.0, "tree_style": "round", "fill": [50, 120, 50]},
            {"type": "cloud", "x": 0.5, "y": 0.2, "scale": 3.0},
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
