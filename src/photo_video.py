"""Generate photorealistic video frames via free image APIs + motion compositing."""

import os, time, io, json, base64, random, threading, queue, shutil, hashlib
from pathlib import Path
import requests as req
from PIL import Image, ImageDraw, ImageFont
import numpy as np

HF_TOKEN = os.getenv("HF_TOKEN", "")


def apply_ken_burns(frame: np.ndarray, progress: float, zoom_in: bool = True) -> np.ndarray:
    h, w = frame.shape[:2]
    max_zoom = 1.12
    scale = 1.0 + (max_zoom - 1.0) * (progress if zoom_in else 1.0 - progress)
    new_w, new_h = int(w * scale), int(h * scale)
    img = Image.fromarray(frame).resize((new_w, new_h), Image.LANCZOS)
    x = (new_w - w) // 2
    y = int((new_h - h) * (progress if not zoom_in else 0.0))
    y = max(0, min(y, new_h - h))
    return np.array(img.crop((x, y, x + w, y + h)))


def _space_url(repo_id: str) -> str:
    """Convert repo_id to Gradio Space direct URL (bypasses HF API entirely)."""
    s = repo_id.replace("/", "-").lower().replace(".", "-")
    return f"https://{s}.hf.space"


def _download_stock_photo(prompt: str, output_path: str | Path) -> Image.Image | None:
    """Download a free photo matching the prompt (no API key needed).
    Uses loremflickr for searchable Flickr CC images."""
    import urllib.parse
    # Extract key subject words from prompt for Flickr search
    words = prompt.lower().split(",")[0].strip().split()
    # Keep nouns/adjectives, remove generic words
    stop = {"a", "an", "the", "tiny", "small", "big", "large", "beside", "with", "in", "on", "at", "for", "and"}
    keywords = ",".join(w for w in words if w not in stop)[:80]
    urls = [
        f"https://loremflickr.com/1024/576/{keywords}",
        f"https://loremflickr.com/1024/576/{keywords.split(',')[0]}",
        f"https://picsum.photos/1024/576",
    ]
    for url in urls:
        try:
            resp = req.get(url, timeout=15)
            if resp.status_code == 200 and len(resp.content) > 10000:
                img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                img.save(output_path)
                print(f"    Stock photo downloaded ({img.size})")
                return img
        except Exception as e:
            print(f"    Stock photo error: {e}")
    return None


IMAGE_SPACES = [
    {"name": _space_url("stabilityai/stable-diffusion-3.5-large"), "api_name": "/infer", "data_fn": lambda p: [p, "", 0, True, 1024, 1024, 7.5, 28], "timeout": 45},
    {"name": _space_url("stabilityai/stable-diffusion-xl-base-1.0"), "api_name": "/infer", "data_fn": lambda p: [p, "", 0, True, 1024, 1024, 7.5, 28], "timeout": 45},
    {"name": _space_url("black-forest-labs/FLUX.1-dev"), "api_name": "/infer", "data_fn": lambda p: [p, "", 0, True, 1024, 1024, 7.5, 28], "timeout": 45},
]

VIDEO_SPACES = [
    {"name": _space_url("ozilion/text2video"), "api_name": "/generate_video", "data_fn": lambda p, d: [p, "", 40, float(d), 512, 512, 25, 7.5, -1], "timeout": 60},
    {"name": _space_url("null002/genmo-mochi-1-preview"), "api_name": "/predict", "data_fn": lambda p, d: [p], "timeout": 60},
]

WAN_I2V_SPACE = "https://r3gm-wan2-2-fp8da-aoti-preview-2.hf.space"

SVD_SPACES = [
    _space_url("multimodalart/stable-video-diffusion"),
]


def _gc_call(space_name: str, api_name: str, data: list, timeout: int = 60):
    """Call a Gradio Space and return the raw result tuple.
    Retries with backoff on 429 (HF API rate limit).
    Falls back to raw HTTP POST if gradio_client repeatedly fails.
    """
    from gradio_client import Client
    deadline = time.time() + timeout
    last_err = None
    for attempt in range(3):
        try:
            print(f"    Loading Space {space_name} (attempt {attempt+1})...")
            t0 = time.time()
            client = Client(space_name, verbose=False)
            print(f"    Space loaded in {time.time()-t0:.1f}s")
            print(f"    Calling api_name={api_name}...")
            t0 = time.time()
            job = client.submit(*data, api_name=api_name)
            print(f"    Job submitted, waiting for result...")
            result = job.result(timeout=max(30, int(deadline - time.time())))
            print(f"    Result received in {time.time()-t0:.1f}s")
            return result
        except Exception as e:
            last_err = e
            estr = str(e)
            if "429" in estr or "Too Many Requests" in estr or "Rate limit" in estr:
                wait = min(15 * (attempt + 1), 30)
                print(f"    429 hit, waiting {wait}s then retry...")
                time.sleep(wait)
                continue
            if "ZeroGPU" in estr or "quota" in estr:
                wait = min(20 * (attempt + 1), 60)
                print(f"    ZeroGPU quota, waiting {wait}s...")
                time.sleep(wait)
                continue
            if "409" in estr or "space is loading" in estr.lower():
                wait = 15
                print(f"    Space loading/warmup, waiting {wait}s...")
                time.sleep(wait)
                continue
            print(f"    Non-retryable error: {e}")
    print(f"    All retries exhausted, trying raw HTTP fallback...")
    return _gc_raw_http(space_name, api_name, data, timeout)


def _gc_raw_http(space_name: str, api_name: str, data: list, timeout: int = 60) -> tuple:
    """Call Gradio Space API directly via HTTP, bypassing gradio_client entirely."""
    space_url = space_name if space_name.startswith("http") else _space_url(space_name)
    api_url = space_url.rstrip("/") + f"/call/{api_name.lstrip('/')}"
    print(f"    Raw HTTP to {api_url}...")
    payload: list = []
    for d in data:
        if isinstance(d, Image.Image):
            buf = io.BytesIO()
            d.save(buf, format="PNG")
            buf.seek(0)
            upload_url = space_url.rstrip("/") + "/upload"
            r = req.post(upload_url, files={"files": ("img.png", buf, "image/png")}, timeout=30)
            if r.status_code != 200:
                raise Exception(f"Upload failed: {r.status_code}")
            uploaded = r.json()
            payload.append({"path": uploaded[0] if isinstance(uploaded, list) else uploaded})
        else:
            payload.append(d)
    t0 = time.time()
    r = req.post(api_url, json={"data": payload}, timeout=timeout)
    if r.status_code != 200:
        raise Exception(f"API call failed: {r.status_code} {r.text[:200]}")
    event_id = r.json().get("event_id")
    if not event_id:
        raise Exception(f"No event_id: {r.text[:200]}")
    poll_url = api_url + f"/{event_id}/data"
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = req.get(poll_url, timeout=30)
        if r.status_code == 200:
            for line in r.text.strip().split("\n"):
                if line.startswith("data:"):
                    try:
                        parsed = json.loads(line[5:].strip())
                        if isinstance(parsed, list) and len(parsed) > 0 and parsed[0] is not None:
                            print(f"    Raw HTTP result in {time.time()-t0:.1f}s")
                            return tuple(parsed)
                    except json.JSONDecodeError:
                        continue
        time.sleep(0.5)
    raise TimeoutError(f"Raw HTTP Gradio timed out ({timeout}s)")


def _generate_placeholder_image(prompt: str, w: int = 1024, h: int = 576) -> str:
    """Create a simple colored image from prompt keywords as seed for I2V."""
    import hashlib
    seed = int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16)
    rnd = random.Random(seed)
    bg_color = (rnd.randint(20, 60), rnd.randint(30, 80), rnd.randint(50, 120))
    img = Image.new('RGB', (w, h), color=bg_color)
    draw = ImageDraw.Draw(img)
    for _ in range(rnd.randint(8, 16)):
        x1 = rnd.randint(0, w)
        y1 = rnd.randint(0, h)
        x2 = rnd.randint(0, w)
        y2 = rnd.randint(0, h)
        color = (rnd.randint(60, 200), rnd.randint(60, 200), rnd.randint(60, 200))
        draw.ellipse([min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)], fill=color, outline=None)
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except Exception:
        font = ImageFont.load_default()
    words = [w for w in prompt.split() if len(w) > 3][:4]
    label = " ".join(words) if words else "AI"
    bbox = draw.textbbox((0, 0), label, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text(((w - tw) // 2, (h - th) // 2), label, fill=(255, 255, 255), font=font)
    path = Path("_wan_seed.png")
    img.save(path)
    return str(path)


def generate_wan_i2v(prompt: str, output_path: str | Path, duration: int = 5) -> bool:
    """Generate realistic AI video via Wan 2.2 I2V Space (free, no API key).
    Creates a placeholder seed image from prompt, then animates it via the Space.
    """
    output_path = Path(output_path)
    try:
        from gradio_client import Client, handle_file
        img_path = _generate_placeholder_image(prompt)
        print(f"    Seed image created: {img_path}")
        client = Client(WAN_I2V_SPACE, verbose=False)
        print(f"    Calling Wan 2.2 I2V...")
        t0 = time.time()
        result = client.predict(
            handle_file(img_path),
            None,
            prompt + ", cinematic, realistic, high quality motion",
            6,                          # slider
            "",                         # negative prompt
            3.5,                        # guidance
            1.0, 1.0, 42, True, 6,     # sliders
            'UniPCMultistep',           # scheduler
            3.0,                        # slider
            16,                         # steps
            True, True,
            api_name='/generate_video'
        )
        elapsed = time.time() - t0
        print(f"    Wan result in {elapsed:.1f}s")
        if isinstance(result, (list, tuple)):
            for item in result:
                if isinstance(item, str) and item.startswith("http"):
                    resp = req.get(item, timeout=120)
                    if resp.status_code == 200 and len(resp.content) > 5000:
                        output_path.write_bytes(resp.content)
                        print(f"  Wan 2.2 video saved ({len(resp.content)} bytes)")
                        return True
                if isinstance(item, str):
                    p = Path(item)
                    if p.exists():
                        import shutil
                        shutil.copy2(str(p), str(output_path))
                        print(f"  Wan 2.2 video saved ({p.stat().st_size} bytes)")
                        return True
                if isinstance(item, dict):
                    for v in item.values():
                        if isinstance(v, str) and v.startswith("http"):
                            resp = req.get(v, timeout=120)
                            if resp.status_code == 200 and len(resp.content) > 5000:
                                output_path.write_bytes(resp.content)
                                print(f"  Wan 2.2 video saved ({len(resp.content)} bytes)")
                                return True
        print(f"    Could not extract video from Wan result")
        return False
    except Exception as e:
        estr = str(e)
        if "ZeroGPU" in estr or "quota" in estr:
            print(f"    Wan 2.2 ZeroGPU quota exhausted: {estr[:100]}")
        else:
            print(f"    Wan 2.2 error: {estr[:200]}")
        return False


def generate_via_space_video(prompt: str, output_path: str | Path, duration: int = 5) -> bool:
    """Generate real AI video via Gradio Spaces (uses gradio_client)."""
    output_path = Path(output_path)
    for space in VIDEO_SPACES:
        try:
            data = space["data_fn"](prompt, duration)
            result = _gc_call(space["name"], space["api_name"], data, timeout=space.get("timeout", 300))
            print(f"    Raw result type={type(result).__name__}, len={len(str(result))}")
            if result is None:
                print(f"    No result from {space['name']}")
                continue
            if isinstance(result, (list, tuple)):
                for i, item in enumerate(result):
                    print(f"    item[{i}]: type={type(item).__name__}, val={str(item)[:200]}")
                    if isinstance(item, dict):
                        for k, v in item.items():
                            print(f"      dict key={k}, val={str(v)[:200]}")
            url = _extract_video_url(result)
            if not url:
                print(f"    No video URL found in result")
                continue
            resp = req.get(url, timeout=120)
            if resp.status_code == 200 and len(resp.content) > 5000:
                output_path.write_bytes(resp.content)
                print(f"  Video saved from {space['name']} ({len(resp.content)} bytes)")
                return True
        except Exception as e:
            print(f"    {space['name']} error: {e}")
    return False


def _extract_video_url(result) -> str | None:
    """Extract a video URL from various result formats."""
    if result is None:
        return None
    if isinstance(result, str) and result.startswith("http"):
        return result
    if isinstance(result, dict):
        if "video" in result:
            v = result["video"]
            if isinstance(v, str):
                return v
            if isinstance(v, dict):
                return v.get("url", v.get("video", ""))
        for v in result.values():
            if isinstance(v, str) and v.startswith("http"):
                return v
        return None
    if isinstance(result, (list, tuple)):
        for item in result:
            url = _extract_video_url(item)
            if url:
                return url
    return None


def generate_via_svd_img2vid(prompt: str, output_path: str | Path, duration: int = 4) -> bool:
    """Generate SD image then animate via SVD Space img2vid.
    Falls back to a real stock photo if AI image generation fails (ZeroGPU quota exhausted)."""
    output_path = Path(output_path)
    try:
        svd_img_path = str(output_path.with_suffix(".svd_input.png"))

        print(f"    Downloading stock photo (fast, no GPU needed)...")
        img = _download_stock_photo(prompt, svd_img_path)
        if img is None or img.size[0] < 100:
            print(f"    Stock photo failed, trying SD Space...")
            img = _gradio_image(prompt)
            if img is None or img.size[0] < 100:
                print(f"    No image source works, aborting SVD")
                return False
        img = img.resize((1024, 576), Image.LANCZOS)
        print(f"    Image resized to 1024x576")
        img.save(svd_img_path)
        print(f"    Saved to {svd_img_path}")

        for space_name in SVD_SPACES:
            try:
                print(f"    Calling {space_name} /video...")
                result = _gc_call(space_name, "/video", [svd_img_path, 42, True, 127, 6], timeout=45)
                if result and len(result) >= 1:
                    video_part = result[0]
                    if isinstance(video_part, str):
                        vid_path = Path(video_part)
                        if vid_path.exists():
                            shutil.copy2(str(vid_path), str(output_path))
                            print(f"  SVD video saved ({vid_path.stat().st_size} bytes)")
                            return True
                        if video_part.startswith("http"):
                            resp = req.get(video_part, timeout=60)
                            if resp.status_code == 200 and len(resp.content) > 5000:
                                output_path.write_bytes(resp.content)
                                print(f"  SVD downloaded ({len(resp.content)} bytes)")
                                return True
                    if isinstance(video_part, dict):
                        for v in video_part.values():
                            if isinstance(v, str) and v.startswith("http"):
                                resp = req.get(v, timeout=60)
                                if resp.status_code == 200 and len(resp.content) > 5000:
                                    output_path.write_bytes(resp.content)
                                    print(f"  SVD downloaded dict ({len(resp.content)} bytes)")
                                    return True
                            if isinstance(v, str) and Path(v).exists():
                                shutil.copy2(v, str(output_path))
                                print(f"  SVD video saved dict ({Path(v).stat().st_size} bytes)")
                                return True
            except Exception as e:
                print(f"    {space_name} error: {e}")
        return False
    except Exception as e:
        print(f"    SVD img2vid error: {e}")
        return False


def _hf_inference_api(prompt: str) -> Image.Image | None:
    from huggingface_hub import InferenceClient
    client = InferenceClient(token=HF_TOKEN or None)
    try:
        img = client.text_to_image(
            prompt,
            model="stabilityai/stable-diffusion-3.5-large",
            height=1280, width=720,
            guidance_scale=7.5, num_inference_steps=25,
        )
        if img and img.size[0] > 100:
            return img.convert("RGB")
    except Exception as e:
        print(f"    HF InferenceClient: {e}")
    return None


def _gradio_image(prompt: str) -> Image.Image | None:
    for space in IMAGE_SPACES:
        try:
            data = space["data_fn"](prompt)
            result = _gc_call(space["name"], space["api_name"], data, timeout=space.get("timeout", 45))
            if result and len(result) >= 1:
                img_path = result[0]
                if isinstance(img_path, str) and Path(img_path).exists():
                    return Image.open(img_path).convert("RGB")
        except Exception as e:
            print(f"    Gradio image error: {e}")
    return None


def _extract_keywords(prompt: str, max_words: int = 3) -> str:
    stop = {"a", "an", "the", "in", "on", "at", "for", "and", "of", "to", "is", "it", "with", "this", "that",
            "tiny", "small", "big", "large", "beside", "under", "over", "above", "below", "beside", "behind"}
    words = prompt.lower().split(",")[0].strip().split()
    keywords = [w for w in words if w not in stop and len(w) > 2][:max_words]
    return ",".join(keywords) if keywords else "nature,landscape"


def _download_multiple_photos(prompt: str, count: int = 5, w: int = 720, h: int = 1280) -> list[Image.Image]:
    keywords = _extract_keywords(prompt)
    results = []
    seen = set()
    sources = [
        f"https://loremflickr.com/{w*2}/{h*2}/{keywords}",
        f"https://loremflickr.com/{w*2}/{h*2}/{keywords.split(',')[0]}",
        f"https://picsum.photos/{w*2}/{h*2}",
    ]
    for attempt in range(3):
        for url in sources:
            try:
                resp = req.get(url, timeout=20)
                if resp.status_code == 200 and len(resp.content) > 10000:
                    key = hashlib.md5(resp.content[:500]).hexdigest()
                    if key in seen:
                        continue
                    seen.add(key)
                    img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                    img = img.resize((w, h), Image.LANCZOS)
                    results.append(img)
                    if len(results) >= count:
                        return results
            except Exception:
                continue
    return results


def generate_stock_photo_video(prompt: str, w: int = 720, h: int = 1280,
                                num_frames: int = 60, fps: int = 12) -> list[np.ndarray] | None:
    """Download free stock photos matching prompt and create a Ken Burns video."""
    print(f"    Downloading stock photos for: {prompt[:60]}...")
    photos = _download_multiple_photos(prompt, count=min(6, max(2, num_frames // 10)), w=w, h=h)
    if not photos:
        print("    No stock photos downloaded")
        return None
    print(f"    {len(photos)} stock photos downloaded")
    frames_per_photo = num_frames // len(photos)
    result = []
    for i, photo in enumerate(photos):
        arr = np.array(photo)
        for j in range(frames_per_photo):
            progress = j / max(frames_per_photo - 1, 1)
            zoom_in = (i % 2 == 0)
            frame = apply_ken_burns(arr, progress, zoom_in=zoom_in)
            result.append(frame)
    while len(result) < num_frames:
        result.append(result[-1])
    print(f"    Generated {len(result)} Ken Burns frames")
    return result[:num_frames]


def generate_ai_image_video(prompt: str, w: int = 720, h: int = 1280,
                             num_frames: int = 60, fps: int = 12) -> list[np.ndarray] | None:
    """Generate realistic AI video frames via Pollinations.ai (free, no API key).
    Creates varied cinematic images matching the prompt, then applies smooth
    Ken Burns zoom + crossfade for a realistic video feel."""
    keywords = _extract_keywords(prompt, max_words=4) or "nature,landscape"
    variants = [
        f"{prompt}, cinematic lighting, 4K, photorealistic, wide shot, dramatic",
        f"{prompt}, cinematic lighting, detailed, sharp focus, close-up view",
        f"{prompt}, golden hour, warm tones, cinematic, highly detailed",
        f"{prompt}, dynamic composition, dramatic shadows, cinematic mood",
        f"{prompt}, epic cinematic, vibrant colors, stunning visuals, 4K",
        f"{prompt}, cinematic wide angle, atmospheric, breathtaking scenery",
    ]
    all_keyframes = []
    images_needed = max(3, min(6, num_frames // 8))
    from src.image_gen import _try_pollinations
    for i in range(images_needed):
        vp = variants[i % len(variants)]
        img = _try_pollinations(vp, w, h, "flux")
        if img is None:
            img = _try_pollinations(vp, w, h, "sana")
        if img:
            all_keyframes.append(np.array(img))
            print(f"    AI image {i+1}/{images_needed} generated")
        else:
            print(f"    AI image {i+1}/{images_needed} failed, trying stock photo...")
            img = _download_stock_photo(vp, str(Path("_temp_ai_video_img.png")))
            if img:
                img = img.resize((w, h), Image.LANCZOS)
                all_keyframes.append(np.array(img))
    if not all_keyframes:
        print("  No AI images generated")
        return None
    print(f"  {len(all_keyframes)} keyframes generated")
    frames_per_scene = num_frames // max(len(all_keyframes), 1)
    result = []
    for i, kf in enumerate(all_keyframes):
        for j in range(frames_per_scene):
            progress = j / max(frames_per_scene - 1, 1)
            zoom_in = (i % 2 == 0)
            frame = apply_ken_burns(kf, progress, zoom_in=zoom_in)
            result.append(frame)
    while len(result) < num_frames:
        result.append(result[-1])
    print(f"  Generated {len(result)} AI video frames")
    return result[:num_frames]


def generate_hf_text_to_video(prompt: str, output_path: str | Path,
                               duration: int = 5, hf_token: str = "") -> bool:
    """Generate real AI video via HuggingFace text-to-video inference.
    Tries multiple models, both serverless and Spaces. No API key needed (but HF_TOKEN helps)."""
    output_path = Path(output_path)
    models_to_try = [
        "genmo/mochi-1-preview",
        "Lightricks/LTX-Video-0.9.8-13B-distilled",
        "Wan-AI/Wan2.2-T2V-14B",
        "Wan-AI/Wan2.2-T2V-1.3B",
        "dataautogpt3/Text-To-Video",
    ]
    last_err = None
    base_urls = [
        "https://api-inference.huggingface.co/models/{model}",
        "https://router.huggingface.co/hf-inference/models/{model}",
    ]
    for base_url_template in base_urls:
        for model_id in models_to_try:
            try:
                url = base_url_template.format(model=model_id)
                print(f"    HF T2V {model_id}...")
                headers = {"Content-Type": "application/json"}
                token = hf_token or os.getenv("HF_TOKEN", "")
                if token:
                    headers["Authorization"] = f"Bearer {token}"
                payload = {"inputs": prompt, "parameters": {"num_frames": min(49, int(duration * 8))}}
                t0 = time.time()
                r = req.post(url, headers=headers, json=payload, timeout=180)
                elapsed = time.time() - t0
                print(f"    Status {r.status_code} ({elapsed:.0f}s, {len(r.content)} bytes)")
                if r.status_code == 200 and len(r.content) > 5000:
                    output_path.write_bytes(r.content)
                    print(f"  HF T2V video saved ({len(r.content)} bytes)")
                    return True
                if r.status_code in (401, 403):
                    if not token:
                        continue
                    continue
                if r.status_code == 503:
                    try:
                        wait = min(int(r.headers.get("x-wait-for-model", 60)), 60)
                    except:
                        wait = 30
                    print(f"    Model loading, waiting {wait}s...")
                    time.sleep(wait)
                    r = req.post(url, headers=headers, json=payload, timeout=180)
                    if r.status_code == 200 and len(r.content) > 5000:
                        output_path.write_bytes(r.content)
                        print(f"  HF T2V video saved ({len(r.content)} bytes)")
                        return True
            except Exception as e:
                last_err = e
                estr = str(e)
                if "getaddrinfo" in estr or "resolve" in estr.lower():
                    continue
                print(f"    {model_id} error: {e}")
        if "getaddrinfo" in str(last_err or ""):
            break
    print(f"  HF T2V failed, last error: {last_err}")
    return False


def generate_coverr_video(prompt: str, output_path: str | Path) -> bool:
    """Download free stock video clip from Coverr (no API key needed).
    Searches by prompt keywords, falls back to individual keywords then broad nature.
    Returns True if video written successfully."""
    output_path = Path(output_path)
    base_keywords = _extract_keywords(prompt, max_words=3)
    queries = []
    if base_keywords:
        queries.append(base_keywords)
        for kw in base_keywords.split(","):
            queries.append(kw)
    queries.append("nature,landscape,scenery")
    seen_titles = set()
    for q in queries:
        if not q:
            continue
        print(f"    Searching Coverr for: {q}...")
        try:
            r = req.get(f"https://coverr.co/api/videos?query={q}&per_page=5", timeout=10)
            if r.status_code != 200:
                continue
            hits = r.json().get("hits", [])
            if not hits:
                print(f"    No Coverr videos found for '{q}'")
                continue
            print(f"    {len(hits)} Coverr videos found for '{q}'")

            for hit in hits[:3]:
                title = hit.get("title", "")
                if title in seen_titles:
                    continue
                seen_titles.add(title)
                vid_id = hit.get("video_id", "")
                if not vid_id:
                    continue
                rd = req.get(f"https://coverr.co/api/videos/{vid_id}", timeout=10)
                if rd.status_code != 200:
                    continue
                details = rd.json()
                dl_url = (details.get("urls") or {}).get("mp4", "")
                if not dl_url:
                    continue
                print(f"    Downloading {title}...")
                t0 = time.time()
                rv = req.get(dl_url, timeout=60)
                if rv.status_code == 200 and len(rv.content) > 50000:
                    output_path.write_bytes(rv.content)
                    print(f"    Downloaded ({len(rv.content)} bytes) in {time.time()-t0:.1f}s")
                    print(f"  Coverr video saved: {output_path.name}")
                    return True
        except Exception:
            continue
    print(f"    No Coverr videos available")
    return False


def generate_photorealistic_frames(prompt: str, w: int = 720, h: int = 1280,
                                    num_frames: int = 30, fps: int = 6) -> list[np.ndarray] | None:
    base_prompt = prompt.split(",")[0].strip()
    scenes = [
        (f"{base_prompt}, cinematic lighting, 4K, photorealistic, sharp focus", 1.0),
    ]
    all_keyframes = []
    for sp, scale in scenes:
        img = _hf_inference_api(sp)
        if img is None:
            print(f"    Trying Gradio Space for photorealistic image...")
            img = _gradio_image(sp)
        if img:
            img = img.resize((w, h), Image.LANCZOS)
            all_keyframes.append(np.array(img))
        else:
            print(f"  Could not generate image for: {sp[:50]}")
    if not all_keyframes:
        print("  No photorealistic images generated")
        return None
    frames_per_scene = num_frames // max(len(all_keyframes), 1)
    result = []
    for i, kf in enumerate(all_keyframes):
        for j in range(frames_per_scene):
            progress = j / max(frames_per_scene - 1, 1)
            frame = apply_ken_burns(kf, progress, zoom_in=(i % 2 == 0))
            result.append(frame)
    while len(result) < num_frames:
        result.append(result[-1])
    return result[:num_frames]


def generate_pollinations_video(prompt: str, output_path: str | Path,
                                timeout: int = 60) -> bool:
    """Generate AI video via Pollinations.AI free API (no GPU needed)."""
    output_path = Path(output_path)
    key = os.getenv("POLLINATIONS_KEY", "")
    if not key:
        print("    POLLINATIONS_KEY not set, skipping")
        return False
    try:
        import urllib.parse
        enc = urllib.parse.quote(prompt)
        url = f"https://gen.pollinations.ai/video/{enc}?key={key}"
        print(f"    Pollinations API: {url[:80]}...")
        resp = req.get(url, stream=True, timeout=timeout)
        if resp.status_code != 200:
            print(f"    Pollinations returned {resp.status_code}")
            return False
        with open(str(output_path), "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        sz = output_path.stat().st_size
        print(f"    Pollinations video saved ({sz} bytes)")
        return sz > 1000
    except Exception as e:
        print(f"    Pollinations error: {e}")
        return False


def generate_freeai_video(prompt: str, output_path: str | Path,
                          timeout: int = 120,
                          model: str = "") -> bool:
    """Generate AI video via Free.ai API (free tier, no GPU needed).
    First tries Free.ai SDK anonymous mode (no API key needed, daily free limits).
    Falls back to key-based HTTP if SDK unavailable or anonymous fails.
    Free models: cogvideox (default, self-hosted), wan22-ti2v-5b (Wan 2.2), hunyuan-video.
    Free account: 30K tokens/day, ~6 videos/day. No credit card needed."""
    output_path = Path(output_path)
    key = os.getenv("FREEAI_API_KEY", "")
    model = model or os.getenv("FREEAI_VIDEO_MODEL", "cogvideox")

    # Try 1: Free.ai SDK anonymous mode (no key needed)
    try:
        from freeai import FreeAI
        print(f"    Free.ai SDK (anonymous): {prompt[:60]}...")
        t0 = time.time()
        ai = FreeAI()
        video = ai.video(prompt, model=model)
        video.save(str(output_path))
        sz = output_path.stat().st_size
        elapsed = time.time() - t0
        print(f"    Free.ai SDK saved ({sz} bytes) in {elapsed:.0f}s")
        return True
    except ImportError:
        print(f"    free-dot-ai SDK not installed")
    except Exception as e:
        estr = str(e)
        if "402" in estr or "InsufficientCredits" in estr:
            print(f"    Free.ai SDK: daily token pool exhausted")
        elif "401" in estr or "Authentication" in estr:
            print(f"    Free.ai SDK: anonymous not allowed for video")
        else:
            print(f"    Free.ai SDK error: {estr[:200]}")

    # Try 2: Raw HTTP with API key (if configured)
    if not key:
        print("    FREEAI_API_KEY not set, skipping key-based fallback")
        return False
    try:
        url = "https://api.free.ai/v1/video/generate/"
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        payload = {
            "prompt": prompt,
            "duration": 5,
            "model": model,
        }
        print(f"    Free.ai HTTP ({model}): {prompt[:60]}...")
        t0 = time.time()
        r = req.post(url, headers=headers, json=payload, timeout=timeout)
        elapsed = time.time() - t0
        print(f"    Status {r.status_code} ({elapsed:.0f}s)")
        if r.status_code != 200:
            print(f"    Free.ai error: {r.status_code} {r.text[:200]}")
            return False
        data = r.json()
        video_url = data.get("video_url", "")
        if not video_url:
            print(f"    No video_url in response")
            return False
        print(f"    Downloading video...")
        rv = req.get(video_url, timeout=120)
        if rv.status_code == 200 and len(rv.content) > 5000:
            output_path.write_bytes(rv.content)
            sz = output_path.stat().st_size
            print(f"    Free.ai video saved ({sz} bytes)")
            return True
        print(f"    Download failed: {rv.status_code} ({len(rv.content)} bytes)")
        return False
    except Exception as e:
        print(f"    Free.ai HTTP error: {e}")
        return False


def generate_openrouter_video(prompt: str, output_path: str | Path,
                              timeout: int = 300,
                              model: str = "") -> bool:
    """Generate AI video via OpenRouter API (uses your existing LLM_API_KEY).
    Model defaults to OPENROUTER_VIDEO_MODEL env var or 'google/veo-3.1-lite'.
    Polls async job until completion, then downloads the video."""
    output_path = Path(output_path)
    api_key = os.getenv("LLM_API_KEY", "")
    if not api_key:
        print("    LLM_API_KEY not set, skipping OpenRouter video")
        return False
    model = model or os.getenv("OPENROUTER_VIDEO_MODEL", "kwaivgi/kling-v3.0-std")
    base = "https://openrouter.ai/api/v1"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        quality_prompt = f"{prompt}, cinematic, highly detailed, smooth motion, 4K, sharp focus, professional"
        payload = {
            "model": model,
            "prompt": quality_prompt,
            "duration": 5,
            "resolution": "1080p",
            "aspect_ratio": "9:16",
            "generate_audio": False,
        }
        print(f"    OpenRouter video: model={model}")
        r = req.post(f"{base}/videos", headers=headers, json=payload, timeout=30)
        if r.status_code not in (200, 202):
            print(f"    OpenRouter submit failed: {r.status_code} {r.text[:200]}")
            return False
        job = r.json()
        job_id = job.get("id", "")
        polling_url = job.get("polling_url", f"{base}/videos/{job_id}")
        print(f"    Job submitted: {job_id}")
        deadline = time.time() + timeout
        while time.time() < deadline:
            r2 = req.get(polling_url, headers=headers, timeout=30)
            if r2.status_code != 200:
                print(f"    Poll failed: {r2.status_code}")
                time.sleep(5)
                continue
            status = r2.json()
            s = status.get("status", "")
            print(f"      Status: {s}")
            if s == "completed":
                unsigned_urls = status.get("unsigned_urls", [])
                if unsigned_urls:
                    dl_url = unsigned_urls[0]
                else:
                    dl_url = f"{base}/videos/{job_id}/content?index=0"
                dl_headers = dict(headers) if "openrouter.ai" in dl_url else {}
                r3 = req.get(dl_url, headers=dl_headers, timeout=120)
                if r3.status_code == 200 and len(r3.content) > 5000:
                    output_path.write_bytes(r3.content)
                    sz = output_path.stat().st_size
                    print(f"    OpenRouter video saved ({sz} bytes)")
                    return True
                print(f"    Download failed: {r3.status_code} ({len(r3.content)} bytes)")
                return False
            if s in ("failed", "error", "cancelled"):
                err_msg = status.get("error", status.get("message", "unknown"))
                print(f"    OpenRouter job failed: {err_msg}")
                return False
            time.sleep(5)
        print(f"    OpenRouter job timed out ({timeout}s)")
        return False
    except Exception as e:
        print(f"    OpenRouter error: {e}")
        return False


def generate_hf_space_video(prompt: str, output_path: str | Path,
                            num_frames: int = 16, num_inference_steps: int = 20,
                            guidance_scale: float = 7.5, timeout: int = 600) -> bool:
    """Generate AI video via Gradio Space API.
    Tries T2V_API_URL env var first (Kaggle/Colab notebook), then public HF Spaces.
    Works with: kaggle_cogvideo_api.ipynb (CogVideoX on free T4/P100, 30 hrs/week)
                colab_t2v_api.ipynb (Wan2.1 on free T4)"""
    output_path = Path(output_path)
    try:
        from gradio_client import Client
    except ImportError:
        print("    gradio_client not installed, skipping")
        return False

    hf_token = os.getenv("HF_TOKEN", "")
    custom_url = os.getenv("T2V_API_URL", "")

    # Priority 1: Custom Colab API
    if custom_url:
        print(f"    Using custom T2V API: {custom_url}")
        try:
            client = Client(custom_url)
            job = client.submit(prompt, num_inference_steps, guidance_scale, -1, api_name="/predict")
            waited = 0
            while not job.done() and waited < timeout:
                time.sleep(10)
                waited += 10
                s = job.status()
                print(f"      [{waited}s] {s.code.name}")
            if job.done():
                result = job.result()
                if result:
                    import shutil
                    fp = result[0] if isinstance(result, (list, tuple)) else result
                    shutil.copy2(str(fp), str(output_path))
                    sz = output_path.stat().st_size
                    print(f"    Colab video saved ({sz} bytes)")
                    return sz > 1000
        except Exception as e:
            print(f"    Custom API failed: {e}")

    # Priority 2: Public HF Spaces
    spaces = [
        ("HITMAN6178/text-to-video-gradio-demo", None,
         lambda c: c.predict(prompt, num_frames, num_inference_steps, guidance_scale,
                            api_name="/generate_video")),
        ("Nymbo/CogVideoX-5B-Space", None,
         lambda c: c.predict(prompt, api_name="/generate_video")),
        ("akhaliq/Text-To-Video", None,
         lambda c: c.predict(prompt, 25, 7.0, api_name="/run")),
        ("fffiloni/zeroscope-text-to-video", None,
         lambda c: c.predict(prompt, api_name="/run")),
    ]

    for space_id, api_name, predict_fn in spaces:
        print(f"    Trying HF Space: {space_id}")
        try:
            if hf_token:
                print(f"    Duplicating Space (dedicated GPU)...")
                client = Client.duplicate(space_id, hf_token=hf_token)
            else:
                client = Client(space_id)
            job = predict_fn(client)
            print(f"    Job submitted, waiting up to {timeout}s...")
            waited = 0
            while not job.done() and waited < timeout:
                time.sleep(10)
                waited += 10
                s = job.status()
                status_str = s.code.name
                if s.rank is not None:
                    status_str += f" (queue: {s.rank})"
                if s.eta:
                    status_str += f" eta: {s.eta:.0f}s"
                print(f"      [{waited}s] {status_str}")
            if job.done():
                result = job.result()
                print(f"    Result: {result}")
                if result:
                    import shutil
                    shutil.copy2(result, str(output_path))
                    size = output_path.stat().st_size
                    print(f"    Saved: {output_path} ({size} bytes)")
                    return True if size > 1000 else False
            else:
                print(f"    Space timed out after {timeout}s")
        except Exception as e:
            print(f"    Space {space_id} error: {e}")
            continue
    print("    All T2V sources failed")
    return False


_COGVIDEO_PIPE = None

def generate_cogvideo(prompt: str, output_path: str | Path,
                      num_frames: int = 49, num_inference_steps: int = 25,
                      guidance_scale: float = 6.0) -> bool:
    """Generate AI video via CogVideoX-2B (local, open-source, free, no API).
    Model is loaded on first call (lazy) — requires torch + diffusers.
    Runs on any GPU with ~6GB+ VRAM (fp16) or CPU (very slow)."""
    output_path = Path(output_path)
    global _COGVIDEO_PIPE
    try:
        if _COGVIDEO_PIPE is None:
            print("    Loading CogVideoX-2B (first call only)...")
            import torch
            from diffusers import CogVideoXPipeline
            dtype = torch.float16 if torch.cuda.is_available() else torch.float32
            _COGVIDEO_PIPE = CogVideoXPipeline.from_pretrained(
                "THUDM/CogVideoX-2b",
                torch_dtype=dtype,
            )
            if torch.cuda.is_available():
                _COGVIDEO_PIPE.to("cuda")
                _COGVIDEO_PIPE.enable_model_cpu_offload()
            print("    CogVideoX loaded")
        print(f"    Generating CogVideoX video ({num_frames} frames, {num_inference_steps} steps)...")
        t0 = time.time()
        result = _COGVIDEO_PIPE(
            prompt=prompt,
            num_frames=num_frames,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
        ).frames[0]
        elapsed = time.time() - t0
        print(f"    Generated in {elapsed:.1f}s, exporting...")
        from diffusers.utils import export_to_video
        export_to_video(result, str(output_path), fps=24)
        sz = output_path.stat().st_size
        print(f"    CogVideoX video saved ({sz} bytes)")
        return sz > 1000
    except Exception as e:
        print(f"    CogVideoX error: {e}")
        return False


def generate_mode_video_background(prompt: str, duration: float, w: int = 720, h: int = 1280,
                                    fps: int = 24) -> tuple:
    """Try to generate a real AI video background for any mode.
    Returns (VideoClip, bool) — bool indicates if real AI video was used.
    Falls back through all available methods, ending at image-based Ken Burns."""
    import numpy as np
    from moviepy import VideoFileClip, VideoClip, concatenate_videoclips

    temp_dir = Path("temp") / "mode_video"
    temp_dir.mkdir(parents=True, exist_ok=True)
    video_path = temp_dir / "ai_video.mp4"

    # Try real AI video generation methods (free/no-key methods first)
    generators = [
        ("HF Space T2V", lambda: generate_hf_space_video(prompt, video_path, num_frames=min(32, max(4, int(duration * 8))), num_inference_steps=25, timeout=600), 660),
        ("HF T2V", lambda: generate_hf_text_to_video(prompt, video_path, duration=min(5, int(duration))), 300),
        ("OpenRouter", lambda: generate_openrouter_video(prompt, video_path), 330),
        ("Free.ai", lambda: generate_freeai_video(prompt, video_path), 180),
        ("Pollinations AI", lambda: generate_pollinations_video(prompt, video_path), 90),
        ("CogVideoX", lambda: generate_cogvideo(prompt, video_path), 600),
    ]

    for name, gen_fn, timeout in generators:
        print(f"    [{name}] real AI video...")
        try:
            import threading
            result = [False]
            error = [None]
            done = threading.Event()
            def worker():
                try:
                    result[0] = gen_fn()
                except Exception as e:
                    error[0] = e
                finally:
                    done.set()
            t = threading.Thread(target=worker, daemon=True)
            t.start()
            if done.wait(timeout=timeout):
                if result[0]:
                    try:
                        vid = VideoFileClip(str(video_path))
                        if vid.duration < duration:
                            clips = [vid] * (int(duration // vid.duration) + 1)
                            vid = concatenate_videoclips(clips, method="compose").with_duration(duration)
                        else:
                            vid = vid.with_duration(duration)
                        print(f"    >> Using {name} AI video")
                        return vid, True
                    except Exception as e:
                        print(f"    {name} load failed: {e}")
            else:
                print(f"    {name} timed out ({timeout}s)")
        except Exception as e:
            print(f"    {name} error: {e}")

    # Fallback: AI image Ken Burns
    print("    Trying AI image Ken Burns fallback...")
    frames = generate_ai_image_video(prompt, w, h, int(duration * fps), fps)
    if frames:
        total_frames = len(frames)
        frame_dur = duration / max(total_frames, 1)
        def make_frame(t):
            return frames[min(int(t / frame_dur), total_frames - 1)]
        return VideoClip(make_frame, duration=duration), False

    # Fallback: Stock photo Ken Burns
    print("    Trying stock photo Ken Burns fallback...")
    frames = generate_stock_photo_video(prompt, w, h, int(duration * fps), fps)
    if frames:
        total_frames = len(frames)
        frame_dur = duration / max(total_frames, 1)
        def make_frame2(t):
            return frames[min(int(t / frame_dur), total_frames - 1)]
        return VideoClip(make_frame2, duration=duration), False

    print("    All video generation methods exhausted")
    return None, False
