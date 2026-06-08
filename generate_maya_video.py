"""Generate Maya civilization storyboard video with all 17 scenes."""
import sys, os, json, subprocess, math, random, textwrap
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageDraw, ImageFont
from src.sketch_generator import SketchGenerator
import warnings
warnings.filterwarnings("ignore")

W, H = 1280, 720
FPS = 30
DURATION_PER_SCENE = 5.0  # seconds per scene
FRAMES_PER_SCENE = int(DURATION_PER_SCENE * FPS)

out_dir = os.path.join(os.path.dirname(__file__), "maya_video")
os.makedirs(out_dir, exist_ok=True)
frames_dir = os.path.join(out_dir, "frames")
os.makedirs(frames_dir, exist_ok=True)

rng = random.Random(42)

# ─── Scenes ───
SCENES = [
    {"narration": "Imagine waking up in one of the greatest cities on Earth.",
     "visual": "Blank parchment background. Simple jungle outline. Huge pyramid slowly drawn. Small Maya city appears. Tiny people walking.",
     "elements": ["pyramid", "tree", "sun", "house", "human"],
     "bg": "parchment"},
    {"narration": "Massive stone pyramids rise above the jungle.",
     "visual": "Camera pans upward. Pyramid grows larger. Priests standing at top. Smoke drifting upward.",
     "elements": ["pyramid", "smoke", "tree", "mountain", "human"],
     "bg": "jungle"},
    {"narration": "Astronomers track the stars.",
     "visual": "Night sky sketch. Maya astronomer looking upward. Constellations connected by drawn lines. Calendar symbols appear.",
     "elements": ["star", "moon", "human", "circle"],
     "bg": "night"},
    {"narration": "What happened to the Maya?",
     "visual": "Flourishing city. Record scratch effect. Scene freezes. Question mark drawn over city.",
     "elements": ["house", "building", "question_mark", "sun"],
     "bg": "day"},
    {"narration": "Then, around the 800s AD, something strange began to happen.",
     "visual": "Timeline appears. Arrow moves forward. Buildings begin fading.",
     "elements": ["line", "arrow", "building", "house"],
     "bg": "fade"},
    {"narration": "One by one, major cities stopped building monuments.",
     "visual": "Workers carrying stones. They slowly disappear. Half-built temple remains unfinished.",
     "elements": ["human", "rock", "building", "mountain"],
     "bg": "construction"},
    {"narration": "Royal palaces were abandoned.",
     "visual": "Empty throne. Wind blowing leaves. Cracks appear in walls.",
     "elements": ["throne", "leaf", "wall", "line"],
     "bg": "abandoned"},
    {"narration": "Was it war?",
     "visual": "Two Maya cities facing each other. Spears and shields appear. Small battle silhouettes.",
     "elements": ["human", "fire", "building", "arrow"],
     "bg": "war"},
    {"narration": "Evidence suggests the Maya faced severe droughts.",
     "visual": "Bright sun enlarges. River shrinks. Ground cracks open.",
     "elements": ["sun", "line", "desert"],
     "bg": "drought"},
    {"narration": "Years without enough rain meant crops failed.",
     "visual": "Green corn field. Gradually turns brown. Plants wilt.",
     "elements": ["tree", "sun", "grass"],
     "bg": "field"},
    {"narration": "Food became scarce.",
     "visual": "Empty baskets. Families looking worried. Grain supply shrinking.",
     "elements": ["circle", "human", "house"],
     "bg": "village"},
    {"narration": "As resources shrank, rival city-states fought.",
     "visual": "Map of Maya region. Arrows showing conflicts. Fires appear on city icons.",
     "elements": ["map", "arrow", "fire", "house"],
     "bg": "map_bg"},
    {"narration": "Large forests had been cleared.",
     "visual": "Dense jungle. Trees vanish one by one. Stumps remain.",
     "elements": ["tree", "stump", "grass"],
     "bg": "deforestation"},
    {"narration": "Eventually, many people left.",
     "visual": "Families walking away. City shrinking behind them. Footprints leading into jungle.",
     "elements": ["human", "footprint", "tree", "path"],
     "bg": "exodus"},
    {"narration": "The jungle slowly reclaimed them.",
     "visual": "Vines crawl over pyramid. Trees grow through buildings. Temple nearly hidden.",
     "elements": ["tree", "building", "mountain", "grass"],
     "bg": "reclaim"},
    {"narration": "But here's the biggest misconception. The Maya did not vanish.",
     "visual": "Ancient Maya figure transforms into modern Maya family. Timeline connects past to present.",
     "elements": ["human", "child", "line", "sun"],
     "bg": "reveal"},
    {"narration": "The cities fell. The people remained.",
     "visual": "Split screen: Left ruined temple, Right modern Maya descendants. Fade to sunset.",
     "elements": ["building", "human", "sun", "tree"],
     "bg": "sunset_split"},
]


def add_text(draw, text, y=H-60, font_size=22, fill=(50, 45, 40)):
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", font_size)
    except:
        font = ImageFont.load_default()
    lines = textwrap.wrap(text, width=60)
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(((W - tw)//2, y + i*(font_size+4)), line, fill=fill, font=font)


def add_pyramid(draw, cx, cy, w, h, color=(180, 150, 120), steps=False):
    """Draw a step pyramid silhouette."""
    if steps:
        levels = 5
        for i in range(levels):
            lw = w * (1 - i/levels)
            lh = h / levels
            ly = cy - h + i * lh
            lx = cx - lw/2
            rgb = tuple(min(255, int(c * (1 - i * 0.04))) for c in color)
            draw.rectangle([lx, ly, lx+lw, ly+lh], fill=rgb+(220,), outline=(60,55,50,180), width=2)
    else:
        pts = [(cx, cy-h), (cx-w//2, cy), (cx+w//2, cy)]
        draw.polygon(pts, fill=color+(220,), outline=(60,55,50,180), width=3)
        # Inner detail lines
        mid = (cx - w//6, cy - h//2)
        draw.line([(cx-w//4, cy), mid, (cx+w//4, cy)], fill=(100,90,80,150), width=1)


def add_temple(draw, cx, cy, w, h, color=(160, 130, 100)):
    """Draw a Maya temple with roof comb."""
    # Base platform
    draw.rectangle([cx-w//2, cy-h//4, cx+w//2, cy], fill=color+(220,), outline=(60,55,50,180), width=2)
    # Upper platform
    u = int(w * 0.75)
    draw.rectangle([cx-u//2, cy-h//2, cx+u//2, cy-h//4], fill=color+(220,), outline=(60,55,50,180), width=2)
    # Roof comb (crest at top)
    rc_w = int(w * 0.4)
    rc_h = int(h * 0.3)
    draw.rectangle([cx-rc_w//2, cy-h//2-rc_h, cx+rc_w//2, cy-h//2], fill=color+(200,), outline=(60,55,50,180), width=2)
    # Doorway
    dw, dh = int(w*0.2), int(h*0.25)
    draw.rectangle([cx-dw//2, cy-dh, cx+dw//2, cy], fill=(30,25,20,200))
    # Steps
    for i in range(3):
        sy = cy - i * (h//12)
        sw = int(w * (0.4 - i * 0.08))
        draw.line([(cx-sw//2, sy), (cx+sw//2, sy)], fill=(60,55,50,180), width=2)


def add_throne(draw, cx, cy, w, h, color=(140, 100, 70)):
    """Draw a simple throne."""
    # Seat
    draw.rectangle([cx-w//2, cy-h//4, cx+w//2, cy], fill=color+(220,), outline=(40,35,30,180), width=2)
    # Back
    bw = int(w * 0.6)
    draw.rectangle([cx-bw//2, cy-h, cx+bw//2, cy-h//4], fill=color+(200,), outline=(40,35,30,180), width=2)
    # Armrests
    for side in [-1, 1]:
        ax = cx + side * w//2
        draw.rectangle([ax-3, cy-h//2-5, ax+3, cy-5], fill=color+(200,), outline=(40,35,30,180), width=1)


def add_stump(draw, cx, cy, w, color=(100, 80, 60)):
    """Draw a tree stump."""
    draw.rectangle([cx-w//4, cy-w, cx+w//4, cy], fill=color+(220,), outline=(40,35,30,180), width=2)
    # Rings on top
    draw.ellipse([cx-w//4, cy-w-w//8, cx+w//4, cy-w+w//8], fill=color+(200,), outline=(60,55,50,150), width=1)
    draw.ellipse([cx-w//8, cy-w-w//16, cx+w//8, cy-w+w//16], outline=(60,55,50,120), width=1)


def add_cracked_earth(draw, cx, cy, w, h):
    """Draw cracked/dry ground pattern."""
    draw.rectangle([cx-w//2, cy-h//2, cx+w//2, cy+h//2], fill=(180, 160, 130, 200), outline=(60,55,50,150), width=1)
    # Crack lines
    for _ in range(8):
        sx = cx + rng.randint(-w//2, w//2)
        sy = cy + rng.randint(-h//2, h//2)
        for _ in range(3):
            ex = sx + rng.randint(-20, 20)
            ey = sy + rng.randint(-15, 15)
            draw.line([(sx, sy), (ex, ey)], fill=(100, 85, 70, 200), width=2)
            sx, sy = ex, ey


def add_question_mark(draw, cx, cy, size=40, color=(200, 50, 50)):
    """Draw a large question mark."""
    pts = [(cx-size//4, cy-size//2), (cx+size//4, cy-size//2),
           (cx+size//3, cy-size//4), (cx+size//4, cy),
           (cx, cy+5), (cx-size//6, cy+size//3)]
    draw.line(pts, fill=color+(200,), width=int(size/8))
    draw.ellipse([cx-size//6, cy+size//2-3, cx+size//6, cy+size//2+3], fill=color+(220,))


def add_heat_waves(draw, cx, cy, count=3):
    """Draw wavy heat lines."""
    for i in range(count):
        y = cy - i * 15
        pts = []
        for x in range(cx-40, cx+41, 5):
            pts.append((x, y + 8 * math.sin((x + i*20) * 0.1)))
        if len(pts) > 1:
            draw.line(pts, fill=(200, 180, 100, 150), width=1)


def add_timeline(draw, cx, cy, w):
    """Draw a horizontal timeline with dots."""
    draw.line([(cx-w//2, cy), (cx+w//2, cy)], fill=(60,55,50,200), width=3)
    for i in range(6):
        x = cx - w//2 + int(w * i / 5)
        draw.ellipse([x-4, cy-4, x+4, cy+4], fill=(120, 80, 50, 220))
    # Arrow at end
    draw.polygon([(cx+w//2-15, cy-6), (cx+w//2-15, cy+6), (cx+w//2, cy)], fill=(60,55,50,200))


def add_sunset_gradient(draw, cx, cy, w, h):
    """Draw sunset sky gradient."""
    for i in range(h):
        t = i / h
        r = int(255 * (1 - t * 0.5))
        g = int(200 * (1 - t * 0.7))
        b = int(150 * (1 - t * 0.9))
        draw.line([(cx-w//2, cy-h//2+i), (cx+w//2, cy-h//2+i)], fill=(r, g, b, 220))


def add_smoke(draw, cx, cy, count=5):
    """Draw smoke puffs."""
    for i in range(count):
        r = 10 + i * 8
        alpha = max(30, 150 - i * 25)
        draw.ellipse([cx-r+ rng.randint(-5,5), cy-i*20-r, cx+r+ rng.randint(-5,5), cy-i*20+r],
                     fill=(180, 170, 160, alpha))


# ─── Generate Frames ───
print(f"Generating {len(SCENES)} scenes × {FRAMES_PER_SCENE} frames each...")
all_paths = []

for scene_idx, scene in enumerate(SCENES):
    narration = scene["narration"]
    bg_type = scene["bg"]
    elems = scene["elements"]
    parts = []
    
    for frame_num in range(FRAMES_PER_SCENE):
        t = frame_num / FRAMES_PER_SCENE  # 0..1 progress
        
        canvas = Image.new("RGBA", (W, H), (255, 255, 255, 255))
        draw = ImageDraw.Draw(canvas)
        
        # ── Background ──
        if bg_type == "parchment":
            canvas = Image.new("RGBA", (W, H), (245, 235, 210, 255))
            draw = ImageDraw.Draw(canvas)
        elif bg_type == "jungle":
            for i in range(H):
                g = int(120 + 80 * (1 - i/H))
                draw.line([(0, i), (W, i)], fill=(30, g, 50, 255))
        elif bg_type == "night":
            for i in range(H):
                v = int(30 * (1 - i/H))
                draw.line([(0, i), (W, i)], fill=(v, v, v+10, 255))
            # Stars
            for _ in range(60):
                sx = rng.randint(0, W)
                sy = rng.randint(0, H//2)
                sr = rng.uniform(1, 2.5)
                draw.ellipse([sx-sr, sy-sr, sx+sr, sy+sr], fill=(255, 255, 220, rng.randint(150, 255)))
        elif bg_type == "day":
            for i in range(H):
                b = int(200 - 80 * i/H)
                draw.line([(0, i), (W, i)], fill=(100, 160, b, 255))
            # Ground
            draw.rectangle([0, H//2+60, W, H], fill=(60, 130, 60, 255))
        elif bg_type == "fade":
            for i in range(H):
                v = int(180 - 60 * i/H)
                draw.line([(0, i), (W, i)], fill=(v, v-30, v-40, 255))
            draw.rectangle([0, H//2+60, W, H], fill=(100, 120, 100, 200))
        elif bg_type == "drought":
            for i in range(H):
                v = int(220 - 120 * i/H)
                draw.line([(0, i), (W, i)], fill=(v, v-40, v-80, 255))
            draw.rectangle([0, H//2+100, W, H], fill=(180, 150, 100, 255))
            # Cracked ground
            add_cracked_earth(draw, W//2, H-80, W-100, 120)
        elif bg_type == "field":
            for i in range(H):
                g = int(180 - 80 * i/H)
                draw.line([(0, i), (W, i)], fill=(g, min(255, g+50), g-50, 255))
            draw.rectangle([0, H//2+40, W, H], fill=(80, 160, 60, 255))
        elif bg_type == "war":
            for i in range(H):
                v = int(100 + 40 * math.sin(i*0.05))
                draw.line([(0, i), (W, i)], fill=(v, v-20, v-30, 255))
            draw.rectangle([0, H//2+80, W, H], fill=(120, 90, 70, 255))
        elif bg_type == "construction":
            for i in range(H):
                v = int(160 + 40 * math.sin(i*0.03))
                draw.line([(0, i), (W, i)], fill=(v, v-20, v-30, 255))
            draw.rectangle([0, H//2+80, W, H], fill=(140, 120, 100, 255))
        elif bg_type == "abandoned":
            for i in range(H):
                v = int(140 - 40 * i/H)
                draw.line([(0, i), (W, i)], fill=(v, v-10, v-20, 255))
            draw.rectangle([0, H//2+80, W, H], fill=(110, 100, 90, 255))
        elif bg_type == "village":
            for i in range(H):
                v = int(180 - 60 * i/H)
                draw.line([(0, i), (W, i)], fill=(v-20, v, v-30, 255))
            draw.rectangle([0, H//2+80, W, H], fill=(120, 100, 80, 255))
        elif bg_type == "deforestation":
            for i in range(H):
                v = int(150 - 50 * i/H)
                draw.line([(0, i), (W, i)], fill=(v-20, v, v-40, 255))
            draw.rectangle([0, H//2+60, W, H], fill=(100, 120, 80, 255))
        elif bg_type == "exodus":
            for i in range(H):
                v = int(160 - 40 * i/H)
                draw.line([(0, i), (W, i)], fill=(v, v-10, v-15, 255))
            draw.rectangle([0, H//2+80, W, H], fill=(100, 130, 80, 255))
        elif bg_type == "reclaim":
            for i in range(H):
                g = int(100 + 80 * (1 - i/H))
                draw.line([(0, i), (W, i)], fill=(30, g, 40, 255))
        elif bg_type == "map_bg":
            canvas = Image.new("RGBA", (W, H), (200, 190, 170, 255))
            draw = ImageDraw.Draw(canvas)
            # Map grid
            for x in range(0, W, 60):
                draw.line([(x, 0), (x, H)], fill=(180, 170, 150, 100), width=1)
            for y in range(0, H, 60):
                draw.line([(0, y), (W, y)], fill=(180, 170, 150, 100), width=1)
        elif bg_type == "reveal":
            for i in range(H):
                v = int(130 + 80 * (1 - i/H))
                draw.line([(0, i), (W, i)], fill=(v-10, v, v-20, 255))
            draw.rectangle([0, H//2+60, W, H], fill=(80, 150, 80, 255))
        elif bg_type == "sunset_split":
            # Split: left ruins, right modern
            add_sunset_gradient(draw, W//2, H//2, W, H)
            # Left side shadow
            draw.rectangle([0, 0, W//2, H], fill=(0, 0, 0, 40))
            # Divider line
            draw.line([(W//2, 0), (W//2, H)], fill=(255, 200, 100, 150), width=3)
        
        # ── Elements ──
        progress = t  # 0 to 1 for animation
        
        for elem in elems:
            if elem == "pyramid":
                px = W//2
                py = H//2 + 100
                pw = 200
                ph = 250
                # Animate drawing (grow from bottom)
                ph_vis = int(ph * min(1, progress * 1.5))
                add_pyramid(draw, px, py, pw, ph_vis, steps=progress > 0.3)
            
            elif elem == "tree":
                for tx_off, scale in [(0.2, 3.0), (0.8, 2.5), (0.35, 2.0)]:
                    tx = int(W * (tx_off + rng.uniform(-0.02, 0.02)))
                    ty = H//2 + 80 + rng.randint(-20, 20)
                    if progress > 0.1:
                        try:
                            gen = SketchGenerator(W, H)
                            gen.draw_tree(draw, tx, ty, scale * (0.8 + 0.2 * min(1, progress*2)),
                                         rng.choice(["round", "pine"]), (50, 140, 50))
                        except Exception as e:
                            draw.rectangle([tx-5, ty-40, tx+5, ty], fill=(60, 50, 40, 220))
                            draw.ellipse([tx-20, ty-60, tx+20, ty-30], fill=(50, 130, 50, 220))
            
            elif elem == "sun":
                sx = W - 100
                sy = 100
                # Animate sun size for drought scene
                sun_r = 30 if bg_type != "drought" else 30 + 15 * progress
                draw.ellipse([sx-sun_r, sy-sun_r, sx+sun_r, sy+sun_r],
                            fill=(255, 220, 60, 230), outline=(255, 180, 0, 200), width=3)
                # Rays
                for angle in range(0, 360, 30):
                    rad = math.radians(angle)
                    r1 = sun_r + 8
                    r2 = sun_r + 18
                    ax = sx + r1 * math.cos(rad)
                    ay = sy + r1 * math.sin(rad)
                    bx = sx + r2 * math.cos(rad)
                    by = sy + r2 * math.sin(rad)
                    draw.line([(ax, ay), (bx, by)], fill=(255, 200, 50, 180), width=2)
            
            elif elem == "house":
                for hx_off in [0.3, 0.7]:
                    hx = int(W * hx_off)
                    hy = H//2 + 80
                    hw, hh = 50, 40
                    draw.rectangle([hx-hw//2, hy-hh, hx+hw//2, hy],
                                  fill=(160, 140, 120, 220), outline=(60,55,50,180), width=2)
                    draw.polygon([(hx-hw//2-5, hy-hh), (hx, hy-hh-25), (hx+hw//2+5, hy-hh)],
                                fill=(120, 80, 50, 220), outline=(60,55,50,180), width=2)
                    # Door
                    draw.rectangle([hx-8, hy-20, hx+8, hy], fill=(40, 35, 30, 220))
                    if bg_type in ("day", "village"):
                        window_color = (255, 220, 100, 200)
                    else:
                        window_color = (180, 160, 120, 150)
                    draw.rectangle([hx-18, hy-25, hx-6, hy-15], fill=window_color)
                    draw.rectangle([hx+6, hy-25, hx+18, hy-15], fill=window_color)
            
            elif elem == "human":
                for human_x in [0.4, 0.6]:
                    hx = int(W * human_x)
                    hy = H//2 + 70
                    try:
                        gen_small = SketchGenerator(W, H)
                        gen_small.draw_human(draw, hx, hy, size=2.5, color=(120, 80, 50),
                                            skin_color=(200, 170, 150), gender="man", mood="peaceful",
                                            pose="walking" if bg_type in ("exodus", "war") else "standing")
                    except:
                        # Simple stick figure fallback
                        draw.ellipse([hx-6, hy-30, hx+6, hy-18], fill=(200, 170, 150, 220))
                        draw.line([(hx, hy-18), (hx, hy)], fill=(60, 55, 50, 200), width=3)
                        draw.line([(hx, hy-12), (hx-10, hy-20)], fill=(60, 55, 50, 200), width=2)
                        draw.line([(hx, hy-12), (hx+10, hy-20)], fill=(60, 55, 50, 200), width=2)
                        draw.line([(hx, hy), (hx-8, hy+15)], fill=(60, 55, 50, 200), width=2)
                        draw.line([(hx, hy), (hx+8, hy+15)], fill=(60, 55, 50, 200), width=2)
            
            elif elem == "building":
                for bx_off in [0.25, 0.75]:
                    bx = int(W * bx_off)
                    by = H//2 + 80
                    bw, bh = 60, 80 + rng.randint(-20, 20)
                    # Fade effect for certain scenes
                    fade = 1.0
                    if bg_type == "fade":
                        fade = max(0.2, 1.0 - progress * 0.8)
                    alpha = int(220 * fade)
                    draw.rectangle([bx-bw//2, by-bh, bx+bw//2, by],
                                  fill=(150, 120, 100, alpha), outline=(60,55,50,min(180, alpha)), width=2)
                    # Roof
                    draw.polygon([(bx-bw//2-5, by-bh), (bx, by-bh-20), (bx+bw//2+5, by-bh)],
                                fill=(120, 80, 50, alpha), outline=(60,55,50,min(180, alpha)), width=2)
                    # Windows
                    draw.rectangle([bx-18, by-bh+10, bx-6, by-bh+25], fill=(200, 180, 150, alpha))
                    draw.rectangle([bx+6, by-bh+10, bx+18, by-bh+25], fill=(200, 180, 150, alpha))
            
            elif elem == "mountain":
                mx = W//2 - 150
                my = H//2 + 80
                mw, mh = 180, 140
                pts = [(mx, my-mh), (mx-mw//2, my), (mx+mw//2, my)]
                draw.polygon(pts, fill=(100, 130, 110, 200), outline=(60,55,50,180), width=2)
                # Snow cap
                snow_pts = [(mx, my-mh), (mx-mw//8, my-mh+30), (mx+mw//8, my-mh+30)]
                draw.polygon(snow_pts, fill=(240, 240, 250, 200))
            
            elif elem == "star":
                for _ in range(10):
                    sx = rng.randint(50, W-50)
                    sy = rng.randint(30, H//3)
                    sr = rng.uniform(1, 3)
                    draw.ellipse([sx-sr, sy-sr, sx+sr, sy+sr], fill=(255, 255, 200, rng.randint(150, 255)))
                # Constellation lines
                const_pts = [(100, 80), (200, 120), (150, 160), (250, 180), (300, 100)]
                for i in range(len(const_pts)-1):
                    draw.line([const_pts[i], const_pts[i+1]], fill=(255, 255, 200, 120), width=1)
            
            elif elem == "moon":
                draw.ellipse([W-180, 50, W-100, 130], fill=(220, 220, 200, 220))
                draw.ellipse([W-170, 55, W-110, 120], fill=(30, 30, 40, 255))
            
            elif elem == "circle":
                # Calendar symbol
                cx_elem, cy_elem = W//2 + 80, H//2 - 80
                draw.ellipse([cx_elem-25, cy_elem-25, cx_elem+25, cy_elem+25], outline=(60,55,50,200), width=2)
                draw.ellipse([cx_elem-30, cy_elem-30, cx_elem+30, cy_elem+30], outline=(60,55,50,150), width=1)
                draw.text((cx_elem-15, cy_elem-8), "📅", fill=(60,55,50))
            
            elif elem == "question_mark":
                add_question_mark(draw, W//2, H//2 - 40, size=80)
            
            elif elem == "line":
                # Timeline
                add_timeline(draw, W//2, H-80, W-200)
            
            elif elem == "arrow":
                # Conflict arrows (map)
                ax, ay = W//4, H//3
                bx, by = 3*W//4, H//3
                draw.line([(ax, ay), (bx, by)], fill=(200, 60, 50, 200), width=3)
                # Arrowhead
                draw.polygon([(bx-15, by-6), (bx-15, by+6), (bx, by)], fill=(200, 60, 50, 200))
                # Counter arrow
                draw.line([(bx-50, by+20), (ax+50, ay+20)], fill=(200, 60, 50, 150), width=2, dash=[5,3])
            
            elif elem == "fire":
                # Fire on city
                fx, fy = W//2, H//2 + 40
                for i in range(5):
                    fw = 15 + i * 8
                    fh = 20 + i * 12
                    fy_off = -i * 8
                    draw.ellipse([fx-fw//2, fy+fh//2+fy_off, fx+fw//2, fy-fh+fy_off],
                                fill=(255, random.randint(100,200), 0, 180-i*20))
            
            elif elem == "rock":
                # Stone blocks
                for _ in range(3):
                    rx = rng.randint(W//2-100, W//2+50)
                    ry = H//2 + 80 + rng.randint(-20, 20)
                    draw.rectangle([rx-15, ry-12, rx+15, ry+12],
                                  fill=(140, 130, 120, 220), outline=(60,55,50,180), width=2)
            
            elif elem == "leaf":
                for _ in range(5):
                    lx = rng.randint(50, W-50)
                    ly = rng.randint(100, H-100)
                    draw.ellipse([lx-4, ly-3, lx+4, ly+3], fill=(140, 180, 60, 180))
            
            elif elem == "wall":
                wx, wy = W//2, H//2 + 60
                draw.rectangle([wx-120, wy-60, wx+120, wy+20],
                              fill=(140, 120, 100, 220), outline=(60,55,50,180), width=2)
                # Cracks
                for _ in range(4):
                    cx1 = wx + rng.randint(-100, 100)
                    cy1 = wy - 50 + rng.randint(0, 60)
                    cx2 = cx1 + rng.randint(-20, 20)
                    cy2 = cy1 + rng.randint(10, 30)
                    draw.line([(cx1, cy1), (cx2, cy2)], fill=(60, 55, 50, 200), width=2)
                    draw.line([(cx2, cy2), (cx2+rng.randint(-15,15), cy2+rng.randint(10,20))], fill=(60, 55, 50, 180), width=1)
            
            elif elem == "desert":
                for i in range(H//2):
                    t = i / (H//2)
                    r = int(220 - 100 * t)
                    g = int(200 - 100 * t)
                    b = int(150 - 100 * t)
                    draw.line([(0, H//2+i), (W, H//2+i)], fill=(r, g, b))
                # Dunes
                for dx in range(0, W, 60):
                    dy = H//2+40 + 20 * math.sin(dx * 0.02)
                    draw.arc([dx-30, dy-15, dx+30, dy+15], 0, 180, fill=(200, 180, 130, 180), width=3)
            
            elif elem == "grass":
                for _ in range(20):
                    gx = rng.randint(20, W-20)
                    gy = H//2 + 70 + rng.randint(-10, 20)
                    gh = rng.randint(8, 18)
                    draw.line([(gx, gy), (gx-rng.randint(-3,3), gy-gh)], fill=(60, 140, 60, 180), width=2)
            
            elif elem == "stump":
                add_stump(draw, W//4, H//2+70, 30)
                add_stump(draw, 3*W//4, H//2+80, 25)
            
            elif elem == "map":
                # Draw simple region map
                for region in [(W//3, H//3, 80, 60), (2*W//3, H//3+20, 60, 50), (W//2, H//3-10, 50, 40)]:
                    rx, ry, rw, rh = region
                    draw.rectangle([rx-rw//2, ry-rh//2, rx+rw//2, ry+rh//2],
                                  fill=(160, 140, 110, 180), outline=(100, 80, 60, 200), width=2)
                    draw.text((rx-15, ry-5), "🛕", fill=(80, 60, 40))
            
            elif elem == "footprint":
                for fx_off in [0.3, 0.35, 0.4, 0.45]:
                    fx = int(W * fx_off)
                    fy = H//2 + 100
                    draw.ellipse([fx-5, fy-10, fx+8, fy+2], fill=(100, 90, 80, 150))
                    draw.ellipse([fx-2, fy-14, fx+5, fy-8], fill=(100, 90, 80, 150))
                    for toe in [-1, 0, 1]:
                        draw.ellipse([fx+toe*2-1, fy-4, fx+toe*2+1, fy], fill=(100, 90, 80, 120))
            
            elif elem == "path":
                draw.line([(W//4, H-20), (W//2, H//2+100), (3*W//4, H//2+80)],
                         fill=(110, 100, 90, 180), width=4)
            
            elif elem == "throne":
                add_throne(draw, W//2, H//2+80, 80, 120)
            
            elif elem == "smoke":
                if progress > 0.2:
                    add_smoke(draw, W//2 + 80, H//2, count=int(5 * min(1, progress*2)))
            
            elif elem == "child":
                cx_elem = W//2 + 100
                cy_elem = H//2 + 70
                try:
                    gen_small = SketchGenerator(W, H)
                    gen_small.draw_human(draw, cx_elem, cy_elem, size=1.8, color=(80, 120, 80),
                                        skin_color=(220, 190, 170), gender="child", mood="peaceful")
                except:
                    draw.ellipse([cx_elem-4, cy_elem-18, cx_elem+4, cy_elem-10], fill=(220, 190, 170, 220))
                    draw.line([(cx_elem, cy_elem-10), (cx_elem, cy_elem+5)], fill=(60,55,50,200), width=2)
        
        # ── Narration text at bottom ──
        add_text(draw, narration, y=H-50, font_size=24, fill=(60, 55, 50))
        
        # ── Scene label ──
        draw.text((15, 12), f"Scene {scene_idx+1}", fill=(80, 75, 70, 180), font=ImageFont.load_default())
        
        # Save frame
        fpath = os.path.join(frames_dir, f"scene_{scene_idx:03d}_frame_{frame_num:04d}.png")
        canvas.save(fpath)
        parts.append(fpath)
    
    all_paths.extend(parts)
    print(f"  Scene {scene_idx+1}/{len(SCENES)} done")

print(f"\nAll {len(all_paths)} frames generated. Creating video...")

# ─── Assemble Video ───
video_path = os.path.join(out_dir, "maya_video.mp4")
scene_duration = f"{DURATION_PER_SCENE}"
scene_frames = FRAMES_PER_SCENE

# Build ffmpeg concat file
concat_path = os.path.join(out_dir, "concat.txt")
with open(concat_path, "w") as f:
    for scene_idx in range(len(SCENES)):
        # Each scene gets a clip with proper duration
        pattern = os.path.join(frames_dir, f"scene_{scene_idx:03d}_frame_%04d.png")
        f.write(f"file '{pattern}'\n")
        f.write(f"duration {scene_duration}\n")
    # Last frame needs file again for ffmpeg
    f.write(f"file '{os.path.join(frames_dir, f'scene_{len(SCENES)-1:03d}_frame_{FRAMES_PER_SCENE-1:04d}.png')}'")

# Use ffmpeg with image sequence concat
# First create per-scene videos, then concat
scene_videos = []
for scene_idx in range(len(SCENES)):
    sv = os.path.join(out_dir, f"scene_{scene_idx:03d}.mp4")
    pattern = os.path.join(frames_dir, f"scene_{scene_idx:03d}_frame_%04d.png")
    cmd = [
        "ffmpeg", "-y", "-framerate", str(FPS),
        "-i", pattern,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-vf", f"scale={W}:{H},format=yuv420p",
        "-r", str(FPS),
        sv
    ]
    subprocess.run(cmd, capture_output=True)
    scene_videos.append(sv)
    print(f"  Scene video {scene_idx+1}/{len(SCENES)} created")

# Concat all scene videos
concat_video = os.path.join(out_dir, "concat_videos.txt")
with open(concat_video, "w") as f:
    for sv in scene_videos:
        f.write(f"file '{os.path.abspath(sv)}'\n")

cmd = [
    "ffmpeg", "-y", "-f", "concat", "-safe", "0",
    "-i", concat_video,
    "-c", "copy",
    video_path
]
subprocess.run(cmd, capture_output=True)
print(f"\n✅ Video saved: {video_path}")

# Try TTS if edge-tts is available
try:
    import asyncio
    async def do_tts():
        tts_dir = os.path.join(out_dir, "tts")
        os.makedirs(tts_dir, exist_ok=True)
        audio_paths = []
        for i, scene in enumerate(SCENES):
            ap = os.path.join(tts_dir, f"scene_{i:03d}.mp3")
            cmd = ["edge-tts", "--voice", "en-GB-RyanNeural", "--text", scene["narration"], "--write-media", ap]
            proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            await proc.wait()
            audio_paths.append(ap)
        # Combine audio
        audio_dir = os.path.join(out_dir, "tts")
        audio_concat = os.path.join(out_dir, "concat_audio.txt")
        with open(audio_concat, "w") as f:
            for ap in audio_paths:
                f.write(f"file '{os.path.abspath(ap)}'\n")
        
        full_audio = os.path.join(out_dir, "full_audio.mp3")
        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", audio_concat, "-c", "copy", full_audio]
        subprocess.run(cmd, capture_output=True)
        
        # Combine video + audio
        final_out = os.path.join(out_dir, "maya_video_tts.mp4")
        cmd = ["ffmpeg", "-y", "-i", video_path, "-i", full_audio,
               "-c:v", "copy", "-c:a", "aac", "-shortest", final_out]
        subprocess.run(cmd, capture_output=True)
        print(f"✅ With TTS: {final_out}")
    
    asyncio.run(do_tts())
except ImportError:
    print("edge-tts not available, skipping TTS")
except Exception as e:
    print(f"TTS skipped: {e}")

print("\nDone!")
