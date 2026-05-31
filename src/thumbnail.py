"""Generate YouTube-optimized thumbnails from video frames or procedurally."""

import random, io
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import numpy as np
import requests as req
import config

FONT = "C:\\Windows\\Fonts\\impact.ttf"
if not Path(FONT).exists():
    FONT = "C:\\Windows\\Fonts\\arialbd.ttf"
if not Path(FONT).exists():
    FONT = "C:\\Windows\\Fonts\\arial.ttf"

W, H = 1280, 720  # YouTube thumbnail size


def generate_thumbnail(chapter: int, story_title: str, scene_images: dict | None = None) -> Image.Image:
    """Generate a clickable YouTube thumbnail."""
    img = None

    # Try to use a generated scene image as base
    if scene_images:
        keys = list(scene_images.keys())
        if keys:
            base = scene_images[random.choice(keys)]
            img = base.resize((W, H), Image.LANCZOS)

    if img is None:
        # Procedural thumbnail
        arr = np.zeros((H, W, 3), dtype=np.uint8)
        for y in range(H):
            ratio = y / H
            r = int(50 + 150 * (1 - ratio) + abs(np.sin(y * 0.01)) * 60)
            g = int(10 + 50 * (1 - ratio) + abs(np.cos(y * 0.008)) * 40)
            b = int(80 + 180 * ratio + abs(np.sin(y * 0.012)) * 50)
            noise = np.random.randint(-20, 20, W)
            arr[y, :, 0] = np.clip(r + noise, 0, 255).astype(np.uint8)
            arr[y, :, 1] = np.clip(g + (noise * 0.5).astype(int), 0, 255).astype(np.uint8)
            arr[y, :, 2] = np.clip(b + (noise * 0.3).astype(int), 0, 255).astype(np.uint8)
        img = Image.fromarray(arr)

    # Apply cinematic effects
    img = ImageEnhance.Contrast(img).enhance(1.4)
    img = ImageEnhance.Color(img).enhance(1.5)
    img = img.filter(ImageFilter.SHARPEN)

    draw = ImageDraw.Draw(img)

    # Dark gradient overlay at bottom
    for i in range(180):
        alpha = int(120 * (1 - i / 180))
        draw.rectangle([0, H - 180 + i, W, H - 180 + i + 1], fill=(0, 0, 0, alpha))

    # Chapter badge (top-left)
    badge_text = f"CH.{chapter}"
    try:
        font_badge = ImageFont.truetype(FONT, 48)
        font_title = ImageFont.truetype(FONT, 52)
        font_sub = ImageFont.truetype(FONT, 28)
    except:
        font_badge = ImageFont.load_default()
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    # Badge background
    badge_bbox = draw.textbbox((0, 0), badge_text, font=font_badge)
    bw, bh = badge_bbox[2] - badge_bbox[0] + 40, badge_bbox[3] - badge_bbox[1] + 20
    draw.rectangle([15, 15, 15 + bw, 15 + bh], fill=(255, 50, 100))
    draw.text((25, 18), badge_text, fill="white", font=font_badge)

    # Main title
    words = story_title.split()
    line1 = " ".join(words[:3])
    line2 = " ".join(words[3:6]) if len(words) > 3 else ""
    draw.text((30, H - 140), line1, fill="white", font=font_title, stroke_width=3, stroke_color="black")
    if line2:
        draw.text((30, H - 80), line2, fill="white", font=font_title, stroke_width=3, stroke_color="black")

    # "NEW" tag
    tag_text = "NEW"
    tag_bbox = draw.textbbox((0, 0), tag_text, font=font_sub)
    tw, th = tag_bbox[2] - tag_bbox[0] + 30, tag_bbox[3] - tag_bbox[1] + 15
    draw.rectangle([W - tw - 15, 15, W - 15, 15 + th], fill=(0, 0, 0, 180))
    draw.text((W - tw - 5, 17), tag_text, fill="white", font=font_sub)

    # Arrow / attention element
    for _ in range(3):
        cx = random.randint(200, W - 200)
        cy = random.randint(100, H - 300)
      # Glowing circle
        for r in range(30, 0, -5):
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 100, 50))

    return img


def save_thumbnail(chapter: int, story_title: str, output_dir: Path, scene_images: dict | None = None) -> Path:
    """Generate and save thumbnail."""
    img = generate_thumbnail(chapter, story_title, scene_images)
    path = output_dir / f"thumbnail_ch{chapter}.jpg"
    img.save(path, "JPEG", quality=92)
    return path
