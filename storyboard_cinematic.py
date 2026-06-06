"""Cinematic animated storyboard — 11-scene pirate short with ink effects, pans, zooms, reveals, text-write animation."""

import sys, os, math, random, json, time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
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
rng = random.Random(42)
SEED = 42

# ─── Primitives ────────────────────────────────────────────────

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

def _get_font(size=36):
    try: return ImageFont.truetype(config.get_font(), size)
    except: return ImageFont.load_default()

# ─── Scene 1: Opening (0-20s) ──────────────────────────────────

def scene_opening(t, dur=20):
    """Blank parchment → ink line becomes ocean → ship zooms in → sailor → title writes itself."""
    img = Image.new("RGB", (W, H), (252, 250, 245))
    draw = ImageDraw.Draw(img)
    # Paper grain
    for _ in range(1000):
        x, y = rng.randint(0, W-1), rng.randint(0, H-1)
        v = rng.randint(-10, 4)
        c = 250+v; draw.point((x, y), fill=(c, c-2, c-4))
    p = min(t/dur, 1)
    phase = min(p*3, 1)

    if p > 0.02:
        # Ocean horizon line draws itself
        line_prog = min((p-0.02)/0.15, 1)
        oh = int(H*0.6)
        drawn = int(oh + (W-oh)*line_prog)
        if drawn > oh:
            _stroke(draw, [(oh, oh), (drawn, oh)], w=2, color=(40,35,30), amp=0.5)

    if p > 0.1:
        # Ocean fills
        ocean_prog = min((p-0.1)/0.15, 1)
        for y in range(int(H*0.6), H):
            t2 = y/H
            c = int(120+60*t2)
            if (y-int(H*0.6)) < ocean_prog*(H-int(H*0.6)):
                draw.line([(0,y),(W,y)], fill=(c, c+30, c+60))
        # Waves
        for i in range(int(10*ocean_prog)):
            wx = rng.randint(0, W)
            wy = int(H*0.6)+rng.randint(0, int(H*0.3))
            _stroke(draw, [(wx, wy), (wx+rng.randint(8,20), wy+rng.randint(-2,2))], w=1, color=(80,100,140,100), amp=0.3)

    if p > 0.2:
        # Ship draws itself
        ship_prog = min((p-0.2)/0.2, 1)
        sx, sy = W//2, int(H*0.55)
        # Hull
        hull = [(sx-30*ship_prog, sy), (sx-25*ship_prog, sy+12), (sx+25*ship_prog, sy+12), (sx+30*ship_prog, sy)]
        _fill(draw, hull, (60,50,40,180), amp=1.5)
        _stroke(draw, hull, w=2, color=(40,35,25))
        # Mast
        _stroke(draw, [(sx, sy), (sx, sy-40*ship_prog)], w=3, color=(50,40,30))
        # Sail
        if ship_prog > 0.5:
            sail_prog = (ship_prog-0.5)/0.5
            _fill(draw, [(sx, sy-35*sail_prog), (sx-20*sail_prog, sy-10*sail_prog), (sx, sy-5*sail_prog)], (240,235,220,180), amp=1.5)
            _stroke(draw, [(sx, sy-35*sail_prog), (sx-20*sail_prog, sy-10*sail_prog), (sx, sy-5*sail_prog)], w=1.5, color=(100,95,85))

    if p > 0.35:
        # Sailor appears
        sailor_prog = min((p-0.35)/0.1, 1)
        px, py = W//2+5, int(H*0.53)-2
        _circle(draw, px, py-18*sailor_prog, 5*sailor_prog, fill_c=(230,200,170,200*sailor_prog), line_c=(180,150,130))
        body = [(px-4*sailor_prog, py-13*sailor_prog), (px-3*sailor_prog, py-2*sailor_prog), (px+3*sailor_prog, py-2*sailor_prog), (px+4*sailor_prog, py-13*sailor_prog)]
        _fill(draw, body, (100,80,60,180*sailor_prog), amp=1)

    if p > 0.45:
        # Wind lines sweep
        wind_prog = min((p-0.45)/0.15, 1)
        for i in range(int(8*wind_prog)):
            wx = rng.randint(30, W-30)
            wy = rng.randint(int(H*0.3), int(H*0.55))
            _stroke(draw, [(wx, wy), (wx+20+10*wind_prog, wy-5*wind_prog)], w=1, color=(100,95,85,100), amp=0.5)

    if p > 0.55:
        # Title writes itself
        title_prog = min((p-0.55)/0.2, 1)
        tf = _get_font(48)
        title = "HOW PIRATES"
        title2 = "REALLY LIVED"
        chars_per = int(len(title)*title_prog)
        drawn_title = title[:chars_per]
        tb = draw.textbbox((0,0), drawn_title, font=tf)
        tx = (W-(tb[2]-tb[0]))//2
        draw.text((tx, 60), drawn_title, font=tf, fill=(40,35,30))
        if title_prog > 0.5:
            chars2 = int(len(title2)*((title_prog-0.5)/0.5))
            drawn2 = title2[:chars2]
            tb2 = draw.textbbox((0,0), drawn2, font=tf)
            tx2 = (W-(tb2[2]-tb2[0]))//2
            draw.text((tx2, 120), drawn2, font=tf, fill=(40,35,30))

    # Parchment border
    border_w = 15
    _rect = ImageDraw.Draw(img)
    for i in range(border_w):
        c = 240-i
        draw.line([(i,i),(W-i,i)], fill=(c,c-2,c-5))
        draw.line([(i,H-i),(W-i,H-i)], fill=(c,c-2,c-5))
        draw.line([(i,i),(i,H-i)], fill=(c,c-2,c-5))
        draw.line([(W-i,i),(W-i,H-i)], fill=(c,c-2,c-5))

    return np.array(img)

# ─── Scene 2: Sailor's Life (20-50s) ───────────────────────────

def scene_sailor_life(t, dur=30):
    img = Image.new("RGB", (W, H), (252, 250, 245))
    draw = ImageDraw.Draw(img)
    for _ in range(800):
        x, y = rng.randint(0, W-1), rng.randint(0, H-1)
        draw.point((x, y), fill=(248+rng.randint(-8,3), 246+rng.randint(-8,3), 240+rng.randint(-8,3)))
    p = min(t/dur, 1)

    # Hundreds of tiny stick sailors
    num_sailors = int(200 * min(p/0.3, 1))
    fade_start = min(max((p-0.5)/0.2, 0), 1)
    remaining = min(max((p-0.7)/0.2, 0), 1)

    sailors = []
    for i in range(num_sailors):
        sx = rng.randint(30, W-30)
        sy = rng.randint(40, H-60)
        alpha = 255
        if fade_start > 0:
            if rng.random() < fade_start * 0.8:
                alpha = max(0, 255 - int(255 * (fade_start - 0.3) / 0.3))
        if remaining > 0 and i < num_sailors * remaining:
            alpha = 255
        if alpha > 10:
            c = (80,70,60,alpha)
            _stroke(draw, [(sx, sy-15), (sx, sy)], w=1.5, color=c, amp=0.3)
            _stroke(draw, [(sx-5, sy-8), (sx+5, sy-8)], w=1, color=c, amp=0.2)
            _circle(draw, sx, sy-18, 4, fill_c=(*[min(255, x+150) for x in c[:3]], alpha), line_c=(*c[:3], alpha), w=1)

    # One whipped
    if p > 0.2:
        wx, wy = W//2, int(H*0.5)
        _stroke(draw, [(wx-5, wy-20), (wx-5, wy+10)], w=2, color=(100,30,30,200), amp=0.5)
        # Blood drop
        _circle(draw, wx-3, wy+12, 3, fill_c=(180,20,20,180), line_c=None)

    # One collapsed
    if p > 0.35:
        cx, cy = int(W*0.7), int(H*0.6)
        _stroke(draw, [(cx, cy-15), (cx-3, cy-3), (cx, cy)], w=2, color=(80,70,60,180), amp=0.5)

    # Empty bowl
    if p > 0.45:
        bx, by = int(W*0.3), int(H*0.55)
        _stroke(draw, [(bx-8, by), (bx-6, by+8), (bx+6, by+8), (bx+8, by)], w=2, color=(80,70,60,180), amp=0.5)

    # Final single sailor
    if remaining > 0.5:
        fx, fy = W//2, int(H*0.55)
        _circle(draw, fx, fy-18, 6, fill_c=(230,200,170,255), line_c=(180,150,130))
        body = [(fx-5, fy-13), (fx-4, fy+3), (fx+4, fy+3), (fx+5, fy-13)]
        _fill(draw, body, (100,80,60,200), amp=1)
        # Spotlight circle
        for r in range(100, 0, -3):
            a = max(0, 60 - r//2)
            draw.ellipse([fx-r, fy+r-30, fx+r, fy+r+10], fill=(252,250,245,a))

    return np.array(img)

# ─── Scene 3: Turning Point (50-80s) ───────────────────────────

def scene_turning_point(t, dur=30):
    img = Image.new("RGB", (W, H), (252, 250, 245))
    draw = ImageDraw.Draw(img)
    for _ in range(800):
        x, y = rng.randint(0, W-1), rng.randint(0, H-1)
        draw.point((x, y), fill=(248+rng.randint(-8,3), 246+rng.randint(-8,3), 240+rng.randint(-8,3)))
    p = min(t/dur, 1)

    # Ocean
    for y in range(int(H*0.5), H):
        t2 = y/H
        draw.line([(0,y),(W,y)], fill=(int(130+50*t2), int(150+40*t2), int(170+30*t2)))

    # Ship (merchant)
    sx, sy = W//2, int(H*0.45)
    _fill(draw, [(sx-25, sy), (sx-20, sy+12), (sx+20, sy+12), (sx+25, sy)], (60,50,40,200), amp=1.5)
    _stroke(draw, [(sx, sy), (sx, sy-35)], w=3, color=(50,40,30))
    _fill(draw, [(sx, sy-30), (sx-18, sy-8), (sx, sy-5)], (240,235,220,180), amp=1.5)

    # Lookout appears
    if p > 0.05:
        lx, ly = sx+10, sy-35
        _circle(draw, lx, ly-10, 5, fill_c=(230,200,170,200), line_c=(180,150,130))
        body = [(lx-3, ly-5), (lx-3, ly+2), (lx+3, ly+2), (lx+3, ly-5)]
        _fill(draw, body, (100,80,60,180), amp=1)

    # Speech bubble
    if p > 0.15:
        bubble_prog = min((p-0.15)/0.1, 1)
        _circle(draw, lx+25, ly-25, 18*bubble_prog, fill_c=(255,255,255,200), line_c=(100,100,100))
        tf = _get_font(int(14*bubble_prog))
        draw.text((lx+18, ly-32), "Sail!", font=tf, fill=(30,25,20))

    # Freeze frame effect (frame border)
    if 0.15 < p < 0.25:
        for i in range(4):
            c = int(200 * (1 - abs(p-0.2)*20))
            draw.line([(i,i),(W-i,i)], fill=(c,c,c))
            draw.line([(i,H-i),(W-i,H-i)], fill=(c,c,c))

    # Tiny triangle on horizon
    if p > 0.25:
        sail_grow = min((p-0.25)/0.3, 1)
        hx = int(W*0.15)
        hy = int(H*0.35)
        sz = 3 + 20*sail_grow
        _fill(draw, [(hx, hy+sz), (hx+sz*0.5, hy), (hx+sz, hy+sz)], (30,30,30,150*sail_grow), amp=1)
        _stroke(draw, [(hx+sz*0.5, hy), (hx+sz*0.5, hy+sz)], w=2, color=(20,20,20), amp=0.5)

    # Pirate ship emerges
    if p > 0.5:
        emerge = min((p-0.5)/0.3, 1)
        px, py = int(W*0.15)+30*emerge, int(H*0.35)+10*emerge
        _fill(draw, [(px-35*emerge, py), (px-30*emerge, py+15*emerge), (px+30*emerge, py+15*emerge), (px+35*emerge, py)], (40,35,30,200*emerge), amp=2)
        _stroke(draw, [(px, py), (px, py-50*emerge)], w=3, color=(30,25,20))
        _fill(draw, [(px, py-45*emerge), (px-25*emerge, py-10*emerge), (px, py-5*emerge)], (30,30,30,200*emerge), amp=1.5)
        # Pirate flag
        if emerge > 0.5:
            _fill(draw, [(px, py-50*emerge), (px+12*emerge, py-44*emerge), (px, py-38*emerge)], (20,20,20,200), amp=1)

    # Ink spread effect at edges
    if p > 0.7:
        ink = min((p-0.7)/0.2, 1)
        for i in range(int(15*ink)):
            ix = rng.randint(0, 30)
            iy = rng.randint(0, H)
            _circle(draw, ix, iy, rng.uniform(1,5), fill_c=(30,25,20,rng.randint(30,100)), line_c=None)
            ix = rng.randint(W-30, W)
            iy = rng.randint(0, H)
            _circle(draw, ix, iy, rng.uniform(1,5), fill_c=(30,25,20,rng.randint(30,100)), line_c=None)

    return np.array(img)

# ─── Scene 4: Pirate Offer (80-110s) ───────────────────────────

def scene_pirate_offer(t, dur=30):
    img = Image.new("RGB", (W, H), (252, 250, 245))
    draw = ImageDraw.Draw(img)
    for _ in range(800):
        x, y = rng.randint(0, W-1), rng.randint(0, H-1)
        draw.point((x, y), fill=(248+rng.randint(-8,3), 246+rng.randint(-8,3), 240+rng.randint(-8,3)))
    p = min(t/dur, 1)

    # Two doors drawing themselves
    door_prog = min(p/0.3, 1)
    # Door 1 (left) - Merchant
    dw, dh = 120, 200
    dx1, dy = int(W*0.25)-dw//2, int(H*0.4)
    _rect(draw, dx1, dy, dw*door_prog, dh*door_prog, fill_c=(150,140,120,150*door_prog), line_c=(60,50,40))
    # Door 2 (right) - Pirate
    dx2 = int(W*0.75)-dw//2
    _rect(draw, dx2, dy, dw*door_prog, dh*door_prog, fill_c=(120,100,80,150*door_prog), line_c=(60,50,40))

    if p > 0.1:
        # Merchant labels
        tf = _get_font(16)
        labels_m = ["Hunger", "Beatings", "No Pay"]
        for i, l in enumerate(labels_m):
            draw.text((dx1+15, dy+40+i*25), l, font=tf, fill=(180,60,50))
        labels_p = ["Risk", "Freedom", "Share"]
        for i, l in enumerate(labels_p):
            draw.text((dx2+15, dy+40+i*25), l, font=tf, fill=(200,180,100))

    # Sailor hesitates
    if p > 0.3:
        hx, hy = W//2, int(H*0.7)
        _circle(draw, hx, hy-18, 6, fill_c=(230,200,170,200), line_c=(180,150,130))
        body = [(hx-5, hy-13), (hx-4, hy+3), (hx+4, hy+3), (hx+5, hy-13)]
        _fill(draw, body, (100,80,60,200), amp=1)
        # Question mark
        tf = _get_font(28)
        draw.text((hx+10, hy-30), "?", font=tf, fill=(100,80,60))

    # Step toward piracy
    if p > 0.6:
        step = min((p-0.6)/0.2, 1)
        target_x = dx2 + dw//2
        step_x = hx + (target_x - hx) * step * 0.5
        draw.ellipse([step_x-3, hy+3, step_x+3, hy+6], fill=(100,80,60))

    return np.array(img)

# ─── Scene 5: Myth Breaker (110-140s) ──────────────────────────

def scene_myth_breaker(t, dur=30):
    img = Image.new("RGB", (W, H), (252, 250, 245))
    draw = ImageDraw.Draw(img)
    for _ in range(800):
        x, y = rng.randint(0, W-1), rng.randint(0, H-1)
        draw.point((x, y), fill=(248+rng.randint(-8,3), 246+rng.randint(-8,3), 240+rng.randint(-8,3)))
    p = min(t/dur, 1)

    tf = _get_font(32)
    draw.text((30, 30), "Forget what movies taught you.", font=tf, fill=(100,80,60))

    # Clichés appear then crumble
    items = [
        ("Parrot", W//4, int(H*0.35)),
        ("Treasure Map", W*3//4, int(H*0.3)),
        ("Wooden Leg", W//3, int(H*0.6)),
        ("Buried Chest", W*3//4, int(H*0.6)),
    ]

    for i, (label, ix, iy) in enumerate(items):
        appear_p = min(max((p - 0.05 - i*0.05)/0.1, 0), 1)
        crumble_p = min(max((p - 0.4 - i*0.08)/0.15, 0), 1)
        if appear_p > 0 and crumble_p < 1:
            alpha = int(255 * appear_p * (1-crumble_p))
            if alpha > 10:
                _circle(draw, ix, iy, 15*appear_p, fill_c=(200,180,150,alpha), line_c=(100,90,80,alpha))
                tf_item = _get_font(14)
                draw.text((ix-20, iy+20), label, font=tf_item, fill=(80,70,60,alpha))
        # Crumble particles
        if crumble_p > 0:
            for _ in range(int(5*crumble_p)):
                px = ix + rng.randint(-20, 20)
                py = iy + rng.randint(-15, 15) + int(30*crumble_p)
                sz = rng.uniform(1, 3)
                _circle(draw, px, py, sz, fill_c=(180,160,130,rng.randint(30,100)), line_c=None)

    return np.array(img)

# ─── Scene 6: Real Pirate Life (140-180s) ──────────────────────

def scene_real_life(t, dur=40):
    img = Image.new("RGB", (W, H), (252, 250, 245))
    draw = ImageDraw.Draw(img)
    for _ in range(600):
        x, y = rng.randint(0, W-1), rng.randint(0, H-1)
        draw.point((x, y), fill=(248+rng.randint(-8,3), 246+rng.randint(-8,3), 240+rng.randint(-8,3)))
    p = min(t/dur, 1)

    # Huge ocean
    for y in range(int(H*0.1), H):
        t2 = y/H
        draw.line([(0,y),(W,y)], fill=(int(120+80*t2), int(140+70*t2), int(160+60*t2)))

    # Tiny ship
    sx, sy = W//2, int(H*0.35)
    sz = max(0.3, 0.8 - p*0.3)
    _fill(draw, [(sx-10*sz, sy), (sx-8*sz, sy+5*sz), (sx+8*sz, sy+5*sz), (sx+10*sz, sy)], (60,50,40,180), amp=1)
    _stroke(draw, [(sx, sy), (sx, sy-15*sz)], w=2, color=(50,40,30))

    # Calendar pages
    if p > 0.1:
        days = ["Day 7", "Day 19", "Day 41", "Day 63"]
        for i, day in enumerate(days):
            day_p = min(max((p - 0.1 - i*0.12)/0.08, 0), 1)
            if day_p > 0:
                _rect(draw, W-100, 50+i*45, 70, 35, fill_c=(245,240,225,180*day_p), line_c=(100,90,80,180*day_p))
                tf = _get_font(14)
                draw.text((W-90, 58+i*45), day, font=tf, fill=(80,70,60,int(255*day_p)))

    return np.array(img)

# ─── Scene 7: Storm (180-220s) ─────────────────────────────────

def scene_storm(t, dur=40):
    img = Image.new("RGB", (W, H), (230, 225, 215))
    draw = ImageDraw.Draw(img)
    p = min(t/dur, 1)

    # Darkening sky
    for y in range(int(H*0.4)):
        t2 = y/int(H*0.4)
        c = int(200 - 180*p*t2)
        draw.line([(0,y),(W,y)], fill=(c, c-5, c-10))

    # Angry ocean
    for y in range(int(H*0.4), H):
        t2 = (y-int(H*0.4))/(H-int(H*0.4))
        c = int(80 - 60*p + 40*t2)
        draw.line([(0,y),(W,y)], fill=(c, c+20, c+40))

    # Ink stain clouds
    if p > 0.05:
        for i in range(int(10*min(p/0.3, 1))):
            cx = rng.randint(50, W-50)
            cy = rng.randint(10, int(H*0.3))
            r = rng.randint(30, 80)
            _circle(draw, cx, cy, r, fill_c=(30,25,20,rng.randint(20,80)), line_c=None)

    # Lightning
    if p > 0.2 and int(p*30) % 5 == 0:
        lx = rng.randint(100, W-100)
        ly = 0
        pts = [(lx, ly)]
        for i in range(5):
            pts.append((lx+rng.randint(-15, 15), ly+30*(i+1)))
        _stroke(draw, pts, w=3, color=(255,255,200,150), amp=0.5)

    # Ship bending
    ship_p = min(max((p-0.3)/0.3, 0), 1)
    sx, sy = W//2, int(H*0.45)
    bend = ship_p * 10
    _fill(draw, [(sx-25, sy+bend), (sx-20, sy+12+bend), (sx+20, sy+12-bend), (sx+25, sy-bend)], (60,50,40,200), amp=2)
    _stroke(draw, [(sx, sy+bend), (sx, sy-35+bend)], w=3, color=(50,40,30))

    # Sailor falling
    if p > 0.5:
        fall = min((p-0.5)/0.2, 1)
        fx = sx + 10*fall
        fy = sy + 20 + 40*fall
        _stroke(draw, [(fx, fy-10), (fx-3, fy), (fx+3, fy)], w=2, color=(100,80,60,200*(1-fall*0.7)), amp=1)

    # Ocean monster
    if p > 0.6:
        monster = min((p-0.6)/0.3, 1)
        for i in range(int(20*monster)):
            mx = rng.randint(0, W)
            my = int(H*0.4) + rng.randint(0, int(H*0.3))
            r = rng.randint(5, 15)*monster
            _circle(draw, mx, my, r, fill_c=(20,15,10,rng.randint(30,120)), line_c=None)

    return np.array(img)

# ─── Scene 8: Treasure Reality (220-250s) ──────────────────────

def scene_treasure(t, dur=30):
    img = Image.new("RGB", (W, H), (252, 250, 245))
    draw = ImageDraw.Draw(img)
    for _ in range(800):
        x, y = rng.randint(0, W-1), rng.randint(0, H-1)
        draw.point((x, y), fill=(248+rng.randint(-8,3), 246+rng.randint(-8,3), 240+rng.randint(-8,3)))
    p = min(t/dur, 1)

    # Chest opening
    open_prog = min(p/0.2, 1)
    cx, cy = W//2, int(H*0.45)
    _rect(draw, cx-40, cy, 80, 50, fill_c=(120,80,40,180*open_prog), line_c=(80,50,30))
    _stroke(draw, [(cx-40, cy+15*open_prog), (cx, cy-5*open_prog), (cx+40, cy+15*open_prog)], w=3, color=(80,50,30), amp=1)

    # Reveal items
    if p > 0.2:
        items = [("Sugar", (255,220,150)), ("Cloth", (200,180,160)), ("Tea", (150,130,80)), ("Spices", (180,100,50)), ("Rum", (200,180,100))]
        for i, (label, color) in enumerate(items):
            item_p = min(max((p - 0.2 - i*0.08)/0.05, 0), 1)
            if item_p > 0:
                ix = cx - 30 + i * 15
                iy = cy + 30
                _circle(draw, ix, iy, 8*item_p, fill_c=(*color, 180*item_p), line_c=(*[max(0,x-30) for x in color], 150*item_p))
                tf = _get_font(12)
                draw.text((ix-10, iy+12), label, font=tf, fill=(80,70,60,int(255*item_p)))

    return np.array(img)

# ─── Scene 9: The Hunt (250-290s) ──────────────────────────────

def scene_hunt(t, dur=40):
    img = Image.new("RGB", (W, H), (252, 250, 245))
    draw = ImageDraw.Draw(img)
    for _ in range(800):
        x, y = rng.randint(0, W-1), rng.randint(0, H-1)
        draw.point((x, y), fill=(248+rng.randint(-8,3), 246+rng.randint(-8,3), 240+rng.randint(-8,3)))
    p = min(t/dur, 1)

    # Map background
    _rect(draw, 20, 20, W-40, H-40, fill_c=(220,210,190,100), line_c=(100,90,80))
    # Grid lines
    for i in range(8):
        _stroke(draw, [(30, 30+i*(H-60)//7), (W-30, 30+i*(H-60)//7)], w=1, color=(180,170,150,80), amp=0.2)
        _stroke(draw, [(30+i*(W-60)//7, 30), (30+i*(W-60)//7, H-30)], w=1, color=(180,170,150,80), amp=0.2)

    # Pirate icon moving
    pirate_prog = min(p/0.4, 1)
    px = 50 + (W-100) * pirate_prog
    py = int(H*0.3 + (H*0.4)*math.sin(pirate_prog*math.pi))
    _circle(draw, px, py, 8, fill_c=(180,30,30,200), line_c=(120,20,20))

    # Navy ships appearing
    if p > 0.3:
        navy_p = min((p-0.3)/0.4, 1)
        for i, (nx, ny) in enumerate([(int(W*0.1), int(H*0.25)), (int(W*0.85), int(H*0.2)), (int(W*0.2), int(H*0.8)), (int(W*0.8), int(H*0.75))]):
            np_i = min(max((navy_p - i*0.1)/0.1, 0), 1)
            if np_i > 0:
                _fill(draw, [(nx-15*np_i, ny), (nx-12*np_i, ny+8*np_i), (nx+12*np_i, ny+8*np_i), (nx+15*np_i, ny)], (30,50,90,180*np_i), amp=1.5)
                _stroke(draw, [(nx, ny), (nx, ny-20*np_i)], w=2, color=(30,40,70))
                _fill(draw, [(nx, ny-18*np_i), (nx-10*np_i, ny-5*np_i), (nx, ny-3*np_i)], (30,60,120,180*np_i), amp=1)

    return np.array(img)

# ─── Scene 10: End of Pirate (290-330s) ────────────────────────

def scene_end_pirate(t, dur=40):
    img = Image.new("RGB", (W, H), (230, 225, 215))
    draw = ImageDraw.Draw(img)
    p = min(t/dur, 1)

    # Dark harbor
    for y in range(H):
        t2 = y/H
        draw.line([(0,y),(W,y)], fill=(int(30+20*t2), int(25+15*t2), int(20+10*t2)))

    # Moon
    _circle(draw, int(W*0.8), 50, 25, fill_c=(200,200,180,60), line_c=(180,180,160,80))

    # Gallows silhouette
    gallows_p = min(p/0.3, 1)
    gx, gy = W//2, int(H*0.55)
    _stroke(draw, [(gx, gy), (gx, gy-60*gallows_p)], w=4, color=(20,15,10))
    _stroke(draw, [(gx-20*gallows_p, gy-60*gallows_p), (gx+20*gallows_p, gy-60*gallows_p)], w=3, color=(20,15,10))
    _stroke(draw, [(gx, gy-60*gallows_p), (gx, gy-45*gallows_p)], w=1.5, color=(30,25,20))

    # Pirate names fading
    names = ["Blackbeard", "Calico Jack", "Anne Bonny", "Charles Vane", "Edward Teach"]
    for i, name in enumerate(names):
        name_p = min(max((p - 0.2 - i*0.1)/0.08, 0), 1)
        if name_p > 0:
            alpha = int(255 * (1-name_p))
            tf = _get_font(16)
            draw.text((50, 100+i*35), name, font=tf, fill=(150,140,130,alpha))

    return np.array(img)

# ─── Scene 11: Final Scene (330-end) ───────────────────────────

def scene_final(t, dur=50):
    img = Image.new("RGB", (W, H), (252, 250, 245))
    draw = ImageDraw.Draw(img)
    for _ in range(1000):
        x, y = rng.randint(0, W-1), rng.randint(0, H-1)
        draw.point((x, y), fill=(248+rng.randint(-8,3), 246+rng.randint(-8,3), 240+rng.randint(-8,3)))
    p = min(t/dur, 1)

    # Old map background
    if p < 0.6:
        map_prog = 1 - p/0.6
        _rect(draw, int(20*map_prog), int(20*map_prog), int((W-40)*map_prog), int((H-40)*map_prog), fill_c=(220,210,190,80), line_c=(100,90,80,100))
        # Grid
        for i in range(6):
            gi = i * (H-60)//5
            _stroke(draw, [(30, 30+gi*map_prog), (W-30, 30+gi*map_prog)], w=1, color=(180,170,150,60), amp=0.2)

    # Water/ocean returning
    if p > 0.3:
        ocean_p = min((p-0.3)/0.2, 1)
        for y in range(int(H*0.6), H):
            t2 = (y-int(H*0.6))/(H-int(H*0.6))
            c = int(120+60*t2)
            draw.line([(0,y),(W,y)], fill=(c, c+30, c+60))

    # Lone pirate at edge
    if p > 0.15:
        sailor_p = min((p-0.15)/0.15, 1)
        px, py = W//2, int(H*0.55)
        _circle(draw, px, py-18*sailor_p, 6*sailor_p, fill_c=(30,25,20,200), line_c=(20,15,10))
        body = [(px-5*sailor_p, py-13*sailor_p), (px-4*sailor_p, py+3*sailor_p), (px+4*sailor_p, py+3*sailor_p), (px+5*sailor_p, py-13*sailor_p)]
        _fill(draw, body, (40,35,30,200), amp=1)

    # Final text writes itself
    if p > 0.55:
        text_prog = min((p-0.55)/0.25, 1)
        tf = _get_font(36)
        final_text = "Freedom was the treasure."
        final_text2 = "The sea was the price."
        chars = int(len(final_text)*text_prog)
        if chars > 0:
            drawn = final_text[:chars]
            tb = draw.textbbox((0,0), drawn, font=tf)
            draw.text(((W-(tb[2]-tb[0]))//2, int(H*0.75)), drawn, font=tf, fill=(40,35,30))
        if text_prog > 0.5:
            chars2 = int(len(final_text2)*((text_prog-0.5)/0.5))
            if chars2 > 0:
                drawn2 = final_text2[:chars2]
                tb2 = draw.textbbox((0,0), drawn2, font=tf)
                draw.text(((W-(tb2[2]-tb2[0]))//2, int(H*0.75)+50), drawn2, font=tf, fill=(40,35,30))

    # Parchment reclaiming (edges fade to blank)
    if p > 0.8:
        fade = min((p-0.8)/0.15, 1)
        overlay = Image.new("RGBA", (W, H), (252, 250, 245, int(255*fade)))
        img = Image.alpha_composite(img.convert("RGBA"), overlay)

    return np.array(img.convert("RGB")) if p > 0.8 else np.array(img)

# ─── Scene selector ────────────────────────────────────────────

SCENE_MAP = [
    (0, 20, scene_opening),
    (20, 50, scene_sailor_life),
    (50, 80, scene_turning_point),
    (80, 110, scene_pirate_offer),
    (110, 140, scene_myth_breaker),
    (140, 180, scene_real_life),
    (180, 220, scene_storm),
    (220, 250, scene_treasure),
    (250, 290, scene_hunt),
    (290, 330, scene_end_pirate),
    (330, 380, scene_final),
]

def build_video(output_path: str):
    scenes_text = [
        "The year is 1715. The Atlantic Ocean stretches endlessly in every direction. You have been at sea for three months. Your clothes smell of salt. Your stomach growls. And your captain has not paid you a single coin.",
        "History remembers pirates. But before most men became pirates they were sailors. Forgotten sailors.",
        "Then one morning someone spots a sail. Far away on the horizon a tiny black triangle. The sail grows. A pirate ship emerges from darkness.",
        "You expect death. Instead the pirates offer a choice. Merchant life or pirate life. The sailor hesitates. Then steps toward piracy.",
        "Forget what movies taught you. Parrot. Treasure map. Wooden leg. Buried chest. One by one the myths crumble into dust.",
        "Most pirate days were not adventures. They were waiting. Huge ocean. Tiny ship. Days turn into weeks. Nothing happens.",
        "Then nature reminds everyone who truly rules the sea. Clouds grow from ink stains. Lightning scratches across the sky. The ship bends. One sailor disappears into waves.",
        "And when treasure finally appeared it rarely looked like treasure. Sugar. Cloth. Tea. Spices. Rum barrels.",
        "Soon the hunter becomes the hunted. Navy ships appear from all sides like wolves circling prey.",
        "Most pirates did not retire rich. Most did not retire at all. Harbor gallows in silhouette. One by one pirate names fade away.",
        "The pirate was not searching for gold. He was searching for freedom. Freedom was the treasure. The sea was the price.",
    ]
    total_dur = SCENE_MAP[-1][1]

    print(f"\n{'='*55}")
    print(f"  CINEMATIC STORYBOARD — {len(SCENE_MAP)} scenes, {total_dur}s")
    print(f"{'='*55}")

    temp_dir = config.TEMP_DIR / "cinematic"
    temp_dir.mkdir(exist_ok=True)

    print(f"\n[1/3] Generating TTS...")
    full_text = " ".join(scenes_text)
    tts_path = temp_dir / "narration.mp3"
    words = generate_tts_with_timestamps(full_text, tts_path)
    print(f"  {len(words)} words")

    TITLE, END = 2.0, 2.0
    video_dur = total_dur + TITLE + END
    bg = np.full((H, W, 3), 248, dtype=np.uint8)

    # Title card
    title_img = Image.new("RGB", (W, H), (252, 250, 245))
    tdraw = ImageDraw.Draw(title_img)
    tf = _get_font(48)
    lines = ["HOW PIRATES", "REALLY LIVED"]
    y = H//2 - 60
    for line in lines:
        tb = tdraw.textbbox((0,0), line, font=tf)
        tdraw.text(((W-(tb[2]-tb[0]))//2, y), line, font=tf, fill=(40,35,30))
        y += 70
    title_arr = np.array(title_img)

    print(f"\n[2/3] Rendering {total_dur}s of animation...")
    def make_frame(t):
        if t < TITLE:
            p = t/TITLE
            a = int(255 * p*p*(3-2*p))
            if a < 255:
                return ((bg.astype(np.float32)*(255-a)+title_arr.astype(np.float32)*a)/255).astype(np.uint8)
            return title_arr
        t_rel = t - TITLE
        if t_rel >= total_dur:
            return bg
        for start_s, end_s, fn in SCENE_MAP:
            if start_s <= t_rel < end_s:
                return fn(t_rel - start_s, end_s - start_s)
        return bg

    clip = VideoClip(make_frame, duration=video_dur)
    audio = AudioFileClip(str(tts_path))
    if video_dur > audio.duration + TITLE:
        s = AudioFileClip(str(tts_path)).with_duration(video_dur-audio.duration-TITLE).with_volume_scaled(0)
        audio = concatenate_audioclips([audio, s])
    music_paths = list(config.MUSIC_DIR.glob("*.mp3"))
    if music_paths:
        m = AudioFileClip(str(random.choice(music_paths))).with_duration(video_dur).with_volume_scaled(0.04)
        audio = CompositeAudioClip([audio, m])

    end_card = subscribe_end_frame(np.full((H,W,3), 240, dtype=np.uint8), END)
    end_card = end_card.with_start(total_dur+TITLE)
    final = CompositeVideoClip([clip, end_card], size=config.SHORTS_SIZE).with_audio(audio)

    print(f"\n[3/3] Writing video...")
    t0 = time.time()
    final.write_videofile(str(output_path), fps=FPS, codec="libx264", audio_codec="aac",
                          threads=4, preset="medium", ffmpeg_params=["-movflags", "+faststart", "-crf", "18"], logger=None)
    final.close()
    print(f"\n  Done in {time.time()-t0:.0f}s: {output_path} ({os.path.getsize(output_path):,} bytes)")

def subscribe_end_frame(arr, dur):
    try:
        from src.engagement import subscribe_end_card
        return subscribe_end_card(arr, dur)
    except:
        from moviepy import ImageClip
        return ImageClip(arr, duration=dur)

if __name__ == "__main__":
    out = config.OUTPUT_DIR / "how_pirates_really_lived_cinematic.mp4"
    build_video(out)
