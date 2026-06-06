"""Auto story — LLM-powered documentary video generator.
Uses sketch_generator.py for clean, full-color illustrations of any topic.
Each scene builds up progressively (stroke-by-stroke reveal animation)."""

import sys, os, re, time, random, json
if sys.stdout.encoding.lower() != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except: pass
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from moviepy import (
    VideoClip, AudioFileClip, CompositeAudioClip,
    CompositeVideoClip,
)
import config
from src.text_to_speech import generate_tts_with_timestamps
from src.engagement import subscribe_end_card
from src.sketch_generator import SketchGenerator

W, H = config.VIDEO_WIDTH, config.VIDEO_HEIGHT
FPS = config.VIDEO_FPS
rng = random.Random()


def _font(size=36):
    try: return ImageFont.truetype(config.get_font(), size)
    except: return ImageFont.load_default()


# ═══════════════════════════════════════════════════════════════
#  LLM SCRIPT GENERATION
# ═══════════════════════════════════════════════════════════════

def generate_script(topic: str) -> dict:
    """LLM generates a full documentary script with visual scene descriptions."""
    from src.script_generator import _generate

    system = """You are a documentary filmmaker and visual artist. You create rich, atmospheric visual stories like David Attenborough or Carl Sagan.
You output ONLY valid JSON. You describe every visual detail precisely. Your narration is immersive storytelling — never Q&A, never textbook facts."""

    prompt = f"""Create a documentary about: {topic}

Style: Immersive storytelling like a nature documentary. Rich, descriptive narration. Paint a picture with words. Never use question-and-answer format. Never list facts. Tell a story.

NARRATION STYLE REFERENCE (this is how your narration should read):
"Imagine standing in the African savanna millions of years ago. The land stretches endlessly. Trees dot the horizon. Herds of ancient animals wander through tall grass, all competing for the same thing: food."
"But high above the struggle, untouched leaves sway in the branches. A green buffet hanging just out of reach."
"Generation after generation, the process repeats. Not because nature planned it. Not because animals decided they wanted longer necks. But because individuals with small advantages were often better at surviving."
"Over millions of years, those tiny differences accumulated. A centimeter became several. Several became dozens."

For each scene, provide narration AND a full visual description that an illustration engine can render.

Output a JSON object with this structure:
{{
  "title": "documentary title",
  "scenes": [
    {{
      "scene_num": 1,
      "title": "scene title (like 'The Beginning')",
      "narration": "one to three compelling sentences, storytelling style, no Q&A",
      "mood": "peaceful|dramatic|hopeful|somber|epic|mysterious",
      "camera": null or "ken_burns_in|pan_right|pan_left|dolly_in",
      "visual": {{
        "bg": {{
          "type": "gradient|night|ocean|indoor|solid|sunset|forest",
          "colors": [[R,G,B], [R,G,B], ...],
          "horizon": 0.55 or null,
          "ground_color": [R,G,B] or null
        }},
        "elements": [
          {{
            "type": "mountain|tree|cloud|water|human|house|hill|sun|moon|star|ship|building|text|label|arrow|x_mark|line|circle|rect|cannon|flag|polygon|animal|bird|grass|flower",
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
            "tree_style": "round|pine|palm" or null,
            "snow": true|false or null,
            "sail_color": [R,G,B] or null,
            "window_color": [R,G,B] or null
          }}
        ],
        "atmosphere": {{
          "particles": "stars|rain|snow|none",
          "fog": true|false,
          "star_count": 0-60
        }}
      }}
    }}
  ]
}}

CREATIVE RULES:
- 6-12 scenes flowing like a documentary narrative
- First scene: atmospheric setup. Last scene: powerful, reflective conclusion.
- NARRATION: storytelling style — descriptive, atmospheric, 1-3 sentences per scene. Never Q&A. Never textbook.
- The "visual" describes what the audience SEES during this scene
- Choose background type and colors that match the mood and setting
- Place 3-8 elements per scene for a complete composition
- Use rich, harmonious colors (exact [R,G,B] values)
- Use "text" or "label" type for on-screen titles/labels only when needed
- Use "x_mark" for crossing out myths, "arrow" for pointing
- VARY scenes — don't repeat the same element types in every scene

Respond with ONLY the JSON object, no other text."""

    fallback = _fallback_script(topic)

    try:
        raw = _generate(prompt, temperature=0.9, max_tokens=1600, system=system)
        raw = re.sub(r'^```(?:json)?\s*', '', raw.strip())
        raw = re.sub(r'\s*```$', '', raw)
        data = json.loads(raw)
        if "scenes" in data and len(data["scenes"]) >= 4:
            print(f"  LLM OK: {data['title']} ({len(data['scenes'])} scenes)")
            return data
    except Exception as e:
        print(f"  LLM script error: {e}")

    print("  Using fallback script")
    return fallback


def _infer_visuals(text: str, scene_num: int, total: int) -> dict:
    """Infer scene visuals from narrative arc position + keywords.

    The story arc drives the emotional progression: opening (mystery/setup)
    → rising action → climax → falling action → resolution.
    This gives the video a cinematic feel — scenes flow naturally.
    """
    t = text.lower()
    progress = (scene_num - 1) / max(total - 1, 1)

    # ── Pick arc phase from position ──
    if progress < 0.10:
        phase = "opening"
    elif progress < 0.30:
        phase = "rising_early"
    elif progress < 0.55:
        phase = "rising_late"
    elif progress < 0.70:
        phase = "climax"
    elif progress < 0.88:
        phase = "falling"
    else:
        phase = "resolution"

    # ── Arc-driven mood base (overridden by keywords below) ──
    arc_moods = {
        "opening": "mysterious",
        "rising_early": "hopeful",
        "rising_late": "peaceful",
        "climax": "dramatic",
        "falling": "somber",
        "resolution": "hopeful",
    }

    # ── Arc-driven background palette ──
    arc_bgs = {
        "opening":      {"type": "gradient", "colors": [[25, 25, 55], [55, 45, 80]]},
        "rising_early": {"type": "gradient", "colors": [[60, 70, 110], [120, 100, 130]]},
        "rising_late":  {"type": "gradient", "colors": [[100, 130, 170], [180, 150, 130]]},
        "climax":       {"type": "sunset",   "colors": [[200, 90, 40], [140, 60, 80]]},
        "falling":      {"type": "gradient", "colors": [[120, 100, 130], [80, 70, 110]]},
        "resolution":   {"type": "sunset",   "colors": [[240, 190, 120], [200, 140, 100]]},
    }

    bg = dict(arc_bgs[phase])
    bg["horizon"] = 0.55

    # ── Arc-driven camera ──
    arc_cameras = {
        "opening": "ken_burns_in",
        "rising_early": None,
        "rising_late": "pan_right",
        "climax": "dolly_in",
        "falling": None,
        "resolution": "ken_burns_in",
    }

    # ── Arc-driven element density ──
    arc_density = {
        "opening": 0.4,
        "rising_early": 0.6,
        "rising_late": 0.8,
        "climax": 1.0,
        "falling": 0.6,
        "resolution": 0.5,
    }

    # ── Keyword overrides ──
    mood = arc_moods[phase]
    camera = arc_cameras[phase]

    # Mood override from keywords
    if any(w in t for w in ["terrify", "fear", "darken", "eclipse", "monster", "devour", "end of the world"]):
        mood = "somber"
    elif any(w in t for w in ["amazing", "extraordinary", "astonish", "revolutionary", "discover", "astonishing"]):
        mood = "epic"
    elif any(w in t for w in ["mystery", "mysterious", "unknown", "strange", "why"]):
        mood = "mysterious"
    elif any(w in t for w in ["hope", "relief", "return", "spared", "won"]):
        mood = "hopeful"
    elif any(w in t for w in ["battle", "fought", "powerful", "immense", "force", "terrifying"]):
        mood = "dramatic"

    # Background override from keywords
    if any(w in t for w in ["sunset", "dusk", "dawn", "morning", "sunrise"]) or \
       ("rise" in t and "horizon" in t):
        bg = {"type": "sunset", "colors": [[255, 190, 80], [210, 120, 60]], "horizon": 0.55}
    elif any(w in t for w in ["night", "dark", "darkness", "evening", "disappear", "fade"]):
        bg = {"type": "night", "colors": [[8, 8, 35], [28, 18, 55]], "horizon": 0.55}
    elif any(w in t for w in ["ocean", "sea", "sail", "boat", "ship"]):
        bg = {"type": "ocean", "colors": [[25, 105, 190], [190, 210, 230]], "horizon": 0.55}
    elif any(w in t for w in ["forest", "tree", "plant", "grow", "woods"]):
        bg = {"type": "forest", "colors": [[50, 110, 50], [90, 150, 70]], "horizon": 0.55}
    elif any(w in t for w in ["snow", "frozen", "ice", "cold", "winter"]):
        bg = {"type": "gradient", "colors": [[190, 215, 235], [140, 170, 200]], "horizon": 0.55}
    elif any(w in t for w in ["indoor", "temple", "cave", "inside"]):
        bg = {"type": "indoor", "colors": [[70, 55, 45], [130, 100, 80]], "horizon": 0.55}
    elif any(w in t for w in ["fire", "campfire", "flame", "burn"]):
        bg = {"type": "sunset", "colors": [[175, 70, 25], [75, 25, 10]], "horizon": 0.55}
    elif any(w in t for w in ["desert", "sand", "egypt"]):
        bg = {"type": "gradient", "colors": [[210, 180, 130], [175, 140, 95]], "horizon": 0.55}

    camera_override = None
    if any(w in t for w in ["journey", "across", "sail", "travel", "crossing"]):
        camera_override = "pan_right"
    elif any(w in t for w in ["rise", "rises", "ascend", "above"]):
        camera_override = "dolly_in"
    elif any(w in t for w in ["observe", "watch", "stare", "gaze", "look"]):
        camera_override = "ken_burns_in"
    if camera_override:
        camera = camera_override

    # ── Elements ──
    elements = []
    added_types = set()
    rng = random.Random(scene_num * 9973 + total * 7919)
    density = arc_density[phase]

    def add(etype, x=None, y=None, scale=None, fill=None):
        if etype in added_types and len([e for e in elements if e["type"] == etype]) >= 2:
            return
        added_types.add(etype)
        elements.append({
            "type": etype,
            "x": x if x is not None else round(rng.uniform(0.15, 0.85), 2),
            "y": y if y is not None else round(rng.uniform(0.25, 0.75), 2),
            "scale": scale if scale is not None else round(rng.uniform(0.6, 1.5), 1),
            "fill": fill if fill else [rng.randint(80, 255) for _ in range(3)],
        })

    # Background layer — mountains/horizon always present (scaled by density)
    if rng.random() < density:
        add("mountain", 0.5, 0.68, round(1.0 + density * 0.3, 1), [80 + int(40 * density), 90 + int(40 * density), 120 + int(40 * density)])

    # Keyword-matched elements with arc-aware count
    def kw_count(keywords, max_n=3):
        """Return how many of this element to place based on keyword match + arc density."""
        if not any(w in t for w in keywords):
            return 0
        raw = max_n if phase == "climax" else max(1, int(max_n * density))
        return rng.randint(1, raw)

    n = kw_count(["sun", "sunrise", "dawn", "morning", "daylight"], 2)
    for _ in range(n):
        add("sun", 0.5 if n == 1 else round(rng.uniform(0.3, 0.7), 2), 0.22 + rng.random() * 0.08, 1.2 + rng.random() * 0.4, [255, 215 + int(rng.random() * 40), 50])

    n = kw_count(["moon", "night"], 1)
    for _ in range(n):
        add("moon", round(rng.uniform(0.6, 0.8), 2), 0.18, 1.1, [215, 215, 235])

    if any(w in t for w in ["star", "stars", "universe", "galaxy", "billions"]):
        n = rng.randint(3, 8) if phase == "climax" else max(1, int(6 * density))
        for _ in range(min(n, 8)):
            add("star", round(rng.uniform(0.05, 0.95), 2), round(rng.uniform(0.03, 0.4), 2), 0.2 + rng.random() * 0.2, [255, 255, 210 + int(rng.random() * 45)])

    n = kw_count(["cloud", "sky"], 2)
    for _ in range(n):
        add("cloud", round(rng.uniform(0.2, 0.8), 2), round(rng.uniform(0.08, 0.22), 2), 0.7 + rng.random() * 0.5, [210, 215, 225])

    n = kw_count(["tree", "forest", "plant", "grow", "woods", "jungle"], 3)
    for _ in range(n):
        side = 0.15 if _ == 0 else (0.85 if _ == 2 else round(rng.uniform(0.25, 0.75), 2))
        add("tree", side, round(rng.uniform(0.5, 0.65), 2), 0.7 + rng.random() * 0.6, [50 + int(rng.random() * 60), 120 + int(rng.random() * 60), 50 + int(rng.random() * 30)])
    n = kw_count(["tree", "forest", "plant", "grow", "woods", "jungle"], 2)
    for _ in range(n):
        add("grass", round(rng.uniform(0.15, 0.85), 2), round(rng.uniform(0.72, 0.88), 2), 0.5 + rng.random() * 0.3, [70 + int(rng.random() * 50), 155 + int(rng.random() * 40), 60 + int(rng.random() * 30)])

    n = kw_count(["animal", "animals", "creature", "beast"], 2)
    for _ in range(n):
        add("animal", round(rng.uniform(0.2, 0.7), 2), round(rng.uniform(0.58, 0.72), 2), 0.8 + rng.random() * 0.4, [130 + int(rng.random() * 50), 85 + int(rng.random() * 40), 65 + int(rng.random() * 40)])

    n = kw_count(["bird", "birds"], 3)
    for _ in range(n):
        add("bird", round(rng.uniform(0.15, 0.85), 2), round(rng.uniform(0.08, 0.3), 2), 0.5 + rng.random() * 0.4, [90 + int(rng.random() * 40), 90 + int(rng.random() * 40), 110 + int(rng.random() * 30)])

    n = kw_count(["water", "river", "lake", "ocean", "sea"], 1)
    for _ in range(n):
        add("water", 0.5, 0.72, 1.3 + rng.random() * 0.4, [50 + int(rng.random() * 30), 130 + int(rng.random() * 30), 200 + int(rng.random() * 20)])

    n = kw_count(["flower", "bloom"], 2)
    for _ in range(n):
        add("flower", round(rng.uniform(0.2, 0.8), 2), round(rng.uniform(0.58, 0.78), 2), 0.5 + rng.random() * 0.3, [200 + int(rng.random() * 55), 60 + int(rng.random() * 60), 140 + int(rng.random() * 60)])

    n = kw_count(["ship", "boat", "sail"], 1)
    for _ in range(n):
        add("ship", round(rng.uniform(0.3, 0.6), 2), round(rng.uniform(0.5, 0.6), 2), 1.0 + rng.random() * 0.3, [110, 75, 45])

    n = kw_count(["fire", "campfire", "flame", "burn"], 1)
    for _ in range(n):
        add("fire", round(rng.uniform(0.35, 0.65), 2), 0.62, 0.8 + rng.random() * 0.3, [255, 150 + int(rng.random() * 60), 30 + int(rng.random() * 30)])

    n = kw_count(["temple", "pyramid", "monument", "stone", "ruin"], 2)
    for _ in range(n):
        add("building", round(rng.uniform(0.2, 0.6), 2), round(rng.uniform(0.52, 0.6), 2), 0.9 + rng.random() * 0.4, [160 + int(rng.random() * 40), 135 + int(rng.random() * 40), 85 + int(rng.random() * 40)])

    n = kw_count(["human", "people", "civilization", "ancient", "culture"], 2)
    for _ in range(n):
        add("human", round(rng.uniform(0.25, 0.55), 2), round(rng.uniform(0.52, 0.65), 2), 0.7 + rng.random() * 0.2, [165 + int(rng.random() * 40), 125 + int(rng.random() * 40), 95 + int(rng.random() * 40)])

    n = kw_count(["book", "scroll", "story", "knowledge"], 1)
    for _ in range(n):
        add("book", round(rng.uniform(0.35, 0.65), 2), round(rng.uniform(0.5, 0.6), 2), 0.7 + rng.random() * 0.2, [170, 130, 75])

    n = kw_count(["compass", "map", "astronomer", "science", "observ"], 1)
    for _ in range(n):
        add("compass", round(rng.uniform(0.35, 0.65), 2), round(rng.uniform(0.45, 0.55), 2), 0.7 + rng.random() * 0.2, [170, 130, 75])

    n = kw_count(["globe", "earth", "world", "planet"], 1)
    for _ in range(n):
        add("globe", round(rng.uniform(0.4, 0.6), 2), round(rng.uniform(0.42, 0.52), 2), 0.8 + rng.random() * 0.2, [50 + int(rng.random() * 30), 110 + int(rng.random() * 30), 170 + int(rng.random() * 30)])

    # Cultural overrides
    if any(w in t for w in ["egypt", "pharaoh", "ra", "nile"]):
        add("building", 0.25, 0.55, 1.3 + rng.random() * 0.3, [195, 165, 95])
        add("sun", 0.75, 0.22, 1.6, [255, 195, 35])
    if any(w in t for w in ["greece", "greek", "helio", "chariot"]):
        add("building", 0.5, 0.55, 1.0 + rng.random() * 0.3, [195, 185, 165])
    if any(w in t for w in ["eclipse"]):
        add("moon", 0.48, 0.28, 1.4, [25, 25, 45])
        add("sun", 0.52, 0.28, 1.4, [255, 215, 45])

    n = kw_count(["snow", "ice", "frozen"], 3)
    for _ in range(n):
        add("snow", round(rng.uniform(0.1, 0.9), 2), round(rng.uniform(0.65, 0.85), 2), 0.6 + rng.random() * 0.4, [210 + int(rng.random() * 45), 220 + int(rng.random() * 35), 240 + int(rng.random() * 15)])

    n = kw_count(["village", "city", "settle"], 2)
    for _ in range(n):
        add("building", round(rng.uniform(0.2, 0.7), 2), round(rng.uniform(0.5, 0.62), 2), 0.6 + rng.random() * 0.3, [150 + int(rng.random() * 40), 120 + int(rng.random() * 40), 90 + int(rng.random() * 40)])

    if any(w in t for w in ["cave"]):
        add("cave", 0.5, 0.5, 1.1 + rng.random() * 0.3, [75, 55, 45])
    if any(w in t for w in ["volcano", "lava"]):
        add("volcano", 0.5, 0.45, 1.4 + rng.random() * 0.3, [115, 55, 35])
    if any(w in t for w in ["rainbow"]):
        add("rainbow", 0.5, 0.25, 0.9 + rng.random() * 0.3, [255, 200, 100])

    if not elements:
        add("star", 0.5, 0.3, 0.7, [255, 255, 210])

    # ── Atmosphere ──
    particles = "none"
    star_count = 0
    fog = False

    if bg["type"] == "night":
        star_count = rng.randint(15, 45)
        particles = "stars"

    if any(w in t for w in ["snow", "ice", "frozen", "winter"]):
        particles = "snow"
    if any(w in t for w in ["rain", "storm"]):
        particles = "rain"
    if any(w in t for w in ["fog", "mist", "shadow", "underworld"]):
        fog = True

    if phase == "climax" and particles == "none":
        particles = "stars" if bg["type"] == "night" else "rain"

    # ── Title ──
    words = text.split()
    title = " ".join(words[:5]).rstrip(".,!?") if len(words) > 3 else f"Scene {scene_num}"
    if len(title) > 40:
        title = title[:40]

    return {
        "title": title,
        "mood": mood,
        "camera": camera,
        "visual": {
            "bg": bg,
            "elements": elements,
            "atmosphere": {"particles": particles, "fog": fog, "star_count": star_count},
        },
    }


def generate_script_from_narration(text: str) -> dict:
    """Split pre-written narration into scenes. Keyword-based visuals — no LLM needed."""
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]

    if len(paragraphs) < 4:
        sentences = [s.strip() for s in text.replace('?', '.').replace('!', '.').split('.') if s.strip()]
        sentences = [s + '.' for s in sentences if s]
        paragraphs = []
        chunk = []
        for s in sentences:
            chunk.append(s)
            if len(chunk) >= 3:
                paragraphs.append(' '.join(chunk))
                chunk = []
        if chunk:
            paragraphs.append(' '.join(chunk))

    if len(paragraphs) < 2:
        paragraphs = [text]

    title_words = paragraphs[0].split()[:6]
    title = " ".join(title_words).rstrip(".,!?")

    scenes = []
    for i, para in enumerate(paragraphs):
        scene_num = i + 1
        raw_prompt = para.strip()
        if not raw_prompt:
            continue

        visuals = _infer_visuals(raw_prompt, scene_num, len(paragraphs))

        scene = {
            "scene_num": scene_num,
            "title": visuals["title"],
            "narration": raw_prompt,
            "mood": visuals["mood"],
            "camera": visuals["camera"],
            "visual": visuals["visual"],
        }
        scenes.append(scene)
        elems = len(scene["visual"]["elements"])
        print(f"  Scene {scene_num}/{len(paragraphs)}: {scene['mood']} ({elems} elems)")

    print(f"  Created {len(scenes)} scenes from narration")
    return {"title": title, "scenes": scenes}


def _fallback_script(topic: str) -> dict:
    """Fallback when LLM fails — uses SceneComposer for ANY topic."""
    from src.scene_composer import SceneComposer
    composer = SceneComposer()
    return composer.compose_script(topic, n_scenes=4)


# ═══════════════════════════════════════════════════════════════
#  SCENE RENDERER — stroke-by-stroke progressive reveal
# ═══════════════════════════════════════════════════════════════

RENDER_FPS = 3  # Low fps for progressive reveal — each frame holds for ~8 video frames at 24fps

def render_scene_frames(scene: dict, scene_duration: float, fps=RENDER_FPS):
    """Render a scene as progressive frames. Elements appear one by one."""
    visual = scene.get("visual", {})
    mood = scene.get("mood", "peaceful")
    camera = scene.get("camera", None)
    generator = SketchGenerator(W, H, seed=rng.randint(0, 99999))

    elements = visual.get("elements", [])
    if not elements:
        img = generator.render_scene(visual)
        frames = [np.array(img)] * max(int(fps * scene_duration), 1)
        return frames

    n_steps = len(elements)
    time_per_step = scene_duration / n_steps
    frames_per_step = max(1, int(time_per_step * fps))

    all_frames = []
    for step in range(1, n_steps + 1):
        partial_visual = dict(visual)
        partial_visual["elements"] = elements[:step]

        img = generator.render_scene(partial_visual)
        frame_arr = np.array(img)

        if camera:
            from src.cinematic import apply_camera_move
            progress = step / n_steps
            frame_arr = apply_camera_move(frame_arr, progress, camera, W, H)

        for _ in range(frames_per_step):
            all_frames.append(frame_arr.copy())

    return all_frames


# ═══════════════════════════════════════════════════════════════
#  VIDEO BUILDER
# ═══════════════════════════════════════════════════════════════

def build_video(script_data: dict, output_path: str):
    scenes = script_data["scenes"]
    title = script_data["title"]

    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"  {len(scenes)} scenes | stroke-by-stroke documentary")
    print(f"{'='*55}")

    temp_dir = config.TEMP_DIR / "auto_story"
    temp_dir.mkdir(exist_ok=True)

    # ── 1. Generate narration ──
    print(f"\n[1/4] Generating narration...")
    full_script = " ".join(s["narration"] for s in scenes)
    tts_path = temp_dir / "narration.mp3"
    words = generate_tts_with_timestamps(full_script, tts_path)
    total_dur = words[-1]["end"] if words else 8.0
    print(f"  {total_dur:.1f}s | {len(words)} words")

    # ── 2. Build timeline ──
    print(f"\n[2/4] Building timeline...")
    timeline = []
    global_wi = 0
    for i, scene in enumerate(scenes):
        sw = scene["narration"].split()
        ws = global_wi
        we = min(ws + len(sw) - 1, len(words) - 1)
        timeline.append({
            "start": words[ws]["start"] if we >= ws else 0,
            "end": words[we]["end"] if we >= ws else total_dur / len(scenes),
            "word_start": ws,
            "word_end": we,
            "duration": (words[we]["end"] - words[ws]["start"]) if we >= ws else total_dur / len(scenes),
        })
        global_wi = we + 1

    # ── 3. Render scenes ──
    print(f"\n[3/4] Rendering {len(scenes)} scenes...")
    TD, ED = 2.5, 2.0
    scene_data = []
    total_frames = 0
    for i, scene in enumerate(scenes):
        sd = timeline[i]["duration"]
        if sd < 0.5: sd = 1.0
        print(f"  Scene {i+1}: {scene.get('title','')[:30]} [{scene.get('mood','')}] ({sd:.1f}s)")
        frames = render_scene_frames(scene, sd)
        tl = timeline[i]
        scene_data.append({"frames": frames, "duration": sd, "timeline": tl})
        total_frames += len(frames)
        print(f"    -> {len(frames)} frames")

    # ── 4. Assemble ──
    print(f"\n[4/4] Assembling video ({total_frames} scene frames)...")

    # Title card
    ti = Image.new("RGB", (W, H), (252, 250, 245))
    td = ImageDraw.Draw(ti)
    ft = _font(42)
    tlines = []
    cur = ""
    for w in title.split():
        test = (cur + " " + w).strip()
        tb = td.textbbox((0, 0), test, font=ft)
        if tb[2] - tb[0] > W - 80:
            tlines.append(cur); cur = w
        else: cur = test
    tlines.append(cur)
    y = H // 2 - 70
    for line in tlines:
        tb = td.textbbox((0, 0), line, font=ft)
        td.text(((W - (tb[2] - tb[0])) // 2, y), line, font=ft, fill=(40, 35, 30))
        y += 70
    fsub = _font(20)
    sub = "AN ILLUSTRATED DOCUMENTARY"
    tb = td.textbbox((0, 0), sub, font=fsub)
    td.text(((W - (tb[2] - tb[0])) // 2, H - 160), sub, font=fsub, fill=(140, 130, 120))
    title_arr = np.array(ti)

    # Build frame map (like original but with single clip)
    frame_map = []
    cursor = TD
    for sd in scene_data:
        sd["start"] = cursor
        sd["end"] = cursor + sd["duration"]
        sd["ft"] = sd["duration"] / max(len(sd["frames"]), 1)
        frame_map.append(sd)
        cursor += sd["duration"]
    vdur = cursor + ED

    bg_arr = np.full((H, W, 3), 248, dtype=np.uint8)

    def make_frame(t):
        if t < TD:
            p = t / TD
            a = int(255 * p * p * (3 - 2 * p))
            if a < 255:
                return ((bg_arr.astype(np.float32) * (255 - a) + title_arr.astype(np.float32) * a) / 255).astype(np.uint8)
            return title_arr
        tr = t - TD
        if tr > cursor - TD:
            return bg_arr
        active = None
        for sd in frame_map:
            if sd["start"] <= t < sd["end"]:
                active = sd; break
        if active is None:
            for sd in reversed(frame_map):
                if t >= sd["end"]:
                    active = sd; break
        if active is None:
            return bg_arr
        lt = t - active["start"]
        fi = min(int(lt / active["ft"]), len(active["frames"]) - 1)
        base = active["frames"][fi].copy()
        tl = active["timeline"]
        tr_abs = t - TD
        cap = Image.fromarray(base)
        cd = ImageDraw.Draw(cap)
        ov = Image.new("RGBA", (W, 90), (0, 0, 0, 180))
        cap.paste(ov, (0, H - 100), ov)
        fcap = _font(28)
        fhl = _font(32)
        widx = list(range(tl["word_start"], min(tl["word_end"] + 1, len(words))))
        cw = -1
        for wi in widx:
            if words[wi]["start"] <= tr_abs:
                cw = wi; break
        x, lh_base = 20, 40
        for wi in widx:
            wt = words[wi]["text"]
            f = fhl if wi == cw else fcap
            d = " " + wt + " "
            bb = cd.textbbox((0, 0), d, font=f)
            ww = bb[2] - bb[0]
            if x + ww > W - 20:
                x = 20; lh_base += 40
            if wi == cw:
                cd.rounded_rectangle([x - 4, lh_base - 2, x + ww + 4, lh_base + 38], radius=5, fill=(200, 80, 60, 200))
            cd.text((x, lh_base), d, font=f, fill=(255, 255, 255) if wi != cw else (255, 220, 80))
            x += ww
        return np.array(cap)

    clip = VideoClip(make_frame, duration=vdur)

    audio = AudioFileClip(str(tts_path)).with_start(TD)
    music = list(config.MUSIC_DIR.glob("*.mp3"))
    if music:
        try:
            m = AudioFileClip(str(random.choice(music))).with_duration(vdur).with_volume_scaled(0.04)
            audio = CompositeAudioClip([audio, m])
        except:
            pass

    try:
        ec = subscribe_end_card(np.full((H, W, 3), 240, dtype=np.uint8), ED)
        ec = ec.with_start(cursor)
        final = CompositeVideoClip([clip, ec], size=config.SHORTS_SIZE).with_audio(audio)
    except Exception as e:
        print(f"  End card error: {e}")
        final = clip.with_audio(audio)

    t0 = time.time()
    final.write_videofile(str(output_path), fps=FPS, codec="libx264", audio_codec="aac",
                          threads=4, preset="fast", ffmpeg_params=["-movflags", "+faststart", "-crf", "22"], logger=None)
    final.close()
    print(f"\n  Done in {time.time() - t0:.0f}s: {output_path} ({os.path.getsize(output_path):,} bytes)")


# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    script = None
    custom_title = ""
    script_file = None

    # Parse --title flag
    args = sys.argv[1:]
    if "--title" in args:
        idx = args.index("--title")
        if idx + 1 < len(args):
            custom_title = args[idx + 1]
            args = args[:idx] + args[idx+2:]

    if args:
        arg = args[0]
        # .json file → load pre-made script
        if arg.endswith(".json"):
            path = Path(arg)
            if path.exists():
                print(f"Loading script from: {path}")
                with open(path, encoding="utf-8") as f:
                    script = json.load(f)
                print(f"  Loaded: {script.get('title', 'untitled')} ({len(script.get('scenes', []))} scenes)")
        # .txt file → pre-written narration, auto-generate visuals
        elif arg.endswith(".txt"):
            script_file = arg
            path = Path(arg)
            if path.exists():
                text = path.read_text(encoding="utf-8")
                print(f"Loaded narration ({len(text)} chars from {path})")
                print("\n[1/4] Generating scenes from narration...")
                script = generate_script_from_narration(text)
        else:
            topic = " ".join(args)
            print(f"Topic: {topic}")
            print("\n[1/4] Generating LLM script...")
            script = generate_script(topic)
    else:
        topic = "how the printing press changed the world"
        print(f"Topic: {topic}")
        print("\n[1/4] Generating LLM script...")
        script = generate_script(topic)

    if script:
        if custom_title:
            script["title"] = custom_title
        for s in script.get("scenes", []):
            ne = len(s.get("visual", {}).get("elements", []))
            print(f"  {s.get('title','?')[:35]}: {s['narration'][:50]}... [{s.get('mood','')}] ({ne} elements)")
        safe = re.sub(r'[^\w]+', '_', script.get('title', 'untitled').lower())[:40]
        out = config.OUTPUT_DIR / f"auto_story_{safe}.mp4"
        build_video(script, out)


if __name__ == "__main__":
    main()
