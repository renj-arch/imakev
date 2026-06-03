"""Centralized image generation — tries Pollinations.ai, falls back to procedural scene drawing."""
import io, time, random, math
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import numpy as np
import requests as req
import config

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}?width={w}&height={h}&model={model}&seed={seed}"
MAX_RETRIES = 1
RETRY_DELAY = 2


def gen_img(prompt: str, width: int = None, height: int = None) -> Image.Image:
    w = width or config.VIDEO_WIDTH
    h = height or config.VIDEO_HEIGHT
    for model in ("flux", "sana"):
        img = _try_pollinations(prompt, w, h, model)
        if img is not None:
            return img
    return _generate_scene(w, h, prompt)


def _try_pollinations(prompt: str, w: int, h: int, model: str, timeout: int = 30) -> Image.Image | None:
    for attempt in range(MAX_RETRIES):
        seed = random.randint(0, 999999)
        url = POLLINATIONS_URL.format(prompt=req.utils.quote(prompt), w=w, h=h, model=model, seed=seed)
        try:
            r = req.get(url, timeout=timeout)
            if r.status_code == 200 and len(r.content) > 500:
                img = Image.open(io.BytesIO(r.content)).convert("RGB")
                img = img.resize((w, h), Image.LANCZOS)
                img = ImageEnhance.Contrast(img).enhance(1.3)
                return img
        except Exception:
            pass
        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAY)
    return None


def _generate_scene(w: int, h: int, prompt: str = "") -> Image.Image:
    seed = hash(prompt) & 0xFFFFFFFF
    rng = random.Random(seed)
    p_lower = prompt.lower()

    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)

    _draw_sky(draw, w, h, rng, p_lower)
    _draw_ground(draw, w, h, rng, p_lower)
    _draw_scene_elements(draw, w, h, rng, p_lower)

    return img.filter(ImageFilter.SMOOTH)


def _draw_sky(draw, w, h, rng, prompt):
    sky_h = int(h * (0.5 + rng.random() * 0.2))
    top = (rng.randint(20, 80), rng.randint(20, 80), rng.randint(60, 180))
    bottom = (rng.randint(100, 255), rng.randint(100, 255), rng.randint(150, 255))
    if "night" in prompt or "dark" in prompt or "space" in prompt:
        top = (5, 2, 20)
        bottom = (20, 10, 50)
    elif "sunset" in prompt or "sunrise" in prompt or "golden" in prompt:
        top = (255, 150, 50)
        bottom = (255, 200, 100)

    for y in range(sky_h):
        t = y / sky_h
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    if "star" in prompt or "night" in prompt or "space" in prompt:
        for _ in range(rng.randint(30, 80)):
            sx = rng.randint(0, w - 1)
            sy = rng.randint(0, int(sky_h * 0.8))
            sz = rng.randint(1, 3)
            draw.ellipse([sx - sz, sy - sz, sx + sz, sy + sz], fill=(255, 255, 200))

    if "sun" in prompt or "sunset" in prompt or "sunrise" in prompt:
        sx = rng.randint(w // 3, 2 * w // 3)
        sy = int(sky_h * 0.7)
        sr = rng.randint(30, 60)
        draw.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=(255, 220, 50))
        for i in range(3, 8):
            a = rng.randint(20, 80)
            draw.ellipse([sx - sr * i, sy - sr * i, sx + sr * i, sy + sr * i],
                         fill=(255, 200, 50, a) if hasattr(Image, 'RGBA') else (255, 200, 50))

    if "moon" in prompt or "night" in prompt:
        mx = rng.randint(w // 4, 3 * w // 4)
        my = rng.randint(30, int(sky_h * 0.4))
        mr = rng.randint(20, 40)
        draw.ellipse([mx - mr, my - mr, mx + mr, my + mr], fill=(240, 240, 220))
        draw.ellipse([mx - mr + 5, my - mr - 5, mx + mr - 5, my + mr - 5], fill=(top if 'top' in dir() else (5, 2, 20)))

    if "cloud" in prompt or "sky" in prompt:
        for _ in range(rng.randint(2, 5)):
            cx = rng.randint(0, w)
            cy = rng.randint(10, int(sky_h * 0.5))
            cr = rng.randint(20, 50)
            for dx, dy in [(0, 0), (cr // 2, cr // 4), (-cr // 3, cr // 3), (cr // 3, cr // 3)]:
                draw.ellipse([cx + dx - cr, cy + dy - cr // 2, cx + dx + cr, cy + dy + cr // 2],
                             fill=(255, 255, 255, 180))


def _draw_ground(draw, w, h, rng, prompt):
    sky_h = int(h * (0.5 + rng.random() * 0.2))
    ground_h = h - sky_h

    top = (rng.randint(30, 120), rng.randint(60, 150), rng.randint(20, 80))
    bottom = (rng.randint(10, 50), rng.randint(30, 80), rng.randint(5, 30))

    if "water" in prompt or "ocean" in prompt or "sea" in prompt or "pond" in prompt or "lake" in prompt or "river" in prompt:
        top = (rng.randint(20, 80), rng.randint(60, 160), rng.randint(120, 220))
        bottom = (rng.randint(5, 30), rng.randint(30, 80), rng.randint(80, 150))
        for y in range(sky_h, h):
            t = (y - sky_h) / ground_h
            r = int(top[0] + (bottom[0] - top[0]) * t)
            g = int(top[1] + (bottom[1] - top[1]) * t)
            b = int(top[2] + (bottom[2] - top[2]) * t)
            wave = int(math.sin((y - sky_h) * 0.2 + seed_hash(prompt, 1)) * 15)
            draw.line([(0, y), (w, y)], fill=(r, g + wave, b + wave))
        for _ in range(rng.randint(5, 15)):
            wx = rng.randint(0, w)
            wy = rng.randint(sky_h + 10, h - 10)
            wlen = rng.randint(20, 60)
            w_alpha = rng.randint(30, 80)
            draw.line([(wx, wy), (wx + wlen, wy)],
                      fill=(180, 220, 255, w_alpha), width=1)
        return

    if "snow" in prompt or "ice" in prompt:
        top = (200, 220, 240)
        bottom = (240, 245, 255)

    for y in range(sky_h, h):
        t = (y - sky_h) / ground_h
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    if "grass" in prompt or "field" in prompt or "forest" in prompt:
        for _ in range(rng.randint(50, 150)):
            gx = rng.randint(0, w)
            gy = rng.randint(sky_h, h - 1)
            gh = rng.randint(5, 20)
            gc = (rng.randint(30, 100), rng.randint(80, 180), rng.randint(20, 60))
            draw.line([(gx, gy), (gx + rng.randint(-3, 3), gy - gh)], fill=gc, width=1)


def _draw_scene_elements(draw, w, h, rng, prompt):
    sky_h = int(h * (0.5 + rng.random() * 0.2))

    if "tree" in prompt or "forest" in prompt:
        for _ in range(rng.randint(1, 4)):
            tx = rng.randint(50, w - 50)
            ty = sky_h + rng.randint(-20, 30)
            trunk_h = rng.randint(40, 80)
            trunk_w = rng.randint(8, 15)
            draw.rectangle([tx - trunk_w // 2, ty - trunk_h, tx + trunk_w // 2, ty], fill=(60, 40, 20))
            crown_r = rng.randint(30, 60)
            crown_c = (rng.randint(20, 60), rng.randint(80, 160), rng.randint(20, 50))
            draw.ellipse([tx - crown_r, ty - trunk_h - crown_r, tx + crown_r, ty - trunk_h + crown_r // 2], fill=crown_c)

    if "mountain" in prompt or "mountains" in prompt:
        for _ in range(rng.randint(1, 3)):
            mt_x = rng.randint(0, w)
            mt_h = rng.randint(80, 200)
            mt_w = rng.randint(100, 250)
            mt_color = (rng.randint(60, 100), rng.randint(60, 100), rng.randint(80, 120))
            points = [(mt_x - mt_w, sky_h), (mt_x, sky_h - mt_h), (mt_x + mt_w, sky_h)]
            draw.polygon(points, fill=mt_color)
            if rng.random() > 0.5:
                points2 = [(mt_x - mt_w // 2, sky_h), (mt_x, sky_h - mt_h + rng.randint(20, 50)), (mt_x + mt_w // 2, sky_h)]
                draw.polygon(points2, fill=(100, 100, 140))

    if "duck" in prompt or "bird" in prompt or "swan" in prompt or "goose" in prompt:
        by = sky_h + rng.randint(20, 80)
        bx = rng.randint(w // 3, 2 * w // 3)
        body_c = (rng.randint(180, 255), rng.randint(180, 220), rng.randint(0, 80))
        if "swan" in prompt:
            body_c = (255, 255, 255)
        elif "duck" in prompt:
            body_c = (rng.randint(180, 220), rng.randint(180, 200), rng.randint(20, 60))
        draw.ellipse([bx - 15, by - 8, bx + 15, by + 8], fill=body_c)
        draw.ellipse([bx + 10, by - 12, bx + 22, by + 2], fill=body_c)
        head_c = body_c if "swan" not in prompt else (255, 255, 255)
        draw.ellipse([bx + 18, by - 16, bx + 30, by - 4], fill=head_c)
        draw.polygon([(bx + 28, by - 14), (bx + 38, by - 16), (bx + 28, by - 8)], fill=(255, 200, 0))

    if "cat" in prompt or "kitten" in prompt:
        cx = rng.randint(w // 3, 2 * w // 3)
        cy = sky_h + rng.randint(20, 100)
        c = (rng.randint(150, 220), rng.randint(120, 180), rng.randint(80, 140))
        draw.ellipse([cx - 15, cy - 10, cx + 15, cy + 10], fill=c)
        draw.ellipse([cx - 10, cy - 22, cx + 10, cy - 6], fill=c)
        draw.polygon([(cx - 10, cy - 22), (cx - 14, cy - 30), (cx - 6, cy - 24)], fill=c)
        draw.polygon([(cx + 10, cy - 22), (cx + 14, cy - 30), (cx + 6, cy - 24)], fill=c)
        draw.ellipse([cx - 5, cy - 20, cx - 2, cy - 17], fill=(50, 200, 50))
        draw.ellipse([cx + 2, cy - 20, cx + 5, cy - 17], fill=(50, 200, 50))
        draw.ellipse([cx - 3, cy - 19, cx - 2, cy - 18], fill=(0, 0, 0))
        draw.ellipse([cx + 2, cy - 19, cx + 3, cy - 18], fill=(0, 0, 0))

    if "dragon" in prompt:
        dx = rng.randint(w // 4, 3 * w // 4)
        dy = rng.randint(30, sky_h - 30)
        d_c = (rng.randint(100, 200), rng.randint(0, 50), rng.randint(0, 30))
        draw.ellipse([dx - 20, dy - 8, dx + 20, dy + 8], fill=d_c)
        draw.ellipse([dx - 12, dy - 25, dx + 12, dy - 5], fill=d_c)
        draw.polygon([(dx + 10, dy - 25), (dx + 25, dy - 30), (dx + 10, dy - 15)], fill=d_c)
        draw.polygon([(dx - 10, dy - 25), (dx - 25, dy - 30), (dx - 10, dy - 15)], fill=d_c)
        draw.polygon([(dx + 15, dy - 8), (dx + 40, dy - 3), (dx + 15, dy + 3)], fill=(255, 100, 0))
        draw.polygon([(dx - 20, dy - 8), (dx - 20, dy - 20), (dx - 12, dy - 12)], fill=d_c)

    if "fish" in prompt or "jellyfish" in prompt or "ocean" in prompt or "sea" in prompt:
        for _ in range(rng.randint(2, 5)):
            fx = rng.randint(30, w - 30)
            fy = rng.randint(sky_h + 30, h - 30)
            fc = (rng.randint(50, 200), rng.randint(100, 220), rng.randint(150, 255))
            draw.ellipse([fx - 12, fy - 6, fx + 12, fy + 6], fill=fc)
            draw.polygon([(fx + 10, fy), (fx + 22, fy - 6), (fx + 22, fy + 6)], fill=fc)
            draw.ellipse([fx - 4, fy - 2, fx - 1, fy + 2], fill=(0, 0, 0))

    if "flower" in prompt or "garden" in prompt or "spring" in prompt:
        for _ in range(rng.randint(5, 15)):
            flx = rng.randint(10, w - 10)
            fly = rng.randint(sky_h + 10, h - 10)
            fc = (rng.randint(150, 255), rng.randint(50, 200), rng.randint(100, 255))
            draw.ellipse([flx - 4, fly - 2, flx + 4, fly + 2], fill=(30, 120, 30))
            for angle in range(0, 360, 60):
                rad = math.radians(angle)
                px = flx + int(math.cos(rad) * 5)
                py = fly + int(math.sin(rad) * 5)
                draw.ellipse([px - 3, py - 3, px + 3, py + 3], fill=fc)

    if "butterfly" in prompt:
        for _ in range(rng.randint(1, 3)):
            bx = rng.randint(30, w - 30)
            by = rng.randint(30, h - 30)
            bc = (rng.randint(150, 255), rng.randint(50, 200), rng.randint(50, 200))
            draw.ellipse([bx - 8, by - 2, bx + 8, by + 2], fill=(30, 30, 30))
            draw.ellipse([bx - 8, by - 6, bx - 1, by + 6], fill=bc)
            draw.ellipse([bx + 1, by - 6, bx + 8, by + 6], fill=bc)

    if "fox" in prompt:
        f_color = (rng.randint(180, 230), rng.randint(80, 120), rng.randint(20, 50))
        fx = rng.randint(w // 3, 2 * w // 3)
        fy = sky_h + rng.randint(20, 80)
        draw.ellipse([fx - 14, fy - 8, fx + 14, fy + 8], fill=f_color)
        draw.ellipse([fx - 8, fy - 18, fx + 8, fy - 4], fill=f_color)
        draw.polygon([(fx - 8, fy - 18), (fx - 14, fy - 28), (fx - 2, fy - 20)], fill=f_color)
        draw.polygon([(fx + 8, fy - 18), (fx + 14, fy - 28), (fx + 2, fy - 20)], fill=f_color)
        draw.ellipse([fx - 3, fy - 16, fx - 1, fy - 14], fill=(0, 0, 0))
        draw.ellipse([fx + 1, fy - 16, fx + 3, fy - 14], fill=(0, 0, 0))
        draw.polygon([(fx - 4, fy + 4), (fx, fy + 14), (fx + 4, fy + 4)], fill=(255, 255, 255))

    if "horse" in prompt or "elephant" in prompt:
        hx = rng.randint(w // 3, 2 * w // 3)
        hy = sky_h + rng.randint(20, 80)
        body_c = (rng.randint(80, 150), rng.randint(60, 120), rng.randint(40, 80))
        if "elephant" in prompt:
            body_c = (rng.randint(100, 140), rng.randint(100, 140), rng.randint(100, 140))
        draw.ellipse([hx - 20, hy - 10, hx + 20, hy + 10], fill=body_c)
        draw.ellipse([hx - 16, hy - 22, hx + 4, hy - 4], fill=body_c)
        draw.rectangle([hx - 3, hy + 6, hx + 3, hy + 20], fill=(body_c))
        draw.rectangle([hx + 8, hy + 6, hx + 14, hy + 16], fill=(body_c))
        draw.rectangle([hx - 14, hy + 6, hx - 8, hy + 16], fill=(body_c))
        if "elephant" in prompt:
            draw.line([(hx - 12, hy - 4), (hx - 24, hy - 2), (hx - 28, hy)], fill=body_c, width=3)

    if "city" in prompt or "neon" in prompt or "cyberpunk" in prompt:
        for _ in range(rng.randint(5, 15)):
            bx = rng.randint(10, w - 10)
            bh = rng.randint(30, 150)
            bw = rng.randint(15, 30)
            bc = (rng.randint(20, 60), rng.randint(20, 60), rng.randint(40, 80))
            draw.rectangle([bx - bw // 2, sky_h - bh, bx + bw // 2, sky_h], fill=bc)
            if rng.random() > 0.3:
                wy = rng.randint(sky_h - bh + 5, sky_h - 5)
                ww = rng.randint(3, 8)
                wh = rng.randint(4, 10)
                wc = (rng.randint(200, 255), rng.randint(200, 255), rng.randint(50, 200))
                draw.rectangle([bx - ww // 2, wy - wh, bx + ww // 2, wy], fill=wc)

    if "rain" in prompt:
        for _ in range(rng.randint(30, 80)):
            rx = rng.randint(0, w)
            ry = rng.randint(0, h)
            rlen = rng.randint(10, 25)
            draw.line([(rx, ry), (rx - 2, ry + rlen)], fill=(180, 200, 255, 60), width=1)

    if "fire" in prompt or "flame" in prompt:
        for _ in range(rng.randint(3, 8)):
            fx = rng.randint(30, w - 30)
            fy = rng.randint(sky_h + 20, h - 20)
            fh = rng.randint(20, 50)
            fw = rng.randint(10, 20)
            fc = (rng.randint(200, 255), rng.randint(50, 200), rng.randint(0, 50))
            draw.ellipse([fx - fw // 2, fy - fh, fx + fw // 2, fy], fill=fc)
            draw.ellipse([fx - fw // 3, fy - fh, fx + fw // 3, fy], fill=(255, 255, 100))

    try:
        font = ImageFont.truetype(config.get_font(), 14)
    except Exception:
        font = ImageFont.load_default()
    draw.text((15, 15), "AI Generated", fill=(255, 255, 255, 100), font=font)


def seed_hash(prompt: str, offset: int = 0) -> int:
    return hash(prompt + str(offset)) & 0xFFFFFFFF
