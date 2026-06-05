"""Centralized image generation — AI, stock photos, HF Spaces, then procedural scene drawing."""
import io, time, random, math, hashlib, os
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import requests as req
import config

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}?width={w}&height={h}&model={model}&seed={seed}&enhance=true"
ANON_RATE_LIMIT_S = 16  # anonymous tier: 1 request per 15s, use 16 to be safe
_last_pollinations_call = 0.0

_prompt_enhancers = [
    ", cinematic lighting, dramatic shadows, 4K, photorealistic, highly detailed",
    ", golden hour, warm tones, volumetric lighting, sharp focus, 8K",
    ", moody atmosphere, rim lighting, deep colors, professional photography",
    ", soft natural light, film grain, cinematic composition, depth of field",
    ", dramatic side lighting, rich textures, ultra detailed, cinematic mood",
]


def _enhance_prompt(prompt: str, seed: int) -> str:
    enhancer = _prompt_enhancers[seed % len(_prompt_enhancers)]
    return f"{prompt}{enhancer}"


def _extract_keywords(prompt: str, max_words: int = 3) -> str:
    stop = {"a", "an", "the", "in", "on", "at", "for", "and", "of", "to", "is", "it", "with", "this", "that",
            "tiny", "small", "big", "large", "beside", "under", "over", "above", "below", "behind"}
    words = prompt.lower().split(",")[0].strip().split()
    keywords = [w for w in words if w not in stop and len(w) > 2][:max_words]
    return ",".join(keywords) if keywords else "nature,landscape"


def _try_stock_photo(prompt: str, w: int, h: int) -> Image.Image | None:
    keywords = _extract_keywords(prompt, max_words=3)
    first_keyword = keywords.split(",")[0]
    urls = [
        f"https://lorem.media/photo/{w}/{h}",
        f"https://loremflickr.com/{w*2}/{h*2}/{keywords}",
        f"https://loremflickr.com/{w*2}/{h*2}/{first_keyword}",
        f"https://picsum.photos/seed/{hash(prompt) & 0xFFFF}/{w}/{h}",
        f"https://picsum.photos/{w}/{h}",
    ]
    for url in urls:
        try:
            resp = req.get(url, timeout=15)
            if resp.status_code == 200 and len(resp.content) > 10000:
                img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                img = img.resize((w, h), Image.LANCZOS)
                return img
        except Exception:
            continue
    return None


def _try_hf_space_image(prompt: str, w: int, h: int) -> Image.Image | None:
    """Generate image via free HF Gradio Space (no API key needed)."""
    try:
        from gradio_client import Client
    except ImportError:
        return None

    spaces = [
        ("stabilityai/stable-diffusion-3.5-large",
         lambda c: c.predict(
             prompt=prompt,
             negative_prompt="blurry, low quality, distorted",
             seed=random.randint(0, 999999),
             randomize_seed=True,
             width=min(w, 1024),
             height=min(h, 1024),
             guidance_scale=4.5,
             num_inference_steps=25,
             api_name="/infer"
         )),
        ("black-forest-labs/FLUX.1-dev",
         lambda c: c.predict(
             prompt=prompt,
             seed=random.randint(0, 999999),
             width=min(w, 1024),
             height=min(h, 1024),
             guidance_scale=3.5,
             num_inference_steps=20,
             api_name="/infer"
         )),
        ("multimodalart/stable-cascade",
         lambda c: c.predict(
             prompt=prompt,
             negative_prompt="blurry, low quality",
             seed=random.randint(0, 999999),
             width=min(w, 1024),
             height=min(h, 1024),
             guidance_scale=4,
             num_inference_steps=20,
             api_name="/run"
         )),
    ]

    for space_id, predict_fn in spaces:
        print(f"    Trying HF Space: {space_id}")
        try:
            client = Client(space_id)
            job = client.submit(predict_fn(client))
            waited = 0
            while not job.done() and waited < 120:
                time.sleep(5)
                waited += 5
            if job.done():
                result = job.result()
                if isinstance(result, (list, tuple)):
                    fp = result[0]
                else:
                    fp = result
                if isinstance(fp, str) and os.path.isfile(fp):
                    img = Image.open(fp).convert("RGB")
                    img = img.resize((w, h), Image.LANCZOS)
                    print(f"    >> Got image from {space_id}")
                    return img
        except Exception as e:
            print(f"    {space_id} failed: {e}")
            continue
    return None


def _try_hf_inference_api(prompt: str, w: int, h: int) -> Image.Image | None:
    """Try HF free inference API models (no token required, rate-limited)."""
    models = [
        "stabilityai/stable-diffusion-3.5-large",
        "black-forest-labs/FLUX.1-dev",
        "stabilityai/stable-diffusion-xl-base-1.0",
        "runwayml/stable-diffusion-v1-5",
    ]
    for model in models:
        api_url = f"https://api-inference.huggingface.co/models/{model}"
        try:
            resp = req.post(api_url, json={"inputs": prompt}, timeout=60)
            if resp.status_code == 200:
                img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                img = img.resize((w, h), Image.LANCZOS)
                print(f"    >> Got image from HF {model}")
                return img
            elif resp.status_code == 503:
                print(f"    HF {model} loading (503), skipping")
                continue
        except Exception as e:
            print(f"    HF {model} error: {e}")
            continue
    return None


def gen_img(prompt: str, width: int = None, height: int = None) -> Image.Image:
    w = width or config.VIDEO_WIDTH
    h = height or config.VIDEO_HEIGHT
    seed = random.randint(0, 999999)
    enhanced = _enhance_prompt(prompt, seed)

    # Try 1: AI-generated image via Pollinations (free, no key, rate-limited 1/15s)
    pollinations_models = ("flux", "turbo", "gptimage", "kontext", "seedream", "nanobanana")
    for model in pollinations_models:
        img = _try_pollinations(enhanced, w, h, model, seed)
        if img is not None:
            return img
        time.sleep(ANON_RATE_LIMIT_S)  # respect anonymous tier rate limit

    # Try 2: HF Gradio Space (free SDXL/FLUX, no key, queued)
    img = _try_hf_space_image(enhanced, w, h)
    if img is not None:
        return img

    # Try 3: HF Inference API (free, rate-limited)
    img = _try_hf_inference_api(enhanced, w, h)
    if img is not None:
        return img

    # Try 4: Free stock photo matching the prompt (no key, always available)
    stock = _try_stock_photo(prompt, w, h)
    if stock is not None:
        return stock

    # Fallback: Procedural scene drawing (always works)
    return _generate_scene(w, h, prompt)


def _try_pollinations(prompt: str, w: int, h: int, model: str, seed: int = 0, timeout: int = 45) -> Image.Image | None:
    global _last_pollinations_call
    elapsed = time.time() - _last_pollinations_call
    if elapsed < ANON_RATE_LIMIT_S:
        wait = ANON_RATE_LIMIT_S - elapsed
        time.sleep(wait)
    for attempt in range(2):
        s = seed + attempt
        url = POLLINATIONS_URL.format(prompt=req.utils.quote(prompt), w=w, h=h, model=model, seed=s)
        try:
            r = req.get(url, timeout=timeout)
            if r.status_code == 429:
                time.sleep(ANON_RATE_LIMIT_S)
                continue
            if r.status_code == 200 and len(r.content) > 500:
                _last_pollinations_call = time.time()
                img = Image.open(io.BytesIO(r.content)).convert("RGB")
                img = img.resize((w, h), Image.LANCZOS)
                img = ImageEnhance.Sharpness(img).enhance(1.1)
                return img
        except Exception:
            pass
        if attempt == 0:
            time.sleep(ANON_RATE_LIMIT_S)
    _last_pollinations_call = time.time()
    return None


def _generate_scene(w: int, h: int, prompt: str = "") -> Image.Image:
    """Procedural scene generator — draws attractive landscapes with detail and atmosphere."""
    seed = hash(prompt) & 0xFFFFFFFF
    rng = random.Random(seed)
    p_lower = prompt.lower()

    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)

    # Determine scene type from prompt
    is_night = any(w in p_lower for w in ("night", "dark", "space", "moon", "midnight"))
    is_sunset = any(w in p_lower for w in ("sunset", "sunrise", "golden", "dusk", "dawn", "evening"))
    is_water = any(w in p_lower for w in ("water", "ocean", "sea", "pond", "lake", "river", "beach", "coast"))
    is_snow = any(w in p_lower for w in ("snow", "ice", "winter", "arctic", "frozen"))
    is_city = any(w in p_lower for w in ("city", "urban", "street", "neon", "cyberpunk", "town", "building"))
    is_forest = any(w in p_lower for w in ("forest", "woods", "jungle", "tree", "nature"))
    is_desert = any(w in p_lower for w in ("desert", "sand", "dune", "arid"))
    has_animals = any(w in p_lower for w in ("cat", "dog", "bird", "horse", "elephant", "fox",
                                              "dragon", "fish", "butterfly", "duck", "swan", "kitten"))

    sky_h = int(h * (0.45 + rng.random() * 0.15))

    _draw_sky_pro(draw, w, sky_h, rng, p_lower, is_night, is_sunset)
    _draw_ground_pro(draw, w, h, sky_h, rng, p_lower, is_water, is_snow, is_desert, is_night, is_sunset, is_city)
    _draw_mountains(draw, w, sky_h, rng, p_lower, is_night, is_sunset)
    _draw_vegetation(draw, w, sky_h, rng, p_lower, is_forest, is_city, is_desert)
    _draw_scene_elements_pro(draw, w, h, sky_h, rng, p_lower)
    if is_city:
        _draw_buildings(draw, w, sky_h, rng, p_lower, is_night)
    if has_animals:
        _draw_animals_pro(draw, w, h, sky_h, rng, p_lower)
    if is_sunset:
        img = _compose_sunset_glow(img, w, h)

    return img.filter(ImageFilter.SMOOTH_MORE)


def _compose_sunset_glow(img, w, h):
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    glow_start = int(h * 0.55)
    for y in range(glow_start, h):
        t = (y - glow_start) / (h - glow_start)
        alpha = int(30 * (1 - t))
        gdraw.line([(0, y), (w, y)], fill=(255, 180, 80, alpha), width=2)
    return Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")


def _draw_sky_pro(draw, w, h, rng, prompt, is_night, is_sunset):
    if is_night:
        top = (5, 2, 20)
        mid = (10, 5, 40)
        bottom = (20, 10, 60)
    elif is_sunset:
        top = (20, 10, 40)
        mid = (180, 80, 40)
        bottom = (255, 180, 80)
    else:
        top = (30, 60, 140)
        mid = (80, 140, 210)
        bottom = (140, 190, 240)

    for y in range(h):
        t = y / h
        if t < 0.5:
            t2 = t / 0.5
            r = int(top[0] + (mid[0] - top[0]) * t2)
            g = int(top[1] + (mid[1] - top[1]) * t2)
            b = int(top[2] + (mid[2] - top[2]) * t2)
        else:
            t2 = (t - 0.5) / 0.5
            r = int(mid[0] + (bottom[0] - mid[0]) * t2)
            g = int(mid[1] + (bottom[1] - mid[1]) * t2)
            b = int(mid[2] + (bottom[2] - mid[2]) * t2)
        noise = rng.randint(-8, 8)
        draw.line([(0, y), (w, y)], fill=(
            max(0, min(255, r + noise)),
            max(0, min(255, g + noise)),
            max(0, min(255, b + noise)),
        ))

    if is_night or "star" in prompt:
        for _ in range(rng.randint(40, 120)):
            sx = rng.randint(0, w - 1)
            sy = rng.randint(0, int(h * 0.7))
            sz = rng.uniform(0.5, 2.5)
            brightness = rng.randint(180, 255)
            draw.ellipse([sx - sz, sy - sz, sx + sz, sy + sz],
                         fill=(brightness, brightness, max(180, brightness - 20)))

    if "sun" in prompt or is_sunset:
        sx = rng.randint(w // 4, 3 * w // 4)
        sy = int(h * 0.65)
        sr = rng.randint(35, 65)
        for i in range(6, 0, -1):
            alpha = 30 - i * 4 if is_sunset else 15 - i * 2
            rv = max(0, min(255, 255 - (6 - i) * 30))
            gv = max(0, min(255, 180 - (6 - i) * 30))
            bv = max(0, min(255, 80 - (6 - i) * 20))
            draw.ellipse([sx - sr * i, sy - sr * i, sx + sr * i, sy + sr * i],
                         fill=(rv, gv, bv))
        draw.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=(255, 230, 150))

    if "moon" in prompt or is_night:
        mx = rng.randint(w // 4, 3 * w // 4)
        my = rng.randint(30, int(h * 0.35))
        mr = rng.randint(22, 42)
        draw.ellipse([mx - mr, my - mr, mx + mr, my + mr], fill=(235, 230, 210))
        draw.ellipse([mx - mr + 7, my - mr - 5, mx + mr - 5, my + mr - 5], fill=(15, 10, 30))

    if not is_night:
        num_clouds = rng.randint(1, 4) if is_sunset else rng.randint(2, 5)
        for _ in range(num_clouds):
            cx = rng.randint(0, w)
            cy = rng.randint(5, int(h * 0.45))
            cr = rng.randint(25, 55)
            cloud_bright = rng.randint(200, 255)
            for dx, dy in [(0, 0), (cr // 2, cr // 4), (-cr // 3, cr // 3),
                           (cr // 3, cr // 3), (0, cr // 2)]:
                draw.ellipse([cx + dx - cr, cy + dy - cr // 2, cx + dx + cr, cy + dy + cr // 2],
                             fill=(cloud_bright, cloud_bright, cloud_bright))


def _draw_ground_pro(draw, w, h, sky_h, rng, prompt, is_water, is_snow, is_desert, is_night, is_sunset, is_city):
    ground_h = h - sky_h
    if ground_h <= 0:
        return

    if is_water:
        top = (rng.randint(10, 50), rng.randint(50, 130), rng.randint(150, 220))
        bottom = (rng.randint(0, 20), rng.randint(20, 60), rng.randint(80, 140))
    elif is_snow:
        top = (220, 230, 245)
        bottom = (190, 200, 220)
    elif is_desert:
        top = (rng.randint(180, 220), rng.randint(150, 190), rng.randint(80, 120))
        bottom = (rng.randint(120, 160), rng.randint(100, 130), rng.randint(50, 80))
    elif is_city:
        top = (rng.randint(40, 80), rng.randint(40, 80), rng.randint(45, 85))
        bottom = (rng.randint(20, 40), rng.randint(20, 40), rng.randint(25, 45))
    else:
        top = (rng.randint(30, 90), rng.randint(80, 160), rng.randint(20, 60))
        bottom = (rng.randint(10, 40), rng.randint(35, 80), rng.randint(5, 25))

    for y in range(ground_h):
        t = y / ground_h
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        noise = rng.randint(-5, 5)
        draw.line([(0, sky_h + y), (w, sky_h + y)], fill=(
            max(0, min(255, r + noise)),
            max(0, min(255, g + noise)),
            max(0, min(255, b + noise)),
        ))

    if is_water:
        for _ in range(rng.randint(8, 20)):
            wx = rng.randint(0, w)
            wy = rng.randint(sky_h + 10, h - 10)
            wlen = rng.randint(30, 80)
            alpha = rng.randint(40, 100)
            highlight = rng.randint(180, 255)
            draw.line([(wx, wy), (wx + wlen, wy)],
                      fill=(highlight, highlight, max(200, highlight)), width=rng.randint(1, 2))
    elif is_snow:
        pass
    elif not is_city and not is_desert:
        for _ in range(rng.randint(30, 100)):
            gx = rng.randint(0, w)
            gy = rng.randint(sky_h + 5, h - 1)
            gh = rng.randint(4, 18)
            gc = (rng.randint(20, 80), rng.randint(60, 150), rng.randint(15, 50))
            draw.line([(gx, gy), (gx + rng.randint(-3, 3), gy - gh)], fill=gc, width=1)
        for _ in range(rng.randint(3, 12)):
            fx = rng.randint(0, w)
            fy = rng.randint(sky_h + 5, h - 1)
            fr = rng.randint(10, 30)
            fc = (rng.randint(30, 70), rng.randint(50, 100), rng.randint(20, 40))
            draw.ellipse([fx - fr, fy - fr // 2, fx + fr, fy], fill=fc)
    elif is_desert:
        for _ in range(rng.randint(5, 15)):
            dx = rng.randint(0, w)
            dy = rng.randint(sky_h + 10, h - 10)
            dw = rng.randint(40, 120)
            dc = (rng.randint(150, 200), rng.randint(130, 170), rng.randint(70, 100))
            draw.arc([dx - dw, dy - 20, dx + dw, dy + 20], 0, 180, fill=dc, width=2)


def _draw_mountains(draw, w, sky_h, rng, prompt, is_night, is_sunset):
    if "mountain" not in prompt and "mountains" not in prompt:
        return

    layers = [
        (rng.randint(2, 4), 50, (is_night and (30, 30, 50) or (90, 80, 100))),
        (rng.randint(1, 3), rng.randint(100, 180),
         (is_night and (40, 40, 70) or (120, 110, 130) if not is_sunset else (150, 90, 60))),
    ]

    for num_mtns, mt_offset, mt_color in layers:
        for _ in range(num_mtns):
            mt_x = rng.randint(0, w)
            mt_h = rng.randint(mt_offset, mt_offset + 120)
            mt_w = rng.randint(100, 300)
            points = [(mt_x - mt_w, sky_h + 5), (mt_x, sky_h - mt_h), (mt_x + mt_w, sky_h + 5)]
            draw.polygon(points, fill=mt_color)

    if rng.random() > 0.5:
        snow_color = (200, 210, 230) if is_night else (240, 245, 255)
        for _ in range(rng.randint(1, 2)):
            sx = rng.randint(w // 4, 3 * w // 4)
            sh = rng.randint(120, 200)
            sw = rng.randint(50, 80)
            draw.polygon([(sx - sw, sky_h + 5), (sx, sky_h - sh), (sx + sw, sky_h + 5)],
                         fill=snow_color)


def _draw_vegetation(draw, w, sky_h, rng, prompt, is_forest, is_city, is_desert):
    if is_desert:
        return
    num_trees = 0
    if is_forest:
        num_trees = rng.randint(3, 7)
    elif is_city:
        num_trees = rng.randint(0, 2)
    elif "tree" in prompt:
        num_trees = rng.randint(2, 5)
    elif rng.random() < 0.4:
        num_trees = rng.randint(1, 3)

    for _ in range(num_trees):
        tx = rng.randint(30, w - 30)
        ty = sky_h + rng.randint(-10, 20)
        trunk_h = rng.randint(35, 70)
        trunk_w = rng.randint(6, 12)
        draw.rectangle([tx - trunk_w // 2, ty - trunk_h, tx + trunk_w // 2, ty],
                       fill=(rng.randint(40, 70), rng.randint(25, 50), rng.randint(10, 30)))
        crown_r = rng.randint(25, 50)
        crown_colors = [(20, 60, 20), (30, 80, 30), (25, 70, 25), (40, 90, 35)]
        if is_forest:
            crown_colors = [(15, 45, 15), (20, 55, 20), (30, 70, 25)]
        cc = crown_colors[rng.randint(0, len(crown_colors) - 1)]
        cx, cy_base = tx, ty - trunk_h
        for i in range(3):
            cy = cy_base - i * crown_r // 3
            cr = crown_r - i * 8
            if cr > 10:
                draw.ellipse([cx - cr, cy - cr, cx + cr, cy + cr // 2], fill=cc)


def _draw_buildings(draw, w, sky_h, rng, prompt, is_night):
    num_buildings = rng.randint(8, 20)
    for _ in range(num_buildings):
        bx = rng.randint(5, w - 5)
        bh = rng.randint(25, 160)
        bw = rng.randint(12, 30)
        bright = rng.randint(15, 50)
        bc = (bright, bright, bright + 10) if is_night else (bright + 20, bright + 20, bright + 30)
        draw.rectangle([bx - bw // 2, sky_h - bh, bx + bw // 2, sky_h], fill=bc)
        if rng.random() > 0.4:
            wy = rng.randint(sky_h - bh + 4, sky_h - 4)
            ww = rng.randint(2, 6)
            wh = rng.randint(3, 8)
            wc = (rng.randint(200, 255), rng.randint(200, 255), rng.randint(100, 255))
            draw.rectangle([bx - ww // 2, wy - wh, bx + ww // 2, wy], fill=wc)


def _draw_scene_elements_pro(draw, w, h, sky_h, rng, prompt):
    p = prompt.lower()

    if "rain" in p:
        for _ in range(rng.randint(40, 120)):
            rx = rng.randint(0, w)
            ry = rng.randint(0, h)
            rlen = rng.randint(8, 22)
            draw.line([(rx, ry), (rx - 2, ry + rlen)], fill=(160, 180, 220), width=1)

    if "fire" in p or "flame" in p:
        for _ in range(rng.randint(5, 12)):
            fx = rng.randint(40, w - 40)
            fy = rng.randint(sky_h + 20, h - 20)
            fh = rng.randint(25, 60)
            fw = rng.randint(8, 18)
            draw.ellipse([fx - fw // 2, fy - fh, fx + fw // 2, fy], fill=(rng.randint(200, 255), rng.randint(50, 150), 0))
            draw.ellipse([fx - fw // 2 + 2, fy - int(fh * 0.7), fx + fw // 2 - 2, fy],
                         fill=(255, 200, 50))

    if "flower" in p or "garden" in p or "spring" in p or "meadow" in p:
        for _ in range(rng.randint(8, 25)):
            flx = rng.randint(10, w - 10)
            fly = rng.randint(sky_h + 10, h - 10)
            stem_h = rng.randint(10, 25)
            draw.line([(flx, fly), (flx, fly + stem_h)], fill=(30, 100, 30), width=2)
            fc = (rng.randint(150, 255), rng.randint(50, 200), rng.randint(100, 255))
            for angle in range(0, 360, 72):
                rad = math.radians(angle)
                px = flx + int(math.cos(rad) * 4)
                py = fly + int(math.sin(rad) * 4)
                draw.ellipse([px - 3, py - 3, px + 3, py + 3], fill=fc)
            draw.ellipse([flx - 2, fly - 2, flx + 2, fly + 2], fill=(255, 200, 50))

    if "butterfly" in p:
        for _ in range(rng.randint(1, 4)):
            bx = rng.randint(30, w - 30)
            by = rng.randint(30, h - 30)
            bc = (rng.randint(150, 255), rng.randint(50, 200), rng.randint(50, 200))
            draw.ellipse([bx - 10, by - 2, bx + 10, by + 2], fill=(30, 30, 30))
            draw.ellipse([bx - 10, by - 8, bx - 1, by + 8], fill=bc)
            draw.ellipse([bx + 1, by - 8, bx + 10, by + 8], fill=bc)
            for wing_angle in range(0, 360, 45):
                rad = math.radians(wing_angle)
                wx = bx + int(math.cos(rad) * 8)
                wy = by + int(math.sin(rad) * 4)
                draw.ellipse([wx - 2, wy - 2, wx + 2, wy + 2], fill=bc)

    if any(w in p for w in ("fish", "jellyfish", "ocean", "sea")):
            for _ in range(rng.randint(2, 5)):
                fx = rng.randint(30, w - 30)
                fy = rng.randint(sky_h + 30, h - 30)
                fc = (rng.randint(50, 200), rng.randint(100, 220), rng.randint(150, 255))
                draw.ellipse([fx - 14, fy - 6, fx + 14, fy + 6], fill=fc)
                draw.polygon([(fx + 12, fy), (fx + 26, fy - 8), (fx + 26, fy + 8)], fill=fc)
                draw.ellipse([fx - 5, fy - 2, fx - 2, fy + 2], fill=(0, 0, 0))


def _draw_animals_pro(draw, w, h, sky_h, rng, prompt):
    p = prompt.lower()

    if "cat" in p or "kitten" in p:
        cx = rng.randint(w // 3, 2 * w // 3)
        cy = sky_h + rng.randint(10, 80)
        is_black = "black" in p or "dark" in p
        if is_black:
            c = (rng.randint(10, 40), rng.randint(10, 40), rng.randint(10, 40))
            eye_c = (180, 200, 50)
        elif "orange" in p or "ginger" in p:
            c = (rng.randint(180, 230), rng.randint(100, 150), rng.randint(30, 60))
            eye_c = (50, 200, 50)
        elif "white" in p:
            c = (210, 210, 210)
            eye_c = (100, 150, 200)
        else:
            c = (rng.randint(130, 200), rng.randint(100, 160), rng.randint(60, 120))
            eye_c = (50, 200, 50)
        draw.ellipse([cx - 20, cy - 8, cx + 20, cy + 8], fill=c)
        draw.ellipse([cx - 12, cy - 20, cx + 12, cy - 2], fill=c)
        draw.polygon([(cx - 12, cy - 20), (cx - 16, cy - 32), (cx - 7, cy - 24)], fill=c)
        draw.polygon([(cx + 12, cy - 20), (cx + 16, cy - 32), (cx + 7, cy - 24)], fill=c)
        draw.ellipse([cx - 5, cy - 18, cx - 2, cy - 15], fill=eye_c)
        draw.ellipse([cx + 2, cy - 18, cx + 5, cy - 15], fill=eye_c)
        draw.ellipse([cx - 4, cy - 17, cx - 3, cy - 16], fill=(0, 0, 0))
        draw.ellipse([cx + 3, cy - 17, cx + 4, cy - 16], fill=(0, 0, 0))
        draw.ellipse([cx - 2, cy - 12, cx + 2, cy - 9], fill=(200, 150, 150))
        if "lying" in p or "sleep" in p or "rest" in p:
            draw.rectangle([cx - 5, cy + 4, cx + 5, cy + 12], fill=c)
            draw.ellipse([cx - 7, cy + 8, cx - 1, cy + 12], fill=c)
            draw.ellipse([cx + 1, cy + 8, cx + 7, cy + 12], fill=c)

    if "dog" in p or "puppy" in p:
        dx = rng.randint(w // 3, 2 * w // 3)
        dy = sky_h + rng.randint(10, 80)
        dc = (rng.randint(100, 180), rng.randint(60, 130), rng.randint(20, 60))
        if "brown" in p:
            dc = (rng.randint(120, 170), rng.randint(70, 110), rng.randint(30, 50))
        elif "black" in p:
            dc = (rng.randint(15, 45), rng.randint(15, 45), rng.randint(15, 45))
        draw.ellipse([dx - 18, dy - 8, dx + 18, dy + 8], fill=dc)
        draw.ellipse([dx - 10, dy - 18, dx + 10, dy - 2], fill=dc)
        draw.polygon([(dx - 10, dy - 18), (dx - 16, dy - 26), (dx - 5, dy - 20)], fill=dc)
        draw.polygon([(dx + 10, dy - 18), (dx + 16, dy - 26), (dx + 5, dy - 20)], fill=dc)
        draw.ellipse([dx - 4, dy - 16, dx - 1, dy - 13], fill=(0, 0, 0))
        draw.ellipse([dx + 1, dy - 16, dx + 4, dy - 13], fill=(0, 0, 0))
        draw.ellipse([dx - 1, dy - 12, dx + 1, dy - 9], fill=(0, 0, 0))

    if "bird" in p or "duck" in p or "swan" in p:
        for _ in range(rng.randint(1, 4)):
            by = sky_h + rng.randint(5, 40)
            bx = rng.randint(w // 4, 3 * w // 4)
            body_c = (rng.randint(180, 255), rng.randint(180, 220), rng.randint(0, 80))
            if "swan" in p:
                body_c = (255, 255, 255)
            elif "duck" in p:
                body_c = (rng.randint(180, 220), rng.randint(180, 200), rng.randint(20, 60))
            draw.ellipse([bx - 14, by - 7, bx + 14, by + 7], fill=body_c)
            draw.ellipse([bx + 10, by - 10, bx + 20, by + 1], fill=body_c)
            head_c = body_c if "swan" not in p else (255, 255, 255)
            draw.ellipse([bx + 16, by - 14, bx + 26, by - 3], fill=head_c)
            draw.polygon([(bx + 24, by - 12), (bx + 34, by - 14), (bx + 24, by - 7)], fill=(255, 200, 0))

    if "dragon" in p:
        for _ in range(rng.randint(1, 2)):
            dx = rng.randint(w // 4, 3 * w // 4)
            dy = rng.randint(30, sky_h - 30)
            dc = (rng.randint(100, 200), rng.randint(0, 50), rng.randint(0, 30))
            draw.ellipse([dx - 22, dy - 10, dx + 22, dy + 10], fill=dc)
            draw.ellipse([dx - 14, dy - 28, dx + 14, dy - 6], fill=dc)
            draw.polygon([(dx + 12, dy - 28), (dx + 28, dy - 34), (dx + 12, dy - 18)], fill=dc)
            draw.polygon([(dx - 12, dy - 28), (dx - 28, dy - 34), (dx - 12, dy - 18)], fill=dc)
            draw.polygon([(dx + 18, dy - 8), (dx + 45, dy - 2), (dx + 18, dy + 4)], fill=(255, 100, 0))
            draw.ellipse([dx - 4, dy - 26, dx - 1, dy - 22], fill=(255, 200, 0))
            draw.ellipse([dx + 1, dy - 26, dx + 4, dy - 22], fill=(255, 200, 0))

    if "fox" in p:
        fc = (rng.randint(180, 230), rng.randint(80, 120), rng.randint(20, 50))
        fx = rng.randint(w // 3, 2 * w // 3)
        fy = sky_h + rng.randint(20, 80)
        draw.ellipse([fx - 16, fy - 8, fx + 16, fy + 8], fill=fc)
        draw.ellipse([fx - 10, fy - 20, fx + 10, fy - 4], fill=fc)
        draw.polygon([(fx - 10, fy - 20), (fx - 18, fy - 32), (fx - 4, fy - 24)], fill=fc)
        draw.polygon([(fx + 10, fy - 20), (fx + 18, fy - 32), (fx + 4, fy - 24)], fill=fc)
        draw.ellipse([fx - 4, fy - 18, fx - 1, fy - 15], fill=(0, 0, 0))
        draw.ellipse([fx + 1, fy - 18, fx + 4, fy - 15], fill=(0, 0, 0))
        draw.polygon([(fx - 4, fy + 4), (fx, fy + 16), (fx + 4, fy + 4)], fill=(255, 255, 255))

    if "horse" in p or "elephant" in p or "giraffe" in p:
        hx = rng.randint(w // 3, 2 * w // 3)
        hy = sky_h + rng.randint(20, 80)
        if "elephant" in p:
            body_c = (rng.randint(100, 140), rng.randint(100, 140), rng.randint(100, 140))
        elif "giraffe" in p:
            body_c = (rng.randint(180, 220), rng.randint(140, 180), rng.randint(50, 90))
        else:
            body_c = (rng.randint(80, 150), rng.randint(60, 120), rng.randint(40, 80))
        draw.ellipse([hx - 22, hy - 10, hx + 22, hy + 10], fill=body_c)
        draw.ellipse([hx - 18, hy - 24, hx + 4, hy - 4], fill=body_c)
        draw.rectangle([hx - 3, hy + 8, hx + 3, hy + 24], fill=body_c)
        draw.rectangle([hx + 10, hy + 8, hx + 16, hy + 20], fill=body_c)
        draw.rectangle([hx - 16, hy + 8, hx - 10, hy + 20], fill=body_c)
        if "elephant" in p:
            draw.line([(hx - 14, hy - 4), (hx - 28, hy - 2), (hx - 34, hy)], fill=body_c, width=4)
        elif "giraffe" in p:
            draw.line([(hx - 16, hy - 4), (hx - 10, hy - 24), (hx - 6, hy - 18)], fill=body_c, width=3)


def _draw_ground(draw, w, h, rng, prompt):
    pass


def _draw_scene_elements(draw, w, h, rng, prompt):
    pass


def seed_hash(prompt: str, offset: int = 0) -> int:
    return hash(prompt + str(offset)) & 0xFFFFFFFF
