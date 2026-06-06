"""Auto story: topic → LLM generates full visual script + rich renderer → TTS → video.
The LLM drives every creative decision. No templates, no keyword limits."""

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

def _get_font(size=36):
    try: return ImageFont.truetype(config.get_font(), size)
    except: return ImageFont.load_default()

# ─── Primitives with hand-drawn wobble ─────────────────────────

def _stroke(draw, pts, w=2, color=(0,0,0,255), amp=1.2):
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

def _circle(draw, cx, cy, r, fill_c=None, line_c=(0,0,0,255), w=2):
    pts = [(cx+math.cos(math.radians(a))*r+rng.gauss(0,0.5), cy+math.sin(math.radians(a))*r+rng.gauss(0,0.5)) for a in range(0,361,15)]
    if fill_c: _fill(draw, pts, fill_c, amp=1)
    _stroke(draw, pts, w=w, color=line_c, amp=0.8)

def _hatch(draw, cx, cy, w, h, spacing=6, color=(0,0,0,30)):
    for i in range(int(math.hypot(w,h)/spacing)+10):
        for angle in [45, -45]:
            rad = math.radians(angle)
            sx = cx-w/2 + math.cos(rad)*i*spacing
            sy = cy-h/2 + math.sin(rad)*i*spacing
            ex = sx + math.cos(rad+math.pi/2)*math.hypot(w,h)
            ey = sy + math.sin(rad+math.pi/2)*math.hypot(w,h)
            _stroke(draw, [(sx,sy),(ex,ey)], w=1, color=color, amp=0.3)

# ─── LLM generates the FULL visual script ──────────────────────

def generate_visual_script(topic: str) -> dict:
    """LLM generates a complete visual story — script + per-scene visual descriptions in JSON."""
    from src.script_generator import _generate

    system = """You are a documentary filmmaker and sketch artist. You create compelling visual stories.
You output ONLY valid JSON. You describe every visual detail precisely."""

    prompt = f"""Create a 60-second visual documentary about: {topic}

Output a JSON object with this exact structure:
{{
  "title": "documentary title",
  "scenes": [
    {{
      "scene_num": 1,
      "title": "scene title",
      "narration": "one compelling sentence (10-15 words)",
      "mood": "mysterious|peaceful|dramatic|hopeful|somber|epic",
      "background": {{
        "type": "sky|indoor|abstract|underwater|space",
        "sky_type": "day|night|sunset|sunrise|stormy" or null,
        "base_color": [R,G,B],
        "secondary_colors": [[R,G,B], [R,G,B]],
        "horizon_y": 0.6 or null,
        "ground_color": [R,G,B] or null
      }},
      "elements": [
        {{
          "type": "circle|rect|polygon|arc|text|mountain|tree|human|ship|cloud|sun|moon|star|building|animal|plant|object|abstract",
          "label": "what it represents",
          "x": 0.0-1.0,
          "y": 0.0-1.0,
          "width": 0.0-1.0 or null,
          "height": 0.0-1.0 or null,
          "radius": 0.0-1.0 or null,
          "color": [R,G,B],
          "fill_color": [R,G,B] or null,
          "stroke_width": 1-5,
          "opacity": 0.0-1.0,
          "points": [[x,y],...] or null,
          "text": "text content" or null,
          "rotation": 0-360 or null,
          "children": [similar elements] or null
        }}
      ],
      "atmosphere": {{
        "wind": true/false,
        "rain": true/false,
        "fog": true/false,
        "light_direction": "left|right|top|none",
        "particles": "stars|rain|snow|leaves|none"
      }}
    }}
  ]
}}

Rules:
- Exactly 8 scenes, flowing like a documentary narrative
- First scene: strong hook. Last scene: meaningful conclusion.
- Each narration: one sentence, 10-15 words, spoken naturally
- For each scene, describe 4-12 visual elements that bring it to life
- x,y: 0-1 coordinates on canvas (portrait 720x1280)
- Colors: rich, harmonious palettes matching the mood
- Vary scenes: close-ups, wide shots, different perspectives
- Make each scene visually distinct from the others
- The elements should create a COMPLETE, detailed illustration

Respond with ONLY the JSON object, no other text."""

    fallback = {
        "title": f"The Story of {topic}",
        "scenes": [
            {"scene_num":1,"title":"Introduction","narration":f"Have you ever wondered about {topic}?","mood":"mysterious",
             "background":{"type":"sky","sky_type":"night","base_color":[10,8,30],"secondary_colors":[[30,20,60]],"horizon_y":0.6,"ground_color":[30,40,30]},
             "elements":[{"type":"star","label":"star","x":0.2,"y":0.15,"radius":0.005,"color":[255,255,200],"opacity":0.8},
                         {"type":"star","label":"star","x":0.8,"y":0.1,"radius":0.003,"color":[255,255,200],"opacity":0.6},
                         {"type":"mountain","label":"distant mountain","x":0.5,"y":0.65,"width":0.6,"height":0.15,"color":[60,60,80],"fill_color":[40,40,60],"opacity":0.5}],
             "atmosphere":{"wind":False,"rain":False,"fog":False,"light_direction":"top","particles":"stars"}}
        ] * 8
    }

    try:
        raw = _generate(prompt, temperature=0.8, max_tokens=4000, system=system)
        raw = re.sub(r'^```(?:json)?\s*', '', raw.strip())
        raw = re.sub(r'\s*```$', '', raw)
        data = json.loads(raw)
        if "scenes" in data and len(data["scenes"]) >= 4:
            print(f"  LLM OK: {data['title']} ({len(data['scenes'])} scenes)")
            return data
    except Exception as e:
        print(f"  LLM script error: {e}")

    print("  Using fallback script")
    fallback["title"] = f"The Story of {topic[:50]}"
    return fallback

# ─── Renderer: JSON scene description → hand-drawn image ──────

def render_scene(scene: dict) -> Image.Image:
    """Render a visual scene description into a hand-drawn illustration."""
    img = Image.new("RGBA", (W, H), (252, 250, 245, 255))
    draw = ImageDraw.Draw(img, "RGBA")

    # Paper grain
    for _ in range(1500):
        x, y = rng.randint(0, W-1), rng.randint(0, H-1)
        v = rng.randint(-12, 4)
        c = 250+v
        draw.point((x, y), fill=(c, c-2, c-4))

    bg = scene.get("background", {})
    mood = scene.get("mood", "peaceful")
    atmos = scene.get("atmosphere", {})

    # ── Background layers ──
    bg_type = bg.get("type", "sky")
    sky_type = bg.get("sky_type", "day")
    horizon = bg.get("horizon_y", 0.65)
    base_c = bg.get("base_color", [200, 210, 230])
    sec_c = bg.get("secondary_colors", [[180, 190, 210]])
    ground_c = bg.get("ground_color", [40, 80, 40])

    # Sky gradient
    sky_h = int(H * horizon)
    for y in range(sky_h):
        t = y / sky_h
        r = int(base_c[0] - t*(base_c[0]-sec_c[0][0]))
        g = int(base_c[1] - t*(base_c[1]-sec_c[0][1]))
        b = int(base_c[2] - t*(base_c[2]-sec_c[0][2]))
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Ground
    if bg_type == "sky":
        for y in range(sky_h, H):
            t = (y - sky_h) / (H - sky_h)
            r = int(ground_c[0] + t * 20)
            g = int(ground_c[1] + t * 15)
            b = int(ground_c[2] - t * 10)
            draw.line([(0, y), (W, y)], fill=(r, g, b))
    elif bg_type == "indoor":
        for y in range(H):
            t = y / H
            draw.line([(0, y), (W, y)], fill=(int(200-t*80), int(190-t*70), int(170-t*60)))

    # Stars
    if atmos.get("particles") == "stars" or sky_type == "night":
        for _ in range(rng.randint(30, 60)):
            sx, sy = rng.randint(0, W), rng.randint(0, sky_h-10)
            sr = rng.uniform(0.5, 2.5)
            sa = rng.randint(40, 180)
            _circle(draw, sx, sy, sr, fill_c=(255, 255, 200, sa), line_c=None)

    # ── Elements ──
    for elem in scene.get("elements", []):
        try:
            _draw_element(draw, elem, mood, atmos)
        except Exception as e:
            print(f"    Element error ({elem.get('type','?')}): {e}")

    img = img.filter(ImageFilter.SMOOTH_MORE if hasattr(ImageFilter, 'SMOOTH_MORE') else ImageFilter.SMOOTH)
    return img.convert("RGB")


def _draw_element(draw, elem: dict, mood: str, atmos: dict):
    t = elem.get("type", "")
    x = int(elem.get("x", 0.5) * W)
    y = int(elem.get("y", 0.5) * H)
    color = tuple(elem.get("color", [50, 50, 50]))
    fill_c = elem.get("fill_color")
    if fill_c:
        fill_c = tuple(fill_c + [180])
    sw = int(elem.get("stroke_width", 2))
    opacity = elem.get("opacity", 1.0)
    r = elem.get("radius", 0)
    if r: r = int(r * max(W, H))
    w = elem.get("width", 0)
    h = elem.get("height", 0)
    if w: w = int(w * W)
    if h: h = int(h * H)
    col_with_alpha = color + (int(255 * opacity),)

    if t == "circle":
        _circle(draw, x, y, r if r > 0 else 20, fill_c=fill_c, line_c=col_with_alpha, w=sw)

    elif t == "rect":
        if w == 0: w = 60
        if h == 0: h = 60
        _rect(draw, x-w//2, y-h//2, w, h, fill_c=fill_c, line_c=col_with_alpha, lw=sw)

    elif t == "polygon":
        pts = elem.get("points", [])
        if pts:
            pxs = [(int(p[0]*W), int(p[1]*H)) for p in pts]
            if fill_c:
                _fill(draw, pxs, fill_c, amp=1.5)
            _stroke(draw, pxs + [pxs[0]], w=sw, color=col_with_alpha, amp=1)

    elif t == "arc":
        if w == 0: w = 80
        if h == 0: h = 80
        pts = [(x+math.cos(math.radians(a))*w/2, y+math.sin(math.radians(a))*h/2) for a in range(-90, 91, 10)]
        _stroke(draw, pts, w=sw, color=col_with_alpha, amp=0.8)

    elif t == "text":
        text = elem.get("text", "")
        if text:
            tf = _get_font(int(sw * 10 + 20))
            draw.text((x, y), text, font=tf, fill=col_with_alpha)

    elif t == "mountain":
        mw = w if w > 0 else 200
        mh = h if h > 0 else 120
        pts = [(x-mw//2, y), (x, y-mh), (x+mw//2, y)]
        fc = fill_c or (90, 100, 140, 100)
        _fill(draw, pts, fc, amp=2)
        _stroke(draw, pts, w=sw, color=col_with_alpha, amp=1.5)
        _hatch(draw, x, y-mh//2, mw, mh, spacing=8, color=(40, 40, 60, 25))

    elif t == "tree":
        th = h if h > 0 else 80
        tw = max(w, 6)
        # trunk
        trunk = [(x-tw//2, y), (x-tw//2, y-th), (x+tw//2, y-th), (x+tw//2, y)]
        _fill(draw, trunk, (60, 45, 30, 180), amp=1.5)
        _stroke(draw, trunk, w=2, color=(50, 35, 25), amp=1)
        # crown
        cr = max(r, th * 0.4)
        ccol = fill_c or (50, 90, 50, 80)
        for i in range(rng.randint(3, 5)):
            ox = rng.randint(-int(cr*0.3), int(cr*0.3))
            oy = rng.randint(-int(cr*0.2), int(cr*0.2))
            rr = cr * (0.5 + rng.random() * 0.5)
            _circle(draw, x+ox, y-th+oy, rr, fill_c=ccol, line_c=(40, 70, 30, 150))

    elif t == "human":
        s = max(r, 20) / 20
        # Head
        _circle(draw, x, y-18*s, 6*s, fill_c=(235, 200, 175, int(255*opacity)), line_c=(180, 150, 130, int(255*opacity)))
        # Body
        body = [(x-5*s, y-13*s), (x-4*s, y+3*s), (x+4*s, y+3*s), (x+5*s, y-13*s)]
        bc = fill_c or (80, 70, 120, int(180*opacity))
        _fill(draw, body, bc, amp=1.5)
        _stroke(draw, body, w=2, color=col_with_alpha, amp=1)
        # Arms
        for side in [-1, 1]:
            _stroke(draw, [(x+side*5*s, y-8*s), (x+side*9*s, y-3*s)], w=2, color=col_with_alpha, amp=1)
        # Legs
        for side in [-1, 1]:
            _stroke(draw, [(x+side*3*s, y+3*s), (x+side*5*s, y+8*s)], w=2, color=(70, 60, 50, int(255*opacity)), amp=1)

    elif t == "ship":
        s = max(r, 20) / 20
        st = elem.get("text", "merchant")
        hull_c = (60, 50, 40, int(200*opacity))
        _fill(draw, [(x-30*s, y), (x-25*s, y+12*s), (x+25*s, y+12*s), (x+30*s, y)], hull_c, amp=1.5)
        _stroke(draw, [(x, y), (x, y-40*s)], w=3, color=(50, 40, 30, int(255*opacity)), amp=1)
        if st == "pirate":
            _fill(draw, [(x, y-35*s), (x-22*s, y-8*s), (x, y-3*s)], (30, 30, 30, int(200*opacity)), amp=1.5)
        else:
            _fill(draw, [(x, y-35*s), (x-20*s, y-8*s), (x, y-3*s)], (240, 235, 220, int(180*opacity)), amp=1.5)
        _stroke(draw, [(x, y-35*s), (x-20*s, y-8*s), (x, y-3*s)], w=1.5, color=(100, 95, 85, int(200*opacity)))

    elif t == "cloud":
        s = max(r, 20) / 20 if r else 1.0
        for i in range(rng.randint(3, 5)):
            ox = rng.randint(-15, 15) * s
            oy = rng.randint(-8, 5) * s
            cr = rng.randint(15, 30) * s
            _circle(draw, x+ox, y+oy*0.5, cr, fill_c=(255, 255, 255, rng.randint(60, 100)), line_c=(200, 200, 200, 80))

    elif t == "sun":
        s = max(r, 20) / 20 if r else 1.0
        _circle(draw, x, y, 25*s, fill_c=(255, 200, 50, 100), line_c=(255, 200, 50, 150))
        for a in range(0, 360, 30):
            _stroke(draw, [(x+math.cos(math.radians(a))*30*s, y+math.sin(math.radians(a))*30*s),
                           (x+math.cos(math.radians(a))*40*s, y+math.sin(math.radians(a))*40*s)], w=2, color=(255, 200, 50, 100), amp=0.5)

    elif t == "moon":
        s = max(r, 15) / 15 if r else 1.0
        _circle(draw, x, y, 20*s, fill_c=(240, 235, 210, 80), line_c=(220, 215, 190, 150))

    elif t == "star":
        _circle(draw, x, y, max(r, 3), fill_c=(255, 255, 200, int(150*opacity)), line_c=None)

    elif t == "building":
        bw = max(w, 60)
        bh = max(h, 100)
        bc = fill_c or (120, 100, 80, 150)
        _rect(draw, x-bw//2, y-bh, bw, bh, fill_c=bc, line_c=col_with_alpha, lw=sw)
        # windows
        for wx in range(-bw//4, bw//4, bw//3):
            for wy in range(-bh+15, -10, bh//4):
                _rect(draw, x+wx-5, y+wy-5, 10, 10, fill_c=(255, 220, 100, rng.randint(40, 100)), line_c=(80, 80, 80, 80))

    elif t == "animal":
        s = max(r, 15) / 15
        body_c = fill_c or (150, 120, 80, 180)
        _circle(draw, x, y-8*s, 8*s, fill_c=body_c, line_c=col_with_alpha)
        _circle(draw, x+12*s, y-12*s, 6*s, fill_c=(*body_c[:3], 200), line_c=col_with_alpha)

    elif t == "plant":
        # Simple grass/flower
        _stroke(draw, [(x, y), (x+rng.randint(-2, 2), y-rng.randint(10, 25))], w=2, color=col_with_alpha, amp=0.5)
        if fill_c:
            _circle(draw, x, y-rng.randint(10, 25), 4, fill_c=tuple(fill_c+[180]), line_c=None)

    elif t == "object":
        # Generic object as rounded rect or ellipse
        bw = max(w, 40)
        bh = max(h, 40)
        if fill_c:
            _circle(draw, x, y, min(bw, bh)//2, fill_c=tuple(fill_c+[150]), line_c=col_with_alpha, w=sw)
        else:
            _circle(draw, x, y, min(bw, bh)//2, fill_c=None, line_c=col_with_alpha, w=sw)

    elif t == "abstract":
        # Organic shapes
        for _ in range(rng.randint(3, 6)):
            ox = rng.randint(-30, 30)
            oy = rng.randint(-30, 30)
            rr = rng.randint(10, 30)
            fc = fill_c or (color + (60,))
            _circle(draw, x+ox, y+oy, rr, fill_c=fc, line_c=col_with_alpha, w=1)

    # ── Atmosphere effects ──
    if elem.get("wind"):
        for _ in range(5):
            wx = rng.randint(50, W-50)
            wy = rng.randint(int(H*0.2), int(H*0.5))
            _stroke(draw, [(wx, wy), (wx+rng.randint(20, 40), wy-rng.randint(3, 8))], w=1, color=(150, 140, 130, 60), amp=0.5)

    # Children (sub-elements)
    for child in elem.get("children", []):
        child["x"] = (child.get("x", 0.5) + elem.get("x", 0.5)) / 2
        child["y"] = (child.get("y", 0.5) + elem.get("y", 0.5)) / 2
        _draw_element(draw, child, mood, atmos)


def _rect(draw, x, y, w, h, fill_c=None, line_c=(0,0,0,255), lw=2):
    pts = [(x+rng.gauss(0,1), y+rng.gauss(0,1)), (x+w+rng.gauss(0,1), y+rng.gauss(0,1)),
           (x+w+rng.gauss(0,1), y+h+rng.gauss(0,1)), (x+rng.gauss(0,1), y+h+rng.gauss(0,1))]
    if fill_c: _fill(draw, pts, fill_c, amp=1)
    _stroke(draw, pts+[pts[0]], w=lw, color=line_c, amp=0.8)

# ─── Video builder ─────────────────────────────────────────────

def build_video(script_data: dict, output_path: str):
    scenes = script_data["scenes"]
    title = script_data["title"]

    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"  {len(scenes)} scenes | LLM-driven visual script")
    print(f"{'='*55}")

    temp_dir = config.TEMP_DIR / "auto_story"
    temp_dir.mkdir(exist_ok=True)

    print(f"\n[1/4] Rendering {len(scenes)} hand-drawn scenes...")
    scene_images = []
    for i, scene in enumerate(scenes):
        print(f"  Scene {i+1}: {scene.get('title','')[:30]} [{scene.get('mood','')}]")
        img = render_scene(scene)
        # Overlay title
        rgba = img.convert("RGBA")
        d = ImageDraw.Draw(rgba)
        tf = _get_font(34)
        st = scene.get("title", "").upper()
        tb = d.textbbox((0,0), st, font=tf)
        tw, th = tb[2]-tb[0]+40, tb[3]-tb[1]+20
        d.rounded_rectangle([(W-tw)//2, 35, (W+tw)//2, 35+th], radius=10, fill=(0,0,0,140))
        d.text(((W-(tb[2]-tb[0]))//2, 43), st, font=tf, fill=(255,255,255,230))
        # Badge
        sf = _get_font(18)
        sn = f"{i+1:02d}"
        d.rounded_rectangle([20, 20, 58, 46], radius=8, fill=(0,0,0,120))
        d.text((27, 24), sn, font=sf, fill=(255,255,255,200))
        scene_images.append(np.array(rgba.convert("RGB")))

    print(f"\n[2/4] Generating narration...")
    full_script = " ".join(s["narration"] for s in scenes)
    tts_path = temp_dir / "narration.mp3"
    words = generate_tts_with_timestamps(full_script, tts_path)
    total_dur = words[-1]["end"] if words else 8.0
    print(f"  {total_dur:.1f}s | {len(words)} words")

    print(f"\n[3/4] Building timeline...")
    timeline = []
    global_wi = 0
    for i, scene in enumerate(scenes):
        sw = scene["narration"].split()
        ws = global_wi
        we = min(ws + len(sw) - 1, len(words) - 1)
        timeline.append({"image": scene_images[i], "start": words[ws]["start"],
                         "end": words[we]["end"], "word_start": ws, "word_end": we})
        global_wi = we + 1

    print(f"\n[4/4] Rendering video...")
    TD, ED = 2.5, 2.0
    vdur = total_dur + TD + ED
    bg = np.full((H, W, 3), 248, dtype=np.uint8)

    # Title card
    ti = Image.new("RGB", (W, H), (252, 250, 245))
    td = ImageDraw.Draw(ti)
    tf = _get_font(46)
    tlines = []
    cur = ""
    for w in title.split():
        test = (cur+" "+w).strip()
        tb = td.textbbox((0,0), test, font=tf)
        if tb[2]-tb[0] > W-80: tlines.append(cur); cur = w
        else: cur = test
    tlines.append(cur)
    y = H//2-60
    for line in tlines:
        tb = td.textbbox((0,0), line, font=tf)
        td.text(((W-(tb[2]-tb[0]))//2, y), line, font=tf, fill=(40,35,30)); y += 70
    sf = _get_font(22)
    sub = "A HAND-DRAWN DOCUMENTARY"
    tb = td.textbbox((0,0), sub, font=sf)
    td.text(((W-(tb[2]-tb[0]))//2, H-150), sub, font=sf, fill=(140,130,120))
    ta = np.array(ti)

    trans = {}
    for i in range(len(scene_images)-1):
        frames = []
        for fi in range(int(0.5*FPS)):
            t = fi/(int(0.5*FPS)); e = t*t*(3-2*t)
            frames.append(((1-e)*scene_images[i].astype(np.float32)+e*scene_images[i+1].astype(np.float32)).astype(np.uint8))
        trans[i] = frames

    def mf(t):
        if t < TD:
            p = t/TD; a = int(255*p*p*(3-2*p))
            if a < 255: return ((bg.astype(np.float32)*(255-a)+ta.astype(np.float32)*a)/255).astype(np.uint8)
            return ta
        tr = t-TD
        if tr > total_dur: return bg
        act = None; ai = -1
        for i, s in enumerate(timeline):
            if s["start"] <= tr < s["end"]: act, ai = s, i; break
        if act is None:
            for i, s in reversed(list(enumerate(timeline))):
                if tr >= s["end"]: act, ai = s, i; break
        if act is None: return bg
        base = act["image"].copy()
        if ai < len(timeline)-1 and abs(timeline[ai+1]["start"]-act["end"])<0.05:
            tt = tr-act["end"]
            if 0 <= tt < 0.5 and ai in trans:
                fi = min(int(tt*FPS), len(trans[ai])-1)
                base = trans[ai][fi]
        cw = -1
        for wi in range(act["word_start"], min(act["word_end"]+1, len(words))):
            if words[wi]["start"] <= tr: cw = wi; break
        cap = Image.fromarray(base)
        cd = ImageDraw.Draw(cap)
        ov = Image.new("RGBA", (W, 100), (0,0,0,180))
        cap.paste(ov, (0, H-110), ov)
        ft = _get_font(30); hf = _get_font(34)
        ws = [words[wi]["text"] for wi in range(act["word_start"], min(act["word_end"]+1, len(words)))]
        x, y, lh = 15, H-95, 48
        for i, w in enumerate(ws):
            wi = act["word_start"]+i
            f = hf if wi == cw else ft
            c = (255,220,80) if wi == cw else (255,255,255)
            dw = " "+w+" "
            bb = cd.textbbox((0,0), dw, font=f); ww = bb[2]-bb[0]
            if x+ww > W-15: x, lh = 15, lh+48
            if wi == cw: cd.rounded_rectangle([x-4, lh-2, x+ww+4, lh+42], radius=5, fill=(200,80,60,180))
            cd.text((x, lh), dw, font=f, fill=c); x += ww
        return np.array(cap)

    clip = VideoClip(mf, duration=vdur)
    audio = AudioFileClip(str(tts_path))
    if vdur > audio.duration+TD:
        s = AudioFileClip(str(tts_path)).with_duration(vdur-audio.duration-TD).with_volume_scaled(0)
        audio = concatenate_audioclips([audio, s])
    music = list(config.MUSIC_DIR.glob("*.mp3"))
    if music:
        m = AudioFileClip(str(random.choice(music))).with_duration(vdur).with_volume_scaled(0.04)
        audio = CompositeAudioClip([audio, m])
    try:
        ec = subscribe_end_card(np.full((H,W,3), 240, dtype=np.uint8), ED)
        ec = ec.with_start(total_dur+TD)
        final = CompositeVideoClip([clip, ec], size=config.SHORTS_SIZE).with_audio(audio)
    except: final = clip.with_audio(audio)
    t0 = time.time()
    final.write_videofile(str(output_path), fps=FPS, codec="libx264", audio_codec="aac",
                          threads=4, preset="medium", ffmpeg_params=["-movflags", "+faststart", "-crf", "18"], logger=None)
    final.close()
    print(f"\n  Done in {time.time()-t0:.0f}s: {output_path} ({os.path.getsize(output_path):,} bytes)")

def main():
    topic = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "why the sky is blue"
    print(f"Topic: {topic}")
    print("\n[1/4] Generating LLM visual script...")
    script = generate_visual_script(topic)
    for s in script["scenes"]:
        print(f"  {s['scene_num']}. {s['title']}: {s['narration'][:60]}... [{s['mood']}]")
    safe = re.sub(r'[^\w]+', '_', topic.lower())[:40]
    out = config.OUTPUT_DIR / f"auto_story_{safe}.mp4"
    build_video(script, out)

if __name__ == "__main__":
    main()
