"""Cat domestication video — engine-rendered, 8-scene cinematic documentary."""
import sys, os, subprocess, math, shutil, textwrap
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageDraw, ImageFont
from src.sketch_generator import SketchGenerator
from src.rules_engine import apply_rules, feedback as rules_feedback
from src.brain.dataset import Dataset
from src.brain.models import BrainModel
import warnings
warnings.filterwarnings("ignore")

W, H = 1280, 720
FPS = 30
rng = __import__("random").Random(42)

out_dir = os.path.join(os.path.dirname(__file__), "cat_video")
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
LOW   = Cam(0.0,-0.15,1.0,0.6)
HIGH  = Cam(0.0,0.0,1.0,0.65)
PAN_UP  = lambda t: lerp(Cam(0.25,0.55,0.5,0.45),  Cam(0.2,0.0,0.6,1.0), t)
ZOOM_IN = lambda t: lerp(LONG, Cam(0.2,0.05,0.6,0.9), t)

def E(typ, x=0.5, y=0.5, scale=1.0, **kw):
    d = {"type": typ, "x": x, "y": y, "scale": scale}; d.update(kw); return d

def render_scene(elements, w=W, h=H, seed=None, **overrides):
    """Build a scene dict and render through SketchGenerator."""
    elements = apply_rules([dict(e) for e in elements])
    scene = {
        "bg": {"type": "gradient", "colors": overrides.get("colors", [[140,180,220],[100,160,200]]),
               "horizon": overrides.get("horizon", 0.55),
               "ground_color": overrides.get("ground", [60,130,60])},
        "elements": elements,
        "atmosphere": {"particles": "none", "fog": False},
        "mood": overrides.get("mood", "peaceful"),
        "style": {"vignette": 0.1, "grain": 0.02},
    }
    gen = SketchGenerator(w, h, seed=seed or rng.randint(0,99999))
    return gen.render_scene(scene)

def add_text(img, text):
    draw = ImageDraw.Draw(img)
    try: font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    except:
        try: font = ImageFont.truetype("DejaVuSans.ttf", 22)
        except: font = ImageFont.load_default()
    for i, ln in enumerate(textwrap.wrap(text, 65)):
        b = draw.textbbox((0,0), ln, font=font)
        draw.text(((W-b[2])//2, H-55+i*26), ln, fill=(60,55,50), font=font)
    return img

SCENES = []

# Scene 1 — The First Farmers
SCENES.append({
    "narration": "About 10,000 years ago, humans began storing food. And wherever food appeared, mice followed. Villages suddenly became all-you-can-eat buffets for rodents.",
    "shots": [
        {"cam": LONG, "dur": 3.5, "elems": [
            E("building",0.5,0.7,4.0,width=80,height=100),
            E("rat",0.25,0.65,1.5), E("rat",0.4,0.72,1.2), E("rat",0.6,0.68,1.3), E("rat",0.75,0.7,1.0),
            E("fruit",0.3,0.85,1.5), E("fruit",0.5,0.82,1.2), E("fruit",0.7,0.83,1.0),
        ]},
        {"cam": CU, "dur": 2.5, "elems": [
            E("rat",0.5,0.5,4.0),
        ]},
    ]
})

# Scene 2 — The Hunters Arrive
SCENES.append({
    "narration": "Then another animal noticed the feast. Wildcats. They weren't interested in human friendship. They came for the mice.",
    "shots": [
        {"cam": LONG, "dur": 3.0, "elems": [
            E("cat",0.18,0.68,3.5,pose="crouching"), E("cat",0.85,0.72,2.5,pose="crouching"),
            E("grass",0.5,0.9,2.0), E("rat",0.4,0.78,1.2), E("rat",0.6,0.75,1.0),
            E("building",0.7,0.7,2.5,width=40,height=50),
        ]},
        {"cam": CU, "dur": 2.0, "elems": [
            E("cat",0.5,0.55,6.0,pose="crouching"),
        ]},
    ]
})

# Scene 3 — The Deal
SCENES.append({
    "narration": "A strange partnership began. Humans got pest control. Cats got unlimited food. Civilization had accidentally hired its first feline employees.",
    "shots": [
        {"cam": MED, "dur": 3.0, "elems": [
            E("cat",0.3,0.68,3.5), E("rat",0.35,0.78,1.0),
            E("human",0.7,0.72,3.5,pose="standing",gender="man",mood="peaceful"),
            E("building",0.55,0.7,2.0,width=35,height=45),
        ]},
        {"cam": CU, "dur": 2.0, "elems": [
            E("cat",0.5,0.55,5.5),
        ]},
    ]
})

# Scene 4 — Cats Refuse to Act Domesticated
SCENES.append({
    "narration": "Most domesticated animals changed dramatically. Dogs became obedient. Cows became dependent. Cats? Cats barely changed at all.",
    "shots": [
        {"cam": MED, "dur": 3.0, "elems": [
            E("dog",0.25,0.7,3.5), E("human",0.15,0.7,3.0,pose="standing",gender="man"),
            E("cat",0.7,0.72,3.0), E("human",0.55,0.7,2.5,pose="standing",gender="woman",mood="annoyed"),
        ]},
        {"cam": CU, "dur": 2.0, "elems": [
            E("cat",0.5,0.55,5.0),
        ]},
    ]
})

# Scene 5 — Ancient Egypt's Obsession
SCENES.append({
    "narration": "Then came ancient Egypt. Cats became celebrities. They protected grain stores. They appeared in artwork. Some were even mummified.",
    "shots": [
        {"cam": LONG, "dur": 3.0, "elems": [
            E("temple",0.5,0.72,5.0),
            E("cat",0.3,0.7,3.0), E("cat",0.7,0.68,3.5),
            E("sun",0.88,0.12,3.0),
        ]},
        {"cam": MED, "dur": 2.5, "elems": [
            E("cat",0.5,0.6,5.5), E("temple",0.72,0.72,3.5),
        ]},
    ]
})

# Scene 6 — Global Expansion
SCENES.append({
    "narration": "As humans explored the world, cats came along. Sailors loved them. Ships full of food attracted rats. Cats solved the problem.",
    "shots": [
        {"cam": LONG, "dur": 3.5, "elems": [
            E("ship",0.4,0.75,5.0), E("cat",0.35,0.65,2.5), E("cat",0.5,0.68,2.0),
            E("wave",0.5,0.88,5.0), E("wave",0.1,0.88,3.0),
        ]},
        {"cam": CU, "dur": 2.0, "elems": [
            E("cat",0.5,0.5,5.5),
        ]},
    ]
})

# Scene 7 — The Modern Takeover
SCENES.append({
    "narration": "Today there are hundreds of millions of pet cats. They dominate social media. Humans buy them toys, build them furniture, and spend hours photographing them.",
    "shots": [
        {"cam": MED, "dur": 3.0, "elems": [
            E("cat",0.5,0.65,5.0),
            E("star",0.12,0.12,3.0), E("star",0.88,0.12,3.0), E("star",0.5,0.08,2.5),
        ]},
        {"cam": CU, "dur": 2.5, "elems": [
            E("cat",0.5,0.5,7.0),
        ]},
    ]
})

# Scene 8 — Ending Twist: Cat on Throne
SCENES.append({
    "narration": "Cats never built cities. They never invented money. Yet somehow humans provide them food, shelter, healthcare, and personal servants. Cats didn't conquer humanity with claws. They conquered it with purring.",
    "shots": [
        {"cam": MED, "dur": 3.5, "elems": [
            E("throne",0.5,0.7,5.0), E("cat",0.5,0.52,3.5),
            E("human",0.72,0.72,3.0,pose="standing",gender="man",mood="happy"),
        ]},
        {"cam": ECU, "dur": 2.0, "elems": [
            E("cat",0.5,0.55,8.0),
        ]},
    ]
})


# ─── RENDER ───────────────────────────────────────────────────────

print(f"Rendering {len(SCENES)} scenes...")
total_frames = 0

for si, scene in enumerate(SCENES):
    frame_idx = 0
    for sh_idx, shot in enumerate(scene["shots"]):
        cam_spec = shot["cam"]
        shot_frames = int(shot["dur"] * FPS)

        base = render_scene(shot["elems"], seed=si*100+sh_idx)

        for f in range(shot_frames):
            t = f / shot_frames
            if callable(cam_spec):
                cam = cam_spec(t)
            elif isinstance(cam_spec, tuple):
                cam = lerp(cam_spec[0], cam_spec[1], t)
            else:
                cam = cam_spec

            frame = cam.crop(base)
            add_text(frame, scene["narration"])

            fpath = os.path.join(frames_dir, f"scene_{si:03d}_frame_{frame_idx:04d}.png")
            frame.save(fpath)
            frame_idx += 1

    total_frames += frame_idx
    print(f"  Scene {si+1}/{len(SCENES)} — {frame_idx} frames")

# ─── ASSEMBLE ─────────────────────────────────────────────────────

print(f"\n{total_frames} frames. Assembling...")
video_path = os.path.join(out_dir, "cat_domestication.mp4")
scene_videos = []

for si in range(len(SCENES)):
    sv = os.path.join(out_dir, f"scene_{si:03d}.mp4")
    pattern = os.path.join(frames_dir, f"scene_{si:03d}_frame_%04d.png")
    r = subprocess.run(["ffmpeg","-y","-framerate",str(FPS),"-i",pattern,
        "-c:v","libx264","-pix_fmt","yuv420p","-vf","format=yuv420p","-r",str(FPS),sv],
        capture_output=True, text=True)
    if r.returncode != 0: print(f"  FFmpeg err scene {si}: {r.stderr[:200]}")
    scene_videos.append(sv)

concat_v = os.path.join(out_dir, "concat_videos.txt")
with open(concat_v, "w") as f:
    for sv in scene_videos: f.write(f"file '{os.path.abspath(sv)}'\n")

r = subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",concat_v,"-c","copy",video_path],
    capture_output=True, text=True)
print(f"Video: {video_path}" if r.returncode==0 else f"Error: {r.stderr[:200]}")

# TTS
try:
    import asyncio
    async def tts():
        tts_dir = os.path.join(out_dir, "tts"); os.makedirs(tts_dir)
        audios = []
        for i, sc in enumerate(SCENES):
            ap = os.path.join(tts_dir, f"scene_{i:03d}.mp3")
            p = await asyncio.create_subprocess_exec("edge-tts","--voice","en-GB-RyanNeural","--text",sc["narration"],"--write-media",ap,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
            await p.wait(); audios.append(ap)
        ac = os.path.join(out_dir, "concat_audio.txt")
        with open(ac,"w") as f:
            for ap in audios: f.write(f"file '{os.path.abspath(ap)}'\n")
        fa = os.path.join(out_dir, "full_audio.mp3")
        subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",ac,"-c","copy",fa])
        final = os.path.join(out_dir, "cat_domestication_tts.mp4")
        subprocess.run(["ffmpeg","-y","-i",video_path,"-i",fa,"-c:v","copy","-c:a","aac","-shortest",final])
        print(f"TTS: {final}")
    asyncio.run(tts())
except Exception as e:
    print(f"TTS skipped: {e}")

# ─── BRAIN: record scenes and retrain ───────────────────────────

print("\nTeaching brain from this session...")
from src.brain.dataset import Dataset
from src.brain.models import BrainModel
ds = Dataset()
for sc in SCENES:
    for sh in sc["shots"]:
        ds.add_scene(sc["narration"], sh["elems"], source="cat_video")
brain = BrainModel()
brain.train(ds.examples)
print(f"Brain now knows {len(brain.model['keywords'])} keywords across {len(brain.model['element_stats'])} element types")
print(f"Total scenes in dataset: {ds.count}")

print("Done!")
