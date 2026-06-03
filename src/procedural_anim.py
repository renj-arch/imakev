"""Procedural scene animator — draws frame-by-frame moving scenes with PIL (no API, no GPU)."""

import math, random
from PIL import Image, ImageDraw
import numpy as np


def _rng(seed):
    return random.Random(seed & 0xFFFFFFFF)


def animate_scene(prompt: str, w: int, h: int, num_frames: int, fps: int = 12) -> list[np.ndarray]:
    p_lower = prompt.lower()
    seed = hash(prompt) & 0xFFFFFFFF
    rng = _rng(seed)

    frames = []
    sky_h = int(h * 0.55)

    # scene config
    is_water = any(x in p_lower for x in ("water", "ocean", "sea", "pond", "lake", "river", "swim", "duck"))
    is_night = "night" in p_lower or "dark" in p_lower or "space" in p_lower
    is_sunset = "sunset" in p_lower or "sunrise" in p_lower or "golden" in p_lower
    has_duck = any(x in p_lower for x in ("duck", "swan", "bird", "goose"))
    has_dragon = "dragon" in p_lower
    has_fish = any(x in p_lower for x in ("fish", "jellyfish"))
    has_cat = "cat" in p_lower or "kitten" in p_lower
    has_fox = "fox" in p_lower
    has_tree = any(x in p_lower for x in ("tree", "forest", "wood"))
    has_mountain = "mountain" in p_lower
    has_star = any(x in p_lower for x in ("star", "space"))
    has_cloud = any(x in p_lower for x in ("cloud", "sky"))

    for fi in range(num_frames):
        t = fi / max(num_frames - 1, 1)
        img = Image.new("RGB", (w, h))
        draw = ImageDraw.Draw(img)

        # Sky gradient
        sky_top = (5, 2, 20) if is_night else ((255, 150, 50) if is_sunset else (60, 100, 200))
        sky_bot = (20, 10, 50) if is_night else ((255, 200, 100) if is_sunset else (180, 200, 255))
        for y in range(sky_h):
            ratio = y / sky_h
            r = int(sky_top[0] + (sky_bot[0] - sky_top[0]) * ratio)
            g = int(sky_top[1] + (sky_bot[1] - sky_top[1]) * ratio)
            b = int(sky_top[2] + (sky_bot[2] - sky_top[2]) * ratio)
            draw.line([(0, y), (w, y)], fill=(r, g, b))

        # Stars
        if has_star or is_night:
            for s in range(40):
                sx = int((math.sin(s * 7.3 + fi * 0.02) * 0.5 + 0.5) * w)
                sy = int((math.cos(s * 5.1 + fi * 0.03) * 0.5 + 0.5) * sky_h * 0.7)
                sz = (s % 3) + 1
                bright = 180 + int(math.sin(fi * 0.1 + s) * 75)
                draw.ellipse([sx - sz, sy - sz, sx + sz, sy + sz], fill=(bright, bright, int(bright * 0.8)))

        # Sun/moon
        if is_sunset:
            sx = int(w * (0.3 + 0.4 * math.sin(fi * 0.02)))
            sy = int(sky_h * 0.7 - 10 * math.sin(fi * 0.03))
            draw.ellipse([sx - 40, sy - 40, sx + 40, sy + 40], fill=(255, 220, 50))
            for ri in range(3, 7):
                a = 60 - ri * 8
                draw.ellipse([sx - 40 * ri, sy - 40 * ri, sx + 40 * ri, sy + 40 * ri],
                             fill=(255, 200, 50, max(0, a)))

        # Clouds
        if has_cloud or not is_night:
            for ci in range(3):
                cx = int(w * ((ci * 0.37 + math.sin(fi * 0.01 + ci)) % 1.0))
                cy = int(sky_h * 0.2 * (0.5 + ci * 0.25)) + int(5 * math.sin(fi * 0.03 + ci))
                cr = 30 + ci * 10
                for dx, dy in [(0, 0), (cr // 2, cr // 4), (-cr // 3, cr // 3)]:
                    draw.ellipse([cx + dx - cr, cy + dy - cr // 2, cx + dx + cr, cy + dy + cr // 2],
                                 fill=(255, 255, 255, 160))

        # Ground / water
        if is_water:
            w_top = (30, 80, 160)
            w_bot = (10, 40, 100)
            for y in range(sky_h, h):
                ratio = (y - sky_h) / (h - sky_h)
                r = int(w_top[0] + (w_bot[0] - w_top[0]) * ratio)
                g = int(w_top[1] + (w_bot[1] - w_top[1]) * ratio)
                b = int(w_top[2] + (w_bot[2] - w_top[2]) * ratio)
                wave = int(math.sin((y - sky_h) * 0.15 + fi * 0.3) * 12)
                draw.line([(0, y), (w, y)], fill=(r, g + wave, b + wave))
            # Water highlights
            for wi in range(10):
                wx = int(w * ((wi * 0.13 + math.sin(fi * 0.05 + wi)) % 1.0))
                wy = sky_h + int((h - sky_h) * (0.1 + 0.8 * (wi / 10))) + int(8 * math.sin(fi * 0.1 + wi))
                wlen = 30 + int(15 * math.sin(fi * 0.07 + wi))
                alpha = 40 + int(30 * math.sin(fi * 0.12 + wi * 2))
                draw.line([(wx, wy), (wx + wlen, wy)], fill=(180, 220, 255, alpha), width=1)
        else:
            g_top = (60, 120, 40)
            g_bot = (20, 50, 15)
            for y in range(sky_h, h):
                ratio = (y - sky_h) / (h - sky_h)
                r = int(g_top[0] + (g_bot[0] - g_top[0]) * ratio)
                g = int(g_top[1] + (g_bot[1] - g_top[1]) * ratio)
                b = int(g_top[2] + (g_bot[2] - g_top[2]) * ratio)
                draw.line([(0, y), (w, y)], fill=(r, g, b))

        # Mountains
        if has_mountain:
            for mi in range(2):
                mx = int(w * (0.2 + 0.6 * mi))
                mh = 120 + mi * 40 + int(10 * math.sin(fi * 0.02 + mi))
                mw = 180 + mi * 40
                mt = (80 + mi * 20, 80 + mi * 15, 100 + mi * 20)
                draw.polygon([(mx - mw, sky_h), (mx, sky_h - mh), (mx + mw, sky_h)], fill=mt)

        # Trees
        if has_tree:
            for ti in range(3):
                tx = int(w * (0.2 + 0.3 * ti) + int(5 * math.sin(fi * 0.02 + ti)))
                ty = sky_h + 20 + int(3 * math.sin(fi * 0.04 + ti))
                th = 50 + ti * 10
                draw.rectangle([tx - 5, ty - th, tx + 5, ty], fill=(50, 35, 15))
                cr = 25 + ti * 8
                draw.ellipse([tx - cr, ty - th - cr + 10, tx + cr, ty - th + cr // 2 + 10],
                             fill=(30, 80 + ti * 20, 25))

        # Animated subject - Duck
        if has_duck:
            dx = int(w * 0.2 + w * 0.4 * (0.5 + 0.5 * math.sin(fi * 0.08)))
            dy = sky_h + 20 + int(8 * math.sin(fi * 0.15))
            body_c = (220, 190, 40) if "duck" in p_lower else (255, 255, 255)
            head_c = (30, 120, 30) if "duck" in p_lower else (255, 255, 255)
            draw.ellipse([dx - 18, dy - 8, dx + 18, dy + 8], fill=body_c)
            draw.ellipse([dx - 10, dy - 22, dx + 12, dy - 4], fill=head_c)
            draw.polygon([(dx + 10, dy - 18), (dx + 22, dy - 20), (dx + 10, dy - 12)], fill=(255, 180, 0))
            # neck bob
            bob = int(3 * math.sin(fi * 0.2))
            draw.ellipse([dx - 6, dy - 22 + bob, dx + 8, dy - 6 + bob], fill=head_c)

        # Animated subject - Dragon
        if has_dragon:
            dx = int(w * 0.5 + w * 0.35 * math.sin(fi * 0.06))
            dy = int(sky_h * 0.3 + sky_h * 0.2 * math.sin(fi * 0.07 + 1))
            d_c = (180, 30, 20)
            draw.ellipse([dx - 18, dy - 6, dx + 18, dy + 6], fill=d_c)
            draw.ellipse([dx - 10, dy - 20, dx + 10, dy - 4], fill=d_c)
            draw.polygon([(dx + 8, dy - 20), (dx + 22, dy - 24), (dx + 8, dy - 12)], fill=d_c)
            draw.polygon([(dx - 8, dy - 20), (dx - 22, dy - 24), (dx - 8, dy - 12)], fill=d_c)
            draw.polygon([(dx + 14, dy - 4), (dx + 35, dy), (dx + 14, dy + 4)], fill=(255, 100, 0))
            # tail sway
            tx = dx - 18 + int(6 * math.sin(fi * 0.12))
            ty = dy + int(4 * math.cos(fi * 0.1))
            draw.polygon([(dx - 18, dy - 6), (tx - 10, ty - 12), (dx - 12, dy + 4)], fill=d_c)

        # Animated subject - Fish
        if has_fish:
            for fi2 in range(4):
                fx = int(w * ((fi2 * 0.28 + math.sin(fi * 0.05 + fi2 * 2)) % 1.0))
                fy = sky_h + 50 + int(80 * fi2) + int(10 * math.sin(fi * 0.08 + fi2))
                fc = (50 + fi2 * 40, 120 + fi2 * 20, 200)
                draw.ellipse([fx - 10, fy - 5, fx + 10, fy + 5], fill=fc)
                draw.polygon([(fx + 8, fy), (fx + 18, fy - 5), (fx + 18, fy + 5)], fill=fc)
                tail = int(4 * math.sin(fi * 0.2 + fi2))
                draw.polygon([(fx - 10, fy), (fx - 18, fy - 4 + tail), (fx - 18, fy + 4 - tail)], fill=fc)

        # Animated subject - Cat
        if has_cat:
            cx = int(w * 0.3 + w * 0.4 * (0.5 + 0.5 * math.sin(fi * 0.04)))
            cy = sky_h + 40 + int(5 * math.sin(fi * 0.1))
            c = (180 + int(30 * math.sin(fi * 0.03)), 140, 100)
            draw.ellipse([cx - 16, cy - 8, cx + 16, cy + 8], fill=c)
            draw.ellipse([cx - 8, cy - 20, cx + 8, cy - 6], fill=c)
            draw.polygon([(cx - 8, cy - 20), (cx - 12, cy - 28), (cx - 4, cy - 22)], fill=c)
            draw.polygon([(cx + 8, cy - 20), (cx + 12, cy - 28), (cx + 4, cy - 22)], fill=c)
            draw.ellipse([cx - 4, cy - 18, cx - 1, cy - 15], fill=(50, 200, 50))
            draw.ellipse([cx + 1, cy - 18, cx + 4, cy - 15], fill=(50, 200, 50))
            # tail
            tail_x = cx + 16 + int(8 * math.sin(fi * 0.15))
            tail_y = cy - 4 + int(6 * math.cos(fi * 0.12))
            draw.line([(cx + 14, cy - 2), (tail_x + 10, tail_y - 8)], fill=c, width=3)

        # Animated subject - Fox
        if has_fox:
            fx = int(w * 0.3 + w * 0.3 * math.sin(fi * 0.05))
            fy = sky_h + 30 + int(4 * math.sin(fi * 0.12 + 1))
            fc = (210, 100, 35)
            draw.ellipse([fx - 14, fy - 8, fx + 14, fy + 8], fill=fc)
            draw.ellipse([fx - 8, fy - 18, fx + 8, fy - 4], fill=fc)
            draw.polygon([(fx - 8, fy - 18), (fx - 14, fy - 28), (fx - 2, fy - 20)], fill=fc)
            draw.polygon([(fx + 8, fy - 18), (fx + 14, fy - 28), (fx + 2, fy - 20)], fill=fc)
            draw.ellipse([fx - 3, fy - 16, fx - 1, fy - 14], fill=(0, 0, 0))
            draw.ellipse([fx + 1, fy - 16, fx + 3, fy - 14], fill=(0, 0, 0))
            draw.polygon([(fx - 4, fy + 4), (fx, fy + 14), (fx + 4, fy + 4)], fill=(255, 255, 255))
            # tail
            ftx = fx + 14 + int(10 * math.sin(fi * 0.1))
            fty = fy - 4 + int(6 * math.cos(fi * 0.08))
            draw.ellipse([ftx + 4, fty - 6, ftx + 14, fty + 4], fill=(255, 200, 180))

        frames.append(np.array(img))

    return frames
