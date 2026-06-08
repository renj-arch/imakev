"""Cinematic Maya video — engine-rendered, multi-shot camera work."""
import sys, os, subprocess, math, shutil, textwrap
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageDraw, ImageFont
from src.sketch_generator import SketchGenerator
import warnings
warnings.filterwarnings("ignore")

W, H = 1280, 720
FPS = 30
rng = __import__("random").Random(137)

out_dir = os.path.join(os.path.dirname(__file__), "maya_video")
if os.path.isdir(out_dir): shutil.rmtree(out_dir)
os.makedirs(out_dir)
frames_dir = os.path.join(out_dir, "frames")
os.makedirs(frames_dir)

# ─── Camera ───────────────────────────────────────────────────────

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

# ─── Scene → engine rendering ────────────────────────────────────

def render_scene(elements, w=W*2, h=H*2, seed=None, **overrides):
    """Build a scene dict and render through SketchGenerator."""
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

# ─── Scenes ───────────────────────────────────────────────────────

SCENES = []

# Scene 0 — Cinematic intro
SCENES.append({
    "narration": "Imagine waking up in one of the greatest cities on Earth.",
    "shots": [
        {"cam": LONG, "dur": 3.0, "elems": [
            E("pyramid",0.65,0.72,5.5,steps=5), E("sun",0.88,0.12,3.5),
            E("tree",0.12,0.82,3.0), E("cloud",0.3,0.18,3.0),
        ]},
        {"cam": MED, "dur": 2.0, "elems": [
            E("tree",0.5,0.65,6.0), E("leaf",0.65,0.15,4.0),
        ]},
        {"cam": CU, "dur": 2.5, "elems": [
            E("leaf",0.5,0.3,8.0),
        ]},
        {"cam": ECU, "dur": 1.5, "elems": [
            E("leaf",0.5,0.65,10.0),
        ]},
        {"cam": LOW, "dur": 2.0, "elems": [
            E("leaf",0.35,0.82,6.0), E("human",0.5,0.8,5.0,pose="standing",gender="man",mood="peaceful"),
        ]},
        {"cam": PAN_UP, "dur": 3.5, "elems": [
            E("human",0.5,0.7,5.5,pose="standing_akimbo",gender="man",mood="hopeful"),
            E("pyramid",0.75,0.75,4.5,steps=5), E("sun",0.88,0.15,3.5),
        ]},
        {"cam": MED, "dur": 2.0, "elems": [
            E("human",0.5,0.7,5.5,pose="standing_akimbo",gender="man",mood="hopeful"),
            E("pyramid",0.75,0.75,4.5,steps=5), E("sun",0.88,0.15,3.5),
        ]},
    ]
})

# Scene 1
SCENES.append({"narration":"Massive stone pyramids rise above the jungle.","shots":[
    {"cam":ZOOM_IN,"dur":3.0,"elems":[E("pyramid",0.5,0.72,7.0,steps=5),E("tree",0.08,0.82,3.0),E("tree",0.92,0.82,3.0)]},
    {"cam":CU,"dur":2.5,"elems":[E("pyramid",0.5,0.6,10.0,steps=5),E("human",0.48,0.22,2.5,pose="standing",gender="man"),E("human",0.55,0.25,2.0,pose="standing",gender="man")]},
]})

# Scene 2
SCENES.append({"narration":"Astronomers track the stars.","shots":[
    {"cam":MED,"dur":3.0,"elems":[E("moon",0.85,0.12,3.5),E("star",0.15,0.1,2.5),E("star",0.35,0.08,2.0),E("star",0.55,0.15,2.0),E("star",0.9,0.3,1.5),E("human",0.5,0.7,4.0,pose="standing",gender="man",mood="peaceful")]},
]})

# Scene 3
SCENES.append({"narration":"What happened to the Maya?","shots":[
    {"cam":LONG,"dur":2.5,"elems":[E("pyramid",0.35,0.75,4.5,steps=4),E("pyramid",0.65,0.78,3.5,steps=4),E("sun",0.88,0.12,3.0),E("building",0.2,0.82,2.0)]},
    {"cam":CU,"dur":2.0,"elems":[E("pyramid",0.5,0.65,8.0,steps=4),E("question_mark",0.5,0.18,12)]},
]})

# Scene 4
SCENES.append({"narration":"Then, around the 800s AD, something strange began to happen.","shots":[
    {"cam":MED,"dur":3.0,"elems":[E("building",0.25,0.7,3.5,width=40,height=60),E("building",0.5,0.65,4.0,width=45,height=70),E("building",0.75,0.7,3.5,width=40,height=60),E("line",0.5,0.9,1.0)]},
]})

# Scene 5
SCENES.append({"narration":"One by one, major cities stopped building monuments.","shots":[
    {"cam":MED,"dur":2.5,"elems":[E("human",0.3,0.72,3.0,pose="standing",gender="man"),E("human",0.45,0.7,3.0,pose="standing",gender="man"),E("pyramid",0.72,0.78,3.5,steps=3)]},
    {"cam":CU,"dur":2.0,"elems":[E("pyramid",0.5,0.62,7.0,steps=2)]},
]})

# Scene 6
SCENES.append({"narration":"Royal palaces were abandoned.","shots":[
    {"cam":MED,"dur":2.5,"elems":[E("throne",0.5,0.72,4.0),E("leaf",0.15,0.3,2.0),E("leaf",0.85,0.25,1.5)]},
    {"cam":CU,"dur":2.0,"elems":[E("throne",0.5,0.6,7.0)]},
]})

# Scene 7
SCENES.append({"narration":"Was it war?","shots":[
    {"cam":LONG,"dur":2.5,"elems":[E("pyramid",0.2,0.75,4.0,steps=4),E("pyramid",0.8,0.75,4.0,steps=4),E("human",0.35,0.7,3.0,pose="fighting_stance",gender="man",mood="angry"),E("human",0.65,0.7,3.0,pose="fighting_stance",gender="man",mood="angry"),E("fire",0.5,0.45,3.0)]},
    {"cam":CU,"dur":1.5,"elems":[E("human",0.5,0.68,5.0,pose="fighting_stance",gender="man",mood="angry")]},
]})

# Scene 8
SCENES.append({"narration":"Evidence suggests the Maya faced severe droughts.","shots":[
    {"cam":LONG,"dur":3.0,"elems":[E("sun",0.5,0.08,6.0),E("cracked_ground",0.5,0.72,10,3)]},
]})

# Scene 9
SCENES.append({"narration":"Years without enough rain meant crops failed.","shots":[
    {"cam":MED,"dur":3.0,"elems":[E("tree",0.3,0.72,3.5),E("tree",0.5,0.68,4.0),E("tree",0.7,0.72,3.5),E("sun",0.88,0.1,4.0)]},
]})

# Scene 10
SCENES.append({"narration":"Food became scarce.","shots":[
    {"cam":MED,"dur":3.0,"elems":[E("basket",0.3,0.72,3.5),E("basket",0.7,0.72,3.5),E("human",0.4,0.68,3.5,pose="standing",gender="man",mood="sad"),E("human",0.6,0.7,3.0,pose="standing",gender="woman",mood="sad")]},
]})

# Scene 11
SCENES.append({"narration":"As resources shrank, rival city-states fought.","shots":[
    {"cam":HIGH,"dur":3.5,"elems":[E("building",0.25,0.55,3.0,width=50,height=70),E("building",0.75,0.55,3.0,width=50,height=70),E("fire",0.25,0.38,6.0),E("fire",0.75,0.35,6.0)]},
]})

# Scene 12
SCENES.append({"narration":"Large forests had been cleared.","shots":[
    {"cam":LONG,"dur":3.0,"elems":[E("tree",0.15,0.75,3.5),E("tree",0.35,0.72,4.0),E("tree",0.65,0.72,3.5),E("tree",0.85,0.78,3.0)]},
]})

# Scene 13
SCENES.append({"narration":"Eventually, many people left.","shots":[
    {"cam":ZOOM_IN,"dur":3.5,"elems":[E("pyramid",0.78,0.68,5.0,steps=4),E("human",0.18,0.68,3.5,pose="walking",gender="man"),E("human",0.28,0.72,2.8,pose="walking",gender="woman"),E("human",0.36,0.76,2.2,pose="walking",gender="child"),E("sun",0.88,0.2,2.5)]},
]})

# Scene 14
SCENES.append({"narration":"The jungle slowly reclaimed them.","shots":[
    {"cam":MED,"dur":3.0,"elems":[E("pyramid",0.5,0.72,4.5,steps=4),E("tree",0.18,0.78,3.5),E("tree",0.82,0.78,3.5),E("grass",0.3,0.88,1.5)]},
]})

# Scene 15
SCENES.append({"narration":"But here's the biggest misconception. The Maya did not vanish.","shots":[
    {"cam":MED,"dur":3.0,"elems":[E("human",0.3,0.72,3.5,pose="standing",gender="man",mood="hopeful"),E("human",0.65,0.72,3.5,pose="standing",gender="man",mood="hopeful"),E("human",0.72,0.78,2.2,pose="standing",gender="child",mood="hopeful"),E("sun",0.88,0.12,3.0)]},
]})

# Scene 16
SCENES.append({"narration":"The cities fell. The people remained.","shots":[
    {"cam":LONG,"dur":3.5,"elems":[E("pyramid",0.2,0.78,3.0,steps=3),E("human",0.75,0.72,3.5,pose="standing",gender="man",mood="hopeful"),E("human",0.82,0.76,2.5,pose="standing",gender="woman",mood="hopeful"),E("human",0.88,0.8,1.8,pose="standing",gender="child",mood="hopeful"),E("sun",0.88,0.12,2.5)]},
]})

# ─── RENDER ───────────────────────────────────────────────────────

print(f"Rendering {len(SCENES)} scenes...")
total_frames = 0

for si, scene in enumerate(SCENES):
    frame_idx = 0
    for sh_idx, shot in enumerate(scene["shots"]):
        cam_spec = shot["cam"]
        shot_frames = int(shot["dur"] * FPS)
        
        # Render high-res base image once per shot
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
video_path = os.path.join(out_dir, "maya_cinematic.mp4")
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
print(f"✅ {video_path}" if r.returncode==0 else f"❌ {r.stderr[:200]}")

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
        final = os.path.join(out_dir, "maya_cinematic_tts.mp4")
        subprocess.run(["ffmpeg","-y","-i",video_path,"-i",fa,"-c:v","copy","-c:a","aac","-shortest",final])
        print(f"✅ TTS: {final}")
    asyncio.run(tts())
except Exception as e:
    print(f"TTS skipped: {e}")

print("Done!")
