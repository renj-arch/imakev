"""Manim-style explainer animation engine — PIL + MoviePy, no GPU needed.
Creates smooth educational animations: animated text, highlights, simple shapes,
transition effects. Style inspired by 3Blue1Brown / Manim."""

import math, random, json
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import config

W, H = config.VIDEO_WIDTH, config.VIDEO_HEIGHT
FPS = config.VIDEO_FPS

_BG_COLOR = (15, 15, 25)
_ACCENT = (100, 180, 255)
_WHITE = (240, 240, 245)
_YELLOW = (255, 220, 80)
_GREEN = (80, 220, 140)

def _get_font(size: int = 36):
    try:
        return ImageFont.truetype(config.get_font(), size)
    except Exception:
        return ImageFont.load_default()

def _ease(t: float) -> float:
    """Smooth easing function (smoothstep)."""
    return t * t * (3 - 2 * t)

def _lerp_color(a, b, t):
    return tuple(int(ac + (bc - ac) * t) for ac, bc in zip(a, b))

def _draw_bg(draw: ImageDraw):
    draw.rectangle([(0, 0), (W, H)], fill=_BG_COLOR)

def _draw_title_card(text: str) -> np.ndarray:
    img = Image.new("RGB", (W, H), _BG_COLOR)
    draw = ImageDraw.Draw(img)
    font = _get_font(48)
    lines = text.split("\\n") if "\\n" in text else [text]
    total_h = sum(draw.textbbox((0, 0), l, font=font)[3] - draw.textbbox((0, 0), l, font=font)[1] for l in lines) + (len(lines) - 1) * 10
    y_start = (H - total_h) // 2
    for line in lines:
        bb = draw.textbbox((0, 0), line, font=font)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        x = (W - tw) // 2
        draw.text((x, y_start), line, fill=_ACCENT, font=font)
        y_start += th + 10
    return np.array(img)

def _draw_fact_card(text: str, idx: int, total: int) -> np.ndarray:
    img = Image.new("RGB", (W, H), _BG_COLOR)
    draw = ImageDraw.Draw(img)
    font = _get_font(40)
    title_font = _get_font(28)
    num_text = f"0{idx+1}" if idx + 1 < 10 else str(idx + 1)
    draw.text((40, 60), num_text, fill=_ACCENT, font=title_font)
    draw.text((40, 100), f"of {total}", fill=(100, 100, 120), font=_get_font(20))
    words = text.split()
    lines, current = [], ""
    for w in words:
        if draw.textbbox((0, 0), current + " " + w, font=font)[2] > W - 80:
            lines.append(current)
            current = w
        else:
            current = (current + " " + w).strip()
    if current:
        lines.append(current)
    y = 180
    for line in lines:
        bb = draw.textbbox((0, 0), line, font=font)
        draw.text((40, y), line, fill=_WHITE, font=font)
        y += bb[3] - bb[1] + 8
    return np.array(img)

def _draw_end_card() -> np.ndarray:
    img = Image.new("RGB", (W, H), _BG_COLOR)
    draw = ImageDraw.Draw(img)
    font = _get_font(52)
    sub_font = _get_font(28)
    texts = [
        ("Thanks for watching!", _WHITE, font),
        ("Subscribe for more", (120, 120, 140), sub_font),
    ]
    y = H // 2 - 80
    for text, color, f in texts:
        bb = draw.textbbox((0, 0), text, font=f)
        tw = bb[2] - bb[0]
        draw.text(((W - tw) // 2, y), text, fill=color, font=f)
        y += 80
    return np.array(img)

def generate_explainer_frames(
    title: str,
    points: list[str],
    duration_per_point: float = 4.0,
    intro_duration: float = 2.0,
    outro_duration: float = 2.0,
) -> list[np.ndarray]:
    frames = []
    intro_frames = int(intro_duration * FPS)
    point_frames = int(duration_per_point * FPS)
    outro_frames = int(outro_duration * FPS)

    title_card = _draw_title_card(title)
    for i in range(intro_frames):
        t = i / max(intro_frames - 1, 1)
        img = title_card.copy()
        draw = ImageDraw.Draw(Image.fromarray(img))
        alpha = int(255 * _ease(min(t * 2, 1)))
        bar_h = 3
        bar_w = int(W * 0.6 * _ease(min(t * 1.5, 1)))
        draw.rectangle([(W // 2 - bar_w // 2, H - 40), (W // 2 + bar_w // 2, H - 40 + bar_h)], fill=_ACCENT)
        if t > 0.3:
            sub_alpha = int(255 * _ease(min((t - 0.3) / 0.4, 1)))
            sub = _get_font(24)
            sb = draw.textbbox((0, 0), "AI Generated", font=sub)
            draw.text(((W - (sb[2] - sb[0])) // 2, H - 80), "AI Generated", fill=(*_lerp_color(_BG_COLOR, (100, 100, 120), sub_alpha / 255), sub_alpha), font=sub)
        frame = np.clip(img * (alpha / 255), 0, 255).astype(np.uint8) if alpha < 255 else img
        frames.append(frame)

    for idx, point in enumerate(points):
        card = _draw_fact_card(point, idx, len(points))
        for i in range(point_frames):
            t = i / max(point_frames - 1, 1)
            if i < FPS:
                fade = _ease(i / FPS)
                frame = np.clip(card * fade, 0, 255).astype(np.uint8)
            else:
                frame = card.copy()
                draw = ImageDraw.Draw(Image.fromarray(frame))
                progress_bar = int(W * 0.85 * _ease((i - FPS) / max(point_frames - FPS - 1, 1)))
                draw.rectangle([(W * 0.075, H - 20), (W * 0.075 + progress_bar, H - 10)], fill=_lerp_color(_ACCENT, _GREEN, progress_bar / (W * 0.85)))
            frames.append(frame)

    end_card = _draw_end_card()
    for i in range(outro_frames):
        t = i / max(outro_frames - 1, 1)
        alpha = int(255 * _ease(t))
        frames.append(np.clip(end_card * (alpha / 255), 0, 255).astype(np.uint8) if alpha < 255 else end_card)

    return frames
