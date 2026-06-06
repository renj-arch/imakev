"""Auto story — LLM-powered documentary video generator.
Uses sketch_generator.py for clean, full-color illustrations of any topic.
Each scene builds up progressively (stroke-by-stroke reveal animation)."""

import sys, os, re, time, random, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from moviepy import (
    VideoClip, AudioFileClip, CompositeAudioClip, concatenate_audioclips,
    CompositeVideoClip, concatenate_videoclips, VideoFileClip,
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

    system = """You are a documentary filmmaker and visual artist. You create compelling visual stories.
You output ONLY valid JSON. You describe every visual detail precisely."""

    prompt = f"""Create a 60-90 second documentary about: {topic}

For each scene, you'll provide narration AND a full visual description that an illustration engine can render.

Output a JSON object with this structure:
{{
  "title": "documentary title",
  "scenes": [
    {{
      "scene_num": 1,
      "title": "scene title (like 'The Beginning')",
      "narration": "one compelling sentence, 8-15 words, spoken naturally",
      "mood": "peaceful|dramatic|hopeful|somber|epic|mysterious",
      "camera": null or "ken_burns_in|pan_right|pan_left|dolly_in",
      "visual": {{
        "bg": {{
          "type": "gradient|night|ocean|indoor|solid|sunset",
          "colors": [[R,G,B], [R,G,B], ...],
          "horizon": 0.55 or null,
          "ground_color": [R,G,B] or null
        }},
        "elements": [
          {{
            "type": "mountain|tree|cloud|water|human|house|hill|sun|moon|star|ship|building|text|label|arrow|x_mark|line|circle|rect|cannon|flag|polygon",
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
- 8-12 scenes flowing like a documentary narrative
- First scene: strong hook. Last scene: meaningful conclusion.
- Vary scenes: close-ups, wide shots, different perspectives
- Each scene's narration is 8-15 words, spoken naturally
- The "visual" describes what the audience SEES during this scene
- Choose background type and colors that match the mood and setting
- Place 3-8 elements per scene for a complete composition
- Use rich, harmonious colors (exact [R,G,B] values)
- Use "text" or "label" type for on-screen titles/labels
- Use "x_mark" for crossing out myths, "arrow" for pointing
- VARY scenes — don't repeat the same element types in every scene

VISUAL ELEMENT REFERENCE:
- mountain: with optional "snow": true/false
- tree: use "tree_style": "round|pine|palm"
- cloud: fluffy white cloud
- water: water surface with waves
- human/person: simplified figure, use "fill" for clothing color
- house: simple house with roof, "roof_color" for roof
- hill: rolling green hill
- sun: with rays, "radius" for size
- moon: crescent moon, "radius" for size
- star: small dot, "radius" for size
- ship: sailing ship, "sail_color" for sail
- building: with "window_color" for lit windows
- cannon: simple cannon
- flag: with "text" for flag text
- text: on-screen text, "font_size", "fill" for color
- label/text_box: rounded box with text inside
- arrow: directional arrow, "x2"/"y2" endpoint
- x_mark: red X mark
- circle/rect/line/polygon: primitive shapes

Respond with ONLY the JSON object, no other text."""

    fallback = _fallback_script(topic)

    try:
        raw = _generate(prompt, temperature=0.8, max_tokens=6000, system=system)
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


def _fallback_script(topic: str) -> dict:
    """Fallback when LLM fails — uses SceneComposer for ANY topic."""
    from src.scene_composer import SceneComposer
    composer = SceneComposer()
    return composer.compose_script(topic, n_scenes=4)


# ═══════════════════════════════════════════════════════════════
#  SCENE RENDERER — stroke-by-stroke progressive reveal
# ═══════════════════════════════════════════════════════════════

def render_scene_frames(scene: dict, scene_duration: float, fps=FPS):
    """Render a scene as progressive frames. Elements appear one by one."""
    visual = scene.get("visual", {})
    mood = scene.get("mood", "peaceful")
    camera = scene.get("camera", None)
    generator = SketchGenerator(W, H, seed=rng.randint(0, 99999))

    elements = visual.get("elements", [])
    if not elements:
        # Still render background
        img = generator.render_scene(visual)
        frames = [np.array(img)] * max(int(fps * scene_duration), 1)
        return frames

    # Progressive reveal: elements appear one at a time
    n_steps = len(elements)
    time_per_step = scene_duration / n_steps
    frames_per_step = max(1, int(time_per_step * fps))

    all_frames = []
    for step in range(1, n_steps + 1):
        # Build visual with subset of elements
        partial_visual = dict(visual)
        partial_visual["elements"] = elements[:step]

        img = generator.render_scene(partial_visual)
        frame_arr = np.array(img)

        # Apply camera movement
        if camera:
            from src.cinematic import apply_camera_move
            progress = step / n_steps
            frame_arr = apply_camera_move(frame_arr, progress, camera, W, H)

        # Hold this frame for the step duration
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

    # ── 3. Render scenes one by one → temp files ──
    print(f"\n[3/4] Rendering {len(scenes)} scenes to temp files...")
    TD, ED = 2.5, 2.0
    scene_paths = []
    for i, scene in enumerate(scenes):
        sd = timeline[i]["duration"]
        if sd < 0.5: sd = 1.0
        print(f"  Scene {i+1}: {scene.get('title','')[:30]} [{scene.get('mood','')}] ({sd:.1f}s)")
        frames = render_scene_frames(scene, sd)
        print(f"    → {len(frames)} frames")

        # Wrap frames in a scene-specific make_frame with captions
        tl = timeline[i]
        widx = list(range(tl["word_start"], min(tl["word_end"] + 1, len(words))))

        def make_scene(t, frames=frames, sd=sd, tl=tl, widx=widx, words=words, scene_start=tl["start"]):
            tr = t  # time within scene
            fi = min(int(tr / sd * len(frames)), len(frames) - 1)
            base = frames[fi].copy()
            # Captions overlay
            cap = Image.fromarray(base)
            cd = ImageDraw.Draw(cap)
            ov = Image.new("RGBA", (W, 90), (0, 0, 0, 180))
            cap.paste(ov, (0, H - 100), ov)
            fcap = _font(28)
            fhl = _font(32)
            total_t = scene_start + tr
            cw = -1
            for wi in widx:
                if words[wi]["start"] <= total_t:
                    cw = wi
                    break
            x, lh = 20, H - 82
            lh_base = 40
            for wi in widx:
                wt = words[wi]["text"]
                f = fhl if wi == cw else fcap
                d = " " + wt + " "
                bb = cd.textbbox((0, 0), d, font=f)
                ww = bb[2] - bb[0]
                if x + ww > W - 20:
                    x = 20
                    lh_base += 40
                if wi == cw:
                    cd.rounded_rectangle([x - 4, lh_base - 2, x + ww + 4, lh_base + 38], radius=5, fill=(200, 80, 60, 200))
                cd.text((x, lh_base), d, font=f, fill=(255, 255, 255) if wi != cw else (255, 220, 80))
                x += ww
            return np.array(cap)

        scene_clip = VideoClip(make_scene, duration=sd)
        scene_path = temp_dir / f"scene_{i:03d}.mp4"
        print(f"    → writing {scene_path.name}")
        scene_clip.write_videofile(str(scene_path), fps=FPS, codec="libx264",
                                   preset="fast", ffmpeg_params=["-crf", "22"], logger=None)
        scene_clip.close()
        del frames, scene_clip
        scene_paths.append(scene_path)
        print(f"    → done")

    # ── 4. Assemble ──
    print(f"\n[4/4] Assembling final video...")

    # Reload scene clips from disk (low memory — only header info)
    scene_clips = [VideoFileClip(str(p)) for p in scene_paths]

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

    def make_title(t):
        p = t / TD
        a = int(255 * p * p * (3 - 2 * p))
        bg = np.full((H, W, 3), 248, dtype=np.uint8)
        return ((bg.astype(np.float32) * (255 - a) + title_arr.astype(np.float32) * a) / 255).astype(np.uint8)

    title_clip = VideoClip(make_title, duration=TD)

    # Concatenate with crossfade
    clips_with_fade = [title_clip]
    for i, sc in enumerate(scene_clips):
        if i == 0:
            clips_with_fade.append(sc.crossfadein(0))
        else:
            clips_with_fade.append(sc.crossfadein(0.3).crossfadeout(0.3))

    final_video = concatenate_videoclips(clips_with_fade, method="compose", padding=-0.3)

    # Audio
    audio = AudioFileClip(str(tts_path))
    vdur = final_video.duration
    if vdur > audio.duration + TD:
        s = AudioFileClip(str(tts_path)).with_duration(vdur - audio.duration - TD).with_volume_scaled(0)
        audio = concatenate_audioclips([audio, s])
    music = list(config.MUSIC_DIR.glob("*.mp3"))
    if music:
        try:
            m = AudioFileClip(str(random.choice(music))).with_duration(vdur).with_volume_scaled(0.04)
            audio = CompositeAudioClip([audio, m])
        except:
            pass

    try:
        ec = subscribe_end_card(np.full((H, W, 3), 240, dtype=np.uint8), ED)
        ec = ec.with_start(vdur)
        vdur2 = vdur + ED
        final = CompositeVideoClip([final_video, ec], size=config.SHORTS_SIZE).with_duration(vdur2).with_audio(audio)
    except Exception as e:
        print(f"  End card error: {e}")
        final = final_video.with_audio(audio)

    t0 = time.time()
    final.write_videofile(str(output_path), fps=FPS, codec="libx264", audio_codec="aac",
                          threads=4, preset="medium", ffmpeg_params=["-movflags", "+faststart", "-crf", "18"], logger=None)
    final.close()
    for sc in scene_clips:
        sc.close()
    print(f"\n  Done in {time.time() - t0:.0f}s: {output_path} ({os.path.getsize(output_path):,} bytes)")

    # Cleanup temp files
    for p in scene_paths:
        try: p.unlink()
        except: pass


# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    script = None
    # Check if first arg is a JSON file
    if len(sys.argv) >= 2 and sys.argv[1].endswith(".json"):
        path = Path(sys.argv[1])
        if path.exists():
            print(f"Loading script from: {path}")
            with open(path, encoding="utf-8") as f:
                script = json.load(f)
            print(f"  Loaded: {script.get('title', 'untitled')} ({len(script.get('scenes', []))} scenes)")
    elif len(sys.argv) >= 2:
        topic = " ".join(sys.argv[1:])
        print(f"Topic: {topic}")
        print("\n[1/4] Generating LLM script...")
        script = generate_script(topic)
    else:
        topic = "how the printing press changed the world"
        print(f"Topic: {topic}")
        print("\n[1/4] Generating LLM script...")
        script = generate_script(topic)

    if script:
        for s in script.get("scenes", []):
            ne = len(s.get("visual", {}).get("elements", []))
            print(f"  {s.get('title','?')[:35]}: {s['narration'][:50]}... [{s.get('mood','')}] ({ne} elements)")
        safe = re.sub(r'[^\w]+', '_', script.get('title', 'untitled').lower())[:40]
        out = config.OUTPUT_DIR / f"auto_story_{safe}.mp4"
        build_video(script, out)


if __name__ == "__main__":
    main()
