"""Auto story video: topic → LLM script → hand-drawn sketches → TTS → video.
Just give a topic, get a complete narrated sketch-story video."""

import sys, os, re, time, random, math, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
from moviepy import (
    VideoClip, AudioFileClip, CompositeAudioClip, concatenate_audioclips,
    CompositeVideoClip,
)
import config
from src.text_to_speech import generate_tts_with_timestamps
from src.engagement import subscribe_end_card

W, H = config.VIDEO_WIDTH, config.VIDEO_HEIGHT
FPS = config.VIDEO_FPS
rng = random.Random()

# ─── Drawing primitives (from sketch_pipeline) ────────────────

def _stroke(draw, pts, w=2, color=(0,0,0), amp=1.2):
    if len(pts) < 2: return
    for i in range(len(pts)-1):
        steps = max(int(math.hypot(pts[i+1][0]-pts[i][0], pts[i+1][1]-pts[i][1])/2), 3)
        for s in range(steps):
            t = s/steps
            px = pts[i][0]+(pts[i+1][0]-pts[i][0])*t+rng.gauss(0,amp*0.4)
            py = pts[i][1]+(pts[i+1][1]-pts[i][1])*t+rng.gauss(0,amp*0.4)
            rw = w*(0.85+rng.random()*0.3)
            draw.ellipse([px-rw/2, py-rw/2, px+rw/2, py+rw/2], fill=color)

def _fill(draw, pts, color, amp=2):
    if len(pts) < 3: return
    draw.polygon([(x+rng.gauss(0,amp), y+rng.gauss(0,amp)) for x,y in pts], fill=color)

def _circle(draw, cx, cy, r, fill_c=None, line_c=(0,0,0), w=2):
    pts = [(cx+math.cos(math.radians(a))*r+rng.gauss(0,0.5), cy+math.sin(math.radians(a))*r+rng.gauss(0,0.5)) for a in range(0,361,15)]
    if fill_c: _fill(draw, pts, fill_c, amp=1)
    _stroke(draw, pts, w=w, color=line_c, amp=0.8)

def _rect(draw, x, y, w, h, fill_c=None, line_c=(0,0,0), lw=2):
    pts = [(x+rng.gauss(0,1), y+rng.gauss(0,1)), (x+w+rng.gauss(0,1), y+rng.gauss(0,1)),
           (x+w+rng.gauss(0,1), y+h+rng.gauss(0,1)), (x+rng.gauss(0,1), y+h+rng.gauss(0,1))]
    if fill_c: _fill(draw, pts, fill_c, amp=1)
    _stroke(draw, pts+[pts[0]], w=lw, color=line_c, amp=0.8)

def _get_font(size=36):
    try: return ImageFont.truetype(config.get_font(), size)
    except: return ImageFont.load_default()

def _paper_bg(draw, w, h):
    for _ in range(1000):
        x, y = rng.randint(0, w-1), rng.randint(0, h-1)
        v = rng.randint(-12, 4)
        c = 250+v
        draw.point((x, y), fill=(c, c-2, c-4))

def _sky_grad(draw, w, h, sky_type="day"):
    for y in range(h):
        t = y/h
        if sky_type == "night":
            draw.line([(0,y),(w,y)], fill=(int(10+t*20), int(5+t*15), int(20+t*40)))
        elif sky_type == "sunset":
            draw.line([(0,y),(w,y)], fill=(int(60+195*t), int(30+180*t), int(60+80*(1-t))))
        else:
            draw.line([(0,y),(w,y)], fill=(int(225-t*25), int(230-t*20), int(240-t*15)))

def _ground_grad(draw, x, y, w, h, c=(40,100,40)):
    for gy in range(int(h)):
        t = gy/h
        draw.line([(x, y+gy), (x+w, y+gy)], fill=(int(c[0]+t*20), int(c[1]+t*15), int(c[2]-t*10)))

def _draw_grass_blade(draw, gx, gy):
    _stroke(draw, [(gx, gy), (gx+rng.randint(-2,2), gy-rng.randint(5,15))], w=1.5, color=(50,80,40), amp=0.5)

def _draw_cloud(draw, cx, cy, s=1.0):
    for i in range(rng.randint(3,4)):
        ox, oy = rng.randint(-15,15)*s, rng.randint(-8,5)*s
        r = rng.randint(15,30)*s
        _circle(draw, cx+ox, cy+oy*0.5, r, fill_c=(255,255,255,rng.randint(60,100)), line_c=(200,200,200,100))

def _draw_water(draw, cx, cy, s=1.0):
    for i in range(8):
        wx = cx + rng.randint(-40, 40)*s
        wy = cy + rng.randint(-20, 20)*s
        wl = rng.randint(10, 30)*s
        _stroke(draw, [(wx, wy), (wx+wl, wy+rng.randint(-2,2))], w=1, color=(30,80,150,100), amp=0.5)

def _draw_tree(draw, cx, cy, s=1.0):
    _stroke(draw, [(cx, cy), (cx, cy-40*s)], w=4, color=(60,45,30), amp=1)
    cr = 20*s
    for i in range(rng.randint(3,5)):
        ox, oy = rng.randint(-10,10)*s, rng.randint(-8,5)*s
        rr = cr*(0.6+rng.random()*0.4)
        _circle(draw, cx+ox, cy-40*s+oy, rr, fill_c=(50,80,40,80), line_c=(40,70,30,200))

def _draw_mountain(draw, cx, cy, s=1.0):
    mw, mh = int(120*s), int(80*s)
    pts = [(cx-mw, cy), (cx, cy-mh), (cx+mw, cy)]
    c = (rng.randint(80,120), rng.randint(90,130), rng.randint(130,160))
    _fill(draw, pts, (*c,100), amp=2)
    _stroke(draw, pts, w=2, color=(60,60,80,150), amp=1.5)

def _draw_human(draw, cx, cy, s=1.0):
    _circle(draw, cx, cy-18*s, 6*s, fill_c=(230,200,170,200), line_c=(180,150,130))
    body = [(cx-5*s, cy-13*s), (cx-4*s, cy+3*s), (cx+4*s, cy+3*s), (cx+5*s, cy-13*s)]
    _fill(draw, body, (100,80,60,180), amp=1.5)
    _stroke(draw, [(cx-6*s, cy-8*s), (cx-10*s, cy-3*s)], w=2, color=(100,80,60), amp=1)
    _stroke(draw, [(cx+6*s, cy-8*s), (cx+10*s, cy-3*s)], w=2, color=(100,80,60), amp=1)
    _stroke(draw, [(cx-3*s, cy+3*s), (cx-5*s, cy+8*s)], w=2, color=(80,70,60), amp=1)
    _stroke(draw, [(cx+3*s, cy+3*s), (cx+5*s, cy+8*s)], w=2, color=(80,70,60), amp=1)

def _draw_ship(draw, cx, cy, s=1.0, ship_type="merchant"):
    _fill(draw, [(cx-30*s, cy), (cx-25*s, cy+12*s), (cx+25*s, cy+12*s), (cx+30*s, cy)], (60,50,40,200), amp=1.5)
    _stroke(draw, [(cx, cy), (cx, cy-40*s)], w=3, color=(50,40,30))
    if ship_type == "pirate":
        _fill(draw, [(cx, cy-35*s), (cx-22*s, cy-8*s), (cx, cy-3*s)], (30,30,30,200), amp=1.5)
    else:
        _fill(draw, [(cx, cy-35*s), (cx-20*s, cy-8*s), (cx, cy-3*s)], (240,235,220,180), amp=1.5)
    _stroke(draw, [(cx, cy-35*s), (cx-20*s, cy-8*s), (cx, cy-3*s)], w=1.5, color=(100,95,85))

def _draw_house(draw, cx, cy, s=1.0):
    _rect(draw, cx-30*s, cy-25*s, 60*s, 25*s, fill_c=(180,160,140,150), line_c=(60,50,40))
    _fill(draw, [(cx-35*s, cy-25*s), (cx, cy-40*s), (cx+35*s, cy-25*s)], (150,50,40,120), amp=1.5)
    _stroke(draw, [(cx-35*s, cy-25*s), (cx, cy-40*s), (cx+35*s, cy-25*s)], w=2, color=(100,30,20))

def _draw_stars(draw, w, h, count=40):
    for _ in range(count):
        sx = rng.randint(0, w)
        sy = rng.randint(0, int(h*0.4))
        _circle(draw, sx, sy, rng.uniform(0.5, 2), fill_c=(255,255,200,rng.randint(30,150)), line_c=None)

def _draw_sun(draw, cx, cy, s=1.0):
    _circle(draw, cx, cy, 25*s, fill_c=(255,200,50,100), line_c=(255,200,50))
    for a in range(0, 360, 30):
        _stroke(draw, [(cx+math.cos(math.radians(a))*30*s, cy+math.sin(math.radians(a))*30*s),
                       (cx+math.cos(math.radians(a))*40*s, cy+math.sin(math.radians(a))*40*s)], w=2, color=(255,200,50,100), amp=0.5)

# ─── LLM-driven scene renderer ────────────────────────────────

def render_scene_from_commands(commands: str, w=W, h=H) -> Image.Image:
    """Execute LLM-generated drawing commands with hand-drawn wobble style."""
    img = Image.new("RGBA", (w, h), (252, 250, 245, 255))
    draw = ImageDraw.Draw(img, "RGBA")
    _paper_bg(draw, w, h)

    rng_local = random.Random(len(commands))

    for line in commands.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue

        parts = line.split()
        if not parts:
            continue
        cmd = parts[0].upper()

        try:
            if cmd == "SKY":
                sky_type = parts[1] if len(parts) > 1 else "day"
                _sky_grad(draw, w, h, sky_type)
                if sky_type == "night":
                    for _ in range(50):
                        sx = rng_local.randint(0, w)
                        sy = rng_local.randint(0, int(h*0.4))
                        _circle(draw, sx, sy, rng_local.uniform(0.5,2), fill_c=(255,255,200,rng_local.randint(30,120)), line_c=None)

            elif cmd == "GROUND":
                gy = int(parts[1]) if len(parts) > 1 else int(h*0.65)
                c = (int(parts[2]), int(parts[3]), int(parts[4])) if len(parts) > 4 else (40,100,40)
                _ground_grad(draw, 0, gy, w, h-gy, c)
                # Grass blades
                if len(parts) < 5 or "grass" in line.lower():
                    for _ in range(40):
                        gx = rng_local.randint(20, w-20)
                        _draw_grass_blade(draw, gx, gy+rng_local.randint(0, int(h*0.15)))

            elif cmd == "STROKE":
                coords = [float(x) for x in parts[1:-4]] if len(parts) > 5 else []
                if coords and len(coords) >= 4:
                    pts = [(coords[i], coords[i+1]) for i in range(0, len(coords)-1, 2)]
                    lw = int(parts[-4]) if len(parts) > 4 else 2
                    cr, cg, cb = int(parts[-3]), int(parts[-2]), int(parts[-1])
                    _stroke(draw, pts, w=lw, color=(cr,cg,cb), amp=1.2)

            elif cmd == "FILL":
                coords = [float(x) for x in parts[1:-4]] if len(parts) > 5 else []
                if coords and len(coords) >= 6:
                    pts = [(coords[i], coords[i+1]) for i in range(0, len(coords)-1, 2)]
                    cr, cg, cb = int(parts[-3]), int(parts[-2]), int(parts[-1])
                    _fill(draw, pts, (cr,cg,cb,180), amp=2)
                    _stroke(draw, pts, w=2, color=(cr,cg,cb), amp=1)

            elif cmd == "CIRCLE":
                cx = float(parts[1]); cy = float(parts[2]); r = float(parts[3])
                lcr = int(parts[4]); lcg = int(parts[5]); lcb = int(parts[6])
                fill_c = None
                if len(parts) > 9:
                    fill_c = (int(parts[7]), int(parts[8]), int(parts[9]), 150)
                _circle(draw, cx, cy, r, fill_c=fill_c, line_c=(lcr,lcg,lcb))

            elif cmd == "RECT":
                rx = float(parts[1]); ry = float(parts[2]); rw = float(parts[3]); rh = float(parts[4])
                lcr, lcg, lcb = int(parts[5]), int(parts[6]), int(parts[7])
                fill_c = None
                if len(parts) > 10:
                    fill_c = (int(parts[8]), int(parts[9]), int(parts[10]), 150)
                _rect(draw, rx, ry, rw, rh, fill_c=fill_c, line_c=(lcr,lcg,lcb))

            elif cmd == "HATCH":
                cx = float(parts[1]); cy = float(parts[2]); r = float(parts[3])
                cr, cg, cb = int(parts[4]), int(parts[5]), int(parts[6])
                for _ in range(int(parts[7]) if len(parts) > 7 else 25):
                    a = rng_local.random()*math.pi*2
                    d = rng_local.random()*r
                    x1 = cx+math.cos(a)*d; y1 = cy+math.sin(a)*d
                    x2 = x1+math.cos(a+math.pi/4)*rng_local.uniform(3,8)
                    y2 = y1+math.sin(a+math.pi/4)*rng_local.uniform(3,8)
                    draw.line([(x1,y1),(x2,y2)], fill=(cr,cg,cb,60), width=1)

            elif cmd == "CLOUD":
                cx = float(parts[1]); cy = float(parts[2]); s = float(parts[3]) if len(parts) > 3 else 1.0
                _draw_cloud(draw, cx, cy, s)

            elif cmd == "MOUNTAIN":
                cx = float(parts[1]); cy = float(parts[2]); s = float(parts[3]) if len(parts) > 3 else 1.0
                _draw_mountain(draw, cx, cy, s)

            elif cmd == "TREE":
                cx = float(parts[1]); cy = float(parts[2]); s = float(parts[3]) if len(parts) > 3 else 1.0
                _draw_tree(draw, cx, cy, s)

            elif cmd == "HUMAN":
                cx = float(parts[1]); cy = float(parts[2]); s = float(parts[3]) if len(parts) > 3 else 1.0
                _draw_human(draw, cx, cy, s)

            elif cmd == "SHIP":
                cx = float(parts[1]); cy = float(parts[2]); s = float(parts[3]) if len(parts) > 3 else 1.0
                st = parts[4] if len(parts) > 4 else "merchant"
                _draw_ship(draw, cx, cy, s, st)

            elif cmd == "SUN":
                cx = float(parts[1]); cy = float(parts[2]); s = float(parts[3]) if len(parts) > 3 else 1.0
                _draw_sun(draw, cx, cy, s)

            elif cmd == "MOON":
                cx = float(parts[1]); cy = float(parts[2]); s = float(parts[3]) if len(parts) > 3 else 1.0
                _circle(draw, cx, cy, 20*s, fill_c=(240,235,210,80), line_c=(220,215,190))

            elif cmd == "HOUSE":
                cx = float(parts[1]); cy = float(parts[2]); s = float(parts[3]) if len(parts) > 3 else 1.0
                _draw_house(draw, cx, cy, s)

        except Exception as e:
            print(f"    Cmd error '{cmd}': {e}")
            continue

    img = img.filter(ImageFilter.SMOOTH)
    return img.convert("RGB")


def llm_generate_drawing_commands(scene_title: str, scene_narration: str, visuals_hint: str) -> str:
    """Use LLM to generate drawing commands for a scene."""
    from src.script_generator import _generate

    prompt = f"""Generate drawing commands for a hand-drawn sketch scene.

Scene title: {scene_title}
Narration: {scene_narration}
Visual hints: {visuals_hint}

Available commands:
- SKY [day|night|sunset] — fills the sky with gradient
- GROUND y_pos R G B — fills ground from y_pos down
- STROKE x1 y1 x2 y2 ... w R G B — draws a wobble line through points
- FILL x1 y1 x2 y2 ... R G B — draws a filled polygon
- CIRCLE cx cy r outlineR outlineG outlineB [fillR fillG fillB]
- RECT x y w h outlineR outlineG outlineB [fillR fillG fillB]
- HATCH cx cy radius R G B [density]
- CLOUD cx cy [scale]
- MOUNTAIN cx cy [scale]
- TREE cx cy [scale]
- HUMAN cx cy [scale]
- SHIP cx cy [scale] [merchant|pirate]
- SUN cx cy [scale]
- MOON cx cy [scale]
- HOUSE cx cy [scale]

Rules:
- Canvas is 720x1280 (portrait)
- Use HAND-DRAWN style: organic curves, imperfect placement, varied line widths
- Place main subject at center, supporting elements around it
- Add mood-appropriate sky and ground
- Use 6-15 commands per scene
- For crowds or multiple objects, use STROKE/FILL with multiple points
- Coordinates: x from 0-720, y from 0-1280
- Colors: R G B values 0-255

Output ONLY the drawing commands, one per line. No explanations."""

    system = "You are a sketch artist who generates drawing commands for hand-drawn illustrations."
    try:
        commands = _generate(prompt, temperature=0.6, max_tokens=2000, system=system)
        if commands:
            # Validate — at least get some commands
            cmd_lines = [l.strip() for l in commands.strip().split("\n") if l.strip() and not l.startswith("#") and not l.startswith("//")]
            if cmd_lines:
                return commands.strip()
    except Exception as e:
        print(f"  LLM draw error: {e}")

    # Fallback: simple scene
    from src.script_generator import _generate as _g2
    fallback = f"SKY day\nGROUND 800 40 100 40\nMOUNTAIN 200 750 1.0\nMOUNTAIN 500 780 0.8\nTREE 360 700 1.0"
    return fallback


def render_scene_from_llm(scene_title: str, scene_narration: str, visuals_hint: str, w=W, h=H) -> Image.Image:
    """Full pipeline: LLM generates drawing commands → renderer executes them."""
    commands = llm_generate_drawing_commands(scene_title, scene_narration, visuals_hint)
    print(f"    LLM commands: {len(commands.split(chr(10)))} lines")
    return render_scene_from_commands(commands, w, h)

# ─── LLM script generation ────────────────────────────────────

def generate_script(topic: str) -> dict:
    """Use LLM to generate a narrative with scene descriptions."""
    from src.script_generator import _generate

    prompt = f"""Write a 60-second documentary-style story about: {topic}

Write exactly 8 scenes. Each scene has a short title and one narrative sentence.
Each sentence should be 8-15 words, conversational and compelling.

For each scene, also write visual keywords (3-6 comma-separated words) that describe what should appear in the illustration.

Format EXACTLY like this (separate scenes with ---):

SCENE 1
TITLE: [scene title, 2-5 words]
NARRATION: [one sentence, 8-15 words]
VISUALS: [3-6 comma-separated keywords]

---

SCENE 2
TITLE: [title]
NARRATION: [sentence]
VISUALS: [keywords]

--- etc for all 8 scenes.

Keywords available: sky, night, sunset, sunrise, ocean, sea, water, tree, mountain, house, cabin, ship, boat, pirate, human, person, man, woman, people, sailor, star, moon, sun, cloud, grass, field, forest, desert, ground

Make the story flow naturally from start to finish with a strong opening hook and meaningful ending."""

    system = "You write short documentary narratives with visual scene descriptions."
    fallback = _fallback_script(topic)

    try:
        raw = _generate(prompt, temperature=0.7, max_tokens=2500, system=system)
    except Exception as e:
        print(f"  LLM error: {e}")
        return fallback

    if not raw:
        return fallback

    scenes = []
    current = {}
    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line: continue
        if line.startswith("SCENE"):
            if current.get("narration"):
                scenes.append(current)
            current = {}
        elif line.startswith("TITLE:"):
            current["title"] = line[len("TITLE:"):].strip()
        elif line.startswith("NARRATION:"):
            current["narration"] = line[len("NARRATION:"):].strip()
        elif line.startswith("VISUALS:"):
            current["visuals"] = line[len("VISUALS:"):].strip()

    if current.get("narration"):
        scenes.append(current)

    if len(scenes) < 4:
        print(f"  Only {len(scenes)} scenes parsed, using fallback")
        return fallback

    title = f"The Story of {topic}" if not topic else topic
    return {
        "title": title[:70],
        "topic": topic,
        "scenes": scenes,
        "narration": [s["narration"] for s in scenes],
        "visuals": [s.get("visuals", "") for s in scenes],
    }

def _fallback_script(topic: str) -> dict:
    scenes = [
        {"title": "Introduction", "narration": f"Have you ever wondered about {topic}? The truth is more fascinating than most people realize.", "visuals": f"sky, star, {topic}"},
        {"title": "The Discovery", "narration": f"Scientists have uncovered surprising details about how {topic} came to be.", "visuals": f"mountain, tree, human"},
        {"title": "How It Works", "narration": f"The inner workings of {topic} reveal incredible complexity and beauty.", "visuals": f"ocean, sun, cloud"},
        {"title": "Impact on History", "narration": f"Throughout history, {topic} has shaped the world in unexpected ways.", "visuals": f"ship, house, field"},
        {"title": "Modern Understanding", "narration": f"Today we understand {topic} better than ever before.", "visuals": f"tree, mountain, cloud"},
        {"title": "The Future", "narration": f"And the story of {topic} is far from over. New discoveries await.", "visuals": f"star, night, moon"},
        {"title": "What It Means", "narration": f"{topic} teaches us something important about the world we live in.", "visuals": f"sun, ocean, grass"},
        {"title": "Final Thought", "narration": f"So next time you think of {topic}, remember there is always more to discover.", "visuals": f"star, night, moon"},
    ]
    return {"title": f"The Story of {topic[:50]}", "topic": topic, "scenes": scenes,
            "narration": [s["narration"] for s in scenes],
            "visuals": [s["visuals"] for s in scenes]}

# ─── Main video builder ───────────────────────────────────────

def build_video(script_data: dict, output_path: str):
    scenes = script_data["scenes"]
    title = script_data["title"]

    print(f"\n{'='*55}")
    print(f"  AUTO STORY — {title}")
    print(f"  {len(scenes)} scenes")
    print(f"{'='*55}")

    temp_dir = config.TEMP_DIR / "auto_story"
    temp_dir.mkdir(exist_ok=True)

    # Step 1: Generate scene images via LLM drawing commands
    print(f"\n[1/4] Drawing {len(scenes)} hand-drawn scenes via LLM...")
    scene_images = []
    for i, scene in enumerate(scenes):
        visuals = scene.get("visuals", scene.get("narration", ""))
        print(f"  Scene {i+1}: {scene['title'][:30]}...")
        img = render_scene_from_llm(scene["title"], scene["narration"], visuals, W, H)
        # Overlay title text on image
        img_rgba = img.convert("RGBA")
        draw = ImageDraw.Draw(img_rgba)
        tf = _get_font(36)
        title_text = scene["title"].upper()
        tb = draw.textbbox((0,0), title_text, font=tf)
        tw, th = tb[2]-tb[0]+40, tb[3]-tb[1]+20
        draw.rounded_rectangle([(W-tw)//2, 40, (W+tw)//2, 40+th], radius=10, fill=(0,0,0,140))
        draw.text(((W-(tb[2]-tb[0]))//2, 48), title_text, font=tf, fill=(255,255,255,230))
        # Scene number badge
        sf = _get_font(20)
        sn = f"{i+1:02d}/{len(scenes):02d}"
        sb = draw.textbbox((0,0), sn, font=sf)
        draw.rounded_rectangle([25, 25, 25+sb[2]-sb[0]+20, 25+sb[3]-sb[1]+10], radius=6, fill=(0,0,0,120))
        draw.text((35, 28), sn, font=sf, fill=(255,255,255,200))
        scene_images.append(np.array(img_rgba.convert("RGB")))

    # Step 2: TTS
    print(f"\n[2/4] Generating narration...")
    full_script = " ".join(script_data["narration"])
    tts_path = temp_dir / "narration.mp3"
    words = generate_tts_with_timestamps(full_script, tts_path)
    total_dur = words[-1]["end"] if words else 8.0
    print(f"  {total_dur:.1f}s | {len(words)} words")

    # Step 3: Timeline
    print(f"\n[3/4] Building timeline...")
    timeline = []
    global_wi = 0
    for i, scene in enumerate(scenes):
        scene_words = scene["narration"].split()
        w_start = global_wi
        w_end = min(w_start + len(scene_words) - 1, len(words) - 1)
        s_start = words[w_start]["start"]
        s_end = words[w_end]["end"]
        timeline.append({
            "image": scene_images[i],
            "start": s_start, "end": s_end,
            "word_start": w_start, "word_end": w_end,
        })
        global_wi = w_end + 1

    # Step 4: Render video
    print(f"\n[4/4] Rendering video ({W}x{H} @ {FPS}fps)...")
    TITLE_DUR = 2.5
    END_DUR = 2.0
    video_dur = total_dur + TITLE_DUR + END_DUR
    bg_blank = np.full((H, W, 3), 248, dtype=np.uint8)

    # Title card
    title_img = Image.new("RGB", (W, H), (252, 250, 245))
    tdraw = ImageDraw.Draw(title_img)
    tf = _get_font(48)
    tlines = []
    cur = ""
    for w in title.split():
        test = (cur + " " + w).strip()
        tb = tdraw.textbbox((0,0), test, font=tf)
        if tb[2]-tb[0] > W-80:
            tlines.append(cur); cur = w
        else: cur = test
    tlines.append(cur)
    y = H//2-60
    for line in tlines:
        tb = tdraw.textbbox((0,0), line, font=tf)
        tdraw.text(((W-(tb[2]-tb[0]))//2, y), line, font=tf, fill=(40,35,30))
        y += 70
    sf = _get_font(24)
    sub = "A HAND-DRAWN STORY"
    tb = tdraw.textbbox((0,0), sub, font=sf)
    tdraw.text(((W-(tb[2]-tb[0]))//2, H-160), sub, font=sf, fill=(140,130,120))
    title_arr = np.array(title_img)

    transition_dur = 0.5
    trans_cache = {}
    for i in range(len(scene_images)-1):
        nf = int(transition_dur * FPS)
        frames = []
        for fi in range(nf):
            t = fi/nf
            ease = t*t*(3-2*t)
            frames.append(((1-ease)*scene_images[i].astype(np.float32)+ease*scene_images[i+1].astype(np.float32)).astype(np.uint8))
        trans_cache[i] = frames

    def make_frame(t):
        if t < TITLE_DUR:
            p = t/TITLE_DUR
            a = int(255*p*p*(3-2*p))
            if a < 255:
                return ((bg_blank.astype(np.float32)*(255-a)+title_arr.astype(np.float32)*a)/255).astype(np.uint8)
            return title_arr
        t_rel = t - TITLE_DUR
        if t_rel > total_dur:
            return bg_blank
        active = None; active_idx = -1
        for i, s in enumerate(timeline):
            if s["start"] <= t_rel < s["end"]: active, active_idx = s, i; break
        if active is None:
            for i, s in reversed(list(enumerate(timeline))):
                if t_rel >= s["end"]: active, active_idx = s, i; break
        if active is None: return bg_blank
        base = active["image"].copy()
        if active_idx < len(timeline)-1:
            next_s = timeline[active_idx+1]["start"]
            if abs(next_s-active["end"]) < 0.05:
                trans_t = t_rel - active["end"]
                if 0 <= trans_t < transition_dur and active_idx in trans_cache:
                    fi = min(int(trans_t*FPS), len(trans_cache[active_idx])-1)
                    base = trans_cache[active_idx][fi]
        curr_w = -1
        for wi in range(active["word_start"], min(active["word_end"]+1, len(words))):
            if words[wi]["start"] <= t_rel: curr_w = wi; break
        # Caption
        cap = Image.fromarray(base)
        cdraw = ImageDraw.Draw(cap)
        bar_h = 100
        cap_overlay = Image.new("RGBA", (W, bar_h), (0,0,0,180))
        cap.paste(cap_overlay, (0, H-bar_h-10), cap_overlay)
        font = _get_font(32)
        hl_font = _get_font(36)
        words_to_show = [words[wi]["text"] for wi in range(active["word_start"], min(active["word_end"]+1, len(words)))]
        x, y, lh = 20, H-bar_h+15, 48
        for i, w in enumerate(words_to_show):
            wi = active["word_start"] + i
            f = hl_font if wi == curr_w else font
            c = (255,220,80) if wi == curr_w else (255,255,255)
            dw = " " + w + " "
            bb = cdraw.textbbox((0,0), dw, font=f)
            ww = bb[2]-bb[0]
            if x + ww > W-20: x, lh = 20, lh+48
            if wi == curr_w:
                cdraw.rounded_rectangle([x-4, lh-2, x+ww+4, lh+42], radius=5, fill=(200,80,60,180))
            cdraw.text((x, lh), dw, font=f, fill=c)
            x += ww
        return np.array(cap)

    clip = VideoClip(make_frame, duration=video_dur)
    audio = AudioFileClip(str(tts_path))
    if video_dur > audio.duration + TITLE_DUR:
        s = AudioFileClip(str(tts_path)).with_duration(video_dur-audio.duration-TITLE_DUR).with_volume_scaled(0)
        audio = concatenate_audioclips([audio, s])
    music_paths = list(config.MUSIC_DIR.glob("*.mp3"))
    if music_paths:
        m = AudioFileClip(str(random.choice(music_paths))).with_duration(video_dur).with_volume_scaled(0.04)
        audio = CompositeAudioClip([audio, m])
    try:
        end_card = subscribe_end_card(np.full((H,W,3), 240, dtype=np.uint8), END_DUR)
        end_card = end_card.with_start(total_dur+TITLE_DUR)
        final = CompositeVideoClip([clip, end_card], size=config.SHORTS_SIZE).with_audio(audio)
    except:
        final = clip.with_audio(audio)
    t0 = time.time()
    final.write_videofile(str(output_path), fps=FPS, codec="libx264", audio_codec="aac",
                          threads=4, preset="medium", ffmpeg_params=["-movflags", "+faststart", "-crf", "18"], logger=None)
    final.close()
    print(f"\n  Done in {time.time()-t0:.0f}s: {output_path} ({os.path.getsize(output_path):,} bytes)")

def main():
    topic = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "why the sky is blue"
    print(f"Topic: {topic}")
    print("\n[1/4] Generating script with LLM...")
    script = generate_script(topic)
    print(f"  Title: {script['title']}")
    for i, s in enumerate(script["scenes"]):
        print(f"  {i+1}. {s['title']}: {s['narration'][:60]}...")
    safe = re.sub(r'[^\w]+', '_', topic.lower())[:40]
    out = config.OUTPUT_DIR / f"auto_story_{safe}.mp4"
    build_video(script, out)

if __name__ == "__main__":
    main()
