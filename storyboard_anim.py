"""Animated storyboard — hand-drawn scenes with per-element reveals, pans, zooms, text sync."""

import sys, os, math, random, json, time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
from moviepy import (
    VideoClip, AudioFileClip, CompositeAudioClip, concatenate_audioclips,
    CompositeVideoClip, ImageClip,
)
import config
from src.text_to_speech import generate_tts_with_timestamps
from src.engagement import subscribe_end_card

W, H = config.VIDEO_WIDTH, config.VIDEO_HEIGHT
FPS = config.VIDEO_FPS
rng = random.Random()

# ─── Drawing primitives ────────────────────────────────────────

def _stroke(draw, pts, w=2, color=(0,0,0), amp=1.2):
    if len(pts) < 2: return
    for i in range(len(pts)-1):
        steps = max(int(math.hypot(pts[i+1][0]-pts[i][0], pts[i+1][1]-pts[i][1])/2), 3)
        for s in range(steps):
            t = s/steps
            px = pts[i][0] + (pts[i+1][0]-pts[i][0])*t + rng.gauss(0, amp*0.4)
            py = pts[i][1] + (pts[i+1][1]-pts[i][1])*t + rng.gauss(0, amp*0.4)
            rw = w * (0.85 + rng.random()*0.3)
            draw.ellipse([px-rw/2, py-rw/2, px+rw/2, py+rw/2], fill=color)

def _fill(draw, pts, color, amp=2):
    if len(pts) < 3: return
    draw.polygon([(x+rng.gauss(0,amp), y+rng.gauss(0,amp)) for x,y in pts], fill=color)

def _circle(draw, cx, cy, r, fill_c=None, line_c=(0,0,0), w=2):
    pts = [(cx+math.cos(math.radians(a))*r+rng.gauss(0,0.5), cy+math.sin(math.radians(a))*r+rng.gauss(0,0.5)) for a in range(0,361,15)]
    if fill_c: _fill(draw, pts, fill_c, amp=1)
    _stroke(draw, pts, w=w, color=line_c, amp=0.8)

def _rect(draw, x, y, w, h, fill_c=None, line_c=(0,0,0), lw=2):
    pts = [(x+wg, y+wg) for wg in [rng.gauss(0,1)]*4 for _ in[0]][:0]
    pts = [(x+rng.gauss(0,1), y+rng.gauss(0,1)), (x+w+rng.gauss(0,1), y+rng.gauss(0,1)),
           (x+w+rng.gauss(0,1), y+h+rng.gauss(0,1)), (x+rng.gauss(0,1), y+h+rng.gauss(0,1))]
    if fill_c: _fill(draw, pts, fill_c, amp=1)
    _stroke(draw, pts+[pts[0]], w=lw, color=line_c, amp=0.8)

def _paper_bg(draw, w, h):
    for _ in range(1200):
        x, y = rng.randint(0, w-1), rng.randint(0, h-1)
        v = rng.randint(-12, 4)
        c = 250 + v
        draw.point((x, y), fill=(c, c-2, c-4))

def _sky_grad(draw, w, h, sky_type="day"):
    if sky_type == "night":
        for y in range(h):
            t = y/h
            draw.line([(0,y),(w,y)], fill=(int(10+t*20), int(5+t*15), int(20+t*40)))
    elif sky_type == "sunset":
        for y in range(h):
            t = y/h
            draw.line([(0,y),(w,y)], fill=(int(60+195*t), int(30+180*t), int(60+80*(1-t))))
    else:
        for y in range(h):
            t = y/h
            draw.line([(0,y),(w,y)], fill=(int(225-t*25), int(230-t*20), int(240-t*15)))

def _ground_grad(draw, x, y, w, h, c=(40,100,40)):
    for gy in range(int(h)):
        t = gy/h
        r = int(c[0]+t*20)
        g = int(c[1]+t*15)
        b = int(c[2]-t*10)
        draw.line([(x, y+gy), (x+w, y+gy)], fill=(r, g, b))

def _get_font(size=36):
    try: return ImageFont.truetype(config.get_font(), size)
    except: return ImageFont.load_default()

# ─── High-quality scene drawings ──────────────────────────────

def draw_pirate_with_parrot(draw, cx, cy, s=1.0):
    """Scene 1: Pirate with eyepatch, parrot on shoulder, treasure chest, palm tree."""
    # Palm tree
    _stroke(draw, [(cx-120*s, cy+40*s), (cx-115*s, cy-80*s), (cx-110*s, cy-100*s)], w=5, color=(60,45,30), amp=2)
    for i in range(6):
        a = math.radians(-60 + i*25)
        l = 25*s + rng.randint(5, 10)*s
        _stroke(draw, [(cx-110*s, cy-100*s), (cx-110*s+math.cos(a)*l, cy-100*s+math.sin(a)*l)], w=3, color=(40,70,30), amp=2)
    
    # Treasure chest
    chest_x, chest_y = cx+60*s, cy+20*s
    _rect(draw, chest_x-25*s, chest_y, 50*s, 30*s, fill_c=(120,80,40,180), line_c=(80,50,30))
    _stroke(draw, [(chest_x-25*s, chest_y+10*s), (chest_x+0*s, chest_y-5*s), (chest_x+25*s, chest_y+10*s)], w=3, color=(80,50,30), amp=1)
    # Coins
    for i in range(5):
        _circle(draw, chest_x-15*s+i*7*s, chest_y+25*s, 4*s, fill_c=(255,200,50,150), line_c=(200,160,30))
    
    # Pirate body
    px, py = cx, cy-20*s
    body = [(px-15*s, py+10*s), (px-12*s, py-35*s), (px+12*s, py-35*s), (px+15*s, py+10*s)]
    _fill(draw, body, (60,40,30,200), amp=2)
    _stroke(draw, body, w=3, color=(40,30,20), amp=1.5)
    
    # Pirate head
    _circle(draw, px, py-48*s, 14*s, fill_c=(230,190,160,200), line_c=(180,150,130))
    
    # Eyepatch
    _fill(draw, [(px-10*s, py-52*s), (px-2*s, py-52*s), (px-2*s, py-45*s), (px-10*s, py-45*s)], (20,20,20,200), amp=1)
    _stroke(draw, [(px-14*s, py-50*s), (px-8*s, py-48*s), (px-2*s, py-50*s)], w=2, color=(20,20,20), amp=0.5)
    
    # Other eye
    draw.ellipse([px+4*s, py-50*s, px+7*s, py-47*s], fill=(20,20,20))
    
    # Beard
    for i in range(8):
        _stroke(draw, [(px-8*s+i*2*s, py-38*s), (px-8*s+i*2*s+rng.randint(-3,3), py-28*s+rng.randint(-5,5))], w=2, color=(40,30,20), amp=1)
    
    # Pirate hat
    _fill(draw, [(px-18*s, py-55*s), (px-20*s, py-68*s), (px, py-72*s), (px+20*s, py-68*s), (px+18*s, py-55*s)], (30,25,20,220), amp=2)
    _stroke(draw, [(px-18*s, py-55*s), (px+18*s, py-55*s)], w=3, color=(20,15,10))
    
    # Parrot on shoulder
    par_x, par_y = px+16*s, py-30*s
    _fill(draw, [(par_x, par_y), (par_x+8*s, par_y-12*s), (par_x+14*s, par_y-8*s)], (200,50,50,200), amp=1.5)
    _stroke(draw, [(par_x, par_y), (par_x+8*s, par_y-12*s), (par_x+14*s, par_y-8*s)], w=2, color=(150,30,30))
    _circle(draw, par_x+2*s, par_y-2*s, 4*s, fill_c=(200,50,50,200), line_c=(150,30,30))
    draw.ellipse([par_x+4*s, par_y-4*s, par_x+6*s, par_y-2*s], fill=(255,255,200))
    _stroke(draw, [(par_x+14*s, par_y-8*s), (par_x+18*s, par_y-12*s), (par_x+14*s, par_y-4*s)], w=2, color=(200,180,50), amp=1)
    # Parrot legs
    _stroke(draw, [(par_x, par_y), (par_x-2*s, py-28*s)], w=1.5, color=(80,60,40))
    _stroke(draw, [(par_x+2*s, par_y), (par_x+4*s, py-28*s)], w=1.5, color=(80,60,40))

def draw_x_marks(draw, cx, cy, s=1.0):
    """Scene 2: X marks appearing over myth elements."""
    colors = [(200,30,30), (180,20,20)]
    for i, (ox, oy) in enumerate([(-40*s, -20*s), (0, 10*s), (40*s, -30*s)]):
        c = colors[i % 2]
        _stroke(draw, [(cx+ox-12*s, cy+oy-12*s), (cx+ox+12*s, cy+oy+12*s)], w=5, color=c, amp=1)
        _stroke(draw, [(cx+ox+12*s, cy+oy-12*s), (cx+ox-12*s, cy+oy+12*s)], w=5, color=c, amp=1)

def draw_ship(draw, cx, cy, s=1.0, ship_type="merchant"):
    """Generic sailing ship."""
    hull = [(cx-40*s, cy), (cx-35*s, cy+15*s), (cx+35*s, cy+15*s), (cx+40*s, cy)]
    _fill(draw, hull, (80,60,40,200), amp=2)
    _stroke(draw, hull, w=3, color=(50,35,20))
    # Mast
    _stroke(draw, [(cx, cy), (cx, cy-60*s)], w=4, color=(60,45,30), amp=1)
    # Sail
    sail_c = (240,235,220) if ship_type == "merchant" else (30,30,30)
    _fill(draw, [(cx, cy-55*s), (cx-30*s, cy-15*s), (cx, cy-10*s)], (*sail_c, 200), amp=2)
    _stroke(draw, [(cx, cy-55*s), (cx-30*s, cy-15*s), (cx, cy-10*s)], w=2, color=(100,95,85))
    # Flag
    if ship_type == "pirate":
        _fill(draw, [(cx, cy-60*s), (cx+15*s, cy-55*s), (cx, cy-50*s)], (20,20,20,200), amp=1)
        # Skull
        _circle(draw, cx+7*s, cy-55*s, 4*s, fill_c=(255,255,255,150), line_c=(255,255,255))
    elif ship_type == "navy":
        _fill(draw, [(cx, cy-60*s), (cx+15*s, cy-55*s), (cx, cy-50*s)], (30,60,120,200), amp=1)

def draw_angry_captain(draw, cx, cy, s=1.0):
    """Captain with cane."""
    body = [(cx-10*s, cy+5*s), (cx-8*s, cy-30*s), (cx+8*s, cy-30*s), (cx+10*s, cy+5*s)]
    _fill(draw, body, (40,30,80,200), amp=1.5)
    _stroke(draw, body, w=2.5, color=(30,20,60))
    _circle(draw, cx, cy-42*s, 10*s, fill_c=(230,190,160,200), line_c=(180,150,130))
    # Angry eyebrows
    _stroke(draw, [(cx-7*s, cy-47*s), (cx-3*s, cy-45*s)], w=2.5, color=(30,25,20))
    _stroke(draw, [(cx+3*s, cy-45*s), (cx+7*s, cy-47*s)], w=2.5, color=(30,25,20))
    # Cane
    _stroke(draw, [(cx+12*s, cy-5*s), (cx+20*s, cy+20*s), (cx+15*s, cy+25*s)], w=3, color=(60,40,20), amp=1)

def draw_sailors(draw, cx, cy, s=1.0, count=3):
    """Multiple small sailors pulling ropes."""
    for i in range(count):
        sx = cx - (count-1)*10*s/2 + i*10*s
        _circle(draw, sx, cy-30*s, 6*s, fill_c=(230,190,160,200), line_c=(180,150,130))
        body = [(sx-5*s, cy-25*s), (sx-4*s, cy-2*s), (sx+4*s, cy-2*s), (sx+5*s, cy-25*s)]
        _fill(draw, body, (100,80,60,180), amp=1.5)
        _stroke(draw, body, w=2, color=(70,55,45))
        # Arms pulling
        _stroke(draw, [(sx-5*s, cy-18*s), (sx-12*s, cy-22*s), (sx-15*s, cy-18*s)], w=2, color=(100,80,60), amp=1.5)
        _stroke(draw, [(sx+5*s, cy-18*s), (sx+12*s, cy-22*s), (sx+15*s, cy-18*s)], w=2, color=(100,80,60), amp=1.5)

def draw_doodles(draw, cx, cy, s=1.0, items=None):
    """Small doodle items appearing sequentially."""
    if not items: return
    for i, item in enumerate(items):
        ox = cx + (i - (len(items)-1)/2) * 30*s
        oy = cy + rng.randint(-10, 10)*s
        if item == "biscuit":
            _circle(draw, ox, oy, 8*s, fill_c=(200,180,150,180), line_c=(160,140,110))
            for _ in range(5):
                _stroke(draw, [(ox+rng.randint(-6,6)*s, oy+rng.randint(-6,6)*s), (ox+rng.randint(-6,6)*s, oy+rng.randint(-6,6)*s)], w=1, color=(100,180,80), amp=0.3)
        elif item == "pocket":
            _rect(draw, ox-8*s, oy-5*s, 16*s, 12*s, fill_c=(180,170,150,150), line_c=(100,90,70))
            _rect(draw, ox-4*s, oy-2*s, 8*s, 6*s, fill_c=(250,245,235,200), line_c=(150,140,120))
        elif item == "sick":
            _circle(draw, ox, oy-8*s, 7*s, fill_c=(180,200,180,200), line_c=(120,140,120))
            body = [(ox-5*s, oy-2*s), (ox-4*s, oy+10*s), (ox+4*s, oy+10*s), (ox+5*s, oy-2*s)]
            _fill(draw, body, (180,200,180,180), amp=1)
        elif item == "barrel":
            _rect(draw, ox-8*s, oy-10*s, 16*s, 20*s, fill_c=(140,100,60,180), line_c=(80,60,30))
            _stroke(draw, [(ox-8*s, oy-5*s), (ox+8*s, oy-5*s)], w=2, color=(60,40,20))
            _stroke(draw, [(ox-8*s, oy+5*s), (ox+8*s, oy+5*s)], w=2, color=(60,40,20))

def draw_fork_road(draw, cx, cy, s=1.0):
    """Fork in the road with two paths."""
    _ground_grad(draw, 0, cy, W, int(H-cy), (60,50,30))
    # Road
    _stroke(draw, [(cx, cy+40*s), (cx-30*s, cy-10*s), (cx-40*s, cy-30*s)], w=8, color=(130,110,80), amp=1)
    _stroke(draw, [(cx, cy+40*s), (cx+30*s, cy-10*s), (cx+40*s, cy-30*s)], w=8, color=(130,110,80), amp=1)
    # Left sign
    _rect(draw, cx-55*s, cy-45*s, 30*s, 15*s, fill_c=(240,230,200,180), line_c=(80,60,40))
    _stroke(draw, [(cx-40*s, cy-30*s), (cx-40*s, cy-45*s)], w=2, color=(60,40,20))
    # Right sign
    _rect(draw, cx+25*s, cy-45*s, 30*s, 15*s, fill_c=(240,230,200,180), line_c=(80,60,40))
    _stroke(draw, [(cx+40*s, cy-30*s), (cx+40*s, cy-45*s)], w=2, color=(60,40,20))

def draw_voting_pirates(draw, cx, cy, s=1.0):
    """Pirates around a table voting."""
    # Table
    _rect(draw, cx-35*s, cy-5*s, 70*s, 10*s, fill_c=(100,70,40,180), line_c=(60,40,20))
    # Pirates
    for i, (dx, dc) in enumerate([(-25*s, (60,40,30)), (0, (50,50,80)), (25*s, (80,40,40))]):
        pcx, pcy = cx+dx, cy-25*s
        _circle(draw, pcx, pcy-12*s, 8*s, fill_c=(230,190,160,200), line_c=(180,150,130))
        body = [(pcx-8*s, pcy-5*s), (pcx-6*s, pcy+10*s), (pcx+6*s, pcy+10*s), (pcx+8*s, pcy-5*s)]
        _fill(draw, body, (*dc, 180), amp=1.5)
        # Raised hand
        _stroke(draw, [(pcx+8*s, pcy-2*s), (pcx+14*s, pcy-12*s)], w=2.5, color=dc, amp=1)
    # Speech bubble
    bubble = [(cx, cy-55*s), (cx-20*s, cy-45*s), (cx+20*s, cy-45*s)]
    _fill(draw, bubble, (255,255,255,200), amp=2)
    _stroke(draw, bubble, w=2, color=(100,100,100), amp=1)
    tf = _get_font(18)
    draw.text((cx-15*s, cy-52*s), "VOTE!", font=tf, fill=(30,25,20))

def draw_calendar(draw, cx, cy, s=1.0):
    """Calendar with pages flipping."""
    for i, day in enumerate(["Day 1", "Day 12", "Day 27"]):
        _rect(draw, cx-15*s, cy-10*s+i*18*s, 30*s, 16*s, fill_c=(250,245,235,180), line_c=(100,90,80))
        tf = _get_font(int(12*s))
        draw.text((cx-10*s, cy-6*s+i*18*s), day, font=tf, fill=(100,90,80))

def draw_chest_open(draw, cx, cy, s=1.0):
    """Treasure chest opening with sugar, tobacco, cloth, spices."""
    _rect(draw, cx-30*s, cy, 60*s, 35*s, fill_c=(120,80,40,180), line_c=(80,50,30))
    _stroke(draw, [(cx-30*s, cy+12*s), (cx, cy-5*s), (cx+30*s, cy+12*s)], w=3, color=(80,50,30), amp=1)
    # Items inside
    items = [(255,220,150), (150,120,80), (200,180,160), (180,100,50)]
    for i, c in enumerate(items):
        ix = cx - 18*s + i * 12*s
        iy = cy + 20*s + rng.randint(-3, 3)*s
        _circle(draw, ix, iy, 6*s, fill_c=(*c, 180), line_c=(*[max(0,x-30) for x in c],))

def draw_gallows(draw, cx, cy, s=1.0):
    """Dark harbor with gallows silhouette."""
    # Dark sky
    for y in range(H):
        t = y/H
        draw.line([(0,y),(W,y)], fill=(int(5+t*15), int(3+t*10), int(10+t*20)))
    # Moon
    _circle(draw, int(W*0.8), 60, 25, fill_c=(200,200,180,80), line_c=(180,180,160,100))
    # Gallows
    _stroke(draw, [(cx, cy), (cx, cy-70*s)], w=5, color=(20,15,10), amp=1)
    _stroke(draw, [(cx-25*s, cy-70*s), (cx+25*s, cy-70*s)], w=4, color=(20,15,10), amp=1)
    _stroke(draw, [(cx-25*s, cy-70*s), (cx-25*s, cy-65*s)], w=3, color=(20,15,10), amp=0.5)
    # Rope
    _stroke(draw, [(cx, cy-70*s), (cx, cy-55*s)], w=1.5, color=(40,35,30))
    # Water reflection
    for i in range(20):
        wx = cx + rng.randint(-40, 40)
        wy = cy + rng.randint(5, 25)
        _stroke(draw, [(wx, wy), (wx+rng.randint(5,15), wy)], w=1, color=(20,15,10,80), amp=0.3)

def draw_sunrise_pirate(draw, cx, cy, s=1.0):
    """Pirate at ship bow, sunrise behind."""
    for y in range(H):
        t = y/H
        r = int(60 + 195*max(0, 1-t*2))
        g = int(30 + 180*max(0, 1-t*2))
        b = int(60 + 80*(1-max(0, 1-t*2)))
        draw.line([(0,y),(W,y)], fill=(r, g, b))
    # Sun
    _circle(draw, W//2, int(H*0.25), 40, fill_c=(255,200,50,100), line_c=(255,200,50,150))
    for a in range(0, 360, 30):
        _stroke(draw, [(W//2+math.cos(math.radians(a))*45, int(H*0.25)+math.sin(math.radians(a))*45),
                       (W//2+math.cos(math.radians(a))*60, int(H*0.25)+math.sin(math.radians(a))*60)], w=2, color=(255,200,50,100), amp=0.5)
    # Ship bow
    _fill(draw, [(cx-20*s, cy), (cx-15*s, cy+15*s), (cx+15*s, cy+15*s), (cx+20*s, cy)], (60,45,30,200), amp=2)
    _stroke(draw, [(cx, cy), (cx, cy-50*s)], w=3, color=(50,35,20))
    # Pirate figure
    px, py = cx, cy-30*s
    body = [(px-8*s, py+5*s), (px-6*s, py-20*s), (px+6*s, py-20*s), (px+8*s, py+5*s)]
    _fill(draw, body, (40,30,20,200), amp=1.5)
    _circle(draw, px, py-30*s, 8*s, fill_c=(30,25,20,200), line_c=(20,15,10))

# ─── Scene definitions ─────────────────────────────────────────

SCENE_BUILDERS = {
    1: lambda d: draw_pirate_with_parrot(d, W//2, int(H*0.6), 1.0),
    2: lambda d: draw_x_marks(d, W//2, int(H*0.5), 1.2),
    3: lambda d: (
        draw_ship(d, int(W*0.5), int(H*0.55), 1.5, "merchant"),
        draw_sailors(d, int(W*0.5), int(H*0.75), 0.8, 3),
        draw_angry_captain(d, int(W*0.7), int(H*0.5), 0.8),
    ),
    4: lambda d: draw_doodles(d, W//2, int(H*0.5), 1.0, ["biscuit", "pocket", "sick", "barrel"]),
    5: lambda d: draw_ship(d, W//2, int(H*0.55), 1.8, "pirate"),
    6: lambda d: draw_fork_road(d, W//2, int(H*0.6), 1.0),
    7: lambda d: draw_voting_pirates(d, W//2, int(H*0.55), 1.0),
    8: lambda d: (
        _sky_grad(d, W, H, "day"),
        draw_ship(d, int(W*0.5), int(H*0.6), 0.8, "merchant"),
        draw_calendar(d, int(W*0.5), int(H*0.5), 1.0),
    ),
    9: lambda d: draw_chest_open(d, W//2, int(H*0.55), 1.2),
    10: lambda d: (
        draw_ship(d, W//2, int(H*0.55), 1.2, "pirate"),
        draw_ship(d, int(W*0.15), int(H*0.6), 0.6, "merchant"),
        draw_ship(d, int(W*0.85), int(H*0.55), 1.0, "navy"),
    ),
    11: lambda d: draw_gallows(d, W//2, int(H*0.5), 1.0),
    12: lambda d: draw_sunrise_pirate(d, W//2, int(H*0.65), 1.0),
}

# ─── Scene builder ─────────────────────────────────────────────

def build_scene_bg(scene_num: int) -> np.ndarray:
    """Build the hand-drawn background for a scene."""
    img = Image.new("RGB", (W, H), (252, 250, 245))
    draw = ImageDraw.Draw(img, "RGBA" if hasattr(ImageDraw, 'Draw') else "RGB")
    draw = ImageDraw.Draw(img)
    _paper_bg(draw, W, H)
    if scene_num in SCENE_BUILDERS:
        SCENE_BUILDERS[scene_num](draw)
    if scene_num == 1:
        tf = _get_font(40)
        draw.text((W//2-100, 30), "THE PIRATE MYTH", font=tf, fill=(40,35,30))
    elif scene_num == 2:
        tf = _get_font(36)
        draw.text((W//2-90, H-60), "But almost none of it was true", font=tf, fill=(180,30,30))
    elif scene_num == 12:
        tf = _get_font(48)
        draw.text((W//2-180, int(H*0.85)), "Freedom came at a price", font=tf, fill=(40,35,30))
    img = img.filter(ImageFilter.SMOOTH)
    return np.array(img)

# ─── Video builder ─────────────────────────────────────────────

def build_video(scenes: list, output_path: str):
    print(f"\n{'='*55}")
    print(f"  ANIMATED STORYBOARD — {len(scenes)} scenes")
    print(f"{'='*55}")

    temp_dir = config.TEMP_DIR / "storyboard_anim"
    temp_dir.mkdir(exist_ok=True)

    # Step 1: Build scene images
    print(f"\n[1/4] Drawing {len(scenes)} hand-drawn scenes...")
    scene_images = []
    for i, scene in enumerate(scenes):
        print(f"  Scene {i+1}: {scene.get('title', '')[:40]}")
        scene_images.append(build_scene_bg(scene.get("num", i+1)))

    # Step 2: TTS
    print(f"\n[2/4] Generating narration...")
    full_script = " ".join(s["narration"] for s in scenes)
    tts_path = temp_dir / "narration.mp3"
    words = generate_tts_with_timestamps(full_script, tts_path)
    total_dur = words[-1]["end"] if words else 5.0
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

    # Step 4: Render
    print(f"\n[4/4] Rendering video...")
    TITLE, END_DUR = 2.0, 2.0
    video_dur = total_dur + TITLE + END_DUR
    bg_blank = np.full((H, W, 3), 248, dtype=np.uint8)

    # Title card
    title_img = Image.new("RGB", (W, H), (252, 250, 245))
    tdraw = ImageDraw.Draw(title_img)
    tf = _get_font(52)
    lines = ["How Pirates", "Really Lived"]
    y = H//2 - 80
    for line in lines:
        tb = tdraw.textbbox((0, 0), line, font=tf)
        tdraw.text(((W-(tb[2]-tb[0]))//2, y), line, font=tf, fill=(40,35,30))
        y += 75
    sf = _get_font(26)
    sub = "A Hand-Drawn Story"
    tb = tdraw.textbbox((0, 0), sub, font=sf)
    tdraw.text(((W-(tb[2]-tb[0]))//2, H-180), sub, font=sf, fill=(140,130,120))
    title_arr = np.array(title_img)

    def make_frame(t):
        if t < TITLE:
            p = t/TITLE
            a = int(255 * (p*p*(3-2*p)))
            if a < 255:
                return ((bg_blank.astype(np.float32)*(255-a)+title_arr.astype(np.float32)*a)/255).astype(np.uint8)
            return title_arr
        t_rel = t - TITLE
        if t_rel > total_dur:
            return bg_blank
        active = None
        for i, s in enumerate(timeline):
            if s["start"] <= t_rel < s["end"]:
                active, active_idx = s, i; break
        if active is None:
            for i, s in reversed(list(enumerate(timeline))):
                if t_rel >= s["end"]: active, active_idx = s, i; break
        if active is None: return bg_blank
        base = active["image"].copy()
        curr_w = -1
        for wi in range(active["word_start"], min(active["word_end"]+1, len(words))):
            if words[wi]["start"] <= t_rel: curr_w = wi
            else: break
        # Caption bar
        cap = Image.fromarray(base)
        cdraw = ImageDraw.Draw(cap)
        bar_h = 110
        cap_overlay = Image.new("RGBA", (W, bar_h), (0,0,0,180))
        cap.paste(cap_overlay, (0, H-bar_h-15), cap_overlay)
        font, hl_font = _get_font(34), _get_font(38)
        words_to_show = [words[wi]["text"] for wi in range(active["word_start"], min(active["word_end"]+1, len(words)))]
        x, y, lh = 25, H-bar_h+20, 48
        for i, w in enumerate(words_to_show):
            wi = active["word_start"] + i
            f = hl_font if wi == curr_w else font
            c = (255,220,80) if wi == curr_w else (255,255,255)
            dw = " " + w + " "
            bb = cdraw.textbbox((0,0), dw, font=f)
            ww = bb[2]-bb[0]
            if x + ww > W-25: x, lh = 25, lh+48
            if wi == curr_w:
                cdraw.rounded_rectangle([x-5, lh-3, x+ww+5, lh+44], radius=5, fill=(200,80,60,180))
            cdraw.text((x, lh), dw, font=f, fill=c)
            x += ww
        return np.array(cap)

    clip = VideoClip(make_frame, duration=video_dur)
    audio = AudioFileClip(str(tts_path))
    if video_dur > audio.duration + TITLE:
        silence = AudioFileClip(str(tts_path)).with_duration(video_dur-audio.duration-TITLE).with_volume_scaled(0)
        audio = concatenate_audioclips([audio, silence])
    music_paths = list(config.MUSIC_DIR.glob("*.mp3"))
    if music_paths:
        music = AudioFileClip(str(random.choice(music_paths))).with_duration(video_dur).with_volume_scaled(0.04)
        audio = CompositeAudioClip([audio, music])
    end_card = subscribe_end_card(np.full((H,W,3), 240, dtype=np.uint8), END_DUR).with_start(total_dur+TITLE)
    final = CompositeVideoClip([clip, end_card], size=config.SHORTS_SIZE).with_audio(audio)
    t0 = time.time()
    final.write_videofile(str(output_path), fps=FPS, codec="libx264", audio_codec="aac",
                          threads=4, preset="medium", ffmpeg_params=["-movflags", "+faststart", "-crf", "18"], logger=None)
    final.close()
    print(f"\n  Done in {time.time()-t0:.0f}s: {output_path} ({os.path.getsize(output_path):,} bytes)")

def main():
    scenes = [
        {"num": 1, "title": "The Pirate Myth", "narration": "Picture a pirate. A ragged man with a wooden leg, a parrot on his shoulder, and a chest overflowing with gold."},
        {"num": 2, "title": "Myth Shattered", "narration": "But almost none of it was true."},
        {"num": 3, "title": "Ordinary Sailor", "narration": "Imagine it is 1715. You work on a merchant ship. The captain beats crew members for small mistakes."},
        {"num": 4, "title": "Miserable Conditions", "narration": "The food was rotten. Your pay is delayed. Many sailors die from disease before seeing home again."},
        {"num": 5, "title": "Pirate Ship Appears", "narration": "Then one day a pirate ship appears on the horizon."},
        {"num": 6, "title": "A Choice", "narration": "The pirates offer you a choice. Join them. For many sailors becoming a pirate was about escaping a worse life."},
        {"num": 7, "title": "Pirate Democracy", "narration": "Pirate ships were surprisingly democratic. Crew members could vote. If a captain was cruel they could remove him."},
        {"num": 8, "title": "Boring Days at Sea", "narration": "Most pirate days were boring. Weeks pass without spotting a target. The sun burns relentlessly."},
        {"num": 9, "title": "Reality of Treasure", "narration": "Most pirate loot was not gold. Sugar. Tobacco. Cloth. Spices. Anything valuable enough to sell."},
        {"num": 10, "title": "Constant Danger", "narration": "Every sail on the horizon could be an opportunity. Or the beginning of your execution."},
        {"num": 11, "title": "Capture", "narration": "Captured pirates faced brutal punishment. Many were hanged in public. Their bodies displayed near harbors as warnings."},
        {"num": 12, "title": "Ending", "narration": "Piracy offered something precious. A chance to choose your own fate. Freedom came at a price."},
    ]
    out = config.OUTPUT_DIR / "how_pirates_really_lived.mp4"
    build_video(scenes, out)

if __name__ == "__main__":
    main()
