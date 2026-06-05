"""Cinematic enhancement module — professional visual effects, no APIs needed.
All processing is done with numpy/PIL/OpenCV/MoviePy. Zero external dependencies."""

import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import cv2
import config

W = config.VIDEO_WIDTH
H = config.VIDEO_HEIGHT


def smooth_camera_move(progress: float, move_type: str = "ken_burns") -> tuple:
    """Returns (zoom, pan_x, pan_y) for cinematic camera movement.
    Uses easing functions for professional feel."""
    eased = progress * progress * (3 - 2 * progress)  # smoothstep

    if move_type == "ken_burns_in":
        zoom = 1.0 + 0.08 * eased
        return (zoom, 0, 0)
    elif move_type == "ken_burns_out":
        zoom = 1.08 - 0.08 * eased
        return (zoom, 0, 0)
    elif move_type == "pan_left":
        zoom = 1.0
        pan_x = -0.06 * eased
        return (zoom, pan_x, 0)
    elif move_type == "pan_right":
        zoom = 1.0
        pan_x = 0.06 * eased
        return (zoom, pan_x, 0)
    elif move_type == "pan_up":
        zoom = 1.0
        pan_y = -0.06 * eased
        return (zoom, 0, pan_y)
    elif move_type == "pan_down":
        zoom = 1.0
        pan_y = 0.06 * eased
        return (zoom, 0, pan_y)
    elif move_type == "dolly_in":
        zoom = 1.0 + 0.12 * eased
        return (zoom, 0, 0)
    elif move_type == "dolly_out":
        zoom = 1.12 - 0.12 * eased
        return (zoom, 0, 0)
    else:
        return (1.0, 0, 0)


def apply_camera_move(frame: np.ndarray, progress: float,
                       move_type: str = "ken_burns_in",
                       w: int = W, h: int = H) -> np.ndarray:
    """Apply a cinematic camera move to a frame."""
    zoom, pan_x, pan_y = smooth_camera_move(progress, move_type)

    new_w = int(w * zoom)
    new_h = int(h * zoom)
    resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

    x_offset = int((new_w - w) * (0.5 + pan_x))
    y_offset = int((new_h - h) * (0.5 + pan_y))
    x_offset = max(0, min(x_offset, new_w - w))
    y_offset = max(0, min(y_offset, new_h - h))

    return resized[y_offset:y_offset + h, x_offset:x_offset + w]


def crossfade(frame_a: np.ndarray, frame_b: np.ndarray, t: float) -> np.ndarray:
    """Smooth crossfade between two frames. t=0->1 transitions from A to B."""
    t = max(0, min(1, t))
    t = t * t * (3 - 2 * t)
    return (frame_a * (1 - t) + frame_b * t).astype(np.uint8)


def generate_transition_frames(frames_a: list, frames_b: list,
                                overlap: int = 8) -> list:
    """Create crossfade transition between two frame sequences."""
    if not frames_a or not frames_b:
        return frames_a + frames_b
    transition = []
    for i in range(overlap):
        t = i / max(overlap - 1, 1)
        idx_a = min(i, len(frames_a) - 1)
        idx_b = max(0, len(frames_b) - overlap + i)
        transition.append(crossfade(frames_a[-(idx_a + 1)], frames_b[idx_b], t))
    return transition


def apply_film_grain(frame: np.ndarray, intensity: float = 0.005) -> np.ndarray:
    """Add subtle film grain for cinematic texture."""
    noise = np.random.randn(*frame.shape[:2]) * 255 * intensity
    noise = noise[:, :, np.newaxis]
    result = frame.astype(np.float32)
    result += noise
    return np.clip(result, 0, 255).astype(np.uint8)


def apply_color_grade(frame: np.ndarray, grade: str = "warm") -> np.ndarray:
    """Apply film-style color grading LUT."""
    img = Image.fromarray(frame)
    r, g, b = img.split()

    if grade == "warm":
        r = r.point(lambda x: min(255, int(x * 1.08)))
        b = b.point(lambda x: int(x * 0.92))
        img = ImageEnhance.Contrast(img).enhance(1.05)
    elif grade == "cool":
        r = r.point(lambda x: int(x * 0.92))
        b = b.point(lambda x: min(255, int(x * 1.08)))
        img = ImageEnhance.Contrast(img).enhance(1.02)
    elif grade == "vintage":
        r = r.point(lambda x: min(255, int(x * 0.95)))
        g = g.point(lambda x: int(x * 0.90))
        b = b.point(lambda x: int(x * 0.85))
        img = ImageEnhance.Color(img).enhance(0.8)
    elif grade == "dramatic":
        img = ImageEnhance.Contrast(img).enhance(1.15)
        img = ImageEnhance.Color(img).enhance(1.2)
    elif grade == "muted":
        img = ImageEnhance.Color(img).enhance(0.7)
        img = ImageEnhance.Contrast(img).enhance(1.1)

    return np.array(img.convert("RGB"))


def apply_vignette(frame: np.ndarray, strength: float = 0.35) -> np.ndarray:
    """Add cinematic vignette (darkened corners)."""
    h, w = frame.shape[:2]
    mask = np.zeros((h, w), dtype=np.float32)
    cv2.circle(mask, (w // 2, h // 2), int(min(w, h) * 0.45), 1, -1)
    mask = cv2.GaussianBlur(mask, (w // 3 * 2 + 1 | 1, h // 3 * 2 + 1 | 1), w // 3)
    mask = 1 - (1 - mask) * strength
    for c in range(3):
        frame[:, :, c] = (frame[:, :, c] * mask).astype(np.uint8)
    return frame


def add_glow_text(draw: ImageDraw.Draw, text: str, position: tuple,
                   font: ImageFont, text_color=(255, 255, 255),
                   glow_color=(255, 200, 50), glow_radius: int = 4):
    """Draw text with outer glow effect."""
    x, y = position
    for r in range(glow_radius, 0, -1):
        alpha = int(60 / (glow_radius - r + 1))
        for dx, dy in [(0, -r), (0, r), (-r, 0), (r, 0),
                       (-r, -r), (r, -r), (-r, r), (r, r)]:
            draw.text((x + dx, y + dy), text, font=font,
                     fill=(*glow_color, alpha))
    draw.text((x, y), text, font=font, fill=text_color)


def render_professional_caption(frame: np.ndarray, text: str,
                                 font_size: int = 48,
                                 position: str = "bottom",
                                 with_glow: bool = True) -> np.ndarray:
    """Render a professional caption directly onto a frame."""
    img = Image.fromarray(frame).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    try:
        font = ImageFont.truetype(config.get_font(), font_size)
    except:
        font = ImageFont.load_default()

    lines = []
    words = text.split()
    current = ""
    for w in words:
        test = f"{current} {w}".strip()
        bb = draw.textbbox((0, 0), test, font=font)
        if bb[2] - bb[0] > W - 80:
            lines.append(current)
            current = w
        else:
            current = test
    lines.append(current)

    total_h = len(lines) * (font_size + 10)
    if position == "bottom":
        y_start = H - total_h - 80
    elif position == "top":
        y_start = 80
    else:
        y_start = (H - total_h) // 2

    bar_h = total_h + 40
    bar_y = y_start - 20
    draw.rectangle([(0, bar_y), (W, bar_y + bar_h)],
                   fill=(0, 0, 0, 140))

    for i, line in enumerate(lines):
        y = y_start + i * (font_size + 10)
        bb = draw.textbbox((0, 0), line, font=font)
        x = (W - (bb[2] - bb[0])) // 2

        if with_glow:
            for r in range(3, 0, -1):
                for dx, dy in [(0, -r), (0, r), (-r, 0), (r, 0)]:
                    draw.text((x + dx, y + dy), line, font=font,
                             fill=(255, 200, 50, 40 // r))
        draw.text((x + 2, y + 2), line, font=font, fill=(0, 0, 0, 200))
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))

    img = Image.alpha_composite(img, overlay)
    return np.array(img.convert("RGB"))


def render_brand_overlay(frame: np.ndarray, brand: str = "",
                          show_logo: bool = True) -> np.ndarray:
    """Add a subtle brand watermark to the frame."""
    if not brand:
        return frame
    img = Image.fromarray(frame).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    try:
        font = ImageFont.truetype(config.get_font(), 24)
    except:
        font = ImageFont.load_default()

    bb = draw.textbbox((0, 0), brand, font=font)
    tw = bb[2] - bb[0]
    x = W - tw - 20
    y = H - 50
    draw.text((x + 1, y + 1), brand, font=font, fill=(0, 0, 0, 120))
    draw.text((x, y), brand, font=font, fill=(255, 255, 255, 160))

    img = Image.alpha_composite(img, overlay)
    return np.array(img.convert("RGB"))


def enhance_frame(frame: np.ndarray,
                   color_grade: str = "none",
                   grain: bool = False,
                   sharpen: bool = True,
                   vignette: bool = True) -> np.ndarray:
    """Apply all enhancements to a single frame."""
    if color_grade != "none":
        frame = apply_color_grade(frame, color_grade)
    if sharpen:
        img = Image.fromarray(frame)
        img = ImageEnhance.Sharpness(img).enhance(1.2)
        img = ImageEnhance.Contrast(img).enhance(1.05)
        frame = np.array(img)
    if grain:
        frame = apply_film_grain(frame, 0.003)
    if vignette:
        frame = apply_vignette(frame, 0.3)
    return frame
