"""Prompt-to-hand-drawn-sketch pipeline.
LLM interprets your prompt -> structured scene -> rendered with cross-hatch/wobble style."""

import math, random, json, re, os, sys
from PIL import Image, ImageDraw, ImageFilter
import numpy as np

W, H = 720, 1280
rng = random.Random()

# ─── Drawing primitives ────────────────────────────────────────

def _stroke(draw, points, w=2, color=(0,0,0), amp=1.2):
    if len(points) < 2: return
    for i in range(len(points)-1):
        steps = max(int(math.hypot(points[i+1][0]-points[i][0], points[i+1][1]-points[i][1])/2), 3)
        for s in range(steps):
            t = s/steps
            px = points[i][0] + (points[i+1][0]-points[i][0])*t + rng.gauss(0, amp*0.4)
            py = points[i][1] + (points[i+1][1]-points[i][1])*t + rng.gauss(0, amp*0.4)
            rw = w * (0.85 + rng.random()*0.3)
            draw.ellipse([px-rw/2, py-rw/2, px+rw/2, py+rw/2], fill=color)

def _fill(draw, pts, color, amp=2):
    if len(pts) < 3: return
    draw.polygon([(x+rng.gauss(0,amp), y+rng.gauss(0,amp)) for x,y in pts], fill=color)

def _hatch(draw, poly, spacing=7, color=(0,0,0,35)):
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    if not xs: return
    mnx, mxx, mny, mxy = min(xs), max(xs), min(ys), max(ys)
    diag = math.hypot(mxx-mnx, mxy-mny)
    for a in [45, -45]:
        for i in range(int(diag/spacing)+10):
            rad = math.radians(a)
            cx = mnx + math.cos(rad)*i*spacing
            cy = mny + math.sin(rad)*i*spacing
            dx = math.cos(rad+math.pi/2)*diag
            dy = math.sin(rad+math.pi/2)*diag
            _stroke(draw, [(cx,cy), (cx+dx,cy+dy)], w=1, color=color, amp=0.3)

def _scribble(draw, cx, cy, radius, density=25, color=(0,0,0,50)):
    for _ in range(density):
        a = rng.random()*math.pi*2
        d = rng.random()*radius
        x1 = cx + math.cos(a)*d
        y1 = cy + math.sin(a)*d
        x2 = x1 + math.cos(a+math.pi/4)*rng.uniform(2,6)
        y2 = y1 + math.sin(a+math.pi/4)*rng.uniform(2,6)
        draw.line([(x1,y1),(x2,y2)], fill=color, width=1)

def _circle(draw, cx, cy, r, fill_c=None, line_c=(0,0,0), w=2):
    pts = []
    for a in range(0, 361, 10):
        pts.append((cx+math.cos(math.radians(a))*r+rng.gauss(0,0.5), cy+math.sin(math.radians(a))*r+rng.gauss(0,0.5)))
    if fill_c:
        _fill(draw, pts, fill_c, amp=1)
    _stroke(draw, pts, w=w, color=line_c, amp=0.8)

def _rect(draw, x, y, w, h, fill_c=None, line_c=(0,0,0), lw=2):
    pts = [(x+rng.gauss(0,1), y+rng.gauss(0,1)), (x+w+rng.gauss(0,1), y+rng.gauss(0,1)),
           (x+w+rng.gauss(0,1), y+h+rng.gauss(0,1)), (x+rng.gauss(0,1), y+h+rng.gauss(0,1))]
    if fill_c:
        _fill(draw, pts, fill_c, amp=1)
    _stroke(draw, pts + [pts[0]], w=lw, color=line_c, amp=0.8)

# ─── Object renderers ──────────────────────────────────────────

def draw_sun(draw, cx, cy, s, color=(255,200,50)):
    r = 30*s
    _circle(draw, cx, cy, r, fill_c=(*color,100), line_c=color)
    for a in range(0, 360, 30):
        rad = math.radians(a)
        _stroke(draw, [(cx+math.cos(rad)*r, cy+math.sin(rad)*r),
                       (cx+math.cos(rad)*r*1.5, cy+math.sin(rad)*r*1.5)], w=2, color=color, amp=0.5)

def draw_moon(draw, cx, cy, s, color=(220,215,190)):
    r = 25*s
    _circle(draw, cx, cy, r, fill_c=(240,235,210,80), line_c=color)
    _circle(draw, cx+5*s, cy-3*s, r*0.85, fill_c=(20,15,40,120))

def draw_tree(draw, cx, cy, s, color=(50,80,40)):
    # trunk
    tw, th = 6*s, 40*s
    trunk = [(cx-tw, cy), (cx-tw, cy-th), (cx+tw, cy-th), (cx+tw, cy)]
    _fill(draw, trunk, (60,45,30,180), amp=1.5)
    _stroke(draw, trunk, w=2.5, color=(50,35,25), amp=1)
    # crown
    cr = 25*s
    for i in range(rng.randint(3,5)):
        ox, oy = rng.randint(-10,10)*s, rng.randint(-8,5)*s
        rr = cr * (0.6+rng.random()*0.4)
        _circle(draw, cx+ox, cy-th+oy, rr, fill_c=(*color,80), line_c=(*[c-10 for c in color],200))
        _hatch(draw, [(cx+ox-rr, cy-th+oy-rr), (cx+ox+rr, cy-th+oy-rr), (cx+ox+rr, cy-th+oy+rr), (cx+ox-rr, cy-th+oy+rr)], spacing=5, color=(0,30,0,20))

def draw_mountain(draw, cx, cy, s):
    mw, mh = int(120*s), int(80*s)
    pts = [(cx-mw, cy), (cx, cy-mh), (cx+mw, cy)]
    c = (rng.randint(80,120), rng.randint(90,130), rng.randint(130,160))
    _fill(draw, pts, (*c,100), amp=2)
    _stroke(draw, pts, w=2, color=(60,60,80,150), amp=1.5)
    _hatch(draw, pts, spacing=8, color=(40,40,60,20))

def draw_cloud(draw, cx, cy, s, color=(250,250,250)):
    for i in range(rng.randint(3,5)):
        ox, oy = rng.randint(-15,15)*s, rng.randint(-8,5)*s
        r = rng.randint(15,30)*s
        _circle(draw, cx+ox, cy+oy*0.5, r, fill_c=(*color, rng.randint(60,100)), line_c=(200,200,200,100))

def draw_water(draw, x, y, w, h, color=(30,80,150)):
    for i in range(rng.randint(8,20)):
        wx = rng.randint(int(x), int(x+w))
        wy = rng.randint(int(y), int(y+h))
        wl = rng.randint(10,30)
        _stroke(draw, [(wx,wy), (wx+wl,wy-rng.randint(-3,3))], w=1, color=(*color, 100), amp=0.5)

def draw_grass_blade(draw, gx, gy, gh, color=(50,80,40)):
    _stroke(draw, [(gx, gy), (gx+rng.randint(-2,2), gy-gh)], w=1.5, color=color, amp=0.5)

def draw_flower(draw, cx, cy, s, color=None):
    c = color or (rng.randint(150,255), rng.randint(50,200), rng.randint(100,255))
    _stroke(draw, [(cx, cy), (cx, cy-10*s)], w=1.5, color=(40,100,40), amp=0.3)
    for a in range(0, 360, 45):
        rad = math.radians(a)
        _circle(draw, cx+math.cos(rad)*4, cy-10*s+math.sin(rad)*4, 3, fill_c=(*c,100), line_c=c)

def draw_bird(draw, cx, cy, s):
    _stroke(draw, [(cx-10*s, cy), (cx, cy-8*s), (cx+10*s, cy)], w=2, color=(40,35,30), amp=0.5)

def draw_house(draw, cx, cy, s):
    hw, hh = 40*s, 30*s
    wall_c = (rng.randint(180,210), rng.randint(160,190), rng.randint(140,170))
    _rect(draw, cx-hw, cy-hh, hw*2, hh, fill_c=(*wall_c,120), line_c=(50,40,30))
    _hatch(draw, [(cx-hw, cy-hh), (cx+hw, cy-hh), (cx+hw, cy), (cx-hw, cy)], spacing=8, color=(0,0,0,15))
    # roof
    _fill(draw, [(cx-hw-5, cy-hh), (cx, cy-hh-25*s), (cx+hw+5, cy-hh)], (150,50,40,100), amp=1.5)
    _stroke(draw, [(cx-hw-5, cy-hh), (cx, cy-hh-25*s), (cx+hw+5, cy-hh)], w=2.5, color=(100,30,20), amp=1)
    # door
    _rect(draw, cx-8*s, cy-15*s, 16*s, 15*s, fill_c=(255,220,150,80), line_c=(40,35,25))

def draw_fence(draw, x, y, w, h, s=1.0):
    posts = 5
    for i in range(posts):
        px = x + i * (w / (posts-1))
        _stroke(draw, [(px, y), (px, y-h)], w=2.5, color=(70,55,35), amp=0.8)
    _stroke(draw, [(x, y-h*0.4), (x+w, y-h*0.4)], w=2, color=(70,55,35), amp=0.5)
    _stroke(draw, [(x, y-h*0.7), (x+w, y-h*0.7)], w=2, color=(70,55,35), amp=0.5)

def draw_wave(draw, cx, cy, s, color=(40, 100, 180)):
    """Hand-drawn curling wave with foam."""
    for layer in range(3):
        pts = []
        for i in range(12):
            t = i / 11
            px = cx - 60*s + t * 120*s
            py = cy - math.sin(t * 6.28 * 1.5 + layer) * 15*s - layer * 8*s
            pts.append((px, py))
        _stroke(draw, pts, w=3-layer, color=(*[c-20*layer for c in color], 180-layer*30), amp=1.5)
    # Foam dots
    for _ in range(10):
        fx = cx + rng.randint(-40, 40)*s
        fy = cy - 25*s + rng.randint(-5, 5)*s
        _circle(draw, fx, fy, rng.randint(3, 6)*s, fill_c=(240, 245, 250, rng.randint(100, 200)), line_c=None)
    # Spray
    for _ in range(8):
        sx = cx + rng.randint(-30, 30)*s
        sy = cy - 35*s - rng.randint(0, 10)*s
        _circle(draw, sx, sy, rng.randint(1, 3), fill_c=(255, 255, 255, rng.randint(80, 150)), line_c=None)

def draw_canoe(draw, cx, cy, s, color=(80, 55, 35)):
    """Primitive dugout canoe with paddlers."""
    hull = [(cx-50*s, cy), (cx-40*s, cy-12*s), (cx, cy-15*s), (cx+40*s, cy-12*s), (cx+50*s, cy)]
    _fill(draw, hull, (*color, 150), amp=1.5)
    _stroke(draw, hull+[hull[0]], w=3, color=(*[c-15 for c in color], 200), amp=1.2)
    # Hollow
    inner = [(cx-42*s, cy-2*s), (cx-35*s, cy-10*s), (cx, cy-12*s), (cx+35*s, cy-10*s), (cx+42*s, cy-2*s)]
    _fill(draw, inner, color, amp=1)
    # Paddler 1
    draw_human(draw, cx-18*s, cy-18*s, s*0.4, shirt=(60, 50, 80))
    # Paddle
    _stroke(draw, [(cx-25*s, cy-22*s), (cx-40*s, cy+5*s)], w=2.5, color=(160, 130, 80), amp=1)
    _fill(draw, [(cx-42*s, cy+3*s), (cx-38*s, cy+8*s), (cx-40*s, cy+8*s)], (160, 130, 80, 180), amp=1)
    # Paddler 2
    draw_human(draw, cx+22*s, cy-18*s, s*0.4, shirt=(70, 60, 50))
    _stroke(draw, [(cx+30*s, cy-22*s), (cx+45*s, cy+5*s)], w=2.5, color=(160, 130, 80), amp=1)
    _fill(draw, [(cx+43*s, cy+3*s), (cx+47*s, cy+8*s), (cx+45*s, cy+8*s)], (160, 130, 80, 180), amp=1)

def draw_whale(draw, cx, cy, s, color=(60, 70, 100)):
    """Hand-drawn whale breaching."""
    body = [(cx-45*s, cy-5*s), (cx-30*s, cy-22*s), (cx, cy-28*s), (cx+30*s, cy-22*s), (cx+40*s, cy-5*s)]
    _fill(draw, body, (*color, 180), amp=2)
    _stroke(draw, body+[body[0]], w=2.5, color=(*[c-15 for c in color], 200), amp=1.5)
    # Tail
    _stroke(draw, [(cx-42*s, cy-5*s), (cx-55*s, cy-20*s), (cx-50*s, cy-8*s)], w=2.5, color=color, amp=1.5)
    _stroke(draw, [(cx-42*s, cy-5*s), (cx-55*s, cy+10*s), (cx-50*s, cy-2*s)], w=2.5, color=color, amp=1.5)
    # Eye
    _circle(draw, cx+25*s, cy-15*s, 2, fill_c=(20, 25, 30), line_c=None)
    # Spray
    for _ in range(5):
        _circle(draw, cx+5*s+rng.randint(-3,3)*s, cy-32*s-rng.randint(0,6)*s, rng.randint(2,4), fill_c=(200, 230, 250, rng.randint(80, 160)), line_c=None)

def draw_shark(draw, cx, cy, s, color=(80, 85, 95)):
    """Hand-drawn shark fin."""
    fin = [(cx-10*s, cy+5*s), (cx, cy-25*s), (cx+10*s, cy+5*s)]
    _fill(draw, fin, (*color, 200), amp=1.5)
    _stroke(draw, fin+[fin[0]], w=2, color=(*[c-20 for c in color], 200), amp=1)
    # Water ripples
    for i in range(3):
        rx = cx + rng.randint(-15, 15)*s
        ry = cy + 3*s + i*4*s
        _stroke(draw, [(rx-10*s, ry), (rx+10*s, ry)], w=1, color=(100, 150, 200, 80), amp=0.5)

def draw_sea_serpent(draw, cx, cy, s, color=(40, 100, 60)):
    """Hand-drawn sea serpent — coils and head."""
    for i in range(3):
        coil_cx = cx + i*6*s
        coil_cy = cy - i*15*s
        _circle(draw, coil_cx, coil_cy, 12*s-i*2*s, fill_c=(*color, 150-i*30), line_c=(*[c-10 for c in color], 200-i*30))
    # Neck
    _stroke(draw, [(cx+5*s, cy-45*s), (cx+8*s, cy-60*s), (cx+15*s, cy-70*s)], w=5, color=(*color, 200), amp=1.5)
    # Head
    head_cx, head_cy = cx+15*s, cy-70*s
    _circle(draw, head_cx, head_cy, 10*s, fill_c=(*color, 200), line_c=(*[c-10 for c in color], 200))
    # Eyes
    _circle(draw, head_cx+5*s, head_cy-3*s, 2, fill_c=(255, 200, 50), line_c=None)
    # Tongue
    _stroke(draw, [(head_cx+8*s, head_cy+2*s), (head_cx+18*s, head_cy-2*s)], w=1.5, color=(200, 80, 60), amp=0.5)
    _stroke(draw, [(head_cx+8*s, head_cy+2*s), (head_cx+18*s, head_cy+6*s)], w=1.5, color=(200, 80, 60), amp=0.5)

def draw_totem(draw, cx, cy, s, color=(120, 105, 85)):
    """Hand-drawn standing stone / monolith."""
    pw = 15*s
    ph = 70*s
    pillar = [(cx-pw, cy), (cx-pw, cy-ph), (cx+pw, cy-ph), (cx+pw, cy)]
    _fill(draw, pillar, (*color, 180), amp=2)
    _stroke(draw, pillar+[pillar[0]], w=3, color=(*[c-20 for c in color], 200), amp=1.5)
    # Carvings
    for i in range(3):
        cy_carv = cy-ph+15*s+i*18*s
        _stroke(draw, [(cx-pw+4*s, cy_carv), (cx+pw-4*s, cy_carv)], w=1.5, color=(*[c-30 for c in color], 100), amp=0.5)
        _circle(draw, cx, cy_carv-4*s, 3*s, fill_c=None, line_c=(*[c-30 for c in color], 80))

def draw_anchor(draw, cx, cy, s, color=(80, 75, 70)):
    """Hand-drawn nautical anchor."""
    _stroke(draw, [(cx, cy-30*s), (cx, cy+20*s)], w=4, color=(*color, 200), amp=0.8)
    _stroke(draw, [(cx-12*s, cy-22*s), (cx+12*s, cy-22*s)], w=3, color=(*color, 200), amp=0.8)
    _circle(draw, cx, cy-34*s, 4*s, fill_c=None, line_c=(*color, 200))
    # Curved arms
    pts = []
    for a in range(30, 150, 10):
        rad = math.radians(a)
        pts.append((cx+math.cos(rad)*18*s, cy+18*s-math.sin(rad)*8*s))
    _stroke(draw, pts, w=3, color=(*color, 200), amp=1)
    # Flukes
    _fill(draw, [(pts[-1][0], pts[-1][1]), (pts[-1][0]+5*s, pts[-1][1]-5*s), (pts[-1][0]+5*s, pts[-1][1]+5*s)], (*color, 200), amp=1)
    _fill(draw, [(pts[0][0], pts[0][1]), (pts[0][0]-5*s, pts[0][1]-5*s), (pts[0][0]-5*s, pts[0][1]+5*s)], (*color, 200), amp=1)

def draw_cliff(draw, cx, cy, s, color=(100, 80, 60)):
    c = color
    w, h = int(100*s), int(150*s)
    pts = [(cx, cy)]
    for i in range(9):
        t = i / 8
        pts.append((cx + w*t + rng.randint(-6,6)*s, cy - h*(1-t*0.9) + rng.randint(-8,8)*s*(1-t)))
    pts.append((cx+w, cy))
    _fill(draw, pts, (*c, 200), amp=2)
    _stroke(draw, pts+[pts[0]], w=2.5, color=(*[v-20 for v in c],200), amp=1.5)
    for _ in range(4):
        _stroke(draw, [(cx+rng.randint(10,w-10)*s, cy-h+rng.randint(20,h-20)*s),
                        (cx+rng.randint(10,w-10)*s, cy-h+rng.randint(40,h-10)*s)],
                w=1.5, color=(*[v-30 for v in c],100), amp=1)
    for _ in range(5):
        _circle(draw, cx+rng.randint(5,w-5)*s, int(cy-h+rng.randint(-2,5)*s),
                rng.randint(3,7)*s, fill_c=(240,245,250,rng.randint(80,150)), line_c=None)

def draw_compass_rose(draw, cx, cy, s, color=(180, 160, 120)):
    c = color
    r = int(28*s)
    _circle(draw, cx, cy, r, fill_c=None, line_c=(*c,200))
    _circle(draw, cx, cy, int(24*s), fill_c=None, line_c=(*c,100))
    for dx, dy, label, lc in [(0,-1,"N",(200,60,60)),(0,1,"S",c),(1,0,"E",c),(-1,0,"W",c)]:
        tip = (int(cx+dx*r), int(cy+dy*r))
        b1 = (int(cx+dx*6*s-dy*6*s), int(cy+dy*6*s+dx*6*s))
        b2 = (int(cx+dx*6*s+dy*6*s), int(cy+dy*6*s-dx*6*s))
        _fill(draw, [tip, b1, b2], (*lc,200), amp=1)
        _stroke(draw, [tip, b1, b2, tip], w=1.5, color=(*[v-20 for v in lc],200), amp=1)
    for dx, dy in [(0.707,-0.707),(0.707,0.707),(-0.707,-0.707),(-0.707,0.707)]:
        tip = (int(cx+dx*r), int(cy+dy*r))
        b1 = (int(cx+dx*4*s-dy*4*s), int(cy+dy*4*s+dx*4*s))
        b2 = (int(cx+dx*4*s+dy*4*s), int(cy+dy*4*s-dx*4*s))
        _fill(draw, [tip, b1, b2], (*[v+30 for v in c],160), amp=1)
    _circle(draw, cx, cy, 3, fill_c=(*c,220), line_c=None)

def draw_shadow_figure(draw, cx, cy, s, color=(20, 25, 30)):
    c = color
    hr = int(7*s)
    _circle(draw, cx, int(cy-38*s), hr, fill_c=(*c,200), line_c=None)
    body = [(cx-10*s, cy-30*s), (cx+10*s, cy-30*s), (cx+12*s, cy), (cx-12*s, cy)]
    _fill(draw, body, (*c,200), amp=1)
    arm1 = [(cx-8*s, cy-24*s), (cx-24*s, cy-28*s), (cx-28*s, cy-24*s)]
    _fill(draw, arm1, (*c,200), amp=1)
    arm2 = [(cx+8*s, cy-24*s), (cx+24*s, cy-28*s), (cx+28*s, cy-24*s)]
    _fill(draw, arm2, (*c,200), amp=1)
    leg1 = [(cx-5*s, cy), (cx+2*s, cy), (cx+3*s, cy+18*s), (cx-6*s, cy+18*s)]
    _fill(draw, leg1, (*c,200), amp=1)
    leg2 = [(cx-1*s, cy), (cx+5*s, cy), (cx+6*s, cy+18*s), (cx-3*s, cy+18*s)]
    _fill(draw, leg2, (*c,200), amp=1)
    _fill(draw, [(cx+11*s, cy-26*s), (cx+12*s, cy-18*s), (cx+11*s, cy)], (255,220,150,30), amp=0)

def draw_moon_path(draw, cx, cy, s, color=(200, 210, 230)):
    c = color
    for col in range(5):
        cx2 = cx - 15*s + col * 7*s
        for row in range(8):
            ry = cy + row * 10*s
            rw = rng.randint(3, 6) * s
            _circle(draw, int(cx2), int(ry), max(int(rw//2), 1), fill_c=(*[v+10 for v in c], rng.randint(60, 140)), line_c=None)

def draw_road(draw, x, y, w, h):
    for i in range(int(h)):
        t = i/h
        c = int(120 + t*40)
        draw.line([(x, y+i), (x+w, y+i)], fill=(c, c-5, c-10))
    # dashes
    for i in range(0, int(h), 15):
        _stroke(draw, [(x+w/2, y+i), (x+w/2, y+min(i+8, int(h)))], w=2, color=(220,215,200,150), amp=0.3)

def draw_fire(draw, cx, cy, s):
    for i in range(rng.randint(4,7)):
        ox = rng.randint(-8,8)*s
        fh = rng.randint(20,35)*s
        fw = rng.randint(8,15)*s
        c = (rng.randint(200,255), rng.randint(50,150), 0)
        _fill(draw, [(cx+ox-fw, cy), (cx+ox, cy-fh), (cx+ox+fw, cy)], (*c, 80), amp=2)
        _stroke(draw, [(cx+ox-fw, cy), (cx+ox, cy-fh), (cx+ox+fw, cy)], w=2, color=c, amp=1)

# ─── Human / figure ────────────────────────────────────────────

def draw_human(draw, cx, cy, s, color=(30,25,20), skin=(235,200,175), shirt=(55,65,145), pants=(55,45,70)):
    head_r = 12*s
    # Head
    pts = [(cx+math.cos(math.radians(a))*head_r, cy+math.sin(math.radians(a))*head_r) for a in range(0, 360, 20)]
    _fill(draw, pts, (*skin, 200), amp=1)
    _stroke(draw, pts, w=2, color=(180,150,130), amp=0.8)
    # Face
    draw.ellipse([cx-2.5, cy-2, cx-0.5, cy], fill=(30,25,20))
    draw.ellipse([cx+0.5, cy-2, cx+2.5, cy], fill=(30,25,20))
    _stroke(draw, [(cx, cy+2), (cx, cy+4.5)], w=1.5, color=(180,140,120), amp=0.3)
    _stroke(draw, [(cx-3, cy+6), (cx, cy+7), (cx+3, cy+6)], w=1.5, color=(160,120,100), amp=0.3)
    # Hair
    for i in range(12):
        a = rng.uniform(-math.pi*0.8, math.pi*0.8)
        d = rng.uniform(head_r*0.5, head_r*1.3)
        _stroke(draw, [(cx+math.cos(a)*head_r*0.5, cy+math.sin(a)*head_r*0.5),
                        (cx+math.cos(a)*d, cy+math.sin(a)*d)], w=rng.uniform(1.5,2.5), color=(35,30,25), amp=1)
    # Body
    body = [(cx-14*s, cy+head_r+2*s), (cx-12*s, cy+head_r-38*s), (cx+12*s, cy+head_r-38*s), (cx+14*s, cy+head_r+2*s)]
    _fill(draw, body, (*shirt,200), amp=1.5)
    _hatch(draw, body, spacing=6, color=(0,0,30,20))
    _stroke(draw, body, w=2.5, color=shirt, amp=1.2)
    # Arms
    for side in [-1,1]:
        arm = [(cx+side*12*s, cy+head_r-32*s), (cx+side*22*s, cy+head_r-20*s), (cx+side*18*s, cy+head_r-5*s)]
        _fill(draw, arm, (*shirt,180), amp=1.5)
        _stroke(draw, arm, w=3, color=shirt, amp=1.2)
    # Legs
    for side in [-1,1]:
        leg = [(cx+side*8*s, cy+head_r+2*s), (cx+side*14*s, cy+head_r+22*s)]
        _stroke(draw, leg, w=3.5, color=pants, amp=1.5)

# ─── Animal renderers ──────────────────────────────────────────

def draw_horse(draw, cx, cy, s, color=(40,35,30)):
    hp = color
    body = [(cx-80*s, cy-30*s), (cx-45*s, cy-55*s), (cx-10*s, cy-62*s),
            (cx+25*s, cy-60*s), (cx+55*s, cy-52*s), (cx+75*s, cy-40*s),
            (cx+80*s, cy-28*s), (cx+70*s, cy-18*s), (cx+40*s, cy-12*s),
            (cx-15*s, cy-12*s), (cx-55*s, cy-15*s), (cx-80*s, cy-22*s)]
    _fill(draw, body, (*hp,180), amp=2.5)
    _hatch(draw, body, spacing=8, color=(0,0,0,25))
    _stroke(draw, body+[body[0]], w=3, color=hp, amp=1.5)
    # Neck
    neck = [(cx+55*s, cy-52*s), (cx+65*s, cy-68*s), (cx+72*s, cy-82*s),
            (cx+68*s, cy-90*s), (cx+58*s, cy-88*s), (cx+52*s, cy-75*s), (cx+42*s, cy-58*s)]
    _fill(draw, neck, (*hp,200), amp=2)
    _hatch(draw, neck, spacing=7, color=(0,0,0,20))
    _stroke(draw, neck+[neck[0]], w=3, color=hp, amp=1.5)
    # Head
    head = [(cx+72*s, cy-90*s), (cx+80*s, cy-94*s), (cx+90*s, cy-91*s),
            (cx+98*s, cy-88*s), (cx+102*s, cy-84*s), (cx+98*s, cy-80*s),
            (cx+90*s, cy-78*s), (cx+80*s, cy-78*s), (cx+72*s, cy-82*s)]
    _fill(draw, head, (*[c+5 for c in hp],220), amp=1.5)
    _hatch(draw, head, spacing=6, color=(0,0,0,30))
    _stroke(draw, head, w=3, color=hp, amp=1.2)
    # Eye / nostril
    draw.ellipse([cx+88*s-3, cy-86*s-2, cx+88*s+3, cy-86*s+2], fill=(20,15,10))
    draw.ellipse([cx+98*s-2, cy-82*s-1, cx+98*s+2, cy-82*s+1], fill=(50,40,30))
    # Mane
    for i in range(15):
        mx = cx+48*s+i*2.5*s
        my = cy-50*s-i*2*s
        _stroke(draw, [(mx, my), (mx+rng.randint(-8,-2), my-rng.randint(12,25))], w=rng.uniform(1.5,2.5), color=(30,25,20), amp=1.5)
    # Tail
    for i in range(10):
        tx = cx-80*s+rng.randint(-3,3)
        ty = cy-20*s+i*2*s
        _stroke(draw, [(tx, ty), (tx+rng.randint(-25,-8), ty+rng.randint(5,30))], w=rng.uniform(1.5,2.5), color=(35,30,25), amp=2)
    # Legs
    leg_c = (45,38,32)
    for side, off in [(-1,-8),(1,8)]:
        lx = cx+55*s+off
        ly = cy-25*s
        leg = [(lx, ly), (lx+side*3*s, ly+15*s), (lx+side*s, ly+35*s),
               (lx-side*2*s, ly+50*s), (lx-side*4*s, ly+58*s)]
        _fill(draw, leg+[leg[0]], (*leg_c,180), amp=2)
        _stroke(draw, leg, w=3, color=leg_c, amp=1.5)
        _scribble(draw, lx, ly+30*s, 12*s, 12, (0,0,0,20))
    for side, off in [(-1,-3),(1,3)]:
        lx = cx-50*s+off
        ly = cy-22*s
        leg = [(lx, ly), (lx-side*5*s, ly+20*s), (lx-side*2*s, ly+40*s),
               (lx-side*4*s, ly+50*s), (lx-side*5*s, ly+58*s)]
        _fill(draw, leg+[leg[0]], (*leg_c,180), amp=2)
        _stroke(draw, leg, w=3, color=leg_c, amp=1.5)
        _scribble(draw, lx, ly+30*s, 10*s, 10, (0,0,0,20))

def draw_dog(draw, cx, cy, s, color=(150,100,50)):
    body = [(cx-30*s, cy-12*s), (cx-30*s, cy+2*s), (cx+30*s, cy+2*s), (cx+30*s, cy-12*s)]
    _fill(draw, body, (*color,180), amp=2)
    _stroke(draw, body+[body[0]], w=2.5, color=color, amp=1.5)
    hr = 10*s
    hx, hy = cx+35*s, cy-12*s
    pts = [(hx+math.cos(math.radians(a))*hr, hy+math.sin(math.radians(a))*hr) for a in range(0,360,20)]
    _fill(draw, pts, (*[c+30 for c in color],200), amp=1)
    _stroke(draw, pts, w=2, color=color, amp=0.8)
    draw.ellipse([hx-2, hy-1, hx+2, hy+1], fill=(20,15,10))

def draw_cat(draw, cx, cy, s, color=(180,120,80)):
    body = [(cx-20*s, cy-10*s), (cx-20*s, cy+2*s), (cx+20*s, cy+2*s), (cx+20*s, cy-10*s)]
    _fill(draw, body, (*color,180), amp=2)
    _stroke(draw, body+[body[0]], w=2.5, color=color, amp=1.5)
    hr = 8*s
    hx, hy = cx+24*s, cy-10*s
    pts = [(hx+math.cos(math.radians(a))*hr, hy+math.sin(math.radians(a))*hr) for a in range(0,360,20)]
    _fill(draw, pts, (*[c+30 for c in color],200), amp=1)
    _stroke(draw, pts, w=2, color=color, amp=0.8)
    for ex in [-4, 4]:
        _stroke(draw, [(hx+ex, hy-hr), (hx+ex-2, hy-hr-6*s), (hx+ex+2, hy-hr-4*s)], w=2, color=color, amp=0.8)
    draw.ellipse([hx-2, hy-1, hx+2, hy+1], fill=(20,15,10))
    _stroke(draw, [(hx-3, hy+5), (hx+3, hy+5)], w=1.5, color=(180,140,120), amp=0.3)

# ─── LLM scene parser ──────────────────────────────────────────

OBJECT_RENDERERS = {
    "sun": draw_sun, "moon": draw_moon, "star": lambda d,cx,cy,s: _circle(d, cx, cy, 2, fill_c=(255,255,200,150), line_c=(255,255,200)),
    "tree": draw_tree,     "mountain": lambda d,cx,cy,s: draw_mountain(d, cx, cy, s), "cloud": draw_cloud,
    "water": lambda d,cx,cy,s: draw_water(d, cx-50, cy-50, 100, 100),
    "flower": draw_flower, "grass": lambda d,cx,cy,s: draw_grass_blade(d, cx, cy, 10*s),
    "bird": draw_bird, "house": draw_house, "fence": lambda d,cx,cy,s: draw_fence(d, cx-50, cy, 100, 30*s),
    "fire": draw_fire,
    "human": draw_human, "person": draw_human, "man": draw_human, "woman": draw_human,
    "horse": draw_horse, "dog": draw_dog, "cat": draw_cat,
    "wave": draw_wave, "canoe": draw_canoe, "whale": draw_whale, "shark": draw_shark,
    "sea_serpent": draw_sea_serpent, "seaserpent": draw_sea_serpent,
    "totem": draw_totem, "monolith": draw_totem, "anchor": draw_anchor,
    "cliff": lambda d,cx,cy,s: draw_cliff(d, cx, cy, s),
    "compass_rose": lambda d,cx,cy,s: draw_compass_rose(d, cx, cy, s),
    "shadow_figure": lambda d,cx,cy,s: draw_shadow_figure(d, cx, cy, s),
    "moon_path": lambda d,cx,cy,s: draw_moon_path(d, cx, cy, s),
}

OBJECT_KEYWORDS = {
    "horse": "horse", "riding": "horse",
    "dog": "dog", "puppy": "dog",
    "cat": "cat", "kitty": "cat", "kitten": "cat",
    "tree": "tree", "forest": "tree", "woods": "tree",
    "mountain": "mountain", "hill": "mountain",
    "sun": "sun", "sunrise": "sun", "sunset": "sun",
    "moon": "moon", "night": "moon",
    "star": "star",
    "cloud": "cloud",
    "water": "water", "lake": "water", "river": "water", "ocean": "water", "sea": "water",
    "flower": "flower", "flowers": "flower",
    "bird": "bird",
    "house": "house", "cabin": "house", "cottage": "house",
    "fence": "fence",
    "fire": "fire", "campfire": "fire",
    "human": "human", "person": "human", "man": "human", "woman": "human", "people": "human",
    "riding": "human",
    "wave": "wave", "waves": "wave", "storm": "wave", "surf": "wave",
    "canoe": "canoe", "raft": "canoe", "dugout": "canoe",
    "whale": "whale",
    "shark": "shark",
    "sea_serpent": "sea_serpent", "monster": "sea_serpent", "serpent": "sea_serpent", "leviathan": "sea_serpent",
    "totem": "totem", "monolith": "totem", "standing stone": "totem", "pillar": "totem",
    "anchor": "anchor",
    "cliff": "cliff", "cliffs": "cliff", "bluff": "cliff",
    "compass": "compass_rose", "compass rose": "compass_rose", "wind rose": "compass_rose",
    "shadow": "shadow_figure", "silhouette": "shadow_figure",
    "moonlight": "moon_path", "moon path": "moon_path", "reflection": "moon_path",
}

def _keyword_parse(prompt: str) -> dict:
    p = prompt.lower()
    # Sky
    sky = "day"
    if any(w in p for w in ("night", "moon", "midnight", "dark")): sky = "night"
    elif any(w in p for w in ("sunset", "sunrise", "dusk", "dawn", "evening", "golden")): sky = "sunset"
    # Ground
    ground = "grass"
    if any(w in p for w in ("water", "lake", "river", "ocean", "sea", "beach")): ground = "water"
    elif any(w in p for w in ("snow", "winter", "ice")): ground = "snow"
    elif any(w in p for w in ("desert", "sand", "dune")): ground = "desert"
    elif any(w in p for w in ("road", "path", "trail")): ground = "road"
    # Objects
    found = []
    for word, obj in OBJECT_KEYWORDS.items():
        if word in p and obj not in [f["name"] for f in found]:
            found.append({"name": obj})
    # Position objects
    w_count = len(found)
    objects = []
    for i, obj in enumerate(found):
        ox = 0.2 + 0.6 * (i+1) / (w_count+1) if w_count > 0 else 0.5
        oy = 0.65 + (i % 3) * 0.08
        size = 1.0
        if obj["name"] in ("horse", "dog", "cat"): oy = 0.65
        elif obj["name"] in ("mountain", "tree"): oy = 0.5; size = 1.2
        elif obj["name"] in ("sun", "moon", "star", "cloud"): oy = 0.15 + (i*0.1)
        elif obj["name"] == "bird": oy = 0.2
        elif obj["name"] in ("wave",): oy = 0.35; size = 1.2
        elif obj["name"] in ("canoe",): oy = 0.60; size = 0.9
        elif obj["name"] in ("anchor",): oy = 0.50
        elif obj["name"] in ("totem", "monolith"): oy = 0.55; size = 1.0
        elif obj["name"] in ("cliff",): oy = 0.55; size = 1.0
        elif obj["name"] in ("compass_rose",): oy = 0.35; size = 0.8
        elif obj["name"] in ("shadow_figure",): oy = 0.55; size = 0.9
        elif obj["name"] in ("moon_path",): oy = 0.50
        objects.append({"name": obj["name"], "x": ox, "y": oy, "size": size})
    # Background
    bg = []
    if sky not in ("night",) and "mountain" not in p:
        if rng.random() > 0.5: bg.append("cloud")
    if "mountain" in p: bg.append("mountain")
    return {"sky": sky, "background": bg, "objects": objects, "ground": ground}

def parse_scene(prompt: str) -> dict:
    """Use LLM to turn a prompt into a structured scene description. Falls back to keyword matching."""
    from src.script_generator import _generate
    system = "You output JSON only. Describe a scene for hand-drawn illustration."
    user = f"""Given the prompt: "{prompt}"

Output JSON describing the scene:
{{
  "sky": "day"|"night"|"sunset",
  "background": ["element1", "element2", ...],
  "objects": [
    {{"name": "object_name", "x": 0.0-1.0, "y": 0.0-1.0, "size": 0.5-2.0, "color": [R,G,B]}}
  ],
  "ground": "grass"|"snow"|"desert"|"water"|"road"|"none"
}}

Available objects: sun, moon, star, tree, mountain, cloud, water, flower, grass, bird, house, fence, fire, human, man, woman, horse, dog, cat

Respond with ONLY the JSON, no other text."""
    try:
        raw = _generate(user, temperature=0.5, max_tokens=800, system=system)
        raw = re.sub(r'^```(?:json)?\s*', '', raw.strip())
        raw = re.sub(r'\s*```$', '', raw)
        data = json.loads(raw)
        print(f"  LLM OK: {data.get('sky')}, {[o['name'] for o in data.get('objects',[])]}")
    except Exception as e:
        print(f"  LLM unavailable, using keyword fallback ({e})")
        data = _keyword_parse(prompt)
    return data

# ─── Main renderer ─────────────────────────────────────────────

def render_scene(data: dict, w=W, h=H) -> Image.Image:
    img = Image.new('RGBA', (w, h), (252, 250, 245, 255))
    draw = ImageDraw.Draw(img, 'RGBA')

    # Paper grain
    for _ in range(1500):
        x, y = rng.randint(0, w-1), rng.randint(0, h-1)
        v = rng.randint(-12, 4)
        c = 250 + v
        draw.point((x, y), fill=(c, c-2, c-4))

    sky = data.get("sky", "day")
    ground_y = int(h * 0.75)

    # Sky
    if sky == "night":
        for y in range(ground_y):
            t = y / ground_y
            draw.line([(0, y), (w, y)], fill=(int(10+t*15), int(5+t*10), int(20+t*30)))
        for _ in range(60):
            sx, sy = rng.randint(0, w), rng.randint(0, ground_y-20)
            _circle(draw, sx, sy, rng.uniform(0.5, 2), fill_c=(255,255,200,rng.randint(30,100)), line_c=None)
    elif sky == "sunset":
        for y in range(ground_y):
            t = y / ground_y
            draw.line([(0, y), (w, y)], fill=(int(60+195*t), int(30+180*t), int(60+80*(1-t))))
    else:
        for y in range(ground_y):
            t = y / ground_y
            draw.line([(0, y), (w, y)], fill=(int(225-t*25), int(230-t*20), int(240-t*15)))

    # Background elements (mountains, clouds, etc.)
    for bg in data.get("background", []):
        bg_name = bg.lower() if isinstance(bg, str) else ""
        if not bg_name:
            continue
        if "mountain" in bg_name:
            for i in range(3):
                draw_mountain(draw, int(w*(0.15+0.35*i)), int(ground_y), 0.8)
        elif "cloud" in bg_name:
            for i in range(rng.randint(2,4)):
                draw_cloud(draw, rng.randint(50, w-50), rng.randint(30, ground_y//3), rng.uniform(0.5,1.2))

    # Ground
    ground_type = data.get("ground", "grass")
    if ground_type == "water":
        for y in range(ground_y, h):
            t = (y-ground_y)/(h-ground_y)
            draw.line([(0, y), (w, y)], fill=(int(30+30*t), int(80+60*t), int(150+50*t)))
        draw_water(draw, 0, ground_y, w, h-ground_y)
    elif ground_type == "snow":
        for y in range(ground_y, h):
            draw.line([(0, y), (w, y)], fill=(240, 245, 250))
    elif ground_type == "desert":
        for y in range(ground_y, h):
            t = (y-ground_y)/(h-ground_y)
            draw.line([(0, y), (w, y)], fill=(int(200-t*20), int(180-t*15), int(130-t*10)))
    elif ground_type == "road":
        draw_road(draw, int(w*0.3), ground_y, int(w*0.4), h-ground_y)
    else:
        for y in range(ground_y, h):
            t = (y-ground_y)/(h-ground_y)
            draw.line([(0, y), (w, y)], fill=(int(195-t*50), int(185-t*40), int(165-t*30)))
        for _ in range(rng.randint(30, 60)):
            gx = rng.randint(20, w-20)
            gy = ground_y + rng.randint(0, h-ground_y)
            draw_grass_blade(draw, gx, gy, rng.randint(5, 15), (rng.randint(40,70), rng.randint(70,110), rng.randint(25,45)))

    # Objects from LLM
    for obj in data.get("objects", []):
        name = obj.get("name", "").lower()
        ox = int(obj.get("x", 0.5) * w)
        oy = int(obj.get("y", 0.5) * h)
        size = obj.get("size", 1.0)
        if name in OBJECT_RENDERERS:
            try:
                OBJECT_RENDERERS[name](draw, ox, oy, size)
            except Exception as e:
                print(f"  Error drawing {name}: {e}")

    img = img.filter(ImageFilter.SMOOTH)
    return img.convert("RGB")

def main():
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "a peaceful landscape with mountains and a lake"
    print(f"Prompt: {prompt}")
    print("[1/2] Parsing scene with LLM...")
    data = parse_scene(prompt)
    print(f"  Sky: {data.get('sky')}, Ground: {data.get('ground')}")
    print(f"  Objects: {[o['name'] for o in data.get('objects', [])]}")
    print("[2/2] Rendering hand-drawn sketch...")
    img = render_scene(data)
    safe = re.sub(r'[^\w]+', '_', prompt.lower())[:50]
    out = f"sketch_{safe}.png"
    img.save(out)
    sz = os.path.getsize(out)
    print(f"Done: {out} ({img.size[0]}x{img.size[1]}, {sz:,} bytes)")

if __name__ == "__main__":
    main()
