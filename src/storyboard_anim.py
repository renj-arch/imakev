"""Multi-scene storyboard animator — frame-by-frame animated scenes from prompts.
All drawing via PIL (no API, no GPU). Characters, backgrounds, and actions are
matched via keyword detection and rendered with smooth sin/cos motion."""

import math
import re
import random
from dataclasses import dataclass, field
from typing import Callable
from PIL import Image, ImageDraw
import numpy as np

# ─── Constants ───────────────────────────────────────────────────
W = 720
H = 1280
FPS = 12
SKY_RATIO = 0.55


# ─── Data Classes ────────────────────────────────────────────────
@dataclass
class Char:
    name: str
    x: float = 0.5
    y: float = 0.6
    end_x: float | None = None
    end_y: float | None = None
    action: str = "idle"
    facing: int = 1
    scale: float = 1.0


@dataclass
class Scene:
    background: str = "sky"
    characters: list[Char] = field(default_factory=list)
    duration: float = 5.0
    extra: dict = field(default_factory=dict)


# ─── Helpers ─────────────────────────────────────────────────────
def _clr(c: tuple[int, ...], alpha: int = 255) -> tuple[int, ...]:
    if len(c) == 3:
        return (c[0], c[1], c[2], alpha)
    return c


def _rng(seed: int) -> random.Random:
    return random.Random(seed & 0xFFFFFFFF)


# ─── Background Drawing ─────────────────────────────────────────
# Each bg function receives (draw, w, h, t, extra) where t = frame_idx / fps (scene time)

def _draw_gradient(draw, y0, y1, top_color, bot_color, w):
    for y in range(y0, y1):
        r = (y - y0) / max(y1 - y0 - 1, 1)
        rc = tuple(int(a + (b - a) * r) for a, b in zip(top_color, bot_color))
        draw.line([(0, y), (w, y)], fill=rc)


def _draw_clouds(draw, w, h, t, sky_h, count=3):
    for ci in range(count):
        cx = int(w * ((ci * 0.37 + t * 0.015) % 1.0))
        cy = int(sky_h * (0.12 + ci * 0.13))
        cr = 25 + ci * 8
        for dx, dy in [(0, 0), (cr // 2, cr // 4), (-cr // 3, cr // 3), (cr // 3, -cr // 5)]:
            draw.ellipse(
                [cx + dx - cr, cy + dy - cr // 2, cx + dx + cr, cy + dy + cr // 2],
                fill=(255, 255, 255, 160),
            )


def _bg_sky(draw, w, h, t, extra=None):
    sky_h = int(h * SKY_RATIO)
    _draw_gradient(draw, 0, sky_h, (60, 100, 200), (180, 200, 255), w)
    _draw_clouds(draw, w, h, t, sky_h)
    sx = int(w * (0.3 + 0.4 * math.sin(t * 0.3)))
    sy = int(sky_h * 0.55)
    draw.ellipse([sx - 35, sy - 35, sx + 35, sy + 35], fill=(255, 220, 50))
    _draw_gradient(draw, sky_h, h, (60, 120, 40), (20, 50, 15), w)


def _bg_jungle(draw, w, h, t, extra=None):
    sky_h = int(h * 0.45)
    _draw_gradient(draw, 0, sky_h, (40, 80, 140), (100, 160, 200), w)
    _draw_clouds(draw, w, h, t, sky_h, count=2)
    for ti in range(5):
        tx = int(w * (0.05 + 0.22 * ti) + int(6 * math.sin(t * 0.3 + ti)))
        ty = sky_h + 10
        th = 60 + ti * 8
        tw = 6 + ti % 3
        draw.rectangle([tx - tw, ty - th, tx + tw, ty], fill=(50, 35, 15))
        cr = 28 + ti * 5
        draw.ellipse(
            [tx - cr, ty - th - cr + 5, tx + cr, ty - th + cr // 2 + 5],
            fill=(20 + ti * 10, 70 + ti * 15, 20),
        )
    _draw_gradient(draw, sky_h, h, (40, 100, 30), (15, 45, 12), w)
    for _ in range(20):
        gx = random.randint(0, w)
        gy = sky_h + random.randint(0, h - sky_h)
        gh = random.randint(8, 22)
        gc = (random.randint(25, 80), random.randint(70, 160), random.randint(15, 45))
        draw.line([(gx, gy), (gx + random.randint(-3, 3), gy - gh)], fill=gc, width=1)


def _bg_water(draw, w, h, t, extra=None):
    sky_h = int(h * 0.40)
    _draw_gradient(draw, 0, sky_h, (30, 60, 140), (100, 150, 200), w)
    for wi in range(2):
        cx = int(w * (0.2 + 0.6 * wi))
        cy = int(sky_h * (0.15 + wi * 0.2))
        cr = 20 + wi * 8
        draw.ellipse([cx - cr, cy - cr // 2, cx + cr, cy + cr // 2], fill=(255, 255, 255, 140))
    for y in range(sky_h, h):
        ratio = (y - sky_h) / (h - sky_h)
        r = int(20 + 10 * ratio)
        g = int(60 + 40 * ratio)
        b = int(140 + 80 * ratio)
        wave = int(math.sin((y - sky_h) * 0.12 + t * 2.0) * 10)
        draw.line([(0, y), (w, y)], fill=(r, g + wave, b + wave))
    for wi in range(8):
        wx = int(w * ((wi * 0.15 + t * 0.04 + wi * 0.3) % 1.0))
        wy = sky_h + int((h - sky_h) * (0.1 + 0.8 * (wi / 8)))
        wlen = 25 + int(12 * math.sin(t * 0.5 + wi))
        draw.line([(wx, wy), (wx + wlen, wy)], fill=(180, 220, 255, 50), width=1)


def _bg_river(draw, w, h, t, extra=None):
    sky_h = int(h * 0.38)
    _draw_gradient(draw, 0, sky_h, (50, 80, 160), (140, 180, 230), w)
    _draw_clouds(draw, w, h, t, sky_h, count=2)
    _draw_gradient(draw, sky_h, h, (40, 80, 130), (15, 40, 90), w)
    for y in range(sky_h, h):
        ratio = (y - sky_h) / (h - sky_h)
        wave = int(math.sin((y - sky_h) * 0.15 + t * 2.5) * 12)
        r = int(25 - 15 * ratio + wave // 3)
        g = int(60 + 20 * ratio + wave // 3)
        b = int(130 + 60 * ratio + wave // 2)
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    for wi in range(6):
        wx = int(w * ((wi * 0.2 + t * 0.03) % 1.0))
        wy = sky_h + 30 + int((h - sky_h - 60) * (wi / 6))
        draw.line([(wx, wy), (wx + 20 + int(10 * math.sin(t + wi)), wy)], fill=(180, 220, 255, 60), width=1)


def _bg_desert(draw, w, h, t, extra=None):
    sky_h = int(h * 0.50)
    _draw_gradient(draw, 0, sky_h, (200, 150, 80), (255, 200, 150), w)
    sx = int(w * 0.5 + int(20 * math.sin(t * 0.2)))
    sy = int(sky_h * 0.5)
    draw.ellipse([sx - 45, sy - 45, sx + 45, sy + 45], fill=(255, 230, 80))
    _draw_gradient(draw, sky_h, h, (220, 190, 120), (160, 130, 70), w)
    for ci in range(2):
        cx = int(w * (0.2 + 0.6 * ci))
        cy = sky_h + 30 + int(8 * math.sin(t + ci))
        draw.rectangle([cx - 4, cy - 40, cx + 4, cy], fill=(80, 65, 30))
        draw.line([(cx - 20, cy - 35), (cx, cy - 55), (cx + 20, cy - 35)], fill=(50, 120, 30), width=3)


def _bg_city(draw, w, h, t, extra=None):
    sky_h = int(h * 0.45)
    is_night = extra and extra.get("night")
    if is_night:
        _draw_gradient(draw, 0, sky_h, (5, 2, 20), (20, 10, 50), w)
        for s in range(30):
            sx = int((math.sin(s * 7.3 + t * 10) * 0.5 + 0.5) * w)
            sy = int((math.cos(s * 5.1 + t * 8) * 0.5 + 0.5) * sky_h * 0.7)
            sz = (s % 3) + 1
            draw.ellipse([sx - sz, sy - sz, sx + sz, sy + sz], fill=(200, 200, 180))
    else:
        _draw_gradient(draw, 0, sky_h, (60, 100, 200), (180, 200, 255), w)
    for bi in range(8):
        bx = int(w * (0.06 + 0.12 * bi))
        bh = random.randint(40, 130)
        bw = 14 + bi % 3 * 4
        bc = (random.randint(25, 50), random.randint(25, 55), random.randint(35, 70))
        draw.rectangle([bx - bw // 2, sky_h - bh, bx + bw // 2, sky_h], fill=bc)
        if is_night:
            for _ in range(3):
                wy = sky_h - random.randint(10, bh - 10)
                draw.rectangle([bx - 3, wy - 3, bx + 3, wy], fill=(255, 220, 50))
    _draw_gradient(draw, sky_h, h, (50, 50, 55), (25, 25, 30), w)
    for _ in range(3):
        lx = random.randint(10, w - 10)
        draw.line([(lx, sky_h), (lx, h)], fill=(60, 60, 65), width=1)


def _bg_cave(draw, w, h, t, extra=None):
    _draw_gradient(draw, 0, h, (15, 10, 8), (40, 30, 25), w)
    for si in range(5):
        sx = int(w * (0.1 + 0.2 * si))
        sy = int(h * (0.05 + 0.02 * si))
        sl = 15 + si * 5
        draw.polygon([(sx, 0), (sx - 3, sy), (sx + 3, sy)], fill=(50, 40, 35))
    glow_x = int(w * (0.3 + 0.4 * math.sin(t * 0.2)))
    glow_y = int(h * 0.6)
    for ri in range(5, 0, -1):
        a = 10 + ri * 4
        draw.ellipse(
            [glow_x - ri * 15, glow_y - ri * 15, glow_x + ri * 15, glow_y + ri * 15],
            fill=(255, 200, 50, a),
        )


def _bg_snow(draw, w, h, t, extra=None):
    sky_h = int(h * 0.50)
    _draw_gradient(draw, 0, sky_h, (180, 190, 210), (220, 230, 250), w)
    _draw_clouds(draw, w, h, t, sky_h, count=3)
    _draw_gradient(draw, sky_h, h, (220, 230, 240), (240, 245, 255), w)
    for si in range(40):
        sx = int((math.sin(si * 11.3 + t * 2.0) * 0.5 + 0.5) * w)
        sy = int((math.cos(si * 7.1 + t * 1.5) * 0.5 + 0.5) * h)
        draw.ellipse([sx - 2, sy - 2, sx + 2, sy + 2], fill=(200, 220, 255, 180))


def _bg_sunset(draw, w, h, t, extra=None):
    sky_h = int(h * 0.50)
    _draw_gradient(draw, 0, sky_h, (120, 40, 60), (255, 180, 80), w)
    sx = int(w * 0.5 + int(15 * math.sin(t * 0.2)))
    sy = int(sky_h * 0.65)
    draw.ellipse([sx - 40, sy - 40, sx + 40, sy + 40], fill=(255, 220, 50))
    for ri in range(3, 7):
        a = 70 - ri * 10
        draw.ellipse(
            [sx - 40 * ri, sy - 40 * ri, sx + 40 * ri, sy + 40 * ri],
            fill=(255, 200, 50, max(0, a)),
        )
    _draw_gradient(draw, sky_h, h, (50, 90, 35), (15, 40, 12), w)
    for ti in range(4):
        tx = int(w * (0.1 + 0.25 * ti))
        ty = sky_h + 5
        th = 40 + ti * 5
        draw.rectangle([tx - 4, ty - th, tx + 4, ty], fill=(30, 25, 10))
        cr = 20 + ti * 6
        draw.ellipse([tx - cr, ty - th - cr + 5, tx + cr, ty - th + cr // 2 + 5], fill=(15, 40, 15))


def _bg_space(draw, w, h, t, extra=None):
    _draw_gradient(draw, 0, h, (3, 1, 15), (8, 4, 30), w)
    for s in range(60):
        sx = int((math.sin(s * 7.3 + t * 5) * 0.5 + 0.5) * w)
        sy = int((math.cos(s * 5.1 + t * 4) * 0.5 + 0.5) * h)
        sz = (s % 3) + 1
        bright = 160 + int(math.sin(t * 3 + s) * 60)
        draw.ellipse([sx - sz, sy - sz, sx + sz, sy + sz], fill=(bright, bright, int(bright * 0.8)))
    px = int(w * (0.4 + 0.2 * math.sin(t * 0.15)))
    py = int(h * (0.3 + 0.1 * math.sin(t * 0.12 + 1)))
    draw.ellipse([px - 15, py - 15, px + 15, py + 15], fill=(200, 160, 80))
    draw.ellipse([px - 12, py - 12, px + 12, py + 12], fill=(255, 200, 100, 60))


def _bg_underwater(draw, w, h, t, extra=None):
    _draw_gradient(draw, 0, h, (10, 40, 100), (30, 80, 160), w)
    for y in range(h):
        ratio = y / h
        wave = int(math.sin(y * 0.08 + t * 0.5) * 8)
        r = max(0, min(255, 10 + int(20 * ratio) + wave))
        g = max(0, min(255, 40 + int(40 * ratio) + wave))
        b = max(0, min(255, 100 + int(60 * ratio) + wave * 2))
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    for si in range(15):
        sx = int((math.sin(si * 13.7 + t * 1.2) * 0.5 + 0.5) * w)
        sy = int((math.cos(si * 9.3 + t * 0.8) * 0.5 + 0.5) * h)
        sr = 2 + int(4 * math.sin(t + si))
        sa = 80 + int(50 * math.sin(t * 2 + si * 3))
        draw.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=(180, 220, 255, sa))
    for bi in range(3):
        bx = int(w * (0.15 + 0.35 * bi) + int(5 * math.sin(t * 0.2 + bi)))
        by = int(h * (0.7 + 0.1 * bi))
        draw.rectangle([bx - 2, by, bx + 2, h], fill=(40, 80, 50))
        draw.polygon([(bx - 12, by), (bx, by - 15), (bx + 12, by)], fill=(30, 100, 40))
        draw.polygon([(bx - 8, by - 8), (bx, by - 20), (bx + 8, by - 8)], fill=(20, 80, 30))


def _bg_volcano(draw, w, h, t, extra=None):
    _draw_gradient(draw, 0, int(h * 0.4), (40, 20, 10), (80, 40, 20), w)
    for s in range(15):
        sx = int((math.sin(s * 11.3 + t * 1.5) * 0.5 + 0.5) * w)
        sy = int((math.cos(s * 7.1 + t * 1.2) * 0.5 + 0.5) * h * 0.35)
        draw.ellipse([sx - 1, sy - 1, sx + 1, sy + 1], fill=(200, 100, 50))
    mw = int(w * 0.35)
    mx = w // 2
    my = int(h * 0.3)
    draw.polygon([(mx - mw, h), (mx - mw // 3, my), (mx + mw // 3, my), (mx + mw, h)], fill=(60, 30, 15))
    draw.polygon([(mx - mw // 4, my), (mx, my - 30), (mx + mw // 4, my)], fill=(80, 35, 15))
    glow = int(40 * math.sin(t * 2) + 50)
    draw.ellipse([mx - 12, my - 35, mx + 12, my + 5], fill=(255, glow, 20, 180))
    for li in range(8):
        lx = mx + int(20 * math.sin(t * 3 + li * 2))
        ly = my - 30 - int(20 * li * math.sin(t * 1.5 + li))
        draw.ellipse([lx - 3, ly - 3, lx + 3, ly + 3], fill=(255, 150 + int(50 * math.sin(t + li)), 20))
    _draw_gradient(draw, int(h * 0.4), h, (30, 15, 10), (15, 8, 5), w)


def _bg_aurora(draw, w, h, t, extra=None):
    _draw_gradient(draw, 0, int(h * 0.5), (5, 5, 20), (15, 10, 40), w)
    for s in range(50):
        sx = int((math.sin(s * 7.3 + t * 3) * 0.5 + 0.5) * w)
        sy = int((math.cos(s * 5.1 + t * 2) * 0.5 + 0.5) * h * 0.4)
        sz = (s % 2) + 1
        bright = 180 + int(math.sin(t * 2 + s) * 70)
        draw.ellipse([sx - sz, sy - sz, sx + sz, sy + sz], fill=(bright, bright, bright))
    for ai in range(3):
        offset = ai * 0.4
        for y in range(int(h * 0.05), int(h * 0.35)):
            x_shift = int(80 * math.sin(y * 0.02 + t * 0.8 + offset))
            alpha = int(60 * (1 - abs(y - h * 0.2) / (h * 0.15)))
            g = int(100 + 100 * math.sin(y * 0.03 + t + offset))
            r = int(50 * math.sin(y * 0.02 + t * 0.5 + offset))
            b = int(200 + 50 * math.sin(y * 0.02 + t * 0.7 + offset))
            cx = w // 2 + x_shift
            draw.line([(cx - 40, y), (cx + 40, y)], fill=(max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)), max(0, min(255, alpha))))
    _draw_gradient(draw, int(h * 0.5), h, (30, 40, 50), (10, 15, 25), w)


def _bg_magical_forest(draw, w, h, t, extra=None):
    sky_h = int(h * 0.40)
    _draw_gradient(draw, 0, sky_h, (30, 15, 50), (60, 30, 80), w)
    for s in range(30):
        sx = int((math.sin(s * 9.3 + t * 2) * 0.5 + 0.5) * w)
        sy = int((math.cos(s * 7.1 + t * 1.5) * 0.5 + 0.5) * sky_h)
        draw.ellipse([sx - 1, sy - 1, sx + 1, sy + 1], fill=(200, 180, 255))
    for ti in range(6):
        tx = int(w * (0.08 + 0.16 * ti) + int(4 * math.sin(t * 0.2 + ti)))
        ty = sky_h + 5
        th = 80 + ti * 6
        tw = 4 + ti % 3
        draw.rectangle([tx - tw, ty - th, tx + tw, ty], fill=(30, 20, 15))
        cr = 30 + ti * 6
        glow = int(30 * math.sin(t * 0.5 + ti) + 40)
        draw.ellipse([tx - cr, ty - th - cr + 10, tx + cr, ty - th + 10], fill=(glow, 50 + glow, 80))
    for gi in range(12):
        gx = int(w * (0.05 + 0.08 * gi) + int(3 * math.sin(t * 0.3 + gi)))
        gy = sky_h + int(5 * math.sin(t * 0.2 + gi))
        draw.line([(gx, gy), (gx + int(2 * math.sin(t + gi)), gy + 15 + int(5 * math.sin(t * 0.4 + gi)))], fill=(40, 120, 30), width=1)
    _draw_gradient(draw, sky_h, h, (20, 60, 30), (10, 30, 15), w)
    for pi in range(8):
        px = int(w * ((pi * 0.15 + t * 0.02) % 1.0))
        py = sky_h + int(math.sin(pi * 2 + t * 1.5) * 20) + 30
        size = 2 + int(3 * math.sin(t * 0.7 + pi))
        colors = [(255, 200, 50), (200, 100, 255), (100, 200, 255), (255, 100, 100)]
        c = colors[pi % len(colors)]
        draw.ellipse([px - size, py - size, px + size, py + size], fill=c + (180,))


_BACKGROUNDS: dict[str, Callable] = {
    "sky": _bg_sky,
    "jungle": _bg_jungle,
    "water": _bg_water,
    "river": _bg_river,
    "desert": _bg_desert,
    "city": _bg_city,
    "cave": _bg_cave,
    "snow": _bg_snow,
    "sunset": _bg_sunset,
    "space": _bg_space,
    "underwater": _bg_underwater,
    "volcano": _bg_volcano,
    "aurora": _bg_aurora,
    "magical_forest": _bg_magical_forest,
}


# ─── Character Drawing ──────────────────────────────────────────
def _draw_monkey(draw, x, y, s, fi, action, facing):
    body = (160, 110, 60)
    face = (220, 195, 155)
    dark = (100, 65, 30)
    white = (255, 255, 255)
    black = (30, 20, 15)
    tail_wave = 12 * math.sin(fi * 0.2)
    tx = x - 14 * s * facing
    draw.line(
        [(x - 10 * s * facing, y + 2 * s),
         (x - 18 * s * facing + tail_wave * facing, y - 6 * s),
         (x - 14 * s * facing + tail_wave * 2 * facing, y - 20 * s)],
        fill=body, width=max(2, int(3 * s)),
    )
    draw.ellipse([x - 13 * s, y - 4 * s, x + 13 * s, y + 13 * s], fill=body)
    draw.ellipse([x - 9 * s, y - 18 * s, x + 9 * s, y], fill=face)
    ear_r = 5 * s
    draw.ellipse([x - 14 * s, y - 14 * s, x - 10 * s, y - 10 * s], fill=body)
    draw.ellipse([x + 10 * s, y - 14 * s, x + 14 * s, y - 10 * s], fill=body)
    if action == "shocked":
        eye_r = 4 * s
        draw.ellipse([x - 6 * s - eye_r, y - 14 * s - eye_r, x - 6 * s + eye_r, y - 14 * s + eye_r], fill=white)
        draw.ellipse([x + 2 * s - eye_r, y - 14 * s - eye_r, x + 2 * s + eye_r, y - 14 * s + eye_r], fill=white)
        draw.ellipse([x - 6 * s - eye_r * 0.4, y - 14 * s - eye_r * 0.4, x - 6 * s + eye_r * 0.4, y - 14 * s + eye_r * 0.4], fill=black)
        draw.ellipse([x + 2 * s - eye_r * 0.4, y - 14 * s - eye_r * 0.4, x + 2 * s + eye_r * 0.4, y - 14 * s + eye_r * 0.4], fill=black)
        draw.ellipse([x - 4 * s, y - 7 * s, x + 4 * s, y - 3 * s], fill=(40, 30, 20))
        draw.line([(x - 12 * s * facing, y - 6 * s), (x - 20 * s * facing, y - 22 * s)], fill=body, width=max(2, int(3 * s)))
        draw.line([(x + 12 * s * facing, y - 6 * s), (x + 20 * s * facing, y - 22 * s)], fill=body, width=max(2, int(3 * s)))
    elif action == "shrug":
        eye_r = 3 * s
        draw.ellipse([x - 5 * s - eye_r, y - 13 * s - eye_r, x - 5 * s + eye_r, y - 13 * s + eye_r], fill=white)
        draw.ellipse([x + 3 * s - eye_r, y - 13 * s - eye_r, x + 3 * s + eye_r, y - 13 * s + eye_r], fill=white)
        draw.ellipse([x - 5 * s - eye_r * 0.5, y - 13 * s, x - 5 * s + eye_r * 0.5, y - 13 * s + eye_r * 0.6], fill=black)
        draw.ellipse([x + 3 * s - eye_r * 0.5, y - 13 * s, x + 3 * s + eye_r * 0.5, y - 13 * s + eye_r * 0.6], fill=black)
        draw.arc([x - 4 * s, y - 6 * s, x + 4 * s, y - 3 * s], 0, 180, fill=dark, width=1)
        draw.line([(x - 12 * s * facing, y - 2 * s), (x - 22 * s * facing, y - 16 * s)], fill=body, width=max(2, int(3 * s)))
        draw.line([(x + 12 * s * facing, y - 2 * s), (x + 22 * s * facing, y - 16 * s)], fill=body, width=max(2, int(3 * s)))
        draw.ellipse([x - 24 * s * facing - 4 * s, y - 18 * s, x - 24 * s * facing + 4 * s, y - 12 * s], fill=face)
        draw.ellipse([x + 20 * s * facing - 4 * s, y - 18 * s, x + 20 * s * facing + 4 * s, y - 12 * s], fill=face)
    elif action == "riding":
        eye_r = 3 * s
        draw.ellipse([x - 5 * s - eye_r, y - 13 * s - eye_r, x - 5 * s + eye_r, y - 13 * s + eye_r], fill=white)
        draw.ellipse([x + 3 * s - eye_r, y - 13 * s - eye_r, x + 3 * s + eye_r, y - 13 * s + eye_r], fill=white)
        draw.ellipse([x - 5 * s - eye_r * 0.5, y - 13 * s, x - 5 * s + eye_r * 0.5, y - 13 * s + eye_r * 0.6], fill=black)
        draw.ellipse([x + 3 * s - eye_r * 0.5, y - 13 * s, x + 3 * s + eye_r * 0.5, y - 13 * s + eye_r * 0.6], fill=black)
        mouth_y = y - 7 * s + 2 * math.sin(fi * 0.2)
        draw.arc([x - 3 * s, mouth_y - 1 * s, x + 3 * s, mouth_y + 1 * s], 0, 180, fill=dark, width=1)
        draw.line([(x + 10 * s * facing, y - 3 * s), (x + 18 * s * facing, y - 2 * s)], fill=body, width=max(2, int(3 * s)))
        leg_angle = 8 * math.sin(fi * 0.3)
        draw.line([(x - 5 * s * facing, y + 8 * s), (x - 8 * s * facing + leg_angle, y + 16 * s)], fill=body, width=max(2, int(3 * s)))
        draw.line([(x + 5 * s * facing, y + 8 * s), (x + 8 * s * facing - leg_angle, y + 16 * s)], fill=body, width=max(2, int(3 * s)))
    else:
        eye_r = 3 * s
        draw.ellipse([x - 5 * s - eye_r, y - 13 * s - eye_r, x - 5 * s + eye_r, y - 13 * s + eye_r], fill=white)
        draw.ellipse([x + 3 * s - eye_r, y - 13 * s - eye_r, x + 3 * s + eye_r, y - 13 * s + eye_r], fill=white)
        draw.ellipse([x - 5 * s - eye_r * 0.5, y - 13 * s, x - 5 * s + eye_r * 0.5, y - 13 * s + eye_r * 0.6], fill=black)
        draw.ellipse([x + 3 * s - eye_r * 0.5, y - 13 * s, x + 3 * s + eye_r * 0.5, y - 13 * s + eye_r * 0.6], fill=black)
        draw.arc([x - 3 * s, y - 7 * s, x + 3 * s, y - 4 * s], 0, 180, fill=dark, width=1)
        arm_sway = 3 * math.sin(fi * 0.15)
        draw.line([(x - 10 * s * facing, y - 3 * s), (x - 16 * s * facing + arm_sway, y - 8 * s + arm_sway)], fill=body, width=max(2, int(3 * s)))
        draw.line([(x + 10 * s * facing, y - 3 * s), (x + 16 * s * facing + arm_sway, y - 8 * s - arm_sway)], fill=body, width=max(2, int(3 * s)))
        draw.line([(x - 4 * s, y + 8 * s), (x - 6 * s, y + 16 * s)], fill=body, width=max(2, int(3 * s)))
        draw.line([(x + 4 * s, y + 8 * s), (x + 6 * s, y + 16 * s)], fill=body, width=max(2, int(3 * s)))


def _draw_bicycle(draw, x, y, s, fi, action, facing):
    wheel_r = 14 * s
    pedal_angle = fi * 0.3
    spacing = 28 * s * facing
    draw.ellipse([x - spacing - wheel_r, y - wheel_r, x - spacing + wheel_r, y + wheel_r], outline=(80, 60, 50), width=2)
    draw.ellipse([x + spacing - wheel_r, y - wheel_r, x + spacing + wheel_r, y + wheel_r], outline=(80, 60, 50), width=2)
    for wx in [-spacing, spacing]:
        draw.ellipse([x + wx - 1, y - 1, x + wx + 1, y + 1], fill=(120, 100, 80))
        for sp in range(4):
            sa = math.pi * sp / 4 + pedal_angle
            sx = int(wheel_r * 0.7 * math.cos(sa))
            sy = int(wheel_r * 0.7 * math.sin(sa))
            draw.line([(x + wx, y), (x + wx + sx, y + sy)], fill=(120, 100, 80), width=1)
    top_x = x + spacing * 0.5 * facing
    top_y = y - wheel_r - 8 * s
    draw.line([(x - spacing, y), (top_x, top_y)], fill=(100, 70, 50), width=max(2, int(2 * s)))
    draw.line([(x + spacing, y), (top_x, top_y)], fill=(100, 70, 50), width=max(2, int(2 * s)))
    draw.line([(x - spacing, y), (x + spacing, y)], fill=(100, 70, 50), width=1)
    seat_x = top_x + 2 * s * facing
    draw.ellipse([seat_x - 6 * s, top_y - 2 * s, seat_x + 6 * s, top_y + 2 * s], fill=(60, 40, 30))
    handle_x = top_x + 8 * s * facing
    draw.line([(top_x, top_y), (handle_x, top_y - 4 * s)], fill=(100, 70, 50), width=max(2, int(2 * s)))
    draw.line([(handle_x - 4 * s, top_y - 6 * s), (handle_x + 4 * s, top_y - 4 * s)], fill=(100, 70, 50), width=max(2, int(2 * s)))
    pedal_y = y + wheel_r + 4 * s
    ped_x = int(10 * s * math.cos(pedal_angle))
    ped_y = int(4 * s * math.sin(pedal_angle))
    draw.line([(x - spacing * 0.3, y), (x - spacing * 0.3 + ped_x, ped_y)], fill=(80, 60, 40), width=2)
    draw.line([(x + spacing * 0.3, y), (x + spacing * 0.3 - ped_x, -ped_y)], fill=(80, 60, 40), width=2)


def _draw_parrot(draw, x, y, s, fi, action, facing):
    body_c = (60, 180, 60)
    wing_c = (200, 60, 40)
    head_c = (220, 200, 50)
    beak_c = (240, 180, 30)
    draw.ellipse([x - 8 * s, y - 5 * s, x + 8 * s, y + 5 * s], fill=body_c)
    draw.ellipse([x - 6 * s, y - 11 * s, x + 6 * s, y - 3 * s], fill=head_c)
    eye_r = 2 * s
    draw.ellipse([x + 2 * s - eye_r, y - 10 * s - eye_r, x + 2 * s + eye_r, y - 10 * s + eye_r], fill=(255, 255, 255))
    draw.ellipse([x + 2 * s - eye_r * 0.5, y - 10 * s - eye_r * 0.5, x + 2 * s + eye_r * 0.5, y - 10 * s + eye_r * 0.5], fill=(20, 20, 20))
    draw.polygon([(x + 6 * s * facing, y - 10 * s), (x + 14 * s * facing, y - 8 * s), (x + 6 * s * facing, y - 6 * s)], fill=beak_c)
    wing_flap = 10 * math.sin(fi * 0.4)
    draw.polygon([(x - 2 * s, y - 4 * s), (x - 6 * s, y - 8 * s - wing_flap), (x + 6 * s, y - 4 * s)], fill=wing_c)
    draw.polygon([(x + 2 * s, y - 4 * s), (x + 8 * s, y - 8 * s - wing_flap), (x + 6 * s, y - 4 * s)], fill=(40, 150, 40))
    tail_sway = 5 * math.sin(fi * 0.2)
    draw.polygon([(x - 4 * s, y + 4 * s), (x - 8 * s + tail_sway * facing, y + 14 * s), (x + 4 * s, y + 4 * s)], fill=body_c)


def _draw_crocodile(draw, x, y, s, fi, action, facing):
    body_c = (50, 130, 40)
    belly_c = (100, 180, 80)
    mouth_open = 0
    if action == "snapping":
        mouth_open = abs(math.sin(fi * 0.3)) * 8 * s
    elif action == "swimming":
        mouth_open = 0
    draw.ellipse([x - 25 * s, y - 5 * s, x + 25 * s, y + 5 * s], fill=body_c)
    for bi in range(6):
        bx = x + (-20 + bi * 8) * s
        by = y - 6 * s - 2 * math.sin(bi * 0.5 + fi * 0.1)
        draw.ellipse([bx - 3 * s, by - 2 * s, bx + 3 * s, by + 2 * s], fill=(40, 110, 30))
    draw.ellipse([x - 18 * s, y - 6 * s, x + 18 * s, y + 6 * s], fill=belly_c)
    snout_x = x + 22 * s * facing
    draw.ellipse([snout_x - 5 * s, y - 5 * s - mouth_open * 0.3, snout_x + 12 * s, y + 5 * s], fill=body_c)
    eye_r = 3 * s
    draw.ellipse([x + 8 * s * facing - eye_r, y - 7 * s - eye_r, x + 8 * s * facing + eye_r, y - 7 * s + eye_r], fill=(255, 220, 50))
    draw.ellipse([x + 8 * s * facing - eye_r * 0.5, y - 7 * s - eye_r * 0.5, x + 8 * s * facing + eye_r * 0.5, y - 7 * s + eye_r * 0.5], fill=(10, 10, 10))
    if mouth_open > 1:
        jaw_y = y + 4 * s + mouth_open
        draw.ellipse([snout_x + 2 * s, y, snout_x + 12 * s, jaw_y], fill=(200, 100, 50))
        for tooth in range(4):
            tx = snout_x + 3 * s + tooth * 2.5 * s
            draw.polygon([(tx, y + 2 * s), (tx + 1.5 * s, y + 6 * s), (tx + 3 * s, y + 2 * s)], fill=(255, 255, 255))
        draw.polygon([(snout_x + 2 * s, y + 2 * s), (snout_x + 12 * s, y - 1 * s), (snout_x + 12 * s, y + 2 * s)], fill=(180, 80, 40))
    tail_wag = 8 * math.sin(fi * 0.15)
    draw.polygon(
        [(x - 22 * s, y - 2 * s), (x - 30 * s + tail_wag * facing, y - 4 * s + tail_wag), (x - 22 * s, y + 2 * s)],
        fill=body_c,
    )
    leg_off = 2 * math.sin(fi * 0.2)
    for lx in [x - 14 * s, x + 14 * s]:
        draw.rectangle([lx - 2 * s, y + 3 * s, lx + 2 * s, y + 8 * s + leg_off], fill=body_c)


def _draw_elephant(draw, x, y, s, fi, action, facing):
    body_c = (140, 140, 140)
    dark_c = (100, 100, 100)
    draw.ellipse([x - 22 * s, y - 12 * s, x + 22 * s, y + 12 * s], fill=body_c)
    draw.ellipse([x - 16 * s * facing, y - 24 * s, x + 4 * s * facing, y - 6 * s], fill=body_c)
    ear_c = (120, 120, 120)
    ear_sway = 4 * math.sin(fi * 0.15)
    draw.ellipse([x - 8 * s * facing - 12 * s + ear_sway, y - 18 * s, x - 8 * s * facing + 12 * s + ear_sway, y + 2 * s], fill=ear_c)
    eye_r = 3 * s
    draw.ellipse([x - 4 * s * facing - eye_r, y - 20 * s - eye_r, x - 4 * s * facing + eye_r, y - 20 * s + eye_r], fill=(255, 255, 255))
    draw.ellipse([x - 4 * s * facing - eye_r * 0.5, y - 20 * s - eye_r * 0.5, x - 4 * s * facing + eye_r * 0.5, y - 20 * s + eye_r * 0.5], fill=(20, 20, 20))
    if action == "slipping" or action == "spinning":
        trunk_curve = 10 * math.sin(fi * 0.5)
        draw.line(
            [(x - 12 * s * facing, y - 14 * s),
             (x - 22 * s * facing + trunk_curve, y - 8 * s + trunk_curve),
             (x - 26 * s * facing + trunk_curve * 2, y)],
            fill=body_c, width=max(2, int(4 * s)),
        )
    else:
        trunk_sway = 3 * math.sin(fi * 0.1)
        draw.line(
            [(x - 12 * s * facing, y - 14 * s),
             (x - 20 * s * facing + trunk_sway, y - 6 * s),
             (x - 24 * s * facing + trunk_sway, y + 4 * s)],
            fill=body_c, width=max(2, int(4 * s)),
        )
    if action == "spinning":
        angle = fi * 0.3
        leg_rot = 6 * math.sin(angle)
        draw.line([(x - 16 * s, y + 10 * s), (x - 16 * s + leg_rot, y + 22 * s)], fill=body_c, width=max(2, int(5 * s)))
        draw.line([(x + 16 * s, y + 10 * s), (x + 16 * s - leg_rot, y + 22 * s)], fill=body_c, width=max(2, int(5 * s)))
        draw.line([(x - 8 * s, y + 10 * s), (x - 8 * s - leg_rot, y + 22 * s)], fill=body_c, width=max(2, int(5 * s)))
        draw.line([(x + 8 * s, y + 10 * s), (x + 8 * s + leg_rot, y + 22 * s)], fill=body_c, width=max(2, int(5 * s)))
    elif action == "slipping":
        draw.line([(x - 16 * s, y + 10 * s), (x - 20 * s, y + 22 * s)], fill=body_c, width=max(2, int(5 * s)))
        draw.line([(x + 16 * s, y + 10 * s), (x + 22 * s, y + 22 * s)], fill=body_c, width=max(2, int(5 * s)))
        draw.line([(x - 8 * s, y + 10 * s), (x - 4 * s, y + 22 * s)], fill=body_c, width=max(2, int(5 * s)))
        draw.line([(x + 8 * s, y + 10 * s), (x + 4 * s, y + 22 * s)], fill=body_c, width=max(2, int(5 * s)))
    else:
        leg_off = 3 * math.sin(fi * 0.2)
        for lx in [x - 16 * s, x - 8 * s, x + 8 * s, x + 16 * s]:
            draw.line([(lx, y + 8 * s), (lx + leg_off * (1 if lx < x else -1), y + 22 * s)], fill=body_c, width=max(2, int(5 * s)))
    tail_sway = 6 * math.sin(fi * 0.12)
    draw.line([(x + 20 * s * facing, y - 4 * s), (x + 28 * s * facing + tail_sway, y - 10 * s)], fill=dark_c, width=2)


def _draw_duck(draw, x, y, s, fi, action, facing):
    body_c = (220, 190, 40)
    head_c = (30, 120, 30)
    beak_c = (255, 180, 0)
    draw.ellipse([x - 15 * s, y - 6 * s, x + 15 * s, y + 6 * s], fill=body_c)
    draw.ellipse([x + 8 * s * facing - 8 * s, y - 18 * s, x + 8 * s * facing + 8 * s, y - 4 * s], fill=head_c)
    bob = 3 * math.sin(fi * 0.25)
    draw.ellipse([x + 8 * s * facing - 8 * s, y - 18 * s + bob, x + 8 * s * facing + 8 * s, y - 4 * s + bob], fill=head_c)
    draw.polygon([(x + 14 * s * facing, y - 14 * s), (x + 24 * s * facing, y - 16 * s), (x + 14 * s * facing, y - 10 * s)], fill=beak_c)
    eye_r = 2 * s
    draw.ellipse([x + 10 * s * facing - eye_r, y - 16 * s + bob - eye_r, x + 10 * s * facing + eye_r, y - 16 * s + bob + eye_r], fill=(255, 255, 255))
    draw.ellipse([x + 10 * s * facing - eye_r * 0.5, y - 16 * s + bob - eye_r * 0.5, x + 10 * s * facing + eye_r * 0.5, y - 16 * s + bob + eye_r * 0.5], fill=(10, 10, 10))
    if action == "flying":
        wing_f = 12 * math.sin(fi * 0.4)
        draw.polygon([(x, y - 2 * s), (x - 6 * s * facing, y - 10 * s - wing_f), (x + 6 * s * facing, y)], fill=(200, 170, 30))
        draw.polygon([(x, y - 2 * s), (x + 8 * s * facing, y - 10 * s - wing_f), (x + 6 * s * facing, y)], fill=(200, 170, 30))
    if action == "swimming":
        ripple = 2 * math.sin(fi * 0.3)
        draw.ellipse([x - 10 * s, y + 4 * s + ripple, x + 10 * s, y + 6 * s + ripple], fill=(30, 80, 160, 80))


def _draw_cat(draw, x, y, s, fi, action, facing):
    c = (180, 140, 100)
    draw.ellipse([x - 14 * s, y - 6 * s, x + 14 * s, y + 6 * s], fill=c)
    draw.ellipse([x - 8 * s, y - 18 * s, x + 8 * s, y - 4 * s], fill=c)
    ear_h = 8 * s
    draw.polygon([(x - 8 * s, y - 18 * s), (x - 12 * s, y - 26 * s), (x - 4 * s, y - 20 * s)], fill=c)
    draw.polygon([(x + 8 * s, y - 18 * s), (x + 12 * s, y - 26 * s), (x + 4 * s, y - 20 * s)], fill=c)
    eye_r = 3 * s
    draw.ellipse([x - 5 * s - eye_r, y - 16 * s - eye_r, x - 5 * s + eye_r, y - 16 * s + eye_r], fill=(50, 200, 50))
    draw.ellipse([x + 3 * s - eye_r, y - 16 * s - eye_r, x + 3 * s + eye_r, y - 16 * s + eye_r], fill=(50, 200, 50))
    draw.ellipse([x - 5 * s - eye_r * 0.5, y - 16 * s - eye_r * 0.5, x - 5 * s + eye_r * 0.5, y - 16 * s + eye_r * 0.5], fill=(10, 10, 10))
    draw.ellipse([x + 3 * s - eye_r * 0.5, y - 16 * s - eye_r * 0.5, x + 3 * s + eye_r * 0.5, y - 16 * s + eye_r * 0.5], fill=(10, 10, 10))
    tail_x = x + 14 * s + int(8 * math.sin(fi * 0.15))
    tail_y = y - 2 * s + int(6 * math.cos(fi * 0.12))
    draw.line([(x + 12 * s, y - 2 * s), (tail_x + 8 * s, tail_y - 6 * s)], fill=c, width=3)


def _draw_dragon(draw, x, y, s, fi, action, facing):
    d_c = (180, 30, 20)
    wing_c = (220, 80, 40)
    draw.ellipse([x - 16 * s, y - 6 * s, x + 16 * s, y + 6 * s], fill=d_c)
    draw.ellipse([x - 10 * s, y - 20 * s, x + 10 * s, y - 4 * s], fill=d_c)
    draw.polygon([(x + 8 * s * facing, y - 20 * s), (x + 22 * s * facing, y - 26 * s), (x + 8 * s * facing, y - 12 * s)], fill=d_c)
    draw.polygon([(x - 8 * s * facing, y - 20 * s), (x - 22 * s * facing, y - 26 * s), (x - 8 * s * facing, y - 12 * s)], fill=d_c)
    eye_r = 2 * s
    draw.ellipse([x + 3 * s * facing - eye_r, y - 16 * s - eye_r, x + 3 * s * facing + eye_r, y - 16 * s + eye_r], fill=(255, 200, 50))
    draw.ellipse([x + 3 * s * facing - eye_r * 0.5, y - 16 * s - eye_r * 0.5, x + 3 * s * facing + eye_r * 0.5, y - 16 * s + eye_r * 0.5], fill=(10, 10, 10))
    fire_tip = int(6 * math.sin(fi * 0.3))
    draw.polygon([(x + 14 * s * facing, y - 2 * s), (x + 35 * s * facing + fire_tip, y + 2 * s), (x + 14 * s * facing, y + 4 * s)], fill=(255, 100, 0))
    tail_x = x - 16 * s + int(6 * math.sin(fi * 0.12))
    tail_y = y + int(4 * math.cos(fi * 0.1))
    draw.polygon([(x - 16 * s, y - 5 * s), (tail_x - 8 * s, tail_y - 10 * s), (x - 10 * s, y + 3 * s)], fill=d_c)
    wing_flap = 8 * math.sin(fi * 0.3)
    draw.polygon([(x - 4 * s, y - 5 * s), (x - 14 * s * facing, y - 18 * s - wing_flap), (x + 4 * s, y - 5 * s)], fill=wing_c)
    draw.polygon([(x + 4 * s, y - 5 * s), (x + 16 * s * facing, y - 18 * s - wing_flap), (x + 4 * s, y - 5 * s)], fill=(150, 50, 30))


def _draw_fish(draw, x, y, s, fi, action, facing):
    fc = (80 + int(40 * math.sin(fi * 0.1)), 140 + int(30 * math.sin(fi * 0.1 + 1)), 210)
    draw.ellipse([x - 10 * s, y - 5 * s, x + 10 * s, y + 5 * s], fill=fc)
    draw.polygon([(x + 8 * s * facing, y), (x + 18 * s * facing, y - 5 * s), (x + 18 * s * facing, y + 5 * s)], fill=fc)
    tail_wag = int(4 * math.sin(fi * 0.2))
    draw.polygon([(x - 10 * s * facing, y), (x - 18 * s * facing, y - 4 * s + tail_wag), (x - 18 * s * facing, y + 4 * s - tail_wag)], fill=fc)
    draw.ellipse([x + 2 * s * facing - 2 * s, y - 1 * s, x + 2 * s * facing + 1 * s, y + 1 * s], fill=(20, 20, 20))


def _draw_fox(draw, x, y, s, fi, action, facing):
    fc = (210, 100, 35)
    draw.ellipse([x - 13 * s, y - 6 * s, x + 13 * s, y + 6 * s], fill=fc)
    draw.ellipse([x - 8 * s, y - 16 * s, x + 8 * s, y - 4 * s], fill=fc)
    draw.polygon([(x - 8 * s, y - 16 * s), (x - 14 * s, y - 26 * s), (x - 2 * s, y - 18 * s)], fill=fc)
    draw.polygon([(x + 8 * s, y - 16 * s), (x + 14 * s, y - 26 * s), (x + 2 * s, y - 18 * s)], fill=fc)
    eye_r = 2 * s
    draw.ellipse([x - 4 * s - eye_r, y - 14 * s - eye_r, x - 4 * s + eye_r, y - 14 * s + eye_r], fill=(255, 255, 255))
    draw.ellipse([x + 2 * s - eye_r, y - 14 * s - eye_r, x + 2 * s + eye_r, y - 14 * s + eye_r], fill=(255, 255, 255))
    draw.ellipse([x - 4 * s - eye_r * 0.5, y - 14 * s - eye_r * 0.5, x - 4 * s + eye_r * 0.5, y - 14 * s + eye_r * 0.5], fill=(10, 10, 10))
    draw.ellipse([x + 2 * s - eye_r * 0.5, y - 14 * s - eye_r * 0.5, x + 2 * s + eye_r * 0.5, y - 14 * s + eye_r * 0.5], fill=(10, 10, 10))
    draw.polygon([(x - 4 * s, y + 2 * s), (x, y + 12 * s), (x + 4 * s, y + 2 * s)], fill=(255, 255, 255))
    tail_x = x + 12 * s + int(8 * math.sin(fi * 0.1))
    tail_y = y - 2 * s + int(5 * math.cos(fi * 0.08))
    draw.ellipse([tail_x + 2 * s, tail_y - 5 * s, tail_x + 12 * s, tail_y + 3 * s], fill=(255, 200, 180))


def _draw_rabbit(draw, x, y, s, fi, action, facing):
    body_c = (220, 210, 200)
    dark = (180, 160, 140)
    ear_h = 14 * s
    draw.ellipse([x - 10 * s, y - 5 * s, x + 10 * s, y + 5 * s], fill=body_c)
    draw.ellipse([x - 6 * s, y - 14 * s, x + 6 * s, y - 3 * s], fill=body_c)
    ear_sway = 3 * math.sin(fi * 0.2)
    draw.ellipse([x - 3 * s - 4 * s, y - 32 * s + ear_sway, x - 3 * s + 4 * s, y - 14 * s + ear_sway], fill=body_c)
    draw.ellipse([x + 3 * s - 4 * s, y - 30 * s - ear_sway, x + 3 * s + 4 * s, y - 14 * s - ear_sway], fill=body_c)
    draw.ellipse([x - 3 * s - 2 * s, y - 30 * s + ear_sway, x - 3 * s + 2 * s, y - 16 * s + ear_sway], fill=(255, 200, 220))
    draw.ellipse([x + 3 * s - 2 * s, y - 28 * s - ear_sway, x + 3 * s + 2 * s, y - 16 * s - ear_sway], fill=(255, 200, 220))
    eye_r = 2 * s
    draw.ellipse([x - 4 * s - eye_r, y - 12 * s - eye_r, x - 4 * s + eye_r, y - 12 * s + eye_r], fill=(50, 50, 50))
    draw.ellipse([x + 4 * s - eye_r, y - 12 * s - eye_r, x + 4 * s + eye_r, y - 12 * s + eye_r], fill=(50, 50, 50))
    draw.ellipse([x - 4 * s - eye_r * 0.3, y - 12 * s - eye_r * 0.3, x - 4 * s + eye_r * 0.3, y - 12 * s + eye_r * 0.3], fill=(255, 255, 255))
    draw.ellipse([x + 4 * s - eye_r * 0.3, y - 12 * s - eye_r * 0.3, x + 4 * s + eye_r * 0.3, y - 12 * s + eye_r * 0.3], fill=(255, 255, 255))
    nose_r = 1.5 * s
    draw.ellipse([x - nose_r, y - 9 * s, x + nose_r, y - 7 * s], fill=(255, 150, 180))
    hop = 4 * math.sin(fi * 0.3)
    draw.line([(x - 3 * s, y + 5 * s), (x - 4 * s, y + 12 * s + hop)], fill=body_c, width=max(2, int(2 * s)))
    draw.line([(x + 3 * s, y + 5 * s), (x + 4 * s, y + 12 * s - hop)], fill=body_c, width=max(2, int(2 * s)))
    tail_r = 4 * s
    draw.ellipse([x - 12 * s * facing - tail_r, y - 2 * s - tail_r, x - 12 * s * facing + tail_r, y - 2 * s + tail_r], fill=(255, 255, 255))


def _draw_bear(draw, x, y, s, fi, action, facing):
    body_c = (140, 100, 60)
    dark = (100, 70, 40)
    draw.ellipse([x - 18 * s, y - 10 * s, x + 18 * s, y + 10 * s], fill=body_c)
    draw.ellipse([x - 10 * s, y - 22 * s, x + 10 * s, y - 4 * s], fill=body_c)
    ear_r = 7 * s
    draw.ellipse([x - 12 * s - ear_r, y - 20 * s - ear_r, x - 12 * s + ear_r, y - 20 * s + ear_r], fill=body_c)
    draw.ellipse([x + 12 * s - ear_r, y - 20 * s - ear_r, x + 12 * s + ear_r, y - 20 * s + ear_r], fill=body_c)
    draw.ellipse([x - 12 * s - ear_r * 0.5, y - 20 * s - ear_r * 0.5, x - 12 * s + ear_r * 0.5, y - 20 * s + ear_r * 0.5], fill=dark)
    draw.ellipse([x + 12 * s - ear_r * 0.5, y - 20 * s - ear_r * 0.5, x + 12 * s + ear_r * 0.5, y - 20 * s + ear_r * 0.5], fill=dark)
    eye_r = 2.5 * s
    draw.ellipse([x - 5 * s - eye_r, y - 14 * s - eye_r, x - 5 * s + eye_r, y - 14 * s + eye_r], fill=(30, 30, 30))
    draw.ellipse([x + 5 * s - eye_r, y - 14 * s - eye_r, x + 5 * s + eye_r, y - 14 * s + eye_r], fill=(30, 30, 30))
    draw.ellipse([x - 5 * s - eye_r * 0.3, y - 14 * s - eye_r * 0.3, x - 5 * s + eye_r * 0.3, y - 14 * s + eye_r * 0.3], fill=(255, 255, 255))
    draw.ellipse([x + 5 * s - eye_r * 0.3, y - 14 * s - eye_r * 0.3, x + 5 * s + eye_r * 0.3, y - 14 * s + eye_r * 0.3], fill=(255, 255, 255))
    nose_r = 3 * s
    draw.ellipse([x - nose_r, y - 9 * s, x + nose_r, y - 6 * s], fill=dark)
    arm_sway = 3 * math.sin(fi * 0.15)
    draw.line([(x - 14 * s * facing, y - 2 * s), (x - 18 * s * facing + arm_sway, y - 8 * s + arm_sway)], fill=body_c, width=max(2, int(3 * s)))
    draw.line([(x + 14 * s * facing, y - 2 * s), (x + 18 * s * facing + arm_sway, y - 8 * s - arm_sway)], fill=body_c, width=max(2, int(3 * s)))
    draw.line([(x - 8 * s, y + 8 * s), (x - 8 * s, y + 16 * s)], fill=body_c, width=max(2, int(3 * s)))
    draw.line([(x + 8 * s, y + 8 * s), (x + 8 * s, y + 16 * s)], fill=body_c, width=max(2, int(3 * s)))
    ear_r = 4 * s
    draw.ellipse([x - 16 * s * facing - ear_r, y - 4 * s - ear_r, x - 16 * s * facing + ear_r, y - 4 * s + ear_r], fill=(100, 70, 40))


def _draw_owl(draw, x, y, s, fi, action, facing):
    body_c = (160, 130, 100)
    belly_c = (220, 210, 190)
    draw.ellipse([x - 12 * s, y - 8 * s, x + 12 * s, y + 8 * s], fill=body_c)
    draw.ellipse([x - 8 * s, y - 18 * s, x + 8 * s, y - 4 * s], fill=body_c)
    draw.ellipse([x - 5 * s, y - 6 * s, x + 5 * s, y + 4 * s], fill=belly_c)
    draw.polygon([(x - 8 * s, y - 18 * s), (x - 12 * s, y - 24 * s), (x - 4 * s, y - 14 * s)], fill=body_c)
    draw.polygon([(x + 8 * s, y - 18 * s), (x + 12 * s, y - 24 * s), (x + 4 * s, y - 14 * s)], fill=body_c)
    eye_r = 5 * s
    draw.ellipse([x - 6 * s - eye_r, y - 14 * s - eye_r, x - 6 * s + eye_r, y - 14 * s + eye_r], fill=(255, 255, 255))
    draw.ellipse([x + 6 * s - eye_r, y - 14 * s - eye_r, x + 6 * s + eye_r, y - 14 * s + eye_r], fill=(255, 255, 255))
    draw.ellipse([x - 6 * s - eye_r * 0.4, y - 14 * s - eye_r * 0.4, x - 6 * s + eye_r * 0.4, y - 14 * s + eye_r * 0.4], fill=(200, 150, 50))
    draw.ellipse([x + 6 * s - eye_r * 0.4, y - 14 * s - eye_r * 0.4, x + 6 * s + eye_r * 0.4, y - 14 * s + eye_r * 0.4], fill=(200, 150, 50))
    draw.ellipse([x - 6 * s - eye_r * 0.15, y - 14 * s - eye_r * 0.15, x - 6 * s + eye_r * 0.15, y - 14 * s + eye_r * 0.15], fill=(10, 10, 10))
    draw.ellipse([x + 6 * s - eye_r * 0.15, y - 14 * s - eye_r * 0.15, x + 6 * s + eye_r * 0.15, y - 14 * s + eye_r * 0.15], fill=(10, 10, 10))
    beak = 3 * s
    draw.polygon([(x - beak, y - 8 * s), (x, y - 5 * s), (x + beak, y - 8 * s)], fill=(255, 180, 50))
    wing_flap = 4 * math.sin(fi * 0.25)
    if action == "flying":
        draw.polygon([(x - 6 * s, y - 4 * s), (x - 14 * s, y - 12 * s - wing_flap), (x - 4 * s, y)], fill=body_c)
        draw.polygon([(x + 6 * s, y - 4 * s), (x + 14 * s, y - 12 * s - wing_flap), (x + 4 * s, y)], fill=body_c)
    draw.line([(x - 4 * s, y + 8 * s), (x - 5 * s, y + 14 * s)], fill=body_c, width=max(2, int(2 * s)))
    draw.line([(x + 4 * s, y + 8 * s), (x + 5 * s, y + 14 * s)], fill=body_c, width=max(2, int(2 * s)))


def _draw_turtle(draw, x, y, s, fi, action, facing):
    shell_c = (60, 140, 60)
    shell_p = (80, 170, 80)
    skin_c = (100, 160, 100)
    draw.ellipse([x - 16 * s, y - 6 * s, x + 16 * s, y + 8 * s], fill=shell_c)
    draw.ellipse([x - 14 * s, y - 4 * s, x + 14 * s, y + 6 * s], fill=shell_p)
    for pi in range(6):
        px = x + int(10 * s * math.cos(pi * 1.05 + 0.3))
        py = y + int(5 * s * math.sin(pi * 1.05))
        draw.ellipse([px - 2 * s, py - 1.5 * s, px + 2 * s, py + 1.5 * s], fill=(50, 120, 50))
    head_bob = 2 * math.sin(fi * 0.2)
    draw.ellipse([x + 14 * s * facing - 6 * s, y - 10 * s + head_bob, x + 14 * s * facing + 6 * s, y + 2 * s + head_bob], fill=skin_c)
    eye_r = 1.5 * s
    draw.ellipse([x + 16 * s * facing - eye_r, y - 8 * s + head_bob - eye_r, x + 16 * s * facing + eye_r, y - 8 * s + head_bob + eye_r], fill=(20, 20, 20))
    draw.line([(x - 10 * s, y + 8 * s), (x - 12 * s, y + 14 * s)], fill=skin_c, width=max(2, int(2 * s)))
    draw.line([(x + 10 * s, y + 8 * s), (x + 12 * s, y + 14 * s)], fill=skin_c, width=max(2, int(2 * s)))
    draw.line([(x - 14 * s, y + 6 * s), (x - 18 * s, y + 10 * s)], fill=skin_c, width=max(2, int(2 * s)))
    draw.line([(x + 14 * s, y + 6 * s), (x + 18 * s, y + 10 * s)], fill=skin_c, width=max(2, int(2 * s)))
    tail_wag = 3 * math.sin(fi * 0.15)
    draw.polygon([(x - 18 * s * facing, y), (x - 24 * s * facing + tail_wag, y + 2 * s), (x - 18 * s * facing, y + 4 * s)], fill=skin_c)


def _draw_penguin(draw, x, y, s, fi, action, facing):
    body_c = (40, 40, 55)
    belly_c = (240, 240, 240)
    draw.ellipse([x - 10 * s, y - 6 * s, x + 10 * s, y + 8 * s], fill=body_c)
    draw.ellipse([x - 6 * s, y - 2 * s, x + 6 * s, y + 6 * s], fill=belly_c)
    draw.ellipse([x - 7 * s, y - 16 * s, x + 7 * s, y - 4 * s], fill=body_c)
    eye_r = 2 * s
    draw.ellipse([x - 4 * s - eye_r, y - 12 * s - eye_r, x - 4 * s + eye_r, y - 12 * s + eye_r], fill=(255, 255, 255))
    draw.ellipse([x + 4 * s - eye_r, y - 12 * s - eye_r, x + 4 * s + eye_r, y - 12 * s + eye_r], fill=(255, 255, 255))
    draw.ellipse([x - 4 * s - eye_r * 0.5, y - 12 * s - eye_r * 0.5, x - 4 * s + eye_r * 0.5, y - 12 * s + eye_r * 0.5], fill=(10, 10, 10))
    draw.ellipse([x + 4 * s - eye_r * 0.5, y - 12 * s - eye_r * 0.5, x + 4 * s + eye_r * 0.5, y - 12 * s + eye_r * 0.5], fill=(10, 10, 10))
    beak = 2.5 * s
    draw.polygon([(x - beak, y - 7 * s), (x, y - 4 * s), (x + beak, y - 7 * s)], fill=(255, 180, 50))
    wing_sway = 4 * math.sin(fi * 0.2)
    draw.line([(x - 8 * s * facing, y - 4 * s), (x - 12 * s * facing + wing_sway, y + 2 * s + wing_sway)], fill=body_c, width=max(2, int(3 * s)))
    draw.line([(x + 8 * s * facing, y - 4 * s), (x + 12 * s * facing - wing_sway, y + 2 * s - wing_sway)], fill=body_c, width=max(2, int(3 * s)))
    wobble = 2 * math.sin(fi * 0.15)
    draw.line([(x - 3 * s, y + 6 * s), (x - 4 * s + wobble, y + 12 * s)], fill=(255, 180, 50), width=max(2, int(2 * s)))
    draw.line([(x + 3 * s, y + 6 * s), (x + 4 * s + wobble, y + 12 * s)], fill=(255, 180, 50), width=max(2, int(2 * s)))


_CHAR_DRAWERS: dict[str, Callable] = {
    "monkey": _draw_monkey,
    "bicycle": _draw_bicycle,
    "parrot": _draw_parrot,
    "crocodile": _draw_crocodile,
    "elephant": _draw_elephant,
    "duck": _draw_duck,
    "cat": _draw_cat,
    "dragon": _draw_dragon,
    "fish": _draw_fish,
    "fox": _draw_fox,
    "rabbit": _draw_rabbit,
    "bear": _draw_bear,
    "owl": _draw_owl,
    "turtle": _draw_turtle,
    "penguin": _draw_penguin,
}


def _draw_char(draw, name: str, x: float, y: float, scale: float, fi: int, action: str, facing: int):
    drawer = _CHAR_DRAWERS.get(name)
    if drawer:
        drawer(draw, x, y, scale, fi, action, facing)


# ─── Scene Parser ───────────────────────────────────────────────
def _has_word(text: str, word: str) -> bool:
    return bool(re.search(r'\b' + re.escape(word) + r'\b', text))


CHAR_KEYWORDS = {
    "monkey": "monkey",
    "parrot": "parrot",
    "crocodile": "crocodile", "gator": "crocodile", "croc": "crocodile",
    "elephant": "elephant",
    "duck": "duck", "swan": "duck", "goose": "duck",
    "cat": "cat", "kitten": "cat",
    "dragon": "dragon",
    "fish": "fish", "jellyfish": "fish",
    "fox": "fox",
    "rabbit": "rabbit", "bunny": "rabbit", "hare": "rabbit",
    "bear": "bear", "grizzly": "bear", "polar": "bear",
    "owl": "owl",
    "turtle": "turtle", "tortoise": "turtle",
    "penguin": "penguin",
    "bicycle": "bicycle", "bike": "bicycle", "cycle": "bicycle",
}

BG_KEYWORDS: dict[str, str] = {
    "jungle": "jungle", "forest": "jungle", "tree": "jungle", "wood": "jungle",
    "water": "water", "ocean": "water", "sea": "water", "pond": "water", "lake": "water",
    "river": "river", "stream": "river",
    "desert": "desert", "sand": "desert", "dune": "desert",
    "city": "city", "urban": "city", "street": "city", "building": "city", "neon": "city",
    "cave": "cave", "cavern": "cave", "underground": "cave",
    "snow": "snow", "ice": "snow", "winter": "snow",
    "sunset": "sunset", "sunrise": "sunset", "dusk": "sunset", "dawn": "sunset",
    "space": "space", "star": "space", "galaxy": "space", "planet": "space",
    "sky": "sky", "cloud": "sky",
    "underwater": "underwater", "coral": "underwater", "reef": "underwater",
    "volcano": "volcano", "lava": "volcano", "eruption": "volcano",
    "aurora": "aurora", "northern": "aurora", "polar": "aurora",
    "magical_forest": "magical_forest", "fairy": "magical_forest", "enchanted": "magical_forest", "glowing": "magical_forest", "mushroom": "magical_forest",
}

ACTION_KEYWORDS: dict[str, str] = {
    "fly": "flying", "flying": "flying", "flies": "flying", "flew": "flying",
    "flap": "flying", "flapping": "flying",
    "ride": "riding", "riding": "riding", "rides": "riding", "rode": "riding",
    "soar": "flying", "swoop": "flying",
    "walk": "walking", "walking": "walking", "walks": "walking",
    "run": "walking", "running": "walking", "runs": "walking",
    "swim": "swimming", "swimming": "swimming", "swims": "swimming",
    "float": "swimming", "splash": "swimming",
    "spin": "spinning", "spinning": "spinning", "spins": "spinning",
    "dizzy": "spinning", "whirl": "spinning",
    "slip": "slipping", "slipping": "slipping", "slips": "slipping",
    "fall": "slipping", "falls": "slipping", "trip": "slipping",
    "sleep": "sleeping", "sleeping": "sleeping", "sleeps": "sleeping",
    "nap": "sleeping", "doze": "sleeping", "rest": "sleeping",
    "eat": "eating", "eating": "eating", "eats": "eating",
    "chew": "eating", "munch": "eating",
    "jump": "jumping", "jumping": "jumping", "jumps": "jumping",
    "leap": "jumping", "leaps": "jumping", "hop": "jumping",
    "sit": "sitting", "sitting": "sitting", "sits": "sitting",
    "dance": "dancing", "dancing": "dancing", "dances": "dancing",
    "shock": "shocked", "shocked": "shocked", "shocks": "shocked",
    "surprise": "shocked", "gasp": "shocked", "amaze": "shocked",
    "shrug": "shrug", "shrugging": "shrug", "shrugs": "shrug",
    "snap": "snapping", "snapping": "snapping", "snaps": "snapping",
    "bite": "snapping", "chomp": "snapping",
}

RIDING_ADDITIONS = {
    "monkey": "bicycle",
}

PRONOUNS = {"he", "she", "it", "they", "his", "her", "its", "their"}


def parse_prompt_to_scenes(prompt: str, max_scenes: int = 6) -> list[Scene]:
    p_lower = prompt.lower()
    sentences = [s.strip() for s in re.split(r'[.!?]+', p_lower) if s.strip()]
    if not sentences:
        sentences = [p_lower]

    all_chars = set()
    for word, ch in CHAR_KEYWORDS.items():
        if _has_word(p_lower, word):
            all_chars.add(ch)
    default_bg = "sky"
    for word, bg in sorted(BG_KEYWORDS.items(), key=lambda x: -len(x[0])):
        if _has_word(p_lower, word):
            default_bg = bg
            break

    scenes = []
    scene_chars = set()

    for sent in sentences[:max_scenes]:
        sent_chars = {}
        for word, ch in CHAR_KEYWORDS.items():
            if _has_word(sent, word):
                sent_chars[ch] = sent_chars.get(ch, 0) + 1

        non_vehicle_chars = {k: v for k, v in sent_chars.items() if k not in ("bicycle",)}
        first_word = sent.split()[0] if sent.split() else ""
        if first_word in PRONOUNS and scene_chars and (not non_vehicle_chars or all(k in ("bicycle",) for k in sent_chars)):
            sent_chars = {ch: 1 for ch in scene_chars}
        elif not sent_chars and all_chars:
            sent_chars = {ch: 1 for ch in all_chars}
        elif not non_vehicle_chars and scene_chars:
            sent_chars = {ch: 1 for ch in scene_chars}

        scene_chars.update(sent_chars.keys())

        bg = default_bg
        for word, b in sorted(BG_KEYWORDS.items(), key=lambda x: -len(x[0])):
            if _has_word(sent, word):
                bg = b
                break

        def _char_context_actions(text: str, ch_name: str) -> set:
            words = text.split()
            ch_idx = None
            for wi, w in enumerate(words):
                if ch_name in w:
                    ch_idx = wi
                    break
            if ch_idx is None:
                return set()
            window = words[max(0, ch_idx - 3):min(len(words), ch_idx + 3)]
            window_text = " ".join(window)
            result = set()
            for word, act in sorted(ACTION_KEYWORDS.items(), key=lambda x: -len(x[0])):
                if _has_word(window_text, word):
                    result.add(act)
            return result

        action_priority = [
            "riding", "flying", "spinning", "slipping", "snapping",
            "sleeping", "eating", "jumping", "dancing", "shrug",
            "shocked", "walking", "sitting",
        ]

        chars = []
        all_char_names = [n for n in sent_chars if n != "bicycle"]
        has_water_bg = bg in ("water", "river")
        # if any character was resolved via pronoun, use whole-sentence action detection
        pronoun_resolved = first_word in PRONOUNS

        num_chars = len(all_char_names)
        for i, ch_name in enumerate(all_char_names):
            x_pos = 0.2 + 0.6 * i / max(num_chars - 1, 1)
            facing = -1 if _has_word(sent, "left") else 1
            if pronoun_resolved:
                char_actions = set()
                for word, act in sorted(ACTION_KEYWORDS.items(), key=lambda x: -len(x[0])):
                    if _has_word(sent, word):
                        char_actions.add(act)
            elif _has_word(sent, ch_name):
                char_actions = _char_context_actions(sent, ch_name)
            else:
                char_actions = set()
            action = "idle"

            for ap in action_priority:
                if ap in char_actions:
                    if ap == "riding" and ch_name in RIDING_ADDITIONS:
                        action = ap
                        veh = RIDING_ADDITIONS[ch_name]
                        if veh not in sent_chars:
                            chars.append(Char(name=veh, x=x_pos, y=0.68, action=veh, facing=facing))
                    else:
                        action = ap
                    break

            if action == "idle" and has_water_bg:
                action = "swimming"

            y_base = 0.60
            if action == "flying":
                y_base = 0.25 + 0.12 * (i % 2)
            elif action in ("swimming", "snapping"):
                y_base = 0.65
            elif action in ("shocked", "shrug", "slipping", "spinning", "riding", "sleeping", "sitting"):
                y_base = 0.55

            chars.append(Char(name=ch_name, x=x_pos, y=y_base, action=action, facing=facing))

        extra = {}
        if _has_word(sent, "night") or _has_word(sent, "dark"):
            extra["night"] = True

        has_any_action = any(c.action != "idle" for c in chars)
        duration = max(3.0, min(7.0, 3.0 + len(chars) * 1.5))
        if has_any_action:
            duration = max(duration, 4.5)

        scenes.append(Scene(background=bg, characters=chars, duration=duration, extra=extra))

    if not scenes:
        scenes.append(Scene(background=default_bg, duration=5.0))

    total_dur = sum(s.duration for s in scenes)
    target = min(20.0, total_dur)
    if total_dur > 0:
        for s in scenes:
            s.duration *= target / total_dur

    return scenes


# ─── Scene Renderer ─────────────────────────────────────────────
def render_scene(scene: Scene, fps: int, w: int, h: int) -> list[np.ndarray]:
    num_frames = max(1, int(scene.duration * fps))
    frames = []
    bg_func = _BACKGROUNDS.get(scene.background, _bg_sky)
    sky_h = int(h * SKY_RATIO)

    chars = scene.characters

    for fi in range(num_frames):
        t = fi / fps
        img = Image.new("RGB", (w, h))
        draw = ImageDraw.Draw(img)

        bg_func(draw, w, h, t, scene.extra)

        for ch in chars:
            ch_name = ch.name
            if ch_name == "bicycle":
                continue
            if ch.end_x is not None:
                cx = ch.x + (ch.end_x - ch.x) * (fi / max(num_frames - 1, 1))
            else:
                cx = ch.x
            if ch.end_y is not None:
                cy = ch.y + (ch.end_y - ch.y) * (fi / max(num_frames - 1, 1))
            else:
                cy = ch.y
            px = int(cx * w)
            py = int(cy * h)
            _draw_char(draw, ch_name, px, py, ch.scale, fi, ch.action, ch.facing)

        for ch in chars:
            if ch.name == "bicycle":
                if ch.end_x is not None:
                    cx = ch.x + (ch.end_x - ch.x) * (fi / max(num_frames - 1, 1))
                else:
                    cx = ch.x
                if ch.end_y is not None:
                    cy = ch.y + (ch.end_y - ch.y) * (fi / max(num_frames - 1, 1))
                else:
                    cy = ch.y
                px = int(cx * w)
                py = int(cy * h)
                _draw_bicycle(draw, px, py, ch.scale, fi, "idle", ch.facing)

        frames.append(np.array(img))

    return frames


def generate_storyboard_frames(prompt: str, w: int = W, h: int = H, fps: int = FPS) -> list[np.ndarray]:
    scenes = parse_prompt_to_scenes(prompt)
    all_frames = []
    for i, scene in enumerate(scenes):
        scene_frames = render_scene(scene, fps, w, h)
        all_frames.extend(scene_frames)
    return all_frames


# ─── Main / Test ────────────────────────────────────────────────
if __name__ == "__main__":
    test_prompt = (
        "A clever monkey opens a banana delivery service in the jungle. "
        "He rides his bicycle through the trees, balancing a crate of bananas. "
        "A startled parrot flies overhead. "
        "A crocodile snaps its jaws from the river below."
    )
    print(f"Prompt: {test_prompt}")
    print(f"\nParsing into scenes...\n")
    scenes = parse_prompt_to_scenes(test_prompt)
    for i, s in enumerate(scenes):
        print(f"Scene {i+1}: bg={s.background}, dur={s.duration:.1f}s")
        for ch in s.characters:
            print(f"  {ch.name} @ ({ch.x:.2f}, {ch.y:.2f}) action={ch.action}")
    total_frames = sum(int(s.duration * FPS) for s in scenes)
    print(f"\nTotal frames: {total_frames} @ {FPS}fps = {total_frames/FPS:.1f}s")

    print("\nRendering test frame...")
    frames = generate_storyboard_frames(test_prompt)
    print(f"Generated {len(frames)} frames")
    import os
    from pathlib import Path
    out_dir = Path(__file__).resolve().parent.parent / "temp"
    out_dir.mkdir(exist_ok=True)
    test_img = Image.fromarray(frames[len(frames) // 2])
    test_img.save(str(out_dir / "storyboard_test.png"))
    print(f"Saved test frame to {out_dir / 'storyboard_test.png'}")
