"""Hand-drawn sketch illustration engine — draws beautiful artistic scenes with
wobble lines, watercolor fills, pencil texture, and smart composition from prompts."""

import math, random, io
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
from typing import Callable

WOBBLE = 2.0
LINEW = 3

def _rng(seed: int = 0) -> random.Random:
    return random.Random(seed)

def _noise(x: float, y: float, rng: random.Random) -> float:
    return (rng.random() - 0.5) * 2

def wobble_path(draw: ImageDraw.ImageDraw, points: list[tuple[float,float]], wobble: float = WOBBLE, color=(0,0,0), width: int = LINEW, close: bool = False, fill=None):
    if len(points) < 2:
        return
    if fill:
        fill_pts = []
        for p in points:
            fx = p[0] + _noise(p[0], p[1], _rng(int(p[0]*7+p[1]*13))) * wobble
            fy = p[1] + _noise(p[1], p[0], _rng(int(p[0]*11+p[1]*5))) * wobble
            fill_pts.append((fx, fy))
        if close and len(fill_pts) > 2:
            draw.polygon(fill_pts, fill=fill, outline=None)
    segs = max(abs(points[-1][0]-points[0][0])//5, abs(points[-1][1]-points[0][1])//5, 8)
    for _ in range(1):
        pts = []
        for i, p in enumerate(points):
            wob = wobble * (0.8 + _noise(p[0], p[1], _rng(int(p[0]*3+p[1]*7))) * 0.4)
            px = p[0] + _noise(p[0], p[1], _rng(int(p[0]*5+p[1]*11))) * wob
            py = p[1] + _noise(p[1], p[0], _rng(int(p[1]*7+p[0]*13))) * wob
            pts.append((px, py))
        if close:
            pts.append(pts[0])
        for i in range(len(pts)-1):
            steps = max(int(math.hypot(pts[i+1][0]-pts[i][0], pts[i+1][1]-pts[i][1]) / 3), 2)
            for s in range(steps):
                t = s / steps
                x = pts[i][0] + (pts[i+1][0]-pts[i][0]) * t + _noise(t*10, 0, _rng(int(t*100))) * wobble * 0.5
                y = pts[i][1] + (pts[i+1][1]-pts[i][1]) * t + _noise(0, t*10, _rng(int(t*100+50))) * wobble * 0.5
                r = width * (0.8 + _noise(x, y, _rng(int(x*3+y*7))) * 0.3)
                draw.ellipse([x-r/2, y-r/2, x+r/2, y+r/2], fill=color)

def watercolor_fill(draw: ImageDraw.ImageDraw, points: list[tuple[float,float]], color, wobble: float = 6):
    if len(points) < 3:
        return
    rng = _rng(int(points[0][0]*13+points[0][1]*7))
    for _ in range(rng.randint(2, 4)):
        pts = []
        for p in points:
            fx = p[0] + rng.gauss(0, wobble)
            fy = p[1] + rng.gauss(0, wobble)
            pts.append((fx, fy))
        alpha = rng.randint(60, 120)
        draw.polygon(pts, fill=color + (alpha,) if len(color) == 3 else (*color[:3], alpha))

def draw_grid(draw: ImageDraw.ImageDraw, w: int, h: int, rng: random.Random):
    c = rng.randint(240, 245)
    for x in range(0, w, rng.randint(30, 50)):
        ox = rng.randint(-2, 2)
        draw.line([(x+ox, 0), (x+ox, h)], fill=(c, c, c), width=1)
    for y in range(0, h, rng.randint(30, 50)):
        oy = rng.randint(-2, 2)
        draw.line([(0, y+oy), (w, y+oy)], fill=(c, c, c), width=1)

def draw_textured_bg(draw: ImageDraw.ImageDraw, w: int, h: int, rng: random.Random, base_color=(245, 245, 240)):
    draw.rectangle([0, 0, w, h], fill=base_color)
    for _ in range(rng.randint(200, 500)):
        x = rng.randint(0, w)
        y = rng.randint(0, h)
        v = rng.randint(-15, 5)
        c = (base_color[0]+v, base_color[1]+v, base_color[2]+v)
        draw.point((x, y), fill=c)

def _bezier(draw, pts, wobble, color, width):
    if len(pts) < 4:
        return
    rng = _rng(int(pts[0][0]*3+pts[0][1]*7+pts[2][0]*11))
    steps = rng.randint(15, 25)
    path = []
    for i in range(steps+1):
        t = i / steps
        mt = 1 - t
        x = mt*mt*mt*pts[0][0] + 3*mt*mt*t*pts[1][0] + 3*mt*t*t*pts[2][0] + t*t*t*pts[3][0]
        y = mt*mt*mt*pts[0][1] + 3*mt*mt*t*pts[1][1] + 3*mt*t*t*pts[2][1] + t*t*t*pts[3][1]
        x += rng.gauss(0, wobble)
        y += rng.gauss(0, wobble)
        path.append((x, y))
    for i in range(len(path)-1):
        w2 = width * (0.7 + rng.random() * 0.6)
        draw.line([path[i], path[i+1]], fill=color, width=int(max(1, w2)))

def draw_pencil_shading(draw: ImageDraw.ImageDraw, cx: float, cy: float, radius: float, color, density: int = 30):
    rng = _rng(int(cx*5+cy*13))
    for _ in range(density):
        angle = rng.random() * math.pi * 2
        dist = rng.random() * radius
        x = cx + math.cos(angle) * dist
        y = cy + math.sin(angle) * dist
        dx = math.cos(angle + math.pi/4) * rng.randint(3, 8)
        dy = math.sin(angle + math.pi/4) * rng.randint(3, 8)
        alpha = rng.randint(40, 100)
        draw.line([(x, y), (x+dx, y+dy)], fill=color + (alpha,), width=1)

def draw_circle_rough(draw, cx, cy, r, color, fill=None, width=LINEW, wobble=WOBBLE):
    rng = _rng(int(cx*7+cy*11+r*13))
    pts = []
    steps = max(int(r * 0.8), 12)
    for i in range(steps+1):
        a = (i / steps) * math.pi * 2
        rr = r + rng.gauss(0, wobble)
        x = cx + math.cos(a) * rr + rng.gauss(0, wobble*0.5)
        y = cy + math.sin(a) * rr + rng.gauss(0, wobble*0.5)
        pts.append((x, y))
    if fill:
        wobble_path(draw, pts, wobble, color=(0,0,0,0), width=width, close=True, fill=fill)
    wobble_path(draw, pts, wobble*0.5, color=color, width=width, close=True)

def draw_rect_rough(draw, x, y, w, h, color, fill=None, width=LINEW, wobble=WOBBLE):
    rng = _rng(int(x*3+y*5+w*7))
    pts = []
    corners = [(x, y), (x+w, y), (x+w, y+h), (x, y+h), (x, y)]
    for i, (cx, cy) in enumerate(corners):
        pts.append((cx + rng.gauss(0, wobble), cy + rng.gauss(0, wobble)))
    if fill:
        wobble_path(draw, pts, wobble, fill=fill, width=0)
    wobble_path(draw, pts, wobble*0.5, color=color, width=width)

def draw_face(draw, cx, cy, size, rng):
    s = size
    draw_circle_rough(draw, cx, cy, s, (30, 25, 20), fill=(255, 220, 180), width=2, wobble=1.5)
    ey = cy - s * 0.1
    for ex in (cx - s*0.3, cx + s*0.3):
        draw_circle_rough(draw, ex, ey, s*0.12, (30, 25, 20), fill=(255, 255, 255), width=1)
        draw_circle_rough(draw, ex, ey, s*0.06, (30, 25, 20), fill=(30, 25, 20), width=0)
    
    mouth_y = cy + s * 0.25
    mw = s * 0.25
    wobble_path(draw, [(cx-mw, mouth_y), (cx-mw*0.3, mouth_y+s*0.12), (cx+mw*0.3, mouth_y+s*0.12), (cx+mw, mouth_y)], wobble=1, color=(180, 120, 100), width=2)
    if rng.random() > 0.5:
        nose_y = cy + s * 0.05
        wobble_path(draw, [(cx, cy-s*0.05), (cx-s*0.08, nose_y), (cx+s*0.08, nose_y), (cx, cy-s*0.05)], wobble=0.8, color=(200, 160, 130), width=1)

def draw_human(draw, cx, cy, scale, rng, color=(40, 35, 30), skin=(255, 220, 180)):
    s = scale
    head_r = 16 * s
    body_h = 40 * s
    arm_l = 30 * s
    leg_l = 32 * s
    
    draw_face(draw, cx, cy, head_r, rng)
    
    neck_y = cy + head_r * 0.8
    hip_y = neck_y + body_h
    wobble_path(draw, [(cx, neck_y), (cx, hip_y)], wobble=1.5, color=color, width=int(3*s))

    shoulder_w = 12 * s
    wobble_path(draw, [(cx-shoulder_w, neck_y+body_h*0.2), (cx+shoulder_w, neck_y+body_h*0.2)], wobble=1, color=color, width=int(2.5*s))
    
    la = rng.randint(20, 40)
    wobble_path(draw, [(cx-shoulder_w, neck_y+body_h*0.2), (cx-shoulder_w-arm_l*0.5, neck_y+body_h*0.2+arm_l*0.7), (cx-shoulder_w-arm_l*0.3, neck_y+body_h*0.2+arm_l)], wobble=2, color=color, width=int(2.5*s))
    wobble_path(draw, [(cx+shoulder_w, neck_y+body_h*0.2), (cx+shoulder_w+arm_l*0.5, neck_y+body_h*0.2+arm_l*0.7), (cx+shoulder_w+arm_l*0.3, neck_y+body_h*0.2+arm_l)], wobble=2, color=color, width=int(2.5*s))
    
    spread = rng.randint(8, 15) * s
    wobble_path(draw, [(cx, hip_y), (cx-spread, hip_y+leg_l)], wobble=2, color=color, width=int(3*s))
    wobble_path(draw, [(cx, hip_y), (cx+spread, hip_y+leg_l)], wobble=2, color=color, width=int(3*s))

    shirt_c = (rng.randint(60, 180), rng.randint(60, 180), rng.randint(60, 200))
    wobble_path(draw, [(cx-shoulder_w-2, neck_y+3), (cx-shoulder_w-2, hip_y), (cx+shoulder_w+2, hip_y), (cx+shoulder_w+2, neck_y+3)], wobble=1.5, color=shirt_c, width=int(2*s), fill=(*shirt_c, 80))

def draw_tree(draw, cx, cy, size, rng):
    s = size
    trunk_h = 40 * s
    trunk_w = 6 * s
    trunk_c = (rng.randint(50, 80), rng.randint(35, 55), rng.randint(15, 30))
    wobble_path(draw, [(cx-trunk_w, cy), (cx-trunk_w, cy-trunk_h), (cx+trunk_w, cy-trunk_h), (cx+trunk_w, cy)], wobble=2, color=trunk_c, width=int(2*s), fill=(*trunk_c, 60))
    
    crown_r = 30 * s
    crown_c = (rng.randint(20, 50), rng.randint(60, 110), rng.randint(20, 50))
    for i in range(rng.randint(2, 4)):
        ox = rng.randint(-15, 15) * s
        oy = rng.randint(-10, 5) * s
        cr = crown_r * (0.6 + rng.random() * 0.4)
        draw_circle_rough(draw, cx+ox, cy-trunk_h+oy, cr, crown_c, fill=(*crown_c, 60), width=2)

def draw_cloud(draw, cx, cy, size, rng):
    s = size
    c = (250, 250, 250)
    for _ in range(rng.randint(3, 6)):
        ox = rng.randint(-20, 20) * s
        oy = rng.randint(-10, 5) * s
        r = rng.randint(20, 40) * s
        draw_circle_rough(draw, cx+ox, cy+oy*0.5, r, (200, 200, 200), fill=(*c, rng.randint(60, 100)), width=1)

def draw_mountains(draw, w, h, rng):
    num = rng.randint(2, 4)
    for i in range(num):
        mx = w * (0.2 + 0.6 * i / max(num-1, 1))
        mh = rng.randint(100, 200)
        mw = rng.randint(100, 200)
        c = (rng.randint(80, 120), rng.randint(90, 140), rng.randint(130, 170))
        pts = [(mx-mw, h), (mx, h-mh), (mx+mw, h)]
        wobble_path(draw, pts, wobble=3, color=(60, 60, 80), width=3, fill=(*c, 80))
    
    for i in range(rng.randint(1, 2)):
        sx = w * (0.2 + 0.6 * rng.random())
        sh = rng.randint(60, 120)
        sw = rng.randint(40, 80)
        pts = [(sx-sw, h), (sx, h-sh), (sx+sw, h)]
        wobble_path(draw, pts, wobble=2, color=(220, 220, 240), fill=(255, 255, 255, 100), width=2)

def draw_house(draw, cx, cy, size, rng):
    s = size
    hw = 40 * s
    hh = 30 * s
    wall_c = (rng.randint(180, 220), rng.randint(160, 200), rng.randint(140, 180))
    wobble_path(draw, [(cx-hw, cy), (cx-hw, cy-hh), (cx+hw, cy-hh), (cx+hw, cy)], wobble=1.5, color=(60, 50, 40), width=2, fill=(*wall_c, 80))
    
    roof_h = 25 * s
    wobble_path(draw, [(cx-hw-5, cy-hh), (cx, cy-hh-roof_h), (cx+hw+5, cy-hh)], wobble=2, color=(100, 30, 20), fill=(150, 50, 40, 80), width=2)
    
    dw = 10 * s
    dh = 15 * s
    wobble_path(draw, [(cx-dw, cy-dh), (cx-dw, cy), (cx+dw, cy), (cx+dw, cy-dh)], wobble=1, color=(40, 30, 20), width=2, fill=(255, 220, 150, 60))
    
    if rng.random() > 0.3:
        wobble_path(draw, [(cx, cy-hh-roof_h*0.3), (cx, cy-hh-roof_h*0.7)], wobble=1, color=(60, 50, 40), width=2)
        wobble_path(draw, [(cx-3, cy-hh-roof_h*0.5), (cx+3, cy-hh-roof_h*0.5)], wobble=1, color=(60, 50, 40), width=2)

def draw_fire(draw, cx, cy, size, rng):
    s = size
    for i in range(rng.randint(3, 6)):
        ox = rng.randint(-10, 10) * s
        fh = rng.randint(20, 40) * s
        fw = rng.randint(10, 20) * s
        c = (rng.randint(200, 255), rng.randint(50, 150), 0)
        pts = [(cx+ox-fw, cy), (cx+ox, cy-fh), (cx+ox+fw, cy)]
        wobble_path(draw, pts, wobble=3, color=c, fill=(*c, rng.randint(40, 80)), width=2)
    for i in range(rng.randint(2, 4)):
        ox = rng.randint(-8, 8) * s
        fh = rng.randint(10, 25) * s
        fw = rng.randint(5, 12) * s
        pts = [(cx+ox-fw, cy), (cx+ox, cy-fh*0.7), (cx+ox+fw, cy)]
        wobble_path(draw, pts, wobble=2, color=(255, 200, 50), fill=(255, 200, 50, rng.randint(40, 70)), width=1)

def draw_stars(draw, w, h, rng, count=30):
    for _ in range(count):
        x = rng.randint(0, w)
        y = rng.randint(0, int(h*0.6))
        r = rng.uniform(1, 3)
        b = rng.randint(180, 255)
        draw_circle_rough(draw, x, y, r, (b, b, b), fill=(b, b, b, rng.randint(80, 150)), width=1)

def draw_moon(draw, cx, cy, r, rng):
    draw_circle_rough(draw, cx, cy, r, (220, 215, 190), fill=(240, 235, 210, 80), width=2)
    draw_circle_rough(draw, cx+5, cy-3, r*0.85, (20, 15, 40), fill=(20, 15, 40, 150), width=0)

def draw_sun(draw, cx, cy, r, rng):
    for i in range(rng.randint(8, 12)):
        a = i / rng.randint(8, 12) * math.pi * 2
        ray_len = r * (1.3 + rng.random() * 0.4)
        wobble_path(draw, [(cx+math.cos(a)*r, cy+math.sin(a)*r), (cx+math.cos(a)*ray_len, cy+math.sin(a)*ray_len)], wobble=1, color=(255, 200, 50), width=2)
    draw_circle_rough(draw, cx, cy, r, (255, 200, 50), fill=(255, 220, 80, 100), width=2)

def draw_water(draw, x, y, w, h, rng):
    for _ in range(rng.randint(5, 15)):
        wx = rng.randint(int(x), int(x+w))
        wy = rng.randint(int(y), int(y+h))
        wl = rng.randint(10, 30)
        alpha = rng.randint(60, 150)
        c = (rng.randint(150, 200), rng.randint(180, 220), rng.randint(230, 255))
        pts = [(wx, wy), (wx+wl, wy-2), (wx+wl*2, wy)]
        wobble_path(draw, pts, wobble=1, color=c + (alpha,), width=1)

def draw_grass(draw, x, y, w, h, rng, density=20):
    for _ in range(density):
        gx = rng.randint(int(x), int(x+w))
        gy = rng.randint(int(y), int(y+h))
        gh = rng.randint(5, 15)
        gc = (rng.randint(20, 80), rng.randint(60, 140), rng.randint(15, 40))
        wobble_path(draw, [(gx, gy), (gx+rng.randint(-3, 3), gy-gh)], wobble=1, color=gc, width=1)

def draw_flowers(draw, x, y, w, h, rng, count=5):
    for _ in range(count):
        fx = rng.randint(int(x), int(x+w))
        fy = rng.randint(int(y), int(y+h))
        fc = (rng.randint(150, 255), rng.randint(50, 200), rng.randint(100, 255))
        wobble_path(draw, [(fx, fy), (fx, fy-rng.randint(8, 15))], wobble=1, color=(30, 100, 30), width=1)
        for a in range(0, 360, 60):
            rad = math.radians(a)
            px = fx + math.cos(rad) * 4
            py = fy - rng.randint(8, 15) + math.sin(rad) * 4
            draw_circle_rough(draw, px, py, 3, fc, fill=(*fc, 80), width=1)
        draw_circle_rough(draw, fx, fy-rng.randint(8, 15), 2, (255, 200, 50), fill=(255, 200, 50, 100), width=0)

def draw_ground(draw, w, h, sky_line, rng, is_water=False, is_snow=False, is_desert=False):
    if is_water:
        c = (rng.randint(30, 80), rng.randint(80, 160), rng.randint(180, 230))
        draw.rectangle([0, sky_line, w, h], fill=c)
        draw_water(draw, 0, sky_line, w, h-sky_line, rng)
    elif is_snow:
        draw.rectangle([0, sky_line, w, h], fill=(240, 245, 250))
    elif is_desert:
        c = (rng.randint(190, 220), rng.randint(170, 200), rng.randint(120, 150))
        draw.rectangle([0, sky_line, w, h], fill=c)
    else:
        c = (rng.randint(40, 80), rng.randint(100, 160), rng.randint(20, 50))
        draw.rectangle([0, sky_line, w, h], fill=c)
        draw_grass(draw, 0, sky_line, w, h-sky_line, rng)
        draw_flowers(draw, 0, sky_line, w, h-sky_line, rng)

def draw_sky(draw, w, sky_line, rng, is_night=False, is_sunset=False):
    if is_night:
        for y in range(sky_line):
            t = y / sky_line
            r = int(5 + 15 * t)
            g = int(2 + 10 * t)
            b = int(20 + 40 * t)
            draw.line([(0, y), (w, y)], fill=(r, g, b))
        draw_stars(draw, w, sky_line, rng)
        if rng.random() > 0.5:
            draw_moon(draw, rng.randint(w//4, 3*w//4), rng.randint(40, sky_line//2), rng.randint(20, 35), rng)
    elif is_sunset:
        for y in range(sky_line):
            t = y / sky_line
            r = int(60 + 195 * t)
            g = int(30 + 150 * t)
            b = int(60 + 80 * (1-t))
            draw.line([(0, y), (w, y)], fill=(r, g, b))
        draw_sun(draw, rng.randint(w//3, 2*w//3), int(sky_line*0.6), rng.randint(30, 45), rng)
    else:
        for y in range(sky_line):
            t = y / sky_line
            r = int(80 + 140 * t)
            g = int(130 + 100 * t)
            b = int(200 + 50 * (1-t))
            draw.line([(0, y), (w, y)], fill=(r, g, b))
        for _ in range(rng.randint(2, 4)):
            draw_cloud(draw, rng.randint(50, w-50), rng.randint(5, sky_line//2), rng.uniform(0.5, 1), rng)

def draw_dog(draw, cx, cy, size, rng):
    s = size
    body_c = (rng.randint(120, 170), rng.randint(70, 110), rng.randint(30, 50))
    body_w, body_h = 30*s, 15*s
    wobble_path(draw, [(cx-body_w, cy-body_h), (cx-body_w, cy), (cx+body_w, cy), (cx+body_w, cy-body_h)], wobble=2, color=body_c, fill=(*body_c, 80), width=2)
    head_r = 10*s
    draw_face(draw, cx+body_w+head_r*0.7, cy-body_h*0.7, head_r, rng)
    for ex in (cx-body_w+3, cx+body_w-3):
        wobble_path(draw, [(ex, cy), (ex-3, cy+12*s), (ex+3, cy+12*s)], wobble=2, color=body_c, width=2)
    wobble_path(draw, [(cx+body_w+head_r*0.7+head_r*0.5, cy-body_h*0.7), (cx+body_w+head_r*0.7+head_r*0.8, cy-body_h*0.5)], wobble=1, color=body_c, width=2)
    wobble_path(draw, [(cx, cy-body_h-5*s), (cx-5, cy-body_h-10*s), (cx+5, cy-body_h-10*s)], wobble=2, color=body_c, width=2)

def draw_wolf(draw, cx, cy, size, rng):
    s = size
    body_c = (rng.randint(80, 120), rng.randint(80, 120), rng.randint(80, 120))
    body_w, body_h = 35*s, 14*s
    wobble_path(draw, [(cx-body_w, cy-body_h), (cx-body_w, cy), (cx+body_w, cy), (cx+body_w, cy-body_h)], wobble=2, color=body_c, fill=(*body_c, 80), width=2)
    head_r = 11*s
    draw_face(draw, cx+body_w+head_r*0.7, cy-body_h*0.7, head_r, rng)
    wobble_path(draw, [(cx+body_w+head_r*0.7+head_r*0.5, cy-body_h*0.7), (cx+body_w+head_r*0.7+head_r*0.9, cy-body_h*0.4)], wobble=1, color=body_c, width=2)
    for ex in (cx-body_w+3, cx+body_w-3):
        wobble_path(draw, [(ex, cy), (ex-4, cy+14*s), (ex+4, cy+14*s)], wobble=2, color=body_c, width=2)
    wobble_path(draw, [(cx, cy-body_h-6*s), (cx-6, cy-body_h-12*s), (cx+6, cy-body_h-12*s)], wobble=2, color=body_c, width=2)
    tail_pts = [(cx-body_w-3, cy-body_h*0.5)]
    for i in range(5):
        tail_pts.append((cx-body_w-3-i*5*s, cy-body_h*0.5-i*3*s))
    wobble_path(draw, tail_pts, wobble=2, color=body_c, width=2)

def draw_globe(draw, cx, cy, size, rng):
    s = size
    r = 40*s
    draw_circle_rough(draw, cx, cy, r, (60, 80, 140), fill=(80, 120, 200, 60), width=2)
    for a in range(0, 360, 30):
        rad = math.radians(a)
        ex = cx + math.cos(rad) * r
        ey = cy + math.sin(rad) * r
        wobble_path(draw, [(cx, cy), (ex, ey)], wobble=1, color=(60, 80, 140, 80), width=1)
    for a in (0, 180):
        rad = math.radians(a)
        wobble_path(draw, [(cx+math.cos(rad)*r*0.5, cy-math.sin(rad)*r), (cx+math.cos(rad)*r*0.5, cy+math.sin(rad)*r)], wobble=1, color=(60, 120, 80, 80), width=1)
    stand_w, stand_h = 8*s, 15*s
    draw_rect_rough(draw, cx-stand_w, cy+r, stand_w*2, stand_h, (60, 50, 40), fill=(80, 70, 60, 80))
    wobble_path(draw, [(cx-stand_w*3, cy+r+stand_h), (cx+stand_w*3, cy+r+stand_h)], wobble=1, color=(60, 50, 40), width=3)

def draw_bones(draw, cx, cy, size, rng):
    s = size
    wobble_path(draw, [(cx, cy-8*s), (cx, cy+8*s)], wobble=1.5, color=(240, 235, 220), width=int(5*s))
    draw_circle_rough(draw, cx, cy-8*s, 5*s, (240, 235, 220), fill=(250, 245, 230, 80), width=2)
    draw_circle_rough(draw, cx, cy+8*s, 5*s, (240, 235, 220), fill=(250, 245, 230, 80), width=2)

def draw_campfire(draw, cx, cy, size, rng):
    s = size
    for _ in range(rng.randint(5, 8)):
        angle = rng.random() * math.pi * 2
        dist = rng.randint(10, 20) * s
        lx = cx + math.cos(angle) * dist
        ly = cy + math.sin(angle) * dist
        wobble_path(draw, [(lx, ly), (lx+rng.randint(-3, 3), ly+rng.randint(-8, -3))], wobble=2, color=(rng.randint(40, 80), rng.randint(30, 50), rng.randint(10, 20)), width=2)
    draw_fire(draw, cx, cy-5*s, s, rng)
    for _ in range(rng.randint(3, 6)):
        wobble_path(draw, [(cx+rng.randint(-15, 15)*s, cy), (cx+rng.randint(-15, 15)*s, cy+rng.randint(5, 10)*s)], wobble=1, color=(100, 100, 100), width=1)

def draw_caveman(draw, cx, cy, scale, rng):
    s = scale
    head_r = 16 * s
    draw_face(draw, cx, cy, head_r, rng)
    body_h = 35 * s
    hip_y = cy + head_r * 0.8 + body_h
    wobble_path(draw, [(cx, cy+head_r*0.8), (cx, hip_y)], wobble=2, color=(40, 35, 30), width=int(3*s))
    shoulder_w = 12 * s
    wobble_path(draw, [(cx-shoulder_w, cy+head_r*0.8+body_h*0.2), (cx+shoulder_w, cy+head_r*0.8+body_h*0.2)], wobble=1.5, color=(40, 35, 30), width=int(2.5*s))
    wobble_path(draw, [(cx-shoulder_w, cy+head_r*0.8+body_h*0.2), (cx-shoulder_w-20*s, cy+head_r*0.8+body_h*0.8)], wobble=3, color=(40, 35, 30), width=int(2.5*s))
    wobble_path(draw, [(cx+shoulder_w, cy+head_r*0.8+body_h*0.2), (cx+shoulder_w+15*s, cy+head_r*0.8+body_h*0.7)], wobble=3, color=(40, 35, 30), width=int(2.5*s))
    spread = rng.randint(10, 15) * s
    wobble_path(draw, [(cx, hip_y), (cx-spread, hip_y+30*s)], wobble=2, color=(40, 35, 30), width=int(3*s))
    wobble_path(draw, [(cx, hip_y), (cx+spread, hip_y+30*s)], wobble=2, color=(40, 35, 30), width=int(3*s))
    fc = (rng.randint(40, 70), rng.randint(30, 50), rng.randint(15, 25))
    wobble_path(draw, [(cx-shoulder_w-2, cy+head_r*0.8+2), (cx-shoulder_w-2, hip_y), (cx+shoulder_w+2, hip_y), (cx+shoulder_w+2, cy+head_r*0.8+2)], wobble=2, color=fc, fill=(*fc, 80), width=2)

def draw_dream_bubble(draw, cx, cy, size, rng):
    s = size
    r = 30 * s
    draw_circle_rough(draw, cx, cy, r, (200, 200, 220), fill=(255, 255, 255, 60), width=2)
    for i in range(rng.randint(2, 4)):
        bx = cx + math.cos(i*1.5) * (r + 5*s + i*8*s)
        by = cy + math.sin(i*1.5) * (r + 5*s + i*8*s)
        br = 4*s - i*s
        if br > 1:
            draw_circle_rough(draw, bx, by, br, (200, 200, 220), fill=(255, 255, 255, 40), width=1)
    wobble_path(draw, [(cx-r*0.5, cy+r*0.8), (cx-r*0.8, cy+r*1.3)], wobble=1, color=(200, 200, 220), width=2)

def draw_x_mark(draw, cx, cy, size, rng):
    s = size
    l = 15 * s
    c = (200, 30, 30)
    wobble_path(draw, [(cx-l, cy-l), (cx+l, cy+l)], wobble=1.5, color=c, width=int(4*s))
    wobble_path(draw, [(cx+l, cy-l), (cx-l, cy+l)], wobble=1.5, color=c, width=int(4*s))

def draw_notepad(draw, cx, cy, size, rng):
    s = size
    w, h = 50*s, 60*s
    draw_rect_rough(draw, cx-w/2, cy-h/2, w, h, (60, 50, 40), fill=(250, 245, 235, 80), width=2)
    for i in range(3):
        ly = cy - h/2 + 15*s + i*15*s
        wobble_path(draw, [(cx-w/2+8*s, ly), (cx+w/2-8*s, ly)], wobble=1, color=(200, 190, 180), width=1)
    wobble_path(draw, [(cx-w/2+10*s, cy-h/2+10*s), (cx+w/2-10*s, cy-h/2+10*s)], wobble=1, color=(100, 100, 100), width=1)

def draw_sign(draw, cx, cy, size, rng):
    s = size
    w, h = 60*s, 40*s
    draw_rect_rough(draw, cx-w/2, cy-h/2, w, h, (60, 50, 40), fill=(255, 220, 180, 80), width=2)
    wobble_path(draw, [(cx-w/4, cy), (cx+w/4, cy)], wobble=1, color=(100, 80, 60), width=2)

def draw_evolution(draw, cx, cy, size, rng):
    s = size
    stages = 4
    for i in range(stages):
        x = cx - (stages-1)*20*s/2 + i*20*s
        progress = i / (stages-1)
        body_c = (int(80+140*progress), int(80-40*progress), int(80-50*progress))
        br = 6*s + progress*4*s
        draw_circle_rough(draw, x, cy, br, body_c, fill=(*body_c, 80), width=2)
        if i > 0:
            wobble_path(draw, [(x-10*s, cy), (x-4*s, cy-8*s), (x+2*s, cy-6*s), (x+6*s, cy)], wobble=2, color=(200, 100, 50), width=2)
    wobble_path(draw, [(cx-(stages-1)*10*s+8*s, cy-12*s), (cx+(stages-1)*10*s-8*s, cy-12*s)], wobble=1, color=(200, 180, 220), width=3)

def draw_heart(draw, cx, cy, size, rng):
    s = size
    r = 12*s
    c = (rng.randint(200, 255), rng.randint(30, 80), rng.randint(50, 100))
    pts = []
    for a in range(0, 360, 5):
        rad = math.radians(a)
        hx = cx + r * math.sin(rad) * math.sin(rad) * math.cos(rad)
        hy = cy - r * abs(math.sin(rad)) * math.sin(rad)
        pts.append((hx, hy))
    wobble_path(draw, pts, wobble=1, color=c, fill=(*c, 80), width=2)

def draw_wolf_to_dog_timeline(draw, cx, cy, size, rng):
    s = size
    stages = 4
    for i in range(stages):
        x = cx - (stages-1)*25*s/2 + i*25*s
        progress = i / (stages-1)
        body_c = (int(100-30*progress), int(100-20*progress), int(100-50*progress))
        body_w, body_h = 20*s*(0.7+progress*0.3), 10*s
        wobble_path(draw, [(x-body_w, cy-body_h), (x-body_w, cy), (x+body_w, cy), (x+body_w, cy-body_h)], wobble=2, color=body_c, fill=(*body_c, 80), width=2)
        head_r = 7*s
        draw_circle_rough(draw, x+body_w+head_r*0.7, cy-body_h*0.7, head_r, body_c, fill=(*body_c, 80), width=1)
        if progress > 0.5:
            wobble_path(draw, [(x, cy-body_h-4*s), (x-3, cy-body_h-8*s), (x+3, cy-body_h-8*s)], wobble=2, color=body_c, width=1)
        if i > 0:
            wobble_path(draw, [(x-12*s, cy-3*s), (x-18*s, cy-6*s), (x-22*s, cy-3*s)], wobble=2, color=(150, 100, 50), width=2)


SCENE_ELEMENTS: dict[str, list[Callable]] = {
    "caveman": [draw_caveman],
    "cave_man": [draw_caveman],
    "human": [draw_human],
    "person": [draw_human],
    "man": [draw_human],
    "woman": [draw_human],
    "dog": [draw_dog],
    "wolf": [draw_wolf],
    "tree": [draw_tree],
    "fire": [draw_campfire],
    "campfire": [draw_campfire],
    "house": [draw_house],
    "cave": [],
    "moon": [lambda d,cx,cy,s,r: draw_moon(d, cx, cy, r.randint(20, 35), r)],
    "star": [lambda d,cx,cy,s,r: draw_circle_rough(d, cx, cy, 3, (255,255,200), fill=(255,255,200,100))],
    "star": None,
    "mountain": [],
    "water": [],
    "bone": [draw_bones],
    "bones": [draw_bones],
    "xmark": [draw_x_mark],
    "notepad": [draw_notepad],
    "scroll": [draw_notepad],
    "globe": [draw_globe],
    "dream": [draw_dream_bubble],
    "bubble": [draw_dream_bubble],
    "heart": [draw_heart],
    "sign": [draw_sign],
    "evolution": [draw_evolution],
    "timeline": [draw_wolf_to_dog_timeline],
}

SCENE_COLORS: dict[str, tuple] = {
    "night": (10, 8, 30),
    "dark": (10, 8, 30),
    "moon": (10, 8, 30),
    "space": (5, 3, 20),
    "fire": (180, 60, 20),
    "campfire": (180, 60, 20),
    "warm": (200, 100, 40),
    "sun": (200, 150, 60),
    "forest": (20, 60, 30),
    "nature": (30, 70, 40),
    "mountain": (50, 70, 90),
    "water": (30, 80, 150),
    "ocean": (20, 60, 130),
    "city": (40, 40, 70),
    "urban": (45, 45, 80),
    "snow": (200, 210, 230),
    "ice": (190, 200, 220),
    "desert": (180, 160, 100),
    "cave": (30, 25, 20),
    "home": (100, 80, 60),
    "happy": (200, 180, 100),
}


def generate_sketch_scene(prompt: str, w: int, h: int) -> Image.Image:
    """Main entry — generates a hand-drawn sketch scene from a text prompt."""
    p = prompt.lower()
    rng = _rng(hash(prompt) & 0x7FFFFFFF)

    is_night = any(w in p for w in ("night", "dark", "moon", "midnight", "space", "star"))
    is_sunset = any(w in p for w in ("sunset", "sunrise", "dusk", "dawn", "evening", "golden"))
    is_water = any(w in p for w in ("water", "ocean", "sea", "lake", "river", "beach"))
    is_snow = any(w in p for w in ("snow", "ice", "winter", "arctic"))
    is_desert = any(w in p for w in ("desert", "sand", "dune"))
    is_city = any(w in p for w in ("city", "urban", "town", "building"))
    is_forest = any(w in p for w in ("forest", "woods", "tree", "jungle"))
    is_cave = any(w in p for w in ("cave", "cavern", "underground"))

    paper = Image.new("RGBA", (w, h), (255, 255, 250, 255))
    draw = ImageDraw.Draw(paper, "RGBA")

    draw_textured_bg(draw, w, h, rng, base_color=(250, 248, 242))

    sky_line = int(h * (0.45 + rng.random() * 0.15))
    ground_h = h - sky_line

    if not is_cave:
        draw_sky(draw, w, sky_line, rng, is_night, is_sunset)
        draw_ground(draw, w, h, sky_line, rng, is_water, is_snow, is_desert)
    else:
        draw.rectangle([0, 0, w, h], fill=(25, 22, 18))
        for _ in range(rng.randint(30, 80)):
            sx = rng.randint(0, w)
            sy = rng.randint(0, h)
            b = rng.randint(30, 80)
            draw.point((sx, sy), fill=(b, b-5, b-10))

    if is_night and not is_cave:
        draw_stars(draw, w, sky_line, rng, count=rng.randint(40, 80))
        if "moon" in p or rng.random() > 0.6:
            draw_moon(draw, rng.randint(w//4, 3*w//4), rng.randint(40, int(sky_line*0.4)), rng.randint(20, 35), rng)

    if is_forest:
        for _ in range(rng.randint(3, 6)):
            draw_tree(draw, rng.randint(30, w-30), rng.randint(sky_line+10, h-10), rng.uniform(0.5, 1.2), rng)

    if is_city:
        for _ in range(rng.randint(8, 15)):
            bx = rng.randint(10, w-10)
            bh = rng.randint(40, 140)
            bw = rng.randint(20, 40)
            bc = (rng.randint(30, 60), rng.randint(30, 60), rng.randint(40, 70))
            draw_rect_rough(draw, bx-bw//2, sky_line-bh, bw, bh, bc, fill=(*bc, 60), width=1)
            for _ in range(rng.randint(1, 5)):
                wy = rng.randint(sky_line-bh+5, sky_line-5)
                wc = (rng.randint(200, 255), rng.randint(200, 255), rng.randint(100, 200))
                draw_rect_rough(draw, bx-3, wy-4, 6, 8, wc, fill=(*wc, rng.randint(40, 80)), width=1)

    if "mountain" in p:
        draw_mountains(draw, w, h, rng)

    placed_elements: set = set()
    for word in sorted(p.split(), key=lambda x: len(x), reverse=True):
        if word in SCENE_ELEMENTS and word not in placed_elements:
            funcs = SCENE_ELEMENTS[word]
            if funcs:
                for func in funcs:
                    ex = rng.randint(w//5, 4*w//5)
                    ey = rng.randint(sky_line+20, h-20)
                    func(draw, ex, ey, rng.uniform(0.6, 1.2), rng)
                placed_elements.add(word)

    paper = paper.filter(ImageFilter.SMOOTH_MORE)
    paper = paper.filter(ImageFilter.UnsharpMask(radius=0.5, percent=50, threshold=2))

    grain = Image.effect_noise((w, h), 8).convert("L")
    grain = grain.point(lambda x: 0 if x < 128 else 255, "1")
    grain_overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(grain_overlay, "RGBA")
    for _ in range(500):
        gx = rng.randint(0, w-1)
        gy = rng.randint(0, h-1)
        gdraw.point((gx, gy), fill=(0, 0, 0, rng.randint(5, 15)))
    paper = Image.alpha_composite(paper, grain_overlay)

    return paper.convert("RGB")
