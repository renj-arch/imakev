"""Sketch illustration generator — Pexels photo + OpenCV sketch filter.
Direct Pexels access (fast), bypasses gen_img's slow Pollinations pipeline."""

import os, io, random
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
from PIL import Image
import requests as req
from src.sketch_filter import photo_to_sketch, create_sketch_canvas

W, H = 720, 1280


def _extract_keywords(phrase: str, max_words: int = 4) -> str:
    stop = {"a", "an", "the", "in", "on", "at", "for", "of", "to", "is", "it",
            "with", "this", "that", "and", "but", "or", "as", "by", "from",
            "are", "was", "were", "been", "being", "have", "has", "had",
            "do", "does", "did", "will", "would", "can", "could",
            "their", "they", "them", "its", "over", "under", "than",
            "tiny", "small", "big", "large", "very", "about", "also", "than",
            "into", "through", "during", "before", "after"}
    words = phrase.lower().split()
    keywords = [w.strip(".,!?;:'\"") for w in words
                if w.strip(".,!?;:'\"") not in stop and len(w.strip(".,!?;:'\"")) > 2]
    seen = []
    for k in keywords:
        if k not in seen:
            seen.append(k)
    return ",".join(seen[:max_words]) if seen else ""


def _try_pexels_photo(keywords: str, w: int, h: int) -> Image.Image | None:
    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key:
        return None
    try:
        resp = req.get(
            f"https://api.pexels.com/v1/search?query={keywords}&per_page=5&orientation=portrait",
            headers={"Authorization": api_key},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            photos = data.get("photos", [])
            if photos:
                idx = random.randint(0, min(len(photos) - 1, 2))
                pu = photos[idx]["src"]
                url = pu.get("large2x") or pu.get("large") or pu.get("original")
                if url:
                    ir = req.get(url, timeout=10)
                    if ir.status_code == 200 and len(ir.content) > 10000:
                        img = Image.open(io.BytesIO(ir.content)).convert("RGB")
                        img = img.resize((w, h), Image.LANCZOS)
                        print(f"    Pexels photo: {keywords}")
                        return img
    except Exception:
        pass
    return None


def _try_stock_photo(keywords: str, w: int, h: int) -> Image.Image | None:
    """Fallback: loremflickr stock photo."""
    kw = keywords.split(",")[0] if keywords else "nature"
    try:
        resp = req.get(f"https://loremflickr.com/{w*2}/{h*2}/{kw}", timeout=10)
        if resp.status_code == 200 and len(resp.content) > 10000:
            img = Image.open(io.BytesIO(resp.content)).convert("RGB")
            img = img.resize((w, h), Image.LANCZOS)
            print(f"    Stock photo: {kw}")
            return img
    except Exception:
        pass
    return None


def _generate_scene_fallback(w: int, h: int) -> Image.Image:
    """Clean gradient fallback when no photo available."""
    from PIL import ImageDraw
    img = Image.new("RGB", (w, h), (250, 250, 245))
    draw = ImageDraw.Draw(img)
    for i in range(h):
        t = i / h
        r = int(250 - t * 15)
        g = int(250 - t * 10)
        b = int(245 - t * 20)
        draw.line([(0, i), (w, i)], fill=(r, g, b))
    return img


def draw_sketch_for_phrase(phrase: str, w: int = W, h: int = H) -> Image.Image:
    """Get a photo matching the phrase and convert to sketch style."""
    keywords = _extract_keywords(phrase)
    img = None

    if keywords:
        img = _try_pexels_photo(keywords, w, h)
    if img is None and keywords:
        img = _try_stock_photo(keywords, w, h)
    if img is None:
        # Try individual keywords
        for kw in keywords.split(",")[:2]:
            img = _try_stock_photo(kw, w, h)
            if img:
                break
    if img is None:
        print(f"    No photo for '{phrase[:40]}', using gradient fallback")
        img = _generate_scene_fallback(w, h)

    sketch = photo_to_sketch(img, line_style="pencil")
    canvas = create_sketch_canvas(sketch, bg_color=(250, 250, 245), w=w, h=h)
    return canvas
