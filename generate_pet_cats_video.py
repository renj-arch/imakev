"""Pet Cats — multi-scene cinematic video with custom-designed scenes."""
import sys, os, subprocess, math, shutil
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageDraw, ImageFont
from src.sketch_generator import SketchGenerator
from src.rules_engine import apply_rules
import warnings
warnings.filterwarnings("ignore")

W, H = 1280, 720
FPS = 30
rng = __import__("random").Random(42)

out_dir = os.path.join(os.path.dirname(__file__), "pet_cats_video")
if os.path.isdir(out_dir): shutil.rmtree(out_dir)
os.makedirs(out_dir)
frames_dir = os.path.join(out_dir, "frames")
os.makedirs(frames_dir)

class Cam:
    def __init__(self, x=0, y=0, w=1, h=1):
        self.x, self.y, self.w, self.h = x, y, w, h
    def crop(self, img):
        pw, ph = img.size
        return img.crop((
            int(self.x*pw), int(self.y*ph),
            int((self.x+self.w)*pw), int((self.y+self.h)*ph)
        )).resize((W, H), Image.LANCZOS)

def lerp(a, b, t):
    return Cam(a.x+(b.x-a.x)*t, a.y+(b.y-a.y)*t, a.w+(b.w-a.w)*t, a.h+(b.h-a.h)*t)

LONG  = Cam(0,0,1,1)
MED   = Cam(0.12,0,0.76,1)
CU    = Cam(0.32,0.05,0.36,0.95)
ECU   = Cam(0.4,0.1,0.2,0.85)
ZOOM_IN = lambda t: lerp(LONG, Cam(0.15,0.05,0.7,0.9), t)

def E(typ, x=0.5, y=0.5, scale=1.0, **kw):
    d = {"type": typ, "x": x, "y": y, "scale": scale}; d.update(kw); return d

def render_scene(elements, colors=None, ground=None, mood="playful", seed=None):
    elements = apply_rules([dict(e) for e in elements])
    scene = {
        "bg": {"type": "gradient",
               "colors": colors or [[200, 180, 220], [160, 140, 200]],
               "horizon": 0.6,
               "ground_color": ground or [100, 160, 100]},
        "elements": elements,
        "atmosphere": {"particles": "none", "fog": False},
        "mood": mood,
        "style": {"vignette": 0.15, "grain": 0.02},
    }
    gen = SketchGenerator(W, H, seed=seed or rng.randint(0, 99999))
    return gen.render_scene(scene)

def add_text(img, text, y_bottom=60):
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    for fp in ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
               "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
               "C:/Windows/Fonts/arial.ttf",
               "C:/Windows/Fonts/seguiemj.ttf"]:
        if os.path.exists(fp):
            try: font = ImageFont.truetype(fp, 24); break
            except: pass
    lines = []
    for word in text.split():
        if lines and len(lines[-1] + " " + word) <= 55:
            lines[-1] += " " + word
        else:
            lines.append(word)
    for i, ln in enumerate(lines):
        b = draw.textbbox((0,0), ln, font=font)
        draw.text(((W-b[2])//2, H-y_bottom+i*28), ln, fill=(255,255,255), font=font, stroke_width=2, stroke_fill=(30,30,30))
    return img

# ── Scene 1: Hundreds of millions of pet cats ─────────────────────
# Visual: globe/world + many cat silhouettes spread around
SCENE_1 = {
    "narration": "Today there are hundreds of millions of pet cats.",
    "shots": [
        {"cam": LONG, "dur": 3.0, "elems": [
            E("cat", 0.15, 0.7, 2.5), E("cat", 0.3, 0.68, 2.0, pose="sitting"),
            E("cat", 0.5, 0.65, 3.0), E("cat", 0.7, 0.72, 2.2),
            E("cat", 0.85, 0.68, 2.8, pose="sitting"),
            E("star", 0.1, 0.1, 2.0), E("star", 0.9, 0.15, 2.5),
            E("star", 0.5, 0.08, 3.0),
        ]},
        {"cam": CU, "dur": 2.5, "elems": [
            E("cat", 0.5, 0.58, 5.0, pose="sitting"),
        ]},
    ]
}

# ── Scene 2: Dominate social media ────────────────────────────────
# Visual: smartphone with cat on screen, floating hearts/likes
SCENE_2 = {
    "narration": "They dominate social media.",
    "shots": [
        {"cam": LONG, "dur": 3.0, "elems": [
            E("smartphone", 0.5, 0.55, 6.0),
            E("heart", 0.2, 0.15, 2.0, color=(220, 50, 50)),
            E("heart", 0.75, 0.12, 1.5, color=(220, 50, 50)),
            E("heart", 0.85, 0.25, 1.2, color=(220, 50, 50)),
            E("star", 0.1, 0.2, 1.5),
            E("star", 0.9, 0.1, 1.8),
        ]},
        {"cam": CU, "dur": 2.5, "elems": [
            E("smartphone", 0.5, 0.5, 8.0),
            E("heart", 0.2, 0.2, 2.0, color=(220, 50, 50)),
        ]},
    ]
}

# ── Scene 3: Memes, videos, games, ads ────────────────────────────
# Visual: TV screen showing cat + cat toy/controller
SCENE_3 = {
    "narration": "They appear in memes, videos, games, and advertisements.",
    "shots": [
        {"cam": MED, "dur": 3.5, "elems": [
            E("tv_monitor", 0.5, 0.55, 5.0),
            E("cat", 0.2, 0.7, 2.5),
            E("star", 0.1, 0.1, 1.5), E("star", 0.9, 0.12, 2.0),
        ]},
        {"cam": CU, "dur": 2.5, "elems": [
            E("tv_monitor", 0.5, 0.5, 7.0),
        ]},
    ]
}

# ── Scene 4: Humans buy them toys ─────────────────────────────────
# Visual: human holding a cat toy, cat nearby
SCENE_4 = {
    "narration": "Humans buy them toys.",
    "shots": [
        {"cam": MED, "dur": 3.0, "elems": [
            E("human", 0.3, 0.7, 3.5, pose="standing", gender="woman", mood="happy",
              skin_color=(235, 200, 175)),
            E("cat", 0.65, 0.7, 2.8),
            E("cat_toy", 0.4, 0.55, 3.0),
            E("star", 0.15, 0.15, 1.5), E("star", 0.85, 0.12, 2.0),
        ]},
        {"cam": CU, "dur": 2.5, "elems": [
            E("cat_toy", 0.3, 0.5, 5.0),
            E("cat", 0.7, 0.58, 4.0),
        ]},
    ]
}

# ── Scene 5: Build them furniture ─────────────────────────────────
# Visual: cat on cat tree / throne-like furniture
SCENE_5 = {
    "narration": "Build them furniture.",
    "shots": [
        {"cam": MED, "dur": 3.0, "elems": [
            E("cat", 0.5, 0.52, 3.0, pose="sitting"),
            E("bed", 0.5, 0.72, 4.0),
            E("star", 0.15, 0.12, 1.5), E("star", 0.85, 0.1, 2.0),
        ]},
        {"cam": CU, "dur": 2.5, "elems": [
            E("cat", 0.5, 0.5, 6.0, pose="sitting"),
        ]},
    ]
}

# ── Scene 6: Photographing them ──────────────────────────────────
# Visual: human with camera pointing at cat
SCENE_6 = {
    "narration": "And spend countless hours photographing them.",
    "shots": [
        {"cam": MED, "dur": 3.5, "elems": [
            E("human", 0.25, 0.7, 3.5, pose="standing", gender="man", mood="happy",
              skin_color=(235, 200, 175)),
            E("camera", 0.35, 0.55, 4.0),
            E("cat", 0.7, 0.7, 3.0, pose="sitting"),
            E("star", 0.1, 0.1, 1.5), E("star", 0.9, 0.12, 2.0),
        ]},
        {"cam": CU, "dur": 2.5, "elems": [
            E("camera", 0.5, 0.5, 6.0),
        ]},
    ]
}

SCENES = [SCENE_1, SCENE_2, SCENE_3, SCENE_4, SCENE_5, SCENE_6]

# Color themes per scene for variety
BG_THEMES = [
    {"colors": [[200, 180, 220], [160, 140, 200]], "ground": [100, 160, 100], "mood": "playful"},
    {"colors": [[180, 200, 230], [130, 160, 210]], "ground": [90, 150, 90], "mood": "hopeful"},
    {"colors": [[220, 190, 180], [190, 150, 140]], "ground": [110, 140, 100], "mood": "peaceful"},
    {"colors": [[200, 220, 190], [160, 190, 150]], "ground": [100, 160, 80], "mood": "happy"},
    {"colors": [[180, 170, 200], [140, 130, 170]], "ground": [90, 130, 90], "mood": "peaceful"},
    {"colors": [[210, 200, 170], [180, 160, 130]], "ground": [120, 140, 90], "mood": "hopeful"},
]

# ─── RENDER ────────────────────────────────────────────────────

print(f"Rendering {len(SCENES)} scenes...")
total_frames = 0

for si, scene in enumerate(SCENES):
    frame_idx = 0
    theme = BG_THEMES[si]

    for sh_idx, shot in enumerate(scene["shots"]):
        cam_spec = shot["cam"]
        shot_frames = int(shot["dur"] * FPS)
        seed = si * 100 + sh_idx

        base_img = render_scene(shot["elems"],
                                colors=theme["colors"],
                                ground=theme["ground"],
                                mood=theme["mood"],
                                seed=seed)

        for f in range(shot_frames):
            t = f / max(shot_frames - 1, 1)
            if callable(cam_spec):
                cam = cam_spec(t)
            else:
                cam = cam_spec

            frame = cam.crop(base_img)
            frame = add_text(frame, scene["narration"], y_bottom=55)

            fpath = os.path.join(frames_dir, f"scene_{si:03d}_frame_{frame_idx:04d}.png")
            frame.save(fpath)
            frame_idx += 1

    total_frames += frame_idx
    print(f"  Scene {si+1}/6 — {frame_idx} frames")

# ─── ASSEMBLE ──────────────────────────────────────────────────

print(f"\n{total_frames} frames. Assembling video...")

scene_videos = []
for si in range(len(SCENES)):
    sv = os.path.join(out_dir, f"scene_{si:03d}.mp4")
    pattern = os.path.join(frames_dir.replace("\\", "/"), f"scene_{si:03d}_frame_%04d.png")
    r = subprocess.run([
        "ffmpeg", "-y", "-framerate", str(FPS), "-i", pattern,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-vf", "format=yuv420p", "-r", str(FPS), sv
    ], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  FFmpeg err scene {si}: {r.stderr[:200]}")
    scene_videos.append(sv)
    print(f"  Scene {si+1} video done")

concat_v = os.path.join(out_dir, "concat_videos.txt")
with open(concat_v, "w") as f:
    for sv in scene_videos:
        f.write(f"file '{os.path.abspath(sv)}'\n")

video_path = os.path.join(out_dir, "pet_cats.mp4")
r = subprocess.run([
    "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_v,
    "-c", "copy", video_path
], capture_output=True, text=True)

if r.returncode != 0:
    r = subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_v,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", video_path
    ], capture_output=True, text=True)

print(f"\nVideo: {video_path}" if os.path.exists(video_path) else f"Error: {r.stderr[:200] if r else 'unknown'}")
print("Done!")
