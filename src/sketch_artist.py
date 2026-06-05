"""Hand-drawn pencil/marker sketch illustrations — pure PIL, no external deps.
Each function draws on a PIL ImageDraw surface in a clean whiteboard style."""

import math, random
from PIL import Image, ImageDraw, ImageFont

W, H = 720, 1280
_BG = (250, 250, 245)
_STROKE = (30, 30, 30)
_ACCENT = (200, 80, 60)
_ACCENT2 = (60, 120, 200)


def _r():
    return random.uniform(-1.2, 1.2)


def _wobble(points: list, strength: float = 1.5) -> list:
    return [(x + _r() * strength, y + _r() * strength) for x, y in points]


def _get_font(size: int = 36):
    try:
        return ImageFont.truetype("C:/Windows/Fonts/arial.ttf", size)
    except:
        return ImageFont.load_default()


def new_canvas(w: int = 720, h: int = 1280) -> tuple[Image.Image, ImageDraw.Draw]:
    img = Image.new("RGB", (w, h), _BG)
    return img, ImageDraw.Draw(img)


def draw_sketch_for_phrase(phrase: str, w: int = 720, h: int = 1280) -> Image.Image:
    """Auto-detect subjects in phrase and compose a sketch scene."""
    phrase_lower = phrase.lower()
    subjects = []
    for keyword, draw_fn in SUBJECT_REGISTRY:
        if keyword in phrase_lower:
            subjects.append((keyword, draw_fn))
    if not subjects:
        subjects.append(("question", _draw_question))

    img, draw = new_canvas(w, h)
    cx, cy = w // 2, h // 2 - 80
    scale = min(w, h) / 720

    # Draw subjects arranged on canvas
    if len(subjects) == 1:
        subjects[0][1](draw, cx, cy, scale * 1.5)
    elif len(subjects) >= 2:
        for i, (kw, fn) in enumerate(subjects[:3]):
            ox = cx + (i - 1) * int(180 * scale)
            oy = cy + int(60 * scale) if i == 1 else cy
            fn(draw, ox, oy, scale * 1.2)

    return img


def _draw_brain(draw: ImageDraw.Draw, x: int, y: int, s: float = 1.0):
    """Stylized brain sketch — two hemispheres with folds."""
    r = int(80 * s)
    pts = _wobble([
        (x - r, y), (x - r, y - r * 0.7), (x - r * 0.5, y - r * 1.1),
        (x, y - r * 1.2), (x + r * 0.5, y - r * 1.1),
        (x + r, y - r * 0.7), (x + r, y),
        (x + r * 0.8, y + r * 0.3), (x, y + r * 0.5),
        (x - r * 0.8, y + r * 0.3),
    ])
    draw.line(pts, fill=_STROKE, width=max(2, int(3 * s)))
    # Center divide
    draw.line(_wobble([(x, y - r * 0.9), (x, y + r * 0.2)]), fill=_STROKE, width=max(1, int(2 * s)))
    # Fold lines
    for dx in [-0.4, 0.4]:
        draw.arc(_wobble([(x + dx * r - r * 0.3, y - r * 0.5), (x + dx * r + r * 0.3, y)], strength=0.5),
                 -30, 210, fill=_STROKE, width=max(1, int(2 * s)))


def _draw_heart(draw: ImageDraw.Draw, x: int, y: int, s: float = 1.0):
    r = int(50 * s)
    pts = _wobble([
        (x, y + r), (x - r, y - r * 0.3), (x - r, y - r),
        (x, y - r * 0.5), (x + r, y - r), (x + r, y - r * 0.3),
    ])
    draw.polygon(pts + [(x, y + r)], fill=None, outline=_STROKE, width=max(2, int(3 * s)))
    # Aorta
    draw.line(_wobble([(x, y - r * 0.5), (x, y - r * 1.3)]), fill=_STROKE, width=max(1, int(2 * s)))


def _draw_eye(draw: ImageDraw.Draw, x: int, y: int, s: float = 1.0):
    r = int(50 * s)
    draw.arc(_wobble([(x - r, y - r * 0.3), (x + r, y + r * 0.3)]), 0, 180, fill=_STROKE, width=max(2, int(3 * s)))
    draw.arc(_wobble([(x - r, y + r * 0.3), (x + r, y - r * 0.3)]), 180, 360, fill=_STROKE, width=max(2, int(3 * s)))
    # Iris
    ir = int(18 * s)
    draw.ellipse(_wobble([(x - ir, y - ir), (x + ir, y + ir)]), outline=_STROKE, width=max(1, int(2 * s)))
    draw.ellipse(_wobble([(x - ir * 0.4, y - ir * 0.4), (x + ir * 0.4, y + ir * 0.4)], strength=0.5),
                 fill=_STROKE, outline=None)


def _draw_nose(draw: ImageDraw.Draw, x: int, y: int, s: float = 1.0):
    r = int(40 * s)
    draw.line(_wobble([(x, y - r), (x - r * 0.3, y + r * 0.2)]), fill=_STROKE, width=max(2, int(3 * s)))
    draw.line(_wobble([(x, y - r), (x + r * 0.3, y + r * 0.2)]), fill=_STROKE, width=max(2, int(3 * s)))
    draw.ellipse(_wobble([(x - r * 0.3, y + r * 0.1), (x - r * 0.1, y + r * 0.3)]), outline=_STROKE, width=max(1, int(2 * s)))
    draw.ellipse(_wobble([(x + r * 0.1, y + r * 0.1), (x + r * 0.3, y + r * 0.3)]), outline=_STROKE, width=max(1, int(2 * s)))


def _draw_octopus(draw: ImageDraw.Draw, x: int, y: int, s: float = 1.0):
    r = int(40 * s)
    # Head
    draw.ellipse(_wobble([(x - r * 0.8, y - r * 0.6), (x + r * 0.8, y + r * 0.4)]), outline=_STROKE, width=max(2, int(3 * s)))
    # Tentacles
    for i in range(8):
        angle = i * 45
        rad = math.radians(angle)
        end_x = x + math.cos(rad) * r * 1.3
        end_y = y + r * 0.3 + math.sin(rad) * r * 0.8
        mid_x = x + math.cos(rad + 0.3) * r * 0.7
        mid_y = y + r * 0.2 + math.sin(rad + 0.3) * r * 0.5
        draw.line(_wobble([(x + math.cos(rad) * r * 0.4, y + r * 0.3),
                          (mid_x, mid_y), (end_x, end_y)]), fill=_STROKE, width=max(1, int(2 * s)))
    # Eyes
    for ex in [-1, 1]:
        draw.ellipse(_wobble([(x + ex * r * 0.35 - 5 * s, y - r * 0.25 - 5 * s),
                             (x + ex * r * 0.35 + 5 * s, y - r * 0.25 + 5 * s)]), outline=_STROKE, width=2)


def _draw_tree(draw: ImageDraw.Draw, x: int, y: int, s: float = 1.0):
    r = int(50 * s)
    # Trunk
    draw.line(_wobble([(x, y + r * 0.2), (x - 5 * s, y + r * 1.5), (x + 5 * s, y + r * 1.5)], strength=1),
              fill=_STROKE, width=max(2, int(4 * s)))
    # Canopy (cloud-like)
    for cy in [y - r * 0.3, y, y + r * 0.2]:
        for cx in range(x - r, x + r + 1, r):
            draw.ellipse(_wobble([(cx - r * 0.5, cy - r * 0.4), (cx + r * 0.5, cy + r * 0.3)]),
                         outline=_STROKE, width=max(1, int(2 * s)))


def _draw_water(draw: ImageDraw.Draw, x: int, y: int, s: float = 1.0):
    w = int(120 * s)
    # Waves
    for i in range(3):
        yy = y + i * 20
        pts = [(x - w // 2 + j * 10, yy + math.sin(j * 0.5 + i) * 10) for j in range(int(w / 10) + 1)]
        draw.line(_wobble(pts, 0.8), fill=_STROKE, width=max(1, int(2 * s)))
    # Droplet
    dr = int(15 * s)
    draw.ellipse(_wobble([(x - dr, y - dr * 0.5), (x + dr, y + dr)]), outline=_STROKE, width=max(1, int(2 * s)))
    draw.polygon(_wobble([(x, y - dr * 1.5), (x - dr * 0.5, y - dr * 0.3), (x + dr * 0.5, y - dr * 0.3)]),
                 outline=_STROKE, width=max(1, int(2 * s)))


def _draw_clock(draw: ImageDraw.Draw, x: int, y: int, s: float = 1.0):
    r = int(60 * s)
    draw.ellipse(_wobble([(x - r, y - r), (x + r, y + r)]), outline=_STROKE, width=max(2, int(3 * s)))
    # Tick marks
    for i in range(12):
        a = math.radians(i * 30)
        inner = r * 0.85
        outer = r * 0.92 if i % 3 == 0 else r * 0.88
        draw.line(_wobble([(x + math.cos(a) * inner, y + math.sin(a) * inner),
                          (x + math.cos(a) * outer, y + math.sin(a) * outer)]), fill=_STROKE, width=max(1, int(2 * s)))
    # Hands
    draw.line(_wobble([(x, y), (x, y - r * 0.6)]), fill=_STROKE, width=max(2, int(3 * s)))
    draw.line(_wobble([(x, y), (x + r * 0.45, y - r * 0.1)]), fill=_STROKE, width=max(1, int(2 * s)))
    draw.ellipse(_wobble([(x - 4, y - 4), (x + 4, y + 4)]), fill=_STROKE)


def _draw_computer(draw: ImageDraw.Draw, x: int, y: int, s: float = 1.0):
    sw, sh = int(80 * s), int(60 * s)
    # Screen
    draw.rectangle(_wobble([(x - sw, y - sh), (x + sw, y + sh)], 0.5), outline=_STROKE, width=max(2, int(3 * s)))
    # Stand
    draw.line(_wobble([(x, y + sh), (x, y + sh + 20 * s)]), fill=_STROKE, width=max(2, int(3 * s)))
    draw.line(_wobble([(x - 20 * s, y + sh + 30 * s), (x + 20 * s, y + sh + 30 * s)]), fill=_STROKE, width=max(2, int(3 * s)))


def _draw_virus(draw: ImageDraw.Draw, x: int, y: int, s: float = 1.0):
    r = int(40 * s)
    # Body
    draw.ellipse(_wobble([(x - r, y - r), (x + r, y + r)]), outline=_STROKE, width=max(2, int(3 * s)))
    # Spikes
    for i in range(8):
        a = math.radians(i * 45)
        draw.line(_wobble([(x + math.cos(a) * r, y + math.sin(a) * r),
                          (x + math.cos(a) * r * 1.5, y + math.sin(a) * r * 1.5)]), fill=_STROKE, width=max(1, int(2 * s)))
        draw.ellipse(_wobble([(x + math.cos(a) * r * 1.4 - 5 * s, y + math.sin(a) * r * 1.4 - 5 * s),
                             (x + math.cos(a) * r * 1.4 + 5 * s, y + math.sin(a) * r * 1.4 + 5 * s)]), outline=_STROKE, width=1)


def _draw_fire(draw: ImageDraw.Draw, x: int, y: int, s: float = 1.0):
    r = int(50 * s)
    pts = _wobble([
        (x, y + r),
        (x - r * 0.5, y - r * 0.2),
        (x - r * 0.3, y - r * 0.6),
        (x, y - r * 0.3),
        (x + r * 0.3, y - r * 0.6),
        (x + r * 0.5, y - r * 0.2),
    ])
    draw.polygon(pts + [(x, y + r)], outline=_STROKE, width=max(2, int(3 * s)))
    # Inner flame
    pts2 = _wobble([
        (x, y + r * 0.5),
        (x - r * 0.2, y - r * 0.1),
        (x, y - r * 0.4),
        (x + r * 0.2, y - r * 0.1),
    ])
    draw.polygon(pts2 + [(x, y + r * 0.5)], outline=_STROKE, width=1)


def _draw_honey(draw: ImageDraw.Draw, x: int, y: int, s: float = 1.0):
    r = int(40 * s)
    # Jar
    draw.rectangle(_wobble([(x - r * 0.6, y - r * 0.8), (x + r * 0.6, y + r * 0.2)], 0.5),
                   outline=_STROKE, width=max(2, int(3 * s)))
    # Lid
    draw.rectangle(_wobble([(x - r * 0.5, y - r * 0.9), (x + r * 0.5, y - r * 0.75)], 0.3),
                   outline=_STROKE, width=max(1, int(2 * s)))
    # Honey drip
    draw.ellipse(_wobble([(x - r * 0.15, y - r * 0.45), (x + r * 0.15, y + r * 0.15)]), outline=_STROKE, width=1)
    draw.line(_wobble([(x, y + r * 0.2), (x, y + r * 0.5)]), fill=_STROKE, width=2)
    draw.ellipse(_wobble([(x - 3 * s, y + r * 0.45), (x + 3 * s, y + r * 0.55)]), fill=_STROKE)
    # Label
    draw.text((x - 15, y + 5), "H", fill=_STROKE, font=_get_font(int(14 * s)))


def _draw_human(draw: ImageDraw.Draw, x: int, y: int, s: float = 1.0):
    r = int(40 * s)
    # Head
    draw.ellipse(_wobble([(x - r * 0.35, y - r * 0.7), (x + r * 0.35, y)]), outline=_STROKE, width=max(2, int(3 * s)))
    # Body
    draw.line(_wobble([(x, y), (x, y + r * 1.8)]), fill=_STROKE, width=max(2, int(3 * s)))
    # Arms
    draw.line(_wobble([(x - r * 0.8, y + r * 0.5), (x, y + r * 0.3), (x + r * 0.8, y + r * 0.5)]),
              fill=_STROKE, width=max(1, int(2 * s)))
    # Legs
    draw.line(_wobble([(x, y + r * 1.8), (x - r * 0.5, y + r * 2.6)]), fill=_STROKE, width=max(1, int(2 * s)))
    draw.line(_wobble([(x, y + r * 1.8), (x + r * 0.5, y + r * 2.6)]), fill=_STROKE, width=max(1, int(2 * s)))


def _draw_lightbulb(draw: ImageDraw.Draw, x: int, y: int, s: float = 1.0):
    r = int(45 * s)
    # Bulb
    draw.ellipse(_wobble([(x - r, y - r * 0.6), (x + r, y + r * 0.4)]), outline=_STROKE, width=max(2, int(3 * s)))
    # Base
    draw.rectangle(_wobble([(x - r * 0.3, y + r * 0.4), (x + r * 0.3, y + r * 0.8)], 0.3),
                   outline=_STROKE, width=max(1, int(2 * s)))
    # Filament
    draw.line(_wobble([(x - r * 0.3, y - r * 0.2), (x, y + r * 0.1), (x + r * 0.3, y - r * 0.2)]),
              fill=_STROKE, width=1)
    # Light rays
    for i in range(6):
        a = math.radians(i * 60)
        draw.line(_wobble([(x + math.cos(a) * r * 0.85, y - r * 0.1 + math.sin(a) * r * 0.85),
                          (x + math.cos(a) * r * 1.15, y - r * 0.1 + math.sin(a) * r * 1.15)]),
                  fill=_STROKE, width=max(1, int(2 * s)))


def _draw_globe(draw: ImageDraw.Draw, x: int, y: int, s: float = 1.0):
    r = int(55 * s)
    draw.ellipse(_wobble([(x - r, y - r), (x + r, y + r)]), outline=_STROKE, width=max(2, int(3 * s)))
    # Continents (simplified)
    draw.ellipse(_wobble([(x - r * 0.3, y - r * 0.2), (x + r * 0.5, y + r * 0.1)]), outline=_STROKE, width=1)
    draw.ellipse(_wobble([(x - r * 0.1, y - r * 0.4), (x + r * 0.2, y - r * 0.1)]), outline=_STROKE, width=1)
    draw.ellipse(_wobble([(x - r * 0.5, y + r * 0.1), (x - r * 0.1, y + r * 0.3)]), outline=_STROKE, width=1)
    # Grid lines
    if r > 5:
        draw.arc(_wobble([(x - r, y - 1), (x + r, y + 1)]), 0, 360, fill=_STROKE, width=1)
        draw.arc(_wobble([(x - 1, y - r), (x + 1, y + r)]), 0, 360, fill=_STROKE, width=1)
    # Stand
    draw.line(_wobble([(x, y + r), (x - r * 0.3, y + r * 1.3)]), fill=_STROKE, width=max(1, int(2 * s)))
    draw.line(_wobble([(x, y + r), (x + r * 0.3, y + r * 1.3)]), fill=_STROKE, width=max(1, int(2 * s)))


def _draw_dna(draw: ImageDraw.Draw, x: int, y: int, s: float = 1.0):
    r = int(30 * s)
    h = int(100 * s)
    for i in range(0, int(h), 8):
        t = i / h
        lx = x - r * math.cos(t * math.pi * 4)
        rx = x + r * math.cos(t * math.pi * 4)
        yy = y - h / 2 + i
        draw.line(_wobble([(lx, yy), (rx, yy)], 0.5), fill=_STROKE, width=1)
    draw.line(_wobble([(x - r, y - h / 2), (x + r, y + h / 2)], 0.5), fill=_STROKE, width=max(1, int(2 * s)))
    draw.line(_wobble([(x + r, y - h / 2), (x - r, y + h / 2)], 0.5), fill=_STROKE, width=max(1, int(2 * s)))


def _draw_star(draw: ImageDraw.Draw, x: int, y: int, s: float = 1.0):
    r = int(45 * s)
    pts = []
    for i in range(10):
        a = math.radians(i * 36 - 90)
        radius = r if i % 2 == 0 else r * 0.45
        pts.append((x + math.cos(a) * radius, y + math.sin(a) * radius))
    draw.polygon(_wobble(pts), outline=_STROKE, width=max(2, int(3 * s)))


def _draw_mountain(draw: ImageDraw.Draw, x: int, y: int, s: float = 1.0):
    r = int(60 * s)
    pts = _wobble([
        (x - r, y + r * 0.5),
        (x - r * 0.5, y - r * 0.3),
        (x, y - r * 0.2),
        (x + r * 0.2, y - r * 0.6),
        (x + r * 0.5, y - r * 0.1),
        (x + r, y + r * 0.3),
        (x + r, y + r * 0.5),
    ])
    draw.polygon(pts + [(x - r, y + r * 0.5)], outline=_STROKE, width=max(2, int(3 * s)))
    # Snow cap
    snow = _wobble([
        (x + r * 0.1, y - r * 0.3), (x + r * 0.2, y - r * 0.55),
        (x + r * 0.3, y - r * 0.3), (x + r * 0.2, y - r * 0.2),
    ])
    draw.polygon(snow, outline=_STROKE, width=1)


def _draw_sun(draw: ImageDraw.Draw, x: int, y: int, s: float = 1.0):
    r = int(45 * s)
    draw.ellipse(_wobble([(x - r, y - r), (x + r, y + r)]), outline=_STROKE, width=max(2, int(3 * s)))
    for i in range(8):
        a = math.radians(i * 45)
        draw.line(_wobble([(x + math.cos(a) * r * 1.1, y + math.sin(a) * r * 1.1),
                          (x + math.cos(a) * r * 1.5, y + math.sin(a) * r * 1.5)]), fill=_STROKE, width=max(1, int(2 * s)))


def _draw_moon(draw: ImageDraw.Draw, x: int, y: int, s: float = 1.0):
    r = int(45 * s)
    draw.ellipse(_wobble([(x - r, y - r), (x + r, y + r)]), outline=_STROKE, width=max(2, int(3 * s)))
    # Crescent cutout
    draw.ellipse(_wobble([(x - r * 0.3, y - r * 0.8), (x + r * 0.8, y + r * 0.8)]), fill=_BG, outline=None)


def _draw_question(draw: ImageDraw.Draw, x: int, y: int, s: float = 1.0):
    r = int(45 * s)
    # Circle part
    draw.arc(_wobble([(x - r * 0.3, y - r * 0.4), (x + r * 0.3, y + r * 0.2)]), 30, 330, fill=_STROKE, width=max(2, int(3 * s)))
    # Stem
    draw.line(_wobble([(x, y + r * 0.2), (x, y + r * 0.35)]), fill=_STROKE, width=max(2, int(3 * s)))
    # Dot
    draw.ellipse(_wobble([(x - 4 * s, y + r * 0.45), (x + 4 * s, y + r * 0.55)]), fill=_STROKE)


def _draw_book(draw: ImageDraw.Draw, x: int, y: int, s: float = 1.0):
    r = int(50 * s)
    # Pages
    draw.rectangle(_wobble([(x - r, y - r * 0.7), (x + r, y + r * 0.7)], 0.5),
                   outline=_STROKE, width=max(2, int(3 * s)))
    # Spine
    draw.line(_wobble([(x, y - r * 0.7), (x, y + r * 0.7)]), fill=_STROKE, width=max(1, int(2 * s)))
    # Lines (text)
    for i in range(5):
        yy = y - r * 0.45 + i * r * 0.25
        draw.line(_wobble([(x - r * 0.75, yy), (x + r * 0.75, yy)], 0.3), fill=_STROKE, width=1)


def _draw_fish(draw: ImageDraw.Draw, x: int, y: int, s: float = 1.0):
    r = int(50 * s)
    # Body
    draw.ellipse(_wobble([(x - r, y - r * 0.4), (x + r, y + r * 0.4)]), outline=_STROKE, width=max(2, int(3 * s)))
    # Tail
    draw.polygon(_wobble([(x - r, y), (x - r * 1.4, y - r * 0.4), (x - r * 1.4, y + r * 0.4)]),
                 outline=_STROKE, width=max(1, int(2 * s)))
    # Eye
    draw.ellipse(_wobble([(x + r * 0.4, y - r * 0.1), (x + r * 0.55, y + r * 0.1)]), fill=_STROKE)


def _draw_bird(draw: ImageDraw.Draw, x: int, y: int, s: float = 1.0):
    r = int(30 * s)
    # Body
    draw.ellipse(_wobble([(x, y - r * 0.4), (x + r * 1.2, y + r * 0.4)]), outline=_STROKE, width=max(2, int(3 * s)))
    # Head
    draw.ellipse(_wobble([(x + r * 0.9, y - r * 0.5), (x + r * 1.4, y)]), outline=_STROKE, width=max(1, int(2 * s)))
    # Beak
    draw.polygon(_wobble([(x + r * 1.4, y - r * 0.2), (x + r * 1.7, y - r * 0.15), (x + r * 1.4, y)]),
                 outline=_STROKE, width=1)
    # Wing
    draw.arc(_wobble([(x + r * 0.1, y - r * 0.6), (x + r * 0.7, y + r * 0.5)]), 180, 360, fill=_STROKE, width=max(1, int(2 * s)))
    # Legs
    draw.line(_wobble([(x + r * 0.6, y + r * 0.4), (x + r * 0.5, y + r * 0.8)]), fill=_STROKE, width=1)
    draw.line(_wobble([(x + r * 0.9, y + r * 0.4), (x + r * 0.8, y + r * 0.8)]), fill=_STROKE, width=1)


def _draw_flower(draw: ImageDraw.Draw, x: int, y: int, s: float = 1.0):
    r = int(30 * s)
    # Stem
    draw.line(_wobble([(x, y), (x, y + r * 2)]), fill=_STROKE, width=max(2, int(3 * s)))
    # Leaves
    draw.arc(_wobble([(x, y + r * 0.5), (x - r, y + r * 1.2)]), 0, 180, fill=_STROKE, width=1)
    draw.arc(_wobble([(x, y + r * 0.8), (x + r, y + r * 1.5)]), 180, 360, fill=_STROKE, width=1)
    # Petals
    for i in range(5):
        a = math.radians(i * 72 - 90)
        px = x + math.cos(a) * r * 0.7
        py = y + math.sin(a) * r * 0.7
        draw.ellipse(_wobble([(px - r * 0.35, py - r * 0.35), (px + r * 0.35, py + r * 0.35)]),
                     outline=_STROKE, width=1)
    # Center
    draw.ellipse(_wobble([(x - r * 0.25, y - r * 0.25), (x + r * 0.25, y + r * 0.25)]), outline=_STROKE, width=1)


def _draw_hand(draw: ImageDraw.Draw, x: int, y: int, s: float = 1.0):
    r = int(25 * s)
    # Palm
    draw.rectangle(_wobble([(x - r, y), (x + r, y + r * 1.2)], 0.5), outline=_STROKE, width=max(2, int(3 * s)))
    # Fingers
    for i, (dx, dy) in enumerate([(-0.6, -0.8), (-0.2, -1.0), (0.2, -1.0), (0.6, -0.8)]):
        draw.line(_wobble([(x + dx * r, y), (x + dx * r, y + dy * r)]), fill=_STROKE, width=max(1, int(2 * s)))
        draw.ellipse(_wobble([(x + dx * r - 3 * s, y + dy * r - 6 * s), (x + dx * r + 3 * s, y + dy * r + 3 * s)]),
                     outline=_STROKE, width=1)
    # Thumb
    draw.line(_wobble([(x - r, y + r * 0.3), (x - r * 1.3, y - r * 0.2)]), fill=_STROKE, width=max(1, int(2 * s)))


def _draw_rainbow(draw: ImageDraw.Draw, x: int, y: int, s: float = 1.0):
    r = int(60 * s)
    for i in range(5):
        rr = r - i * 8
        draw.arc(_wobble([(x - rr, y - rr * 0.5), (x + rr, y + rr * 0.5)], 0.5), 0, 180, fill=_STROKE, width=1)


def _draw_gear(draw: ImageDraw.Draw, x: int, y: int, s: float = 1.0):
    r = int(45 * s)
    pts = []
    for i in range(16):
        a = math.radians(i * 22.5 - 90)
        radius = r if i % 2 == 0 else r * 0.75
        pts.append((x + math.cos(a) * radius, y + math.sin(a) * radius))
    draw.polygon(_wobble(pts), outline=_STROKE, width=max(2, int(3 * s)))
    # Center hole
    draw.ellipse(_wobble([(x - r * 0.3, y - r * 0.3), (x + r * 0.3, y + r * 0.3)]), outline=_STROKE, width=1)


def _draw_rocket(draw: ImageDraw.Draw, x: int, y: int, s: float = 1.0):
    r = int(40 * s)
    # Body
    draw.polygon(_wobble([(x, y - r * 1.2), (x - r * 0.4, y), (x - r * 0.3, y + r), (x + r * 0.3, y + r), (x + r * 0.4, y)]),
                 outline=_STROKE, width=max(2, int(3 * s)))
    # Window
    draw.ellipse(_wobble([(x - r * 0.2, y - r * 0.3), (x + r * 0.2, y + r * 0.1)]), outline=_STROKE, width=1)
    # Fins
    draw.polygon(_wobble([(x - r * 0.3, y + r * 0.5), (x - r * 0.6, y + r * 1.2), (x - r * 0.2, y + r * 0.7)]),
                 outline=_STROKE, width=1)
    draw.polygon(_wobble([(x + r * 0.3, y + r * 0.5), (x + r * 0.6, y + r * 1.2), (x + r * 0.2, y + r * 0.7)]),
                 outline=_STROKE, width=1)
    # Fire
    draw.polygon(_wobble([(x - r * 0.15, y + r), (x, y + r * 1.4), (x + r * 0.15, y + r)]),
                 outline=_STROKE, width=1)


def _draw_trophy(draw: ImageDraw.Draw, x: int, y: int, s: float = 1.0):
    r = int(35 * s)
    draw.polygon(_wobble([(x - r, y - r), (x + r, y - r), (x + r * 0.7, y + r * 0.3), (x - r * 0.7, y + r * 0.3)]),
                 outline=_STROKE, width=max(2, int(3 * s)))
    # Handles
    draw.arc(_wobble([(x - r * 1.1, y - r * 0.8), (x - r * 0.7, y + r * 0.1)]), -90, 90, fill=_STROKE, width=max(1, int(2 * s)))
    draw.arc(_wobble([(x + r * 0.7, y - r * 0.8), (x + r * 1.1, y + r * 0.1)]), 90, 270, fill=_STROKE, width=max(1, int(2 * s)))
    # Base
    draw.rectangle(_wobble([(x - r * 0.5, y + r * 0.3), (x + r * 0.5, y + r * 0.55)], 0.3),
                   outline=_STROKE, width=1)
    draw.rectangle(_wobble([(x - r * 0.7, y + r * 0.55), (x + r * 0.7, y + r * 0.75)], 0.3),
                   outline=_STROKE, width=1)


def _draw_magnifying_glass(draw: ImageDraw.Draw, x: int, y: int, s: float = 1.0):
    r = int(40 * s)
    draw.ellipse(_wobble([(x - r, y - r), (x + r, y + r)]), outline=_STROKE, width=max(2, int(3 * s)))
    # Handle
    draw.line(_wobble([(x + r * 0.6, y + r * 0.6), (x + r * 1.3, y + r * 1.3)]), fill=_STROKE, width=max(2, int(4 * s)))


def _draw_puzzle(draw: ImageDraw.Draw, x: int, y: int, s: float = 1.0):
    r = int(30 * s)
    pts = _wobble([
        (x - r, y - r), (x, y - r - r * 0.3), (x + r, y - r),
        (x + r + r * 0.3, y), (x + r, y + r),
        (x, y + r + r * 0.3), (x - r, y + r),
        (x - r - r * 0.3, y),
    ])
    draw.polygon(pts + [(x - r, y - r)], outline=_STROKE, width=max(2, int(3 * s)))


def _draw_shield(draw: ImageDraw.Draw, x: int, y: int, s: float = 1.0):
    r = int(45 * s)
    pts = _wobble([
        (x - r, y - r), (x - r, y), (x - r * 0.5, y + r * 0.7),
        (x, y + r), (x + r * 0.5, y + r * 0.7),
        (x + r, y), (x + r, y - r),
    ])
    draw.polygon(pts + [(x - r, y - r)], outline=_STROKE, width=max(2, int(3 * s)))
    # Check mark
    draw.line(_wobble([(x - r * 0.35, y - r * 0.1), (x, y + r * 0.3), (x + r * 0.5, y - r * 0.3)]),
              fill=_STROKE, width=max(1, int(2 * s)))


def _draw_scales(draw: ImageDraw.Draw, x: int, y: int, s: float = 1.0):
    r = int(45 * s)
    # Beam
    draw.line(_wobble([(x - r, y), (x + r, y)]), fill=_STROKE, width=max(2, int(3 * s)))
    # Center pivot
    draw.line(_wobble([(x, y), (x, y + r * 0.5)]), fill=_STROKE, width=2)
    draw.polygon(_wobble([(x - r * 0.15, y + r * 0.5), (x + r * 0.15, y + r * 0.5), (x, y + r * 0.8)]),
                 outline=_STROKE, width=1)
    # Pans
    draw.line(_wobble([(x - r, y), (x - r, y + r * 0.4)]), fill=_STROKE, width=1)
    draw.line(_wobble([(x + r, y), (x + r, y + r * 0.4)]), fill=_STROKE, width=1)
    draw.arc(_wobble([(x - r * 1.2, y + r * 0.3), (x - r * 0.8, y + r * 0.7)]), 0, 180, fill=_STROKE, width=1)
    draw.arc(_wobble([(x + r * 0.8, y + r * 0.3), (x + r * 1.2, y + r * 0.7)]), 0, 180, fill=_STROKE, width=1)


def _draw_baby(draw: ImageDraw.Draw, x: int, y: int, s: float = 1.0):
    r = int(35 * s)
    # Head
    draw.ellipse(_wobble([(x - r * 0.4, y - r * 0.6), (x + r * 0.4, y + r * 0.1)]), outline=_STROKE, width=max(2, int(3 * s)))
    # Body (blanket)
    draw.polygon(_wobble([(x - r * 0.5, y + r * 0.1), (x + r * 0.5, y + r * 0.1),
                         (x + r * 0.6, y + r * 0.9), (x - r * 0.6, y + r * 0.9)]),
                 outline=_STROKE, width=max(1, int(2 * s)))
    # Pacifier
    draw.ellipse(_wobble([(x + r * 0.15, y - r * 0.1), (x + r * 0.4, y + r * 0.05)]), outline=_STROKE, width=1)
    draw.ellipse(_wobble([(x + r * 0.2, y + r * 0.05), (x + r * 0.35, y + r * 0.15)]), fill=_STROKE)


# Registry for keyword → drawing function matching
SUBJECT_REGISTRY: list[tuple[str, callable]] = [
    ("brain", _draw_brain),
    ("heart", _draw_heart),
    ("eye", _draw_eye),
    ("nose", _draw_nose),
    ("octopus", _draw_octopus),
    ("tree", _draw_tree),
    ("water", _draw_water),
    ("clock", _draw_clock),
    ("time", _draw_clock),
    ("year", _draw_clock),
    ("computer", _draw_computer),
    ("virus", _draw_virus),
    ("fire", _draw_fire),
    ("honey", _draw_honey),
    ("sun", _draw_sun),
    ("moon", _draw_moon),
    ("star", _draw_star),
    ("mountain", _draw_mountain),
    ("mountains", _draw_mountain),
    ("human", _draw_human),
    ("person", _draw_human),
    ("people", _draw_human),
    ("light", _draw_lightbulb),
    ("idea", _draw_lightbulb),
    ("lightbulb", _draw_lightbulb),
    ("globe", _draw_globe),
    ("world", _draw_globe),
    ("earth", _draw_globe),
    ("planet", _draw_globe),
    ("venus", _draw_globe),
    ("dna", _draw_dna),
    ("book", _draw_book),
    ("read", _draw_book),
    ("fish", _draw_fish),
    ("bird", _draw_bird),
    ("flower", _draw_flower),
    ("rainbow", _draw_rainbow),
    ("rain", _draw_rainbow),
    ("hand", _draw_hand),
    ("gear", _draw_gear),
    ("rocket", _draw_rocket),
    ("space", _draw_rocket),
    ("trophy", _draw_trophy),
    ("search", _draw_magnifying_glass),
    ("puzzle", _draw_puzzle),
    ("shield", _draw_shield),
    ("protect", _draw_shield),
    ("scale", _draw_scales),
    ("balance", _draw_scales),
    ("baby", _draw_baby),
    ("ocean", _draw_water),
    ("sea", _draw_water),
    ("life", _draw_dna),
    ("scent", _draw_nose),
    ("smell", _draw_nose),
    ("flamingo", _draw_bird),
    ("flamboyance", _draw_flower),
    ("hundred", _draw_star),
    ("thousand", _draw_star),
    ("trillion", _draw_star),
    ("learn", _draw_book),
    ("question", _draw_question),
    ("believe", _draw_question),
    ("know", _draw_question),
    ("call", _draw_question),
]
