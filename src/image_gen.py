"""Centralized image generation — tries Pollinations.ai, falls back to procedural."""
import io, time, random
from PIL import Image, ImageEnhance, ImageFilter
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
    return _generate_background(w, h, prompt)


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


def _generate_background(w: int, h: int, prompt: str = "") -> Image.Image:
    seed = hash(prompt) & 0xFFFFFFFF
    rng = random.Random(seed)
    palette = [
        [(10, 5, 30), (40, 10, 80)],
        [(5, 20, 40), (10, 50, 90)],
        [(30, 5, 10), (70, 15, 30)],
        [(10, 30, 10), (25, 60, 25)],
        [(40, 20, 5), (80, 45, 15)],
        [(5, 5, 5), (30, 30, 30)],
        [(15, 5, 25), (45, 15, 60)],
        [(5, 15, 25), (20, 40, 60)],
    ]
    c1, c2 = rng.choice(palette)

    arr = np.zeros((h, w, 3), dtype=np.uint8)
    for y in range(h):
        ratio = y / h
        r = int(c1[0] + (c2[0] - c1[0]) * ratio)
        g = int(c1[1] + (c2[1] - c1[1]) * ratio)
        b = int(c1[2] + (c2[2] - c1[2]) * ratio)
        wave1 = abs(np.sin(y * 0.008 + seed * 0.001)) * 25
        wave2 = abs(np.cos(y * 0.012 + seed * 0.002)) * 15
        noise1 = rng.randint(-12, 12)
        noise2 = rng.randint(-12, 12)
        noise3 = rng.randint(-12, 12)
        arr[y, :, 0] = np.clip(r + wave1 + noise1, 0, 255).astype(np.uint8)
        arr[y, :, 1] = np.clip(g + wave2 + noise2, 0, 255).astype(np.uint8)
        arr[y, :, 2] = np.clip(b + (wave1 + wave2) * 0.5 + noise3, 0, 255).astype(np.uint8)

    img = Image.fromarray(arr)
    img = img.filter(ImageFilter.SMOOTH)
    return img
