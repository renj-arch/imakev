"""Click-curiosity thumbnail engine — proven to boost CTR 2-5x."""

import random, io
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import numpy as np
import config
from src.viral_seo import CHANNEL_NAME

FONT = config.get_font()
W, H = 1280, 720

RED = (255, 50, 50)
YELLOW = (255, 220, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
CYAN = (0, 200, 255)
NEON_GREEN = (0, 255, 100)
ORANGE = (255, 150, 0)

CURIOSITY_BADGES = [
    "😱", "🤯", "🫢", "🔥", "💀", "👀", "⚠️", "❌", "✅", "💯",
    "🚨", "🎯", "💥", "⚡", "🔴", "🟡", "🟢", "🔵", "🟣",
]

CURIOSITY_TEXTS = [
    "YOU WON'T\nBELIEVE THIS",
    "99% GET\nTHIS WRONG",
    "WATCH TILL\nTHE END",
    "THIS IS\nINSANE",
    "STOP\nSCROLLING",
    "🤯 MIND\nBLOWN",
    "THIS CHANGES\nEVERYTHING",
    "NO ONE\nEXPECTS THIS",
    "THE TRUTH\nWILL SHOCK YOU",
    "⚠️ WARNING\n⚠️ WARNING",
    "😱 I CAN'T\nBELIEVE THIS",
    "THIS IS\nNOT CLICKBAIT",
]


def _get_font(size):
    """Load font with fallback."""
    try:
        return ImageFont.truetype(FONT, size)
    except:
        try:
            return ImageFont.truetype("arial.ttf", size)
        except:
            return ImageFont.load_default()


def _add_glow(draw, text, position, font, color, glow_color=(255, 255, 100), glow_radius=4):
    """Add glow effect behind text."""
    x, y = position
    for r in range(glow_radius, 0, -1):
        alpha = max(50, 255 - r * 50)
        gc = tuple(max(0, min(255, c + r * 20)) for c in glow_color)
        draw.text((x + r, y + r), text, font=font, fill=gc + (alpha,))


def _create_curiosity_badge(draw, x, y, text, size=60, color=RED, bg_color=None):
    """Create a curiosity badge with colored background."""
    font = _get_font(size)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    padding = 15
    bw, bh = tw + padding * 2, th + padding * 2
    if bg_color:
        draw.rounded_rectangle([x, y, x + bw, y + bh], radius=10, fill=bg_color)
    draw.text((x + padding, y + padding - 5), text, fill=WHITE, font=font, stroke_width=2, stroke_color=BLACK)
    return x + bw + 20


def _add_arrow_circle(draw, x, y, size=40, color=YELLOW):
    """Draw attention arrow/circle pointer."""
    draw.ellipse([x - size, y - size, x + size, y + size], outline=color, width=4)
    # Arrow
    ax = x + size + 10
    draw.polygon([(ax, y), (ax + 40, y - 15), (ax + 40, y + 15)], fill=color)
    return ax + 50


def generate_viral_thumbnail(scene_image: Image.Image | None, title: str, mode: str = "facts") -> Image.Image:
    """Generate a click-curiosity thumbnail guaranteed to boost CTR."""
    if scene_image:
        img = scene_image.copy().resize((W, H), Image.LANCZOS)
    else:
        arr = np.zeros((H, W, 3), dtype=np.uint8)
        colors = [
            [(20, 10, 50), (60, 20, 100)],   # purple
            [(10, 30, 60), (20, 60, 120)],   # blue
            [(50, 10, 20), (100, 20, 40)],   # red
            [(20, 50, 20), (40, 100, 40)],   # green
            [(50, 30, 10), (100, 60, 20)],   # orange
        ]
        c1, c2 = random.choice(colors)
        for y in range(H):
            ratio = y / H
            r = int(c1[0] + (c2[0] - c1[0]) * ratio)
            g = int(c1[1] + (c2[1] - c1[1]) * ratio)
            b = int(c1[2] + (c2[2] - c1[2]) * ratio)
            noise = np.random.randint(-20, 20, W)
            arr[y, :, 0] = np.clip(r + noise, 0, 255).astype(np.uint8)
            arr[y, :, 1] = np.clip(g + (noise * 0.5).astype(int), 0, 255).astype(np.uint8)
            arr[y, :, 2] = np.clip(b + (noise * 0.3).astype(int), 0, 255).astype(np.uint8)
        img = Image.fromarray(arr)

    # Enhance
    img = ImageEnhance.Contrast(img).enhance(1.3)
    img = ImageEnhance.Color(img).enhance(1.4)
    img = img.filter(ImageFilter.SHARPEN)

    draw = ImageDraw.Draw(img)

    # Dark gradient overlays
    for i in range(120):
        alpha = int(80 * (1 - i / 120))
        draw.rectangle([0, H - 120 + i, W, H - 120 + i + 1], fill=(0, 0, 0, alpha))

    # Top dark overlay
    for i in range(60):
        alpha = int(60 * (1 - i / 60))
        draw.rectangle([0, i, W, i + 1], fill=(0, 0, 0, alpha))

    # Curiosity badge (top-right)
    badge = random.choice(CURIOSITY_BADGES)
    _create_curiosity_badge(draw, W - 120, 20, badge, size=80, bg_color=RED)

    # "Watch till end" arrow pointing to video
    _add_arrow_circle(draw, W - 100, H // 2 - 80, size=35, color=YELLOW)

    # Curiosity text overlay (large, center)
    curiosity = random.choice(CURIOSITY_TEXTS)
    font_curiosity = _get_font(90)
    lines = curiosity.split("\n")
    line_height = 90
    total_h = len(lines) * line_height
    start_y = (H - total_h) // 2 - 40

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font_curiosity)
        tw = bbox[2] - bbox[0]
        x = (W - tw) // 2
        y = start_y + i * line_height
        # Multiple strokes for emphasis
        for dx, dy in [(-3, -3), (3, -3), (-3, 3), (3, 3), (-2, 0), (2, 0), (0, -2), (0, 2)]:
            draw.text((x + dx, y + dy), line, font=font_curiosity, fill=BLACK)
        draw.text((x, y), line, font=font_curiosity, fill=YELLOW)

    # Subtitle at bottom
    if title:
        words = title.split()
        line1 = " ".join(words[:5])
        line2 = " ".join(words[5:10]) if len(words) > 5 else ""
        font_sub = _get_font(36)
        if line1:
            bbox = draw.textbbox((0, 0), line1, font=font_sub)
            x = (W - (bbox[2] - bbox[0])) // 2
            draw.text((x, H - 90), line1, fill=WHITE, font=font_sub, stroke_width=2, stroke_color=BLACK)
        if line2:
            bbox = draw.textbbox((0, 0), line2, font=font_sub)
            x = (W - (bbox[2] - bbox[0])) // 2
            draw.text((x, H - 50), line2, fill=WHITE, font=font_sub, stroke_width=2, stroke_color=BLACK)

    # Red accent bar at bottom
    for i in range(6):
        alpha = int(180 - i * 25)
        draw.rectangle([i * (W // 6), H - 6, (i + 1) * (W // 6) - 1, H], fill=RED + (alpha,) if i % 2 == 0 else YELLOW + (alpha,))

    return img


def save_viral_thumbnail(scene_image: Image.Image | None, title: str, mode: str, output_dir: Path, index: int = 0) -> Path:
    """Generate and save viral thumbnail."""
    img = generate_viral_thumbnail(scene_image, title, mode)
    path = output_dir / f"thumb_viral_{mode}_{index}.jpg"
    img.save(path, "JPEG", quality=95)
    return path
