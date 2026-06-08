"""Cinematic Maya storyboard — multi-shot scenes, camera moves, dramatic reveals."""
import sys, os, json, subprocess, math, random, textwrap, shutil
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageDraw, ImageFont
import warnings
warnings.filterwarnings("ignore")

W, H = 1280, 720
FPS = 30
rng = random.Random(137)

out_dir = os.path.join(os.path.dirname(__file__), "maya_video")
if os.path.isdir(out_dir):
    shutil.rmtree(out_dir)
os.makedirs(out_dir)
frames_dir = os.path.join(out_dir, "frames")
os.makedirs(frames_dir)

# ─── helpers ──────────────────────────────────────────────────────

def _font(size=22):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except:
        try:
            return ImageFont.truetype("DejaVuSans.ttf", size)
        except:
            return ImageFont.load_default()

def _text(draw, text, y=H-50, size=22, fill=(60,55,50)):
    f = _font(size)
    lines = textwrap.wrap(text, width=65)
    for i, ln in enumerate(lines):
        b = draw.textbbox((0,0), ln, font=f)
        draw.text(((W-b[2])//2, y+i*(size+4)), ln, fill=fill, font=f)

def _gradient(draw, y1, y2, c1, c2):
    for py in range(y1, y2):
        t = (py-y1)/(y2-y1-1) if y2-y1>1 else 0
        draw.line([(0,py),(W,py)], fill=tuple(int(a+(b-a)*t) for a,b in zip(c1,c2)))

# ─── Camera system ────────────────────────────────────────────────

class Camera:
    """Defines a viewport into the world.  All coords in 0..1."""
    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h
    def crop(self, img):
        pw, ph = img.size
        bx = int(self.x * pw)
        by = int(self.y * ph)
        bw = int(self.w * pw)
        bh = int(self.h * ph)
        return img.crop((bx, by, bx+bw, by+bh)).resize((W, H), Image.LANCZOS)

def lerp_cam(a, b, t):
    """Interpolate between two cameras."""
    return Camera(
        a.x+(b.x-a.x)*t, a.y+(b.y-a.y)*t,
        a.w+(b.w-a.w)*t, a.h+(b.h-a.h)*t,
    )

# Presets
LONG  = Camera(0.0,0.0,1.0,1.0)
MED   = Camera(0.15,0.0,0.7,1.0)
CU    = Camera(0.35,0.05,0.3,0.95)
ECU   = Camera(0.42,0.1,0.16,0.85)
SIDE  = Camera(0.0,0.0,0.5,1.0)
LOW   = Camera(0.0,-0.15,1.0,0.55)
HIGH  = Camera(0.0,0.0,1.0,0.65)
RIGHT = Camera(0.5,0.0,0.5,1.0)

# ─── Element drawing helpers ──────────────────────────────────────

def draw_pyramid(draw, cx, cy, w, h, color=(180,150,120), steps=False):
    if steps:
        for i in range(5):
            lw = w*(1-i/5); lh = h/5; ly = cy-h+i*lh
            draw.rectangle([cx-lw/2,ly,cx+lw/2,ly+lh], fill=color+(220,), outline=(60,55,50,180), width=2)
    else:
        draw.polygon([(cx,cy-h),(cx-w//2,cy),(cx+w//2,cy)], fill=color+(220,), outline=(60,55,50,180), width=3)
        draw.line([(cx-w//4,cy),(cx-w//6,cy-h//2),(cx+w//4,cy)], fill=(100,90,80,150), width=1)

def draw_temple(draw, cx, cy, w, h, color=(160,130,100)):
    draw.rectangle([cx-w//2,cy-h//4,cx+w//2,cy], fill=color+(220,), outline=(60,55,50,180), width=2)
    u = int(w*0.75); draw.rectangle([cx-u//2,cy-h//2,cx+u//2,cy-h//4], fill=color+(220,), outline=(60,55,50,180), width=2)
    rw, rh = int(w*0.4), int(h*0.3); draw.rectangle([cx-rw//2,cy-h//2-rh,cx+rw//2,cy-h//2], fill=color+(200,), outline=(60,55,50,180), width=2)
    dw2, dh2 = int(w*0.2), int(h*0.25); draw.rectangle([cx-dw2//2,cy-dh2,cx+dw2//2,cy], fill=(30,25,20,200))
    for i in range(3):
        sy = cy - i*(h//12); sw = int(w*(0.4-i*0.08))
        draw.line([(cx-sw//2,sy),(cx+sw//2,sy)], fill=(60,55,50,180), width=2)

def draw_throne(draw, cx, cy, w, h, color=(140,100,70)):
    draw.rectangle([cx-w//2,cy-h//4,cx+w//2,cy], fill=color+(220,), outline=(40,35,30,180), width=2)
    bw = int(w*0.6); draw.rectangle([cx-bw//2,cy-h,cx+bw//2,cy-h//4], fill=color+(200,), outline=(40,35,30,180), width=2)
    for s in [-1,1]:
        ax = cx+s*w//2; draw.rectangle([ax-3,cy-h//2-5,ax+3,cy-5], fill=color+(200,), outline=(40,35,30,180), width=1)

def draw_leaf(draw, cx, cy, s=1, color=(100,160,60)):
    draw.ellipse([cx-6*s,cy-3*s,cx+6*s,cy+3*s], fill=color+(200,))
    draw.line([(cx-5*s,cy),(cx+5*s,cy)], fill=(60,80,40,180), width=1)

def draw_stump(draw, cx, cy, w):
    draw.rectangle([cx-w//4,cy-w,cx+w//4,cy], fill=(100,80,60,220), outline=(40,35,30,180), width=2)
    draw.ellipse([cx-w//4,cy-w-w//8,cx+w//4,cy-w+w//8], fill=color+(200,), outline=(60,55,50,150), width=1)

def draw_cracked_earth(draw, cx, cy, w, h):
    draw.rectangle([cx-w//2,cy-h//2,cx+w//2,cy+h//2], fill=(180,160,130,200), outline=(60,55,50,150), width=1)
    for _ in range(8):
        sx,sy = cx+rng.randint(-w//2,w//2), cy+rng.randint(-h//2,h//2)
        for _ in range(3):
            ex,ey = sx+rng.randint(-20,20), sy+rng.randint(-15,15)
            draw.line([(sx,sy),(ex,ey)], fill=(100,85,70,200), width=2); sx,sy=ex,ey

def draw_question_mark(draw, cx, cy, size=40):
    pts = [(cx-size//4,cy-size//2),(cx+size//4,cy-size//2),(cx+size//3,cy-size//4),(cx+size//4,cy),(cx,cy+5),(cx-size//6,cy+size//3)]
    draw.line(pts, fill=(200,50,50,200), width=int(size/8))
    draw.ellipse([cx-size//6,cy+size//2-3,cx+size//6,cy+size//2+3], fill=(200,50,50,220))

def draw_timeline(draw, cx, cy, w):
    draw.line([(cx-w//2,cy),(cx+w//2,cy)], fill=(60,55,50,200), width=3)
    for i in range(6):
        x = cx - w//2 + int(w*i/5); draw.ellipse([x-4,cy-4,x+4,cy+4], fill=(120,80,50,220))
    draw.polygon([(cx+w//2-15,cy-6),(cx+w//2-15,cy+6),(cx+w//2,cy)], fill=(60,55,50,200))

def draw_smoke(draw, cx, cy, count=5):
    for i in range(count):
        r = 10+i*8; a = max(30, 150-i*25)
        draw.ellipse([cx-r+rng.randint(-5,5),cy-i*20-r,cx+r+rng.randint(-5,5),cy-i*20+r], fill=(180,170,160,a))

def draw_footprint(draw, cx, cy, s=1):
    draw.ellipse([cx-5*s,cy-10*s,cx+8*s,cy+2*s], fill=(100,90,80,150))
    draw.ellipse([cx-2*s,cy-14*s,cx+5*s,cy-8*s], fill=(100,90,80,150))
    for t in [-1,0,1]:
        draw.ellipse([cx+t*2*s-s,cy-4*s,cx+t*2*s+s,cy], fill=(100,90,80,120))

def draw_human_stick(draw, cx, cy, s=1, color=(60,55,50)):
    draw.ellipse([cx-6*s,cy-30*s,cx+6*s,cy-18*s], fill=(200,170,150,220))
    draw.line([(cx,cy-18*s),(cx,cy)], fill=color+(200), width=int(3*s))
    draw.line([(cx,cy-12*s),(cx-10*s,cy-20*s)], fill=color+(200), width=int(2*s))
    draw.line([(cx,cy-12*s),(cx+10*s,cy-20*s)], fill=color+(200), width=int(2*s))
    draw.line([(cx,cy),(cx-8*s,cy+15*s)], fill=color+(200), width=int(2*s))
    draw.line([(cx,cy),(cx+8*s,cy+15*s)], fill=color+(200), width=int(2*s))

def draw_sun(draw, cx, cy, r=30):
    draw.ellipse([cx-r,cy-r,cx+r,cy+r], fill=(255,220,60,230), outline=(255,180,0,200), width=3)
    for a in range(0,360,30):
        rad = math.radians(a)
        draw.line([(cx+(r+8)*math.cos(rad),cy+(r+8)*math.sin(rad)),(cx+(r+18)*math.cos(rad),cy+(r+18)*math.sin(rad))], fill=(255,200,50,180), width=2)

def draw_house(draw, cx, cy, s=1):
    hw, hh = 30*s, 25*s
    draw.rectangle([cx-hw,cy-hh,cx+hw,cy], fill=(160,140,120,220), outline=(60,55,50,180), width=2)
    draw.polygon([(cx-hw-3,cy-hh),(cx,cy-hh-15*s),(cx+hw+3,cy-hh)], fill=(120,80,50,220), outline=(60,55,50,180), width=2)
    draw.rectangle([cx-5*s,cy-12*s,cx+5*s,cy], fill=(40,35,30,220))
    draw.rectangle([cx-12*s,cy-16*s,cx-4*s,cy-10*s], fill=(255,220,100,200))
    draw.rectangle([cx+4*s,cy-16*s,cx+12*s,cy-10*s], fill=(255,220,100,200))

def draw_tree(draw, cx, cy, s=1):
    draw.rectangle([cx-3*s,cy-20*s,cx+3*s,cy], fill=(60,50,40,220))
    draw.ellipse([cx-18*s,cy-45*s,cx+18*s,cy-18*s], fill=(50,130,50,220))

def draw_building(draw, cx, cy, s=1, alpha=220):
    bw, bh = 35*s, 50*s + rng.randint(-10,10)
    draw.rectangle([cx-bw,cy-bh,cx+bw,cy], fill=(150,120,100,alpha), outline=(60,55,50,min(180,alpha)), width=2)
    draw.polygon([(cx-bw-3,cy-bh),(cx,cy-bh-12*s),(cx+bw+3,cy-bh)], fill=(120,80,50,alpha), outline=(60,55,50,min(180,alpha)), width=2)
    draw.rectangle([cx-10*s,cy-bh+6*s,cx-4*s,cy-bh+16*s], fill=(200,180,150,alpha))
    draw.rectangle([cx+4*s,cy-bh+6*s,cx+10*s,cy-bh+16*s], fill=(200,180,150,alpha))

def draw_mountain(draw, cx, cy, w, h):
    draw.polygon([(cx,cy-h),(cx-w//2,cy),(cx+w//2,cy)], fill=(100,130,110,200), outline=(60,55,50,180), width=2)
    draw.polygon([(cx,cy-h),(cx-w//8,cy-h+30),(cx+w//8,cy-h+30)], fill=(240,240,250,200))

def draw_stars(draw, count=60):
    for _ in range(count):
        sx,sy,sr = rng.randint(0,W), rng.randint(0,H//2), rng.uniform(1,2.5)
        draw.ellipse([sx-sr,sy-sr,sx+sr,sy+sr], fill=(255,255,220,rng.randint(150,255)))

def draw_constellation(draw):
    pts = [(100,80),(200,120),(150,160),(250,180),(300,100)]
    for i in range(len(pts)-1):
        draw.line([pts[i],pts[i+1]], fill=(255,255,200,120), width=1)
    for p in pts:
        draw.ellipse([p[0]-3,p[1]-3,p[0]+3,p[1]+3], fill=(255,255,200,200))

# ─── Scene definitions with cinematic shots ──────────────────────

def bg_sky(draw, top, bot):
    _gradient(draw, 0, H, top, bot)

def bg_ground(draw, y, top_color, bot_color):
    _gradient(draw, y, H, top_color, bot_color)

# Each scene = list of shots: {camera, duration, bg, draw, elements}
# camera is a Camera or (cam_start, cam_end) for interpolation

SCENES = []

# ── Scene 0: Cinematic intro — establishing shot with leaf-fall & man reveal ──
SCENES.append({
    "narration": "Imagine waking up in one of the greatest cities on Earth.",
    "shots": [
        # Shot 1: Wide establishing — jungle skyline, sun rising
        {"cam": (Camera(0,0,1,1), Camera(-0.05,0,1.1,1)), "dur": 3.0,
         "bg": lambda d: (bg_sky(d,(100,160,200),(180,210,240)), bg_ground(d,H//2+60,(60,130,60),(40,100,40))),
         "draw": [
             lambda d,t: draw_pyramid(d, int(W*0.7), H//2+100, 200, 250, steps=t>0.3),
             lambda d,t: draw_mountain(d, int(W*0.25), H//2+80, 160, 120),
             lambda d,t: draw_sun(d, W-80, 80, r=25+5*math.sin(t*math.pi)),
             lambda d,t: draw_tree(d, int(W*0.15), H//2+80, 2.5),
             lambda d,t: draw_tree(d, int(W*0.85), H//2+90, 2.0),
         ]},
        # Shot 2: Medium shot — tree branch with leaf trembling
        {"cam": MED, "dur": 2.0,
         "bg": lambda d: (bg_sky(d,(80,150,200),(160,200,240)), bg_ground(d,H//2+80,(50,120,50),(30,90,30))),
         "draw": [
             lambda d,t: draw_tree(d, W//2+100, H//2+60, 4.0),
             # Branch
             lambda d,t: d.line([(W//2-20, H//2-80), (W//2+80, H//2-120)], fill=(60,50,40,200), width=4),
             # Leaf trembling on branch
             lambda d,t: draw_leaf(d, W//2+70+int(3*math.sin(t*20)), H//2-115, s=1.5),
         ]},
        # Shot 3: Close-up — single leaf detaches, falls in slow motion
        {"cam": CU, "dur": 2.5,
         "bg": lambda d: (bg_sky(d,(100,160,200),(180,210,240)),),
         "draw": [
             lambda d,t: draw_leaf(d, W//2, int(H*0.2 + t*H*0.6), s=1.5+0.3*math.sin(t*10)),
             # Slight rotation effect via squish
             lambda d,t: d.ellipse([W//2-9, int(H*0.2+t*H*0.6)-4, W//2+9, int(H*0.2+t*H*0.6)+4],
                                   fill=(100,160,60,200)),
         ]},
        # Shot 4: Extreme close-up — leaf hits ground
        {"cam": ECU, "dur": 1.5,
         "bg": lambda d: (bg_sky(d,(120,170,210),(190,220,250)), bg_ground(d,H//2+140,(60,130,60),(40,100,40))),
         "draw": [
             lambda d,t: draw_leaf(d, W//2, H-60+int(5*math.sin(t*5)), s=2.0),
             lambda d,t: d.ellipse([W//2-12, H-64, W//2+12, H-56], fill=(60,55,50,100)) if t>0.8 else None,
         ]},
        # Shot 5: Low angle — foot steps on leaf, crushing it
        {"cam": LOW, "dur": 2.0,
         "bg": lambda d: (bg_sky(d,(100,160,200),(180,210,240)), bg_ground(d,H//2+140,(60,130,60),(40,100,40))),
         "draw": [
             lambda d,t: draw_leaf(d, W//2-20, H-60, s=2.0) if t<0.4 else None,
             lambda d,t: draw_leaf(d, W//2-20, H-60, s=1.0, color=(80,130,50)) if t>=0.4 else None,
             # Foot sliding in from right
             lambda d,t: d.ellipse([int(W*0.5+80*(1-min(1,t/0.3))), H-45, int(W*0.5+80*(1-min(1,t/0.3))+40), H-15],
                                   fill=(180,150,120,220), outline=(60,55,50,180), width=2) if t<0.5 else None,
             # Foot planted
             lambda d,t: d.ellipse([W//2-10, H-45, W//2+30, H-15], fill=(180,150,120,220), outline=(60,55,50,180), width=3) if t>=0.5 else None,
             # Leg appearing
             lambda d,t: d.rectangle([W//2, H-45, W//2+10, H-100], fill=(120,90,70,220), outline=(60,55,50,180), width=2) if t>=0.6 else None,
         ]},
        # Shot 6: Pan up — foot → legs → torso → face (man reveal)
        {"cam": (Camera(0.35,0.65,0.3,0.35), Camera(0.35,0.0,0.3,0.95)), "dur": 3.5,
         "bg": lambda d: (bg_sky(d,(100,160,200),(180,210,240)), bg_ground(d,H//2+60,(60,130,60),(40,100,40))),
         "draw": [
             # Man with arms crossed, heroic pose — camera starts at feet, pans up
             lambda d,t: draw_human_stick(d, W//2, H//2+80, s=3.0),
             # Cloth details appear as camera reaches torso
             lambda d,t: d.rectangle([W//2-12, H//2+10, W//2+12, H//2-20], fill=(200,100,80,220), outline=(60,55,50,180), width=2) if t>0.5 else None,
             # Head details as camera reaches face
             lambda d,t: d.ellipse([W//2-12, H//2-65, W//2+12, H//2-40], fill=(200,170,150,220), outline=(60,55,50,180), width=2) if t>0.7 else None,
             # Eyes appear at last
             lambda d,t: (d.ellipse([W//2-6, H//2-56, W//2-2, H//2-52], fill=(30,25,20,200)),
                         d.ellipse([W//2+2, H//2-56, W//2+6, H//2-52], fill=(30,25,20,200))) if t>0.85 else None,
         ]},
        # Shot 7: Full body — man in frame, confident
        {"cam": Camera(0.25,0.0,0.5,1.0), "dur": 2.0,
         "bg": lambda d: (bg_sky(d,(100,160,200),(180,210,240)), bg_ground(d,H//2+80,(60,130,60),(40,100,40))),
         "draw": [
             lambda d,t: draw_human_stick(d, W//2, H//2+80, s=3.5),
             lambda d,t: d.rectangle([W//2-15, H//2+10, W//2+15, H//2-25], fill=(200,100,80,220), outline=(60,55,50,180), width=2),
             lambda d,t: d.ellipse([W//2-14, H//2-70, W//2+14, H//2-45], fill=(200,170,150,220), outline=(60,55,50,180), width=2),
             lambda d,t: d.ellipse([W//2-6, H//2-60, W//2-2, H//2-56], fill=(30,25,20,200)),
             lambda d,t: d.ellipse([W//2+2, H//2-60, W//2+6, H//2-56], fill=(30,25,20,200)),
             # Pyramid behind him
             lambda d,t: draw_pyramid(d, int(W*0.75), H//2+100, 180, 220),
             # Sun rays
             lambda d,t: draw_sun(d, W-80, 60, r=25),
         ]},
    ]
})

# ── Scene 1 ──
SCENES.append({
    "narration": "Massive stone pyramids rise above the jungle.",
    "shots": [
        {"cam": (Camera(0,0.2,1,0.8), Camera(0,0,1,1)), "dur": 3.0,  # pan down to reveal full
         "bg": lambda d: (bg_sky(d,(60,120,160),(100,170,210)), bg_ground(d,H//2+60,(50,120,50),(30,90,30))),
         "draw": [
             lambda d,t: draw_pyramid(d, W//2, H//2+100, 250, 300, steps=True),
             lambda d,t: draw_smoke(d, W//2+60, H//2-100, count=int(6*min(1,t*2))),
             lambda d,t: draw_tree(d, int(W*0.1), H//2+80, 3.0),
             lambda d,t: draw_tree(d, int(W*0.9), H//2+70, 2.5),
         ]},
        {"cam": (Camera(0.3,0,0.4,1), Camera(0.25,0,0.5,1)), "dur": 2.5,  # zoom out
         "bg": lambda d: (bg_sky(d,(60,120,160),(100,170,210)), bg_ground(d,H//2+60,(50,120,50),(30,90,30))),
         "draw": [
             lambda d,t: draw_pyramid(d, W//2, H//2+100, 250, 300, steps=True),
             lambda d,t: draw_smoke(d, W//2+60, H//2-100, count=5),
             # Priest at top
             lambda d,t: draw_human_stick(d, W//2, H//2-120, s=1.5) if t>0.3 else None,
             lambda d,t: draw_human_stick(d, W//2+30, H//2-110, s=1.2) if t>0.5 else None,
         ]},
    ]
})

# ── Scene 2 ──
SCENES.append({
    "narration": "Astronomers track the stars.",
    "shots": [
        {"cam": (Camera(0,0,1,1), Camera(0.1,0,0.8,1)), "dur": 2.5,  # dolly in
         "bg": lambda d: (bg_sky(d,(10,10,30),(30,30,60)), bg_ground(d,H//2+100,(20,40,20),(10,20,10))),
         "draw": [
             lambda d,t: draw_stars(d, 80),
             lambda d,t: draw_constellation(d),
             lambda d,t: draw_sun(d, W-100, 70, r=15) if False else None,  # moon instead
             lambda d,t: d.ellipse([W-130,50,W-70,110], fill=(220,220,200,220)),
             lambda d,t: d.ellipse([W-120,55,W-80,100], fill=(10,10,30,255)),
         ]},
        {"cam": Camera(0.25,0.1,0.5,0.8), "dur": 2.5,
         "bg": lambda d: (bg_sky(d,(10,10,30),(30,30,60)), bg_ground(d,H//2+100,(20,40,20),(10,20,10))),
         "draw": [
             lambda d,t: draw_stars(d, 40),
             lambda d,t: draw_human_stick(d, W//2, H//2+60, s=2.5),
             lambda d,t: draw_timeline(d, W//2, H//2+120, 200) if t>0.3 else None,
         ]},
    ]
})

# ── Scene 3 ──
SCENES.append({
    "narration": "What happened to the Maya?",
    "shots": [
        {"cam": LONG, "dur": 2.0,
         "bg": lambda d: (bg_sky(d,(100,170,200),(180,210,240)), bg_ground(d,H//2+60,(60,130,60),(40,100,40))),
         "draw": [
             lambda d,t: draw_pyramid(d, int(W*0.35), H//2+100, 150, 200, steps=True),
             lambda d,t: draw_pyramid(d, int(W*0.65), H//2+80, 100, 140, steps=True),
             lambda d,t: draw_house(d, int(W*0.2), H//2+80, 1.2),
             lambda d,t: draw_house(d, int(W*0.8), H//2+70, 1.0),
             lambda d,t: draw_sun(d, W-80, 70, r=25),
         ]},
        {"cam": Camera(0.2,0,0.6,1), "dur": 1.5,
         "bg": lambda d: (bg_sky(d,(100,170,200),(180,210,240)), bg_ground(d,H//2+60,(60,130,60),(40,100,40))),
         "draw": [
             lambda d,t: draw_pyramid(d, W//2, H//2+100, 150, 200, steps=True),
             lambda d,t: draw_question_mark(d, W//2, H//2-110, size=80) if t>0.3 else None,
             # Flash effect
             lambda d,t: d.rectangle([0,0,W,H], fill=(255,255,255,200)) if 0.1<t<0.15 else None,
         ]},
    ]
})

# ── Scene 4 ──
SCENES.append({
    "narration": "Then, around the 800s AD, something strange began to happen.",
    "shots": [
        {"cam": MED, "dur": 2.5,
         "bg": lambda d: (bg_sky(d,(150,170,190),(180,200,220)), bg_ground(d,H//2+60,(100,120,90),(70,90,60))),
         "draw": [
             lambda d,t: draw_timeline(d, W//2, H-100, 500),
             lambda d,t: draw_building(d, int(W*0.3), H//2+80, alpha=220) if t<0.5 else None,
             lambda d,t: draw_building(d, int(W*0.3), H//2+80, alpha=int(220-150*(min(1,max(0,t-0.5))*2))) if t>=0.5 else None,
             lambda d,t: draw_building(d, int(W*0.7), H//2+80, alpha=220) if t<0.3 else None,
         ]},
    ]
})

# ── Scene 5 ──
SCENES.append({
    "narration": "One by one, major cities stopped building monuments.",
    "shots": [
        {"cam": (Camera(0.1,0,0.8,1), Camera(0.3,0,0.4,1)), "dur": 3.0,  # push in
         "bg": lambda d: (bg_sky(d,(140,160,180),(170,190,210)), bg_ground(d,H//2+80,(90,110,80),(60,80,50))),
         "draw": [
             lambda d,t: draw_human_stick(d, int(W*0.35), H//2+80, s=2.0),
             lambda d,t: draw_human_stick(d, int(W*0.45), H//2+75, s=2.0),
             lambda d,t: draw_human_stick(d, int(W*0.55), H//2+80, s=2.0),
             # Workers fade out one by one
             lambda d,t: d.rectangle([0,0,W,H], fill=(140,160,180, 100*min(1,max(0,t-0.5)*2))) if t>0.5 else None,
         ]},
        {"cam": CU, "dur": 1.5,
         "bg": lambda d: (bg_sky(d,(130,150,170),(160,180,200)), bg_ground(d,H//2+80,(80,100,70),(50,70,40))),
         "draw": [
             lambda d,t: draw_pyramid(d, W//2, H//2+100, 100, 130, steps=False),
             # Half-built: missing top
             lambda d,t: draw_pyramid(d, W//2, H//2+100, 100, 70, steps=False),
         ]},
    ]
})

# ── Scene 6 ──
SCENES.append({
    "narration": "Royal palaces were abandoned.",
    "shots": [
        {"cam": MED, "dur": 2.5,
         "bg": lambda d: (bg_sky(d,(130,140,150),(160,170,180)), bg_ground(d,H//2+100,(80,80,70),(50,50,40))),
         "draw": [
             lambda d,t: draw_throne(d, W//2, H//2+80, 100, 150),
             # Leaves blowing
             lambda d,t: draw_leaf(d, int(W*0.15+30*math.sin(t*3)), int(H*0.3+t*H*0.4), s=1.0),
             lambda d,t: draw_leaf(d, int(W*0.8+20*math.sin(t*4)), int(H*0.4+t*H*0.3), s=0.8),
         ]},
        {"cam": CU, "dur": 1.5,
         "bg": lambda d: (bg_sky(d,(130,140,150),(160,170,180)), bg_ground(d,H//2+120,(80,80,70),(50,50,40))),
         "draw": [
             lambda d,t: draw_throne(d, W//2, H//2+80, 100, 150),
             # Cracks appear
             lambda d,t: d.line([(W//2-30,H//2-40),(W//2-10,H//2-15)], fill=(60,55,50,200), width=2) if t>0.3 else None,
             lambda d,t: d.line([(W//2-10,H//2-15),(W//2-25,H//2-10)], fill=(60,55,50,180), width=1) if t>0.5 else None,
         ]},
    ]
})

# ── Scene 7 ──
SCENES.append({
    "narration": "Was it war?",
    "shots": [
        {"cam": LONG, "dur": 2.0,
         "bg": lambda d: (bg_sky(d,(100,90,80),(140,120,100)), bg_ground(d,H//2+80,(100,70,50),(70,50,30))),
         "draw": [
             lambda d,t: draw_pyramid(d, int(W*0.25), H//2+100, 120, 160, steps=True),
             lambda d,t: draw_pyramid(d, int(W*0.75), H//2+100, 120, 160, steps=True),
             # Warriors between
             lambda d,t: draw_human_stick(d, int(W*0.35), H//2+80, s=2.0),
             lambda d,t: draw_human_stick(d, int(W*0.38), H//2+80, s=2.0),
             lambda d,t: draw_human_stick(d, int(W*0.62), H//2+80, s=2.0),
             lambda d,t: draw_human_stick(d, int(W*0.65), H//2+80, s=2.0),
             # Shields (circles)
             lambda d,t: d.ellipse([int(W*0.34),H//2+55,int(W*0.38),H//2+75], fill=(180,120,80,200), outline=(60,55,50,180), width=2),
             lambda d,t: d.ellipse([int(W*0.63),H//2+55,int(W*0.67),H//2+75], fill=(120,80,150,200), outline=(60,55,50,180), width=2),
         ]},
        {"cam": CU, "dur": 1.5,
         "bg": lambda d: (bg_sky(d,(100,90,80),(140,120,100)), bg_ground(d,H//2+100,(100,70,50),(70,50,30))),
         "draw": [
             lambda d,t: draw_human_stick(d, W//2, H//2+80, s=3.0),
             lambda d,t: d.ellipse([W//2-18,H//2+55,W//2-4,H//2+75], fill=(180,120,80,200), outline=(60,55,50,180), width=3),
             lambda d,t: d.line([(W//2-10,H//2-10),(W//2+30,H//2-50)], fill=(150,130,100,200), width=3) if t>0.5 else None,
         ]},
    ]
})

# ── Scene 8 ──
SCENES.append({
    "narration": "Evidence suggests the Maya faced severe droughts.",
    "shots": [
        {"cam": (Camera(0,0,1,1), Camera(0,0.1,0.8,0.9)), "dur": 2.5,  # slight zoom
         "bg": lambda d: (bg_sky(d,(220,180,140),(255,220,180)), bg_ground(d,H//2+100,(180,150,100),(100,80,50))),
         "draw": [
             lambda d,t: draw_sun(d, W//2, 80, r=35+5*t),  # sun enlarges
             draw_cracked_earth,
             lambda d,t: draw_sun(d, W-80, 60, r=30+10*t),
         ]},
        {"cam": CU, "dur": 2.0,
         "bg": lambda d: (bg_sky(d,(220,180,140),(255,220,180)),),
         "draw": [
             lambda d,t: draw_cracked_earth(d, W//2, H//2+40, 300, 120),
         ]},
    ]
})

# ── Scene 9 ──
SCENES.append({
    "narration": "Years without enough rain meant crops failed.",
    "shots": [
        {"cam": MED, "dur": 3.0,
         "bg": lambda d: (bg_sky(d,(180,200,180),(200,220,200)), bg_ground(d,H//2+60,(80,160,60),(60,120,40))),
         "draw": [
             # Corn stalks turning brown
             lambda d,t: draw_tree(d, int(W*0.3), H//2+80, s=2.0) if t<0.3 else None,
             lambda d,t: draw_tree(d, int(W*0.5), H//2+80, s=2.5) if t<0.5 else None,
             lambda d,t: draw_tree(d, int(W*0.7), H//2+80, s=2.0) if t<0.7 else None,
             # Brown tint overlay
             lambda d,t: d.rectangle([0,0,W,H], fill=(180,140,80, 150*min(1,max(0,(t-0.3)*2)))) if t>0.3 else None,
             # Wilted plants
             lambda d,t: draw_stump(d, int(W*0.3), H//2+80, 20) if t>0.5 else None,
         ]},
    ]
})

# ── Scene 10 ──
SCENES.append({
    "narration": "Food became scarce.",
    "shots": [
        {"cam": Camera(0.2,0.1,0.6,0.8), "dur": 2.5,
         "bg": lambda d: (bg_sky(d,(160,170,180),(190,200,210)), bg_ground(d,H//2+80,(100,100,80),(70,70,50))),
         "draw": [
             # Empty baskets
             lambda d,t: d.ellipse([int(W*0.35)-20, H//2-10, int(W*0.35)+20, H//2+30], fill=(160,140,100,220), outline=(100,80,50,180), width=2),
             lambda d,t: d.ellipse([int(W*0.65)-20, H//2-10, int(W*0.65)+20, H//2+30], fill=(160,140,100,220), outline=(100,80,50,180), width=2),
             # Worried family
             lambda d,t: draw_human_stick(d, int(W*0.4), H//2+80, s=2.5),
             lambda d,t: draw_human_stick(d, int(W*0.6), H//2+75, s=2.0),
         ]},
    ]
})

# ── Scene 11 ──
SCENES.append({
    "narration": "As resources shrank, rival city-states fought.",
    "shots": [
        {"cam": Camera(0,0,1,1), "dur": 3.0,
         "bg": lambda d: (d.rectangle([0,0,W,H], fill=(200,190,170,255)),
                          d.rectangle([0,0,W,H], fill=None, outline=(180,170,150,100), width=1)),
         "draw": [
             # Map grid
             lambda d,t: [d.line([(x,0),(x,H)], fill=(180,170,150,100), width=1) for x in range(0,W,60)],
             lambda d,t: [d.line([(0,y),(W,y)], fill=(180,170,150,100), width=1) for y in range(0,H,60)],
             # City markers
             lambda d,t: d.rectangle([W//3-25,H//3-20,W//3+25,H//3+20], fill=(160,140,110,180), outline=(100,80,60,200), width=2),
             lambda d,t: d.rectangle([2*W//3-20,H//3,H//2+20], fill=(160,140,110,180), outline=(100,80,60,200), width=2),
             # Conflict arrows
             lambda d,t: d.line([(W//3+25,H//3),(2*W//3-20,H//3+30)], fill=(200,60,50,200), width=3),
             lambda d,t: d.polygon([(2*W//3-35,H//3+24),(2*W//3-35,H//3+36),(2*W//3-20,H//3+30)], fill=(200,60,50,200)),
             # Fire icons
             lambda d,t: d.ellipse([2*W//3-8,H//3+10,2*W//3+8,H//3+26], fill=(255,150,50,200)),
         ]},
    ]
})

# ── Scene 12 ──
SCENES.append({
    "narration": "Large forests had been cleared.",
    "shots": [
        {"cam": LONG, "dur": 2.5,
         "bg": lambda d: (bg_sky(d,(140,180,200),(170,200,220)), bg_ground(d,H//2+60,(60,120,50),(40,90,30))),
         "draw": [
             # Trees fade out one by one
             lambda d,t: draw_tree(d, int(W*0.2-5*t*W), H//2+80, s=2.5) if t<0.3 else None,
             lambda d,t: draw_tree(d, int(W*0.5-10*t*W), H//2+70, s=2.0) if t<0.5 else None,
             lambda d,t: draw_tree(d, int(W*0.8-5*t*W), H//2+85, s=2.5) if t<0.7 else None,
             # Stumps remain
             lambda d,t: draw_stump(d, int(W*0.2), H//2+80, 20) if t>0.3 else None,
             lambda d,t: draw_stump(d, int(W*0.5), H//2+70, 18) if t>0.5 else None,
             lambda d,t: draw_stump(d, int(W*0.8), H//2+85, 22) if t>0.7 else None,
         ]},
    ]
})

# ── Scene 13 ──
SCENES.append({
    "narration": "Eventually, many people left.",
    "shots": [
        {"cam": (LONG, Camera(0.3,0,0.4,1)), "dur": 3.0,  # zoom in
         "bg": lambda d: (bg_sky(d,(150,170,190),(180,200,220)), bg_ground(d,H//2+80,(80,130,70),(50,90,40))),
         "draw": [
             # City shrinking
             lambda d,t: draw_pyramid(d, int(W*0.7-20*t), H//2+100, int(150-50*t), int(200-80*t), steps=True),
             # Families walking away
             lambda d,t: draw_human_stick(d, int(W*0.2+t*W*0.3), H//2+80, s=2.0),
             lambda d,t: draw_human_stick(d, int(W*0.25+t*W*0.3), H//2+75, s=1.8),
             lambda d,t: draw_human_stick(d, int(W*0.3+t*W*0.2), H//2+85, s=1.5),
             # Footprints
             lambda d,t: draw_footprint(d, int(W*0.15+t*W*0.2)-20, H//2+90) if t>0.2 else None,
             lambda d,t: draw_footprint(d, int(W*0.2+t*W*0.2), H//2+100) if t>0.3 else None,
             lambda d,t: draw_footprint(d, int(W*0.25+t*W*0.2)+20, H//2+95) if t>0.4 else None,
         ]},
    ]
})

# ── Scene 14 ──
SCENES.append({
    "narration": "The jungle slowly reclaimed them.",
    "shots": [
        {"cam": (Camera(0.2,0,0.6,1), Camera(0,0,1,1)), "dur": 3.0,  # zoom out
         "bg": lambda d: (bg_sky(d,(60,130,100),(100,180,140)), bg_ground(d,H//2+80,(40,100,40),(30,70,30))),
         "draw": [
             lambda d,t: draw_pyramid(d, W//2, H//2+100, 150, 200, steps=True),
             # Vines/roots growing over
             lambda d,t: d.line([(W//2-60,H//2-30),(W//2-30,H//2-60),(W//2+20,H//2-40)], fill=(40,120,40,200), width=4) if t>0.3 else None,
             lambda d,t: d.line([(W//2-40,H//2-80),(W//2-10,H//2-100),(W//2+40,H//2-90)], fill=(40,120,40,200), width=3) if t>0.5 else None,
             lambda d,t: d.line([(W//2,H//2-120),(W//2+30,H//2-130),(W//2+60,H//2-110)], fill=(40,120,40,200), width=3) if t>0.7 else None,
             # Trees growing through
             lambda d,t: draw_tree(d, int(W*0.3), H//2+80, s=3.0) if t>0.5 else None,
             lambda d,t: draw_tree(d, int(W*0.7), H//2+70, s=2.5) if t>0.7 else None,
         ]},
    ]
})

# ── Scene 15 ──
SCENES.append({
    "narration": "But here's the biggest misconception. The Maya did not vanish.",
    "shots": [
        {"cam": Camera(0.15,0,0.7,1), "dur": 2.0,
         "bg": lambda d: (bg_sky(d,(180,200,220),(200,220,240)), bg_ground(d,H//2+60,(60,140,60),(40,100,40))),
         "draw": [
             lambda d,t: draw_human_stick(d, W//2-60, H//2+80, s=2.5),  # ancient Maya
             lambda d,t: draw_human_stick(d, W//2+60, H//2+80, s=2.5),  # modern Maya
             lambda d,t: draw_human_stick(d, W//2+80, H//2+75, s=2.0),  # modern child
             # Timeline connecting them
             lambda d,t: d.line([(W//2-80,H//2-60),(W//2+80,H//2-60)], fill=(60,55,50,200), width=3) if t>0.3 else None,
             lambda d,t: d.ellipse([W//2-90,H//2-66,W//2-70,H//2-54], fill=(120,80,50,220)) if t>0.3 else None,
             lambda d,t: d.ellipse([W//2+70,H//2-66,W//2+90,H//2-54], fill=(120,80,50,220)) if t>0.3 else None,
         ]},
    ]
})

# ── Scene 16 ──
SCENES.append({
    "narration": "The cities fell. The people remained.",
    "shots": [
        {"cam": LONG, "dur": 3.0,
         "bg": lambda d: (d.rectangle([0,0,W//2,H], fill=(180,150,120,255)),
                          d.rectangle([W//2,0,W,H], fill=(100,160,200,255)),
                          d.line([(W//2,0),(W//2,H)], fill=(255,200,100,150), width=3)),
         "draw": [
             # Left side: ruined temple
             lambda d,t: draw_pyramid(d, W//4, H//2+80, 100, 140, steps=False),
             lambda d,t: d.line([(W//4-30,H//2-20),(W//4+30,H//2-10)], fill=(60,55,50,150), width=2),
             lambda d,t: d.line([(W//4-20,H//2-40),(W//4+20,H//2-20)], fill=(60,55,50,150), width=2),
             # Right side: modern Maya family
             lambda d,t: draw_human_stick(d, int(3*W//4), H//2+80, s=2.5),
             lambda d,t: draw_human_stick(d, int(3*W//4)+40, H//2+75, s=2.0),
             lambda d,t: draw_house(d, int(3*W//4), H//2+80, 1.5),
             # Sunset fade overlay
             lambda d,t: d.rectangle([0,0,W,H], fill=(255,180,80, 100*min(1,t/2))) if t>1.0 else None,
         ]},
    ]
})


# ─── Render ───────────────────────────────────────────────────────

total_frames = 0
for si, scene in enumerate(SCENES):
    total_shots = len(scene["shots"])
    total_dur = sum(sh["dur"] for sh in scene["shots"])
    total_frames_scene = int(total_dur * FPS)
    
    frame_idx = 0
    for sh_idx, shot in enumerate(scene["shots"]):
        cam_spec = shot["cam"]
        dur = shot["dur"]
        shot_frames = int(dur * FPS)
        
        for f in range(shot_frames):
            t = f / shot_frames  # 0..1 within this shot
            
            # Camera interpolation
            if isinstance(cam_spec, tuple):
                cam = lerp_cam(cam_spec[0], cam_spec[1], t)
            else:
                cam = cam_spec
            
            # Render world at 2x for crop quality
            W2, H2 = W*2, H*2
            world = Image.new("RGBA", (W2, H2), (255,255,255,255))
            dw = ImageDraw.Draw(world)
            
            # Background
            bg_fn = shot.get("bg")
            if bg_fn:
                bg_fn(dw)
            
            # Draw elements
            for draw_fn in shot.get("draw", []):
                try:
                    result = draw_fn(dw, t)
                    if isinstance(result, tuple):
                        for r in result:
                            if r: pass
                except Exception as e:
                    pass
            
            # Text overlay
            _text(dw, scene["narration"], y=H2-60, size=28, fill=(60,55,50))
            
            # Label
            fnt = _font(16)
            dw.text((20, 16), f"Scene {si+1} — shot {sh_idx+1}", fill=(80,75,70,160), font=fnt)
            
            # Crop to camera
            frame = cam.crop(world)
            
            fpath = os.path.join(frames_dir, f"scene_{si:03d}_frame_{frame_idx:04d}.png")
            frame.save(fpath)
            frame_idx += 1
    
    print(f"  Scene {si+1}/{len(SCENES)} — {frame_idx} frames")

# ─── Assemble ─────────────────────────────────────────────────────

total = sum(len(os.listdir(frames_dir)) for _ in [1])
print(f"\n{total} frames. Assembling video...")

video_path = os.path.join(out_dir, "maya_cinematic.mp4")

scene_videos = []
for si in range(len(SCENES)):
    sv = os.path.join(out_dir, f"scene_{si:03d}.mp4")
    pattern = os.path.join(frames_dir, f"scene_{si:03d}_frame_%04d.png")
    subprocess.run(["ffmpeg","-y","-framerate",str(FPS),"-i",pattern,
                    "-c:v","libx264","-pix_fmt","yuv420p","-vf","format=yuv420p",
                    "-r",str(FPS),sv], capture_output=True)
    scene_videos.append(sv)

concat_v = os.path.join(out_dir, "concat_videos.txt")
with open(concat_v, "w") as f:
    for sv in scene_videos:
        f.write(f"file '{os.path.abspath(sv)}'\n")

subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",concat_v,"-c","copy",video_path])
print(f"✅ Video: {video_path}")

# TTS
try:
    import asyncio
    async def tts():
        tts_dir = os.path.join(out_dir, "tts")
        os.makedirs(tts_dir)
        audios = []
        for i, sc in enumerate(SCENES):
            ap = os.path.join(tts_dir, f"scene_{i:03d}.mp3")
            p = await asyncio.create_subprocess_exec("edge-tts","--voice","en-GB-RyanNeural",
                "--text",sc["narration"],"--write-media",ap,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
            await p.wait(); audios.append(ap)
        ac = os.path.join(out_dir, "concat_audio.txt")
        with open(ac,"w") as f:
            for ap in audios: f.write(f"file '{os.path.abspath(ap)}'\n")
        fa = os.path.join(out_dir, "full_audio.mp3")
        subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",ac,"-c","copy",fa])
        final = os.path.join(out_dir, "maya_cinematic_tts.mp4")
        subprocess.run(["ffmpeg","-y","-i",video_path,"-i",fa,"-c:v","copy","-c:a","aac","-shortest",final])
        print(f"✅ With TTS: {final}")
    asyncio.run(tts())
except Exception as e:
    print(f"TTS skipped: {e}")

print("Done!")
