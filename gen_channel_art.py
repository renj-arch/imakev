"""Generate YouTube channel logo (800x800) and banner (2048x1152) for Ding Dong Think."""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw, ImageFont
from gen_characters import draw_ding, draw_dong, draw_owl

CHANNEL_NAME = "Ding Dong Think"
OUT_DIR = "output"

def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def make_gradient(draw, w, h, colors, vertical=True):
    for i in range(h if vertical else w):
        ratio = i / (h if vertical else w)
        idx = ratio * (len(colors) - 1)
        c0 = colors[int(idx)]
        c1 = colors[min(int(idx) + 1, len(colors) - 1)]
        fr = idx - int(idx)
        r = int(c0[0] + (c1[0] - c0[0]) * fr)
        g = int(c0[1] + (c1[1] - c0[1]) * fr)
        b = int(c0[2] + (c1[2] - c0[2]) * fr)
        if vertical:
            draw.line([(0, i), (w, i)], fill=(r, g, b))
        else:
            draw.line([(i, 0), (i, h)], fill=(r, g, b))

def draw_stars(draw, w, h, count=30, seed=42):
    import random
    rng = random.Random(seed)
    for _ in range(count):
        x = rng.randint(0, w)
        y = rng.randint(0, h)
        r = rng.randint(1, 3)
        alpha = rng.randint(80, 220)
        draw.ellipse([x-r, y-r, x+r, y+r], fill=(255, 255, 200, alpha))

def draw_decorative_circles(draw, w, h, count=8, seed=99):
    import random
    rng = random.Random(seed)
    for _ in range(count):
        x = rng.randint(0, w)
        y = rng.randint(0, h)
        r = rng.randint(15, 60)
        alpha = rng.randint(20, 60)
        colors = [(60, 140, 220), (200, 100, 180), (255, 200, 60)]
        c = rng.choice(colors)
        draw.ellipse([x-r, y-r, x+r, y+r], outline=c + (alpha,), width=2)

def generate_logo():
    size = 800
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img, "RGBA")

    # Dark background with radial vignette
    bg = Image.new("RGB", (size, size), (20, 18, 30))
    bg_draw = ImageDraw.Draw(bg, "RGBA")
    make_gradient(bg_draw, size, size, [(20, 18, 30), (35, 30, 55), (25, 22, 40)])
    # Vignette overlay
    for i in range(size // 2):
        alpha = int(80 * (1 - i / (size // 2)))
        draw.ellipse([i, i, size-i, size-i], outline=(0, 0, 0, alpha), width=1)
    bg.paste(img, (0, 0), img)
    img = bg
    draw = ImageDraw.Draw(img, "RGBA")

    # Decorative elements
    draw_stars(draw, size, size, count=25)
    draw_decorative_circles(draw, size, size, count=6)

    # Characters arrangement: Ding (left), Think (center high), Dong (right)
    cy = 280
    cx = size // 2

    # Think the owl (center, largest)
    think_scale = 2.8
    draw_owl(draw, cx, cy - 30, s=think_scale)

    # Ding (left)
    ding_scale = 2.0
    draw_ding(draw, cx - 170, cy + 40, s=ding_scale)

    # Dong (right)
    dong_scale = 2.0
    draw_dong(draw, cx + 170, cy + 40, s=dong_scale)

    # Colored accent lines behind characters
    draw.arc([cx - 200, cy - 80, cx - 80, cy + 40], 180, 270, fill=(60, 140, 220, 120), width=4)
    draw.arc([cx + 80, cy - 80, cx + 200, cy + 40], 270, 360, fill=(200, 100, 180, 120), width=4)
    draw.arc([cx - 70, cy - 140, cx + 70, cy], 0, 180, fill=(255, 200, 60, 120), width=4)

    # Title text
    font_size = 52
    font = None
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()

    # Shadow text
    tw = draw.textbbox((0, 0), CHANNEL_NAME, font=font)
    tw_w = tw[2] - tw[0]
    tx = (size - tw_w) // 2
    ty = 640
    for dx, dy in [(2, 2), (-1, 1), (1, -1)]:
        draw.text((tx + dx, ty + dy), CHANNEL_NAME, fill=(0, 0, 0, 100), font=font)
    draw.text((tx, ty), CHANNEL_NAME, fill=(255, 255, 255, 230), font=font)

    # Tagline
    tagline = "Storyteller | Reflector | Curious"
    font_s = 22
    font2 = None
    try:
        font2 = ImageFont.truetype("arial.ttf", font_s)
    except:
        font2 = font
    tg = draw.textbbox((0, 0), tagline, font=font2)
    tg_w = tg[2] - tg[0]
    draw.text(((size - tg_w) // 2, ty + 55), tagline, fill=(180, 180, 200, 180), font=font2)

    out = os.path.join(OUT_DIR, "yt_logo.png")
    img.save(out)
    print(f"Logo saved: {out} ({img.size})")
    return out

def generate_banner():
    bw, bh = 2048, 1152
    img = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img, "RGBA")

    # Gradient background
    make_gradient(draw, bw, bh, [
        (15, 12, 25), (25, 20, 45), (60, 50, 80),
        (80, 60, 100), (50, 40, 70), (25, 20, 45)
    ])
    draw_stars(draw, bw, bh, count=60)
    draw_decorative_circles(draw, bw, bh, count=12)

    # Subtle horizontal bands of color
    for y_offset, color, alpha in [
        (bh * 0.15, (60, 140, 220), 30),
        (bh * 0.45, (200, 100, 180), 30),
        (bh * 0.75, (255, 200, 60), 30)
    ]:
        for x in range(bw):
            for y in range(int(y_offset - 30), int(y_offset + 30)):
                if 0 <= y < bh:
                    draw.point((x, y), fill=color + (alpha,))

    # Three characters spread across banner
    # Think (center)
    draw_owl(draw, bw // 2, bh // 2 + 40, s=2.5)

    # Ding (left third)
    draw_ding(draw, bw // 2 - 350, bh // 2 + 40, s=2.0)

    # Dong (right third)
    draw_dong(draw, bw // 2 + 350, bh // 2 + 40, s=2.0)

    # Channel name - large centered
    font_size = 96
    font = None
    try:
        font = ImageFont.truetype("arialbd.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()

    # Shadow
    tw = draw.textbbox((0, 0), CHANNEL_NAME, font=font)
    tw_w = tw[2] - tw[0]
    tx = (bw - tw_w) // 2
    ty = bh - 220
    for dx, dy in [(4, 4), (-2, 2), (2, -2)]:
        draw.text((tx + dx, ty + dy), CHANNEL_NAME, fill=(0, 0, 0, 120), font=font)
    draw.text((tx, ty), CHANNEL_NAME, fill=(255, 255, 255, 240), font=font)

    # Tagline below
    tagline = "Three Voices. One Story. Endless Curiosity."
    font_t = 38
    font2 = None
    try:
        font2 = ImageFont.truetype("arial.ttf", font_t)
    except:
        font2 = font
    tg = draw.textbbox((0, 0), tagline, font=font2)
    tg_w = tg[2] - tg[0]
    draw.text(((bw - tg_w) // 2, ty + 110), tagline, fill=(200, 200, 220, 180), font=font2)

    out = os.path.join(OUT_DIR, "yt_banner.png")
    img.save(out)
    print(f"Banner saved: {out} ({img.size})")
    return out

if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    generate_logo()
    generate_banner()
