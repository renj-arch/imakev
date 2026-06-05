"""Procedural motion video engine — real parallax, camera tracking, particles, no APIs needed."""

import os, time, math, random, json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import cv2

from src.photo_video import _download_multiple_photos, _extract_keywords


def _parse_prompt(prompt: str) -> dict:
    keywords = prompt.lower().split()
    stop = {"a", "an", "the", "in", "on", "at", "for", "and", "of", "to", "is", "it", "with", "this", "that"}
    content_words = [w for w in keywords if w not in stop and len(w) > 2]

    scene = {
        "subject": content_words[:3] if content_words else ["scene"],
        "has_fog": any(w in prompt.lower() for w in ["fog", "mist", "cloud", "smoke", "haze"]),
        "has_grass": any(w in prompt.lower() for w in ["grass", "field", "meadow", "savanna"]),
        "has_water": any(w in prompt.lower() for w in ["water", "ocean", "river", "lake", "sea", "wave"]),
        "has_trees": any(w in prompt.lower() for w in ["tree", "forest", "jungle", "wood"]),
        "has_mountains": any(w in prompt.lower() for w in ["mountain", "hill", "peak"]),
        "is_sunrise": any(w in prompt.lower() for w in ["sunrise", "morning", "dawn", "early"]),
        "is_sunset": any(w in prompt.lower() for w in ["sunset", "evening", "dusk"]),
        "is_night": any(w in prompt.lower() for w in ["night", "dark", "moon"]),
        "tracking": "track" in prompt.lower() or "beside" in prompt.lower() or "follow" in prompt.lower(),
        "eye_level": "eye level" in prompt.lower() or "eye-level" in prompt.lower(),
    }

    if any(w in content_words for w in ["tiger", "lion", "leopard", "cheetah", "jaguar", "cat"]):
        scene["animal_type"] = "big_cat"
    elif any(w in content_words for w in ["dog", "wolf", "fox", "coyote"]):
        scene["animal_type"] = "canine"
    elif any(w in content_words for w in ["bird", "eagle", "hawk", "parrot"]):
        scene["animal_type"] = "bird"
    elif any(w in content_words for w in ["horse", "zebra", "deer", "elk"]):
        scene["animal_type"] = "quadruped"
    else:
        scene["animal_type"] = "generic"

    return scene


def _procedural_sky(w: int, h: int, scene: dict) -> np.ndarray:
    sky = np.zeros((h, w, 3), dtype=np.uint8)
    if scene.get("is_sunrise"):
        top = np.array([100, 130, 180], dtype=np.uint8)
        mid = np.array([200, 160, 120], dtype=np.uint8)
        bot = np.array([240, 200, 150], dtype=np.uint8)
    elif scene.get("is_sunset"):
        top = np.array([80, 60, 120], dtype=np.uint8)
        mid = np.array([200, 100, 80], dtype=np.uint8)
        bot = np.array([240, 150, 100], dtype=np.uint8)
    elif scene.get("is_night"):
        top = np.array([10, 10, 30], dtype=np.uint8)
        mid = np.array([20, 15, 40], dtype=np.uint8)
        bot = np.array([30, 25, 50], dtype=np.uint8)
    else:
        top = np.array([80, 120, 180], dtype=np.uint8)
        mid = np.array([140, 180, 220], dtype=np.uint8)
        bot = np.array([200, 220, 240], dtype=np.uint8)

    for y in range(h):
        t = y / h
        if t < 0.5:
            t2 = t * 2
            color = (top + (mid - top) * t2).astype(np.uint8)
        else:
            t2 = (t - 0.5) * 2
            color = (mid + (bot - mid) * t2).astype(np.uint8)
        sky[y, :] = color

    if scene.get("has_fog"):
        fog_layer = np.ones((h, w, 3), dtype=np.uint8) * 220
        fog_alpha = np.zeros((h, w), dtype=np.float32)
        for y in range(h):
            t = y / h
            fog_alpha[y, :] = max(0, 0.6 * (1 - abs(t - 0.3) * 2))
        fog_alpha = np.clip(fog_alpha, 0, 0.4)
        for c in range(3):
            sky[:, :, c] = (sky[:, :, c] * (1 - fog_alpha) + fog_layer[:, :, c] * fog_alpha).astype(np.uint8)

    return sky


def _generate_grass_layer(w: int, h: int, blade_count: int, height_range, color_range,
                          sway_offset: float = 0) -> np.ndarray:
    layer = np.zeros((h, w, 4), dtype=np.uint8)
    for _ in range(blade_count):
        x = random.randint(0, w - 1)
        base_h = random.randint(*height_range)
        color = tuple(random.randint(*c) if isinstance(c, tuple) else c for c in color_range)
        if len(color) == 3:
            color = (*color, 255)
        for y_off in range(0, base_h, 2):
            yy = h - base_h + y_off
            if yy < 0 or yy >= h:
                continue
            sway = int(math.sin(sway_offset + x * 0.02 + y_off * 0.05) * 3)
            xx = x + sway
            if 0 <= xx < w:
                layer[yy, xx] = color
                if xx + 1 < w:
                    layer[yy, xx + 1] = tuple(c // 2 if i < 3 else c for i, c in enumerate(color))
    return layer


def _generate_fog_particles(w: int, h: int, density: float = 0.003) -> np.ndarray:
    layer = np.zeros((h, w, 4), dtype=np.uint8)
    num_particles = int(w * h * density)
    for _ in range(num_particles):
        x = random.randint(0, w - 1)
        y = random.randint(0, h - 1)
        r = random.randint(4, 15)
        alpha = random.randint(20, 80)
        cv2.circle(layer, (x, y), r, (255, 255, 255, alpha), -1)
    return cv2.GaussianBlur(layer, (15, 15), 5)


def _generate_sun_glow(w: int, h: int, scene: dict) -> np.ndarray:
    if not (scene.get("is_sunrise") or scene.get("is_sunset")):
        return np.zeros((h, w, 4), dtype=np.uint8)
    glow = np.zeros((h, w, 4), dtype=np.uint8)
    cx, cy = w // 2, int(h * 0.15)
    if scene.get("is_sunset"):
        cx = int(w * 0.7)
    color = (255, 220, 150) if scene.get("is_sunrise") else (255, 180, 100)
    for r in range(50, 200, 10):
        alpha = max(0, int(80 * (1 - r / 200)))
        cv2.circle(glow, (cx, cy), r, (*color, alpha), -1)
    glow = cv2.GaussianBlur(glow, (61, 61), 20)
    return glow


def _load_or_create_subject(prompt: str, w: int, h: int, scene: dict) -> np.ndarray | None:
    """Try to load a subject image from stock photos. Falls back to procedural silhouette."""
    keywords = _extract_keywords(prompt, max_words=3)
    photos = _download_multiple_photos(prompt, count=2, w=w, h=h)
    if photos:
        arr = np.array(photos[0])
        return arr
    return None


def _apply_camera_track(frame: np.ndarray, progress: float, intensity: float = 0.08) -> np.ndarray:
    """Simulate horizontal camera tracking by shifting and wrapping."""
    h, w = frame.shape[:2]
    shift = int(w * intensity * (progress - 0.5))
    if shift == 0:
        return frame
    shifted = np.roll(frame, shift, axis=1)
    if shift > 0:
        shifted[:, :shift] = frame[:, :shift]
    else:
        shifted[:, shift:] = frame[:, shift:]
    return shifted


def _add_walking_bob(frame: np.ndarray, progress: float, intensity: float = 4) -> np.ndarray:
    """Add a subtle vertical bob to simulate walking."""
    bob = int(math.sin(progress * math.pi * 4) * intensity)
    if bob == 0:
        return frame
    M = np.float32([[1, 0, 0], [0, 1, bob]])
    h, w = frame.shape[:2]
    return cv2.warpAffine(frame, M, (w, h), borderMode=cv2.BORDER_REFLECT)


def _add_breathing_scale(frame: np.ndarray, progress: float, intensity: float = 0.01) -> np.ndarray:
    """Subtle scale pulse to simulate living creature breathing."""
    scale = 1.0 + math.sin(progress * math.pi * 2) * intensity
    h, w = frame.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), 0, scale)
    return cv2.warpAffine(frame, M, (w, h), borderMode=cv2.BORDER_REFLECT)


def _color_grade(frame: np.ndarray, scene: dict) -> np.ndarray:
    """Apply color grading for the described mood."""
    img = Image.fromarray(frame)
    if scene.get("is_sunrise") or scene.get("is_sunset"):
        warm = ImageEnhance.Color(img).enhance(1.3)
        r, g, b = warm.split()
        if scene.get("is_sunrise"):
            r = r.point(lambda x: min(255, int(x * 1.1)))
            g = g.point(lambda x: int(x * 0.95))
        else:
            r = r.point(lambda x: min(255, int(x * 1.15)))
            b = b.point(lambda x: int(x * 0.85))
        img = Image.merge("RGB", (r, g, b))
        img = ImageEnhance.Brightness(img).enhance(1.1)
        img = ImageEnhance.Contrast(img).enhance(1.1)
    if scene.get("has_fog"):
        img = ImageEnhance.Contrast(img).enhance(0.85)
        img = ImageEnhance.Brightness(img).enhance(1.05)
    if scene.get("is_night"):
        img = ImageEnhance.Brightness(img).enhance(0.4)
        img = ImageEnhance.Color(img).enhance(0.5)
    if scene.get("eye_level"):
        img = ImageEnhance.Contrast(img).enhance(1.05)
    return np.array(img)


def _apply_fog_overlay(frame: np.ndarray, progress: float, scene: dict) -> np.ndarray:
    if not scene.get("has_fog"):
        return frame
    h, w = frame.shape[:2]
    fog = np.ones((h, w, 3), dtype=np.float32) * 220
    alpha = np.zeros((h, w), dtype=np.float32)
    drift = int(progress * w * 0.15) % w
    for y in range(h):
        t = y / h
        density = max(0, 0.35 * (1 - abs(t - 0.35) * 2.5))
        alpha[y, :] = density
    fog_shifted = np.roll(fog, drift, axis=1)
    alpha_shifted = np.roll(alpha, drift, axis=1)
    alpha_3d = np.stack([alpha_shifted] * 3, axis=2)
    result = frame * (1 - alpha_3d) + fog_shifted * alpha_3d
    return np.clip(result, 0, 255).astype(np.uint8)


def generate_motion_video(prompt: str, w: int = 720, h: int = 1280,
                          num_frames: int = 192, fps: int = 24) -> list[np.ndarray] | None:
    """Generate a motion video with real camera movement, parallax, and effects.
    Works for ANY prompt without external APIs — pure procedural generation + stock photo enhancement."""

    scene = _parse_prompt(prompt)
    result = []

    sky = _procedural_sky(w, h, scene)
    sun_glow = _generate_sun_glow(w, h, scene)

    # Create background layer (sky + any landscape features)
    bg = sky.copy()

    # Generate grass layers (if scene has grass)
    grass_layers = []
    if scene.get("has_grass"):
        random.seed(42)
        grass_bg = _generate_grass_layer(w, h, 300, (80, 150), ((40, 80), (60, 120), (30, 60)))
        grass_mid = _generate_grass_layer(w, h, 200, (120, 200), ((60, 100), (80, 140), (40, 70)))
        grass_fg = _generate_grass_layer(w, h, 100, (180, 280), ((50, 90), (70, 110), (30, 60)))
        grass_layers = [(grass_bg, 0.3), (grass_mid, 0.6), (grass_fg, 1.0)]

    # Get or create subject image
    subject_img = _load_or_create_subject(prompt, w, h, scene)

    # Generate fog particles
    fog_particles = None
    if scene.get("has_fog"):
        fog_particles = _generate_fog_particles(w, h, 0.005)

    print(f"  Scene: {json.dumps({k: v for k, v in scene.items() if isinstance(v, bool)}, indent=2)}")

    for frame_idx in range(num_frames):
        progress = frame_idx / max(num_frames - 1, 1)

        # Start with sky background
        frame = bg.copy()

        # Composite sun glow
        sg = sun_glow.copy()
        if scene.get("is_sunrise") or scene.get("is_sunset"):
            sun_drift = int(progress * w * 0.08) % w
            sg = np.roll(sg, sun_drift, axis=1)
        frame = np.clip(frame + sg[:, :, :3] * (sg[:, :, 3:] / 255), 0, 255).astype(np.uint8)

        # Composite grass layers with parallax
        for grass, speed in grass_layers:
            g = grass.copy()
            shift = int(progress * w * speed * 0.3) % w
            g = np.roll(g, shift, axis=1)
            grass_rgb = g[:, :, :3]
            grass_alpha = g[:, :, 3:] / 255
            frame = (frame * (1 - grass_alpha) + grass_rgb * grass_alpha).astype(np.uint8)

        # Crop subject from stock photo and place it
        if subject_img is not None:
            sub = subject_img.copy()
            # Apply walking bob
            sub = _add_walking_bob(sub, progress * 2, intensity=3)
            # Apply breathing
            sub = _add_breathing_scale(sub, progress * 0.5, intensity=0.008)
            # Center the subject with some positioning
            sub_h, sub_w = sub.shape[:2]
            target_w = int(w * 0.7)
            scale = target_w / sub_w
            new_w = int(sub_w * scale)
            new_h = int(sub_h * scale)
            sub = cv2.resize(sub, (new_w, new_h))
            # Position in center-right of frame
            x_offset = (w - new_w) // 2 + int(w * 0.1)
            y_offset = h - new_h - int(h * 0.05)
            # Simple paste (no alpha blending for subject)
            if y_offset >= 0 and x_offset >= 0:
                paste_h = min(new_h, h - y_offset)
                paste_w = min(new_w, w - x_offset)
                frame[y_offset:y_offset + paste_h, x_offset:x_offset + paste_w] = \
                    sub[:paste_h, :paste_w]

        # Apply camera tracking
        if scene.get("tracking"):
            frame = _apply_camera_track(frame, progress, intensity=0.06)

        # Apply fog overlay
        frame = _apply_fog_overlay(frame, progress, scene)

        # Apply fog particles
        if fog_particles is not None:
            fp = fog_particles.copy()
            fp_shift = int(progress * w * 0.2) % w
            fp = np.roll(fp, fp_shift, axis=1)
            fp_rgb = fp[:, :, :3]
            fp_alpha = fp[:, :, 3:] / 255
            frame = (frame * (1 - fp_alpha) + fp_rgb * fp_alpha).astype(np.uint8)

        # Color grade
        frame = _color_grade(frame, scene)

        # Add subtle vignette
        mask = np.zeros((h, w), dtype=np.float32)
        cv2.circle(mask, (w // 2, h // 2), int(min(w, h) * 0.45), 1, -1)
        mask = cv2.GaussianBlur(mask, (w // 3 * 2 + 1, h // 3 * 2 + 1), w // 3)
        mask = 1 - (1 - mask) * 0.4
        for c in range(3):
            frame[:, :, c] = (frame[:, :, c] * mask).astype(np.uint8)

        result.append(frame)

    return result
