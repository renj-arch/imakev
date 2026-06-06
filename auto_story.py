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
    """Infer scene visuals from narration keywords — no LLM needed."""
    t = text.lower()

    # ── Mood ──
    if any(w in t for w in ["terrify", "fear", "darken", "eclipse", "monster", "disappear", "end of the world"]):
        mood = "somber"
    elif any(w in t for w in ["amazing", "extraordinary", "astonish", "revolutionary", "discover"]):
        mood = "epic"
    elif any(w in t for w in ["mystery", "mysterious", "unknown", "wonder", "why", "strange"]):
        mood = "mysterious"
    elif any(w in t for w in ["hope", "relief", "return", "won", "spared", "beautiful"]):
        mood = "hopeful"
    elif any(w in t for w in ["battle", "fought", "powerful", "immense", "force"]):
        mood = "dramatic"
    else:
        mood = "peaceful"

    # ── Camera ──
    if any(w in t for w in ["journey", "across", "sail", "travel", "crossing"]):
        camera = "pan_right"
    elif any(w in t for w in ["rise", "rises", "ascend", "above"]):
        camera = "dolly_in"
    elif any(w in t for w in ["observe", "watch", "stare", "gaze"]):
        camera = "ken_burns_in"
    else:
        camera = None

    # ── Background ──
    if any(w in t for w in ["sunset", "dusk", "dawn", "morning", "sunrise"]) or \
       ("rise" in t and "horizon" in t):
        bg_type = "sunset"
        colors = [[255, 180, 80], [200, 100, 60]]
    elif any(w in t for w in ["night", "dark", "darkness", "evening", "disappear", "fade"]):
        bg_type = "night"
        colors = [[10, 10, 40], [30, 20, 60]]
    elif any(w in t for w in ["ocean", "sea", "water", "sail", "boat", "ship"]):
        bg_type = "ocean"
        colors = [[30, 120, 200], [200, 220, 240]]
    elif any(w in t for w in ["forest", "tree", "plant", "grow", "woods", "jungle"]):
        bg_type = "forest"
        colors = [[60, 120, 60], [100, 160, 80]]
    elif any(w in t for w in ["snow", "frozen", "ice", "cold", "winter"]):
        bg_type = "gradient"
        colors = [[200, 220, 240], [150, 180, 210]]
    elif any(w in t for w in ["indoor", "temple", "cave", "room", "inside"]):
        bg_type = "indoor"
        colors = [[80, 60, 50], [140, 110, 90]]
    elif any(w in t for w in ["fire", "campfire", "flame", "burn"]):
        bg_type = "sunset"
        colors = [[180, 80, 30], [80, 30, 10]]
    elif any(w in t for w in ["desert", "sand", "egypt"]):
        bg_type = "gradient"
        colors = [[220, 190, 140], [180, 150, 100]]
    else:
        bg_type = "gradient"
        colors = [[100, 120, 180], [60, 80, 140]]

    # ── Elements ──
    elements = []
    rng = random.Random(scene_num * 9973 + total * 7919)

    def add(etype, x=None, y=None, scale=None, fill=None):
        elements.append({
            "type": etype,
            "x": x if x is not None else round(rng.uniform(0.15, 0.85), 2),
            "y": y if y is not None else round(rng.uniform(0.25, 0.75), 2),
            "scale": scale if scale is not None else round(rng.uniform(0.6, 1.5), 1),
            "fill": fill if fill else [rng.randint(80, 255) for _ in range(3)],
        })

    if any(w in t for w in ["sun", "sunrise", "dawn", "morning", "daylight"]):
        add("sun", 0.5, 0.25, 1.5, [255, 220, 50])
    if any(w in t for w in ["moon", "night"]):
        add("moon", 0.7, 0.2, 1.2, [220, 220, 240])
    if any(w in t for w in ["star", "stars", "universe", "galaxy", "billions"]):
        for _ in range(min(rng.randint(3, 8), 5)):
            add("star", round(rng.uniform(0.1, 0.9), 2), round(rng.uniform(0.05, 0.35), 2), 0.3, [255, 255, 220])
    if any(w in t for w in ["cloud", "sky"]):
        add("cloud", 0.5, 0.15, 1.0, [220, 220, 230])
    if any(w in t for w in ["mountain", "hill", "landscape", "horizon"]):
        add("mountain", 0.5, 0.65, 1.2, [100, 110, 140])
    if any(w in t for w in ["tree", "forest", "plant", "grow", "woods", "jungle"]):
        add("tree", round(rng.uniform(0.2, 0.8), 2), round(rng.uniform(0.5, 0.7), 2), 1.0, [60, 140, 60])
        add("grass", round(rng.uniform(0.3, 0.7), 2), round(rng.uniform(0.7, 0.85), 2), 0.6, [80, 170, 70])
    if any(w in t for w in ["flower", "bloom"]):
        add("flower", round(rng.uniform(0.2, 0.8), 2), round(rng.uniform(0.55, 0.75), 2), 0.7, [220, 80, 160])
    if any(w in t for w in ["animal", "animals", "creature", "beast"]):
        add("animal", round(rng.uniform(0.2, 0.7), 2), round(rng.uniform(0.55, 0.7), 2), 1.0, [150, 100, 80])
    if any(w in t for w in ["bird", "birds"]):
        add("bird", round(rng.uniform(0.3, 0.7), 2), round(rng.uniform(0.15, 0.35), 2), 0.8, [100, 100, 120])
    if any(w in t for w in ["water", "river", "lake", "ocean", "sea"]):
        add("water", 0.5, 0.7, 1.5, [60, 140, 210])
    if any(w in t for w in ["ship", "boat", "sail"]):
        add("ship", 0.5, 0.55, 1.2, [120, 80, 50])
    if any(w in t for w in ["fire", "campfire", "flame", "burn"]):
        add("fire", 0.5, 0.65, 1.0, [255, 160, 40])
    if any(w in t for w in ["temple", "pyramid", "monument", "stone", "ruin"]):
        add("building", 0.5, 0.55, 1.2, [180, 150, 100])
    if any(w in t for w in ["cave"]):
        add("cave", 0.5, 0.5, 1.2, [80, 60, 50])
    if any(w in t for w in ["volcano", "lava"]):
        add("volcano", 0.5, 0.5, 1.5, [120, 60, 40])
    if any(w in t for w in ["rainbow"]):
        add("rainbow", 0.5, 0.3, 1.0, [255, 200, 100])
    if any(w in t for w in ["snow", "ice", "frozen"]):
        add("snow", round(rng.uniform(0.2, 0.8), 2), round(rng.uniform(0.65, 0.8), 2), 0.8, [220, 230, 250])
    if any(w in t for w in ["book", "scroll", "story", "knowledge"]):
        add("book", 0.5, 0.55, 0.8, [180, 140, 80])
    if any(w in t for w in ["chariot", "chariot", "helio", "golden"]):
        add("sun", 0.5, 0.25, 1.5, [255, 220, 50])
    if any(w in t for w in ["compass", "map", "astronomer", "science", "observ"]):
        add("compass", 0.5, 0.5, 0.8, [180, 140, 80])
    if any(w in t for w in ["globe", "earth", "world", "planet"]):
        add("globe", 0.5, 0.45, 0.9, [60, 120, 180])
    if any(w in t for w in ["human", "people", "civilization", "ancient", "culture"]):
        add("human", round(rng.uniform(0.3, 0.6), 2), round(rng.uniform(0.5, 0.65), 2), 0.8, [180, 140, 110])
    if any(w in t for w in ["village", "city", "civilization", "settle"]):
        add("building", round(rng.uniform(0.3, 0.7), 2), round(rng.uniform(0.5, 0.6), 2), 0.7, [160, 130, 100])
    if any(w in t for w in ["egypt", "pharaoh", "ra", "nile"]):
        add("building", 0.3, 0.55, 1.2, [200, 170, 100])
        add("sun", 0.7, 0.25, 1.5, [255, 200, 40])
    if any(w in t for w in ["greece", "greek", "helio", "chariot"]):
        add("building", 0.5, 0.55, 1.0, [200, 190, 170])
    if any(w in t for w in ["eclipse"]):
        add("moon", 0.5, 0.3, 1.5, [30, 30, 50])
        add("sun", 0.5, 0.3, 1.5, [255, 220, 50])

    if not elements:
        add("star", 0.5, 0.3, 0.8, [255, 255, 200])

    # ── Atmosphere ──
    particles = "none"
    star_count = 0
    fog = False
    if bg_type == "night":
        star_count = rng.randint(20, 50)
        particles = "stars"
    if any(w in t for w in ["snow", "ice", "frozen", "winter"]):
        particles = "snow"
    if any(w in t for w in ["rain", "storm"]):
        particles = "rain"
    if any(w in t for w in ["fog", "mist", "shadow"]):
        fog = True

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
            "bg": {"type": bg_type, "colors": colors, "horizon": 0.55},
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
