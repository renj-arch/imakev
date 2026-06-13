"""Pet Cats — multi-scene cinematic video from narration."""
import sys, os, subprocess, math, shutil
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageDraw, ImageFont
from src.narration_to_sketch import _describe_scene
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

def render_scene(desc, seed=None):
    """Render a scene description through SketchGenerator."""
    gen = SketchGenerator(W, H, seed=seed or rng.randint(0, 99999))
    return gen.render_scene(desc)

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
        if lines and len(lines[-1] + " " + word) <= 60:
            lines[-1] += " " + word
        else:
            lines.append(word)
    for i, ln in enumerate(lines):
        b = draw.textbbox((0,0), ln, font=font)
        draw.text(((W-b[2])//2, H-y_bottom+i*28), ln, fill=(40,35,30), font=font)
    return img

# ── Scene definitions ──────────────────────────────────────────

SENTENCES = [
    "Today there are hundreds of millions of pet cats.",
    "They dominate social media.",
    "They appear in memes, videos, games, and advertisements.",
    "Humans buy them toys.",
    "Build them furniture.",
    "And spend countless hours photographing them.",
]

SCENES = []
for i, sentence in enumerate(SENTENCES):
    desc = _describe_scene(sentence)
    mood = desc.get("mood", "peaceful")
    # Define shots per scene
    if i == 0:  # Millions of cats — wide shot, zoom to CU
        shots = [
            {"cam": LONG, "dur": 3.0, "seed": i*100+0},
            {"cam": MED,  "dur": 2.5, "seed": i*100+1},
        ]
    elif i == 1:  # Social media — cat closeup
        shots = [
            {"cam": MED,  "dur": 2.5, "seed": i*100+0},
            {"cam": CU,   "dur": 2.0, "seed": i*100+1},
        ]
    elif i == 2:  # Memes, videos, games — wider frame
        shots = [
            {"cam": LONG, "dur": 3.0, "seed": i*100+0},
            {"cam": MED,  "dur": 2.0, "seed": i*100+1},
        ]
    elif i == 3:  # Humans buy toys — human+cat
        shots = [
            {"cam": MED,  "dur": 2.5, "seed": i*100+0},
            {"cam": CU,   "dur": 2.0, "seed": i*100+1},
        ]
    elif i == 4:  # Furniture
        shots = [
            {"cam": MED,  "dur": 2.5, "seed": i*100+0},
        ]
    else:  # Photographing
        shots = [
            {"cam": MED,  "dur": 2.5, "seed": i*100+0},
            {"cam": ECU,  "dur": 2.0, "seed": i*100+1},
        ]

    SCENES.append({
        "narration": sentence,
        "shots": shots,
        "desc": desc,
    })

# ─── RENDER ────────────────────────────────────────────────────

print(f"Rendering {len(SCENES)} scenes...")
total_frames = 0

for si, scene in enumerate(SCENES):
    frame_idx = 0

    for sh_idx, shot in enumerate(scene["shots"]):
        cam_spec = shot["cam"]
        shot_frames = int(shot["dur"] * FPS)

        base_img = render_scene(scene["desc"], seed=shot["seed"])

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
    print(f"  Scene {si+1}/{len(SCENES)} ({scene['narration'][:40]}...) — {frame_idx} frames")

# ─── ASSEMBLE ──────────────────────────────────────────────────

print(f"\n{total_frames} frames. Assembling video...")

# Build a video per scene
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

# Concatenate
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
