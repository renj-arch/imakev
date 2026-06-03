"""Generate photorealistic video frames via free image APIs + motion compositing."""

import os, time, io, json, base64, random, threading, queue, shutil
from pathlib import Path
import requests as req
from PIL import Image
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
    """Download a free stock photo matching the prompt (no API key needed).
    Uses Unsplash source for random matching images."""
    import urllib.parse
    keywords = urllib.parse.quote(prompt.split(",")[0].strip().lower().replace(" ", "-"))
    urls = [
        f"https://source.unsplash.com/featured/?{keywords}",
        f"https://source.unsplash.com/800x600/?{keywords}",
    ]
    for url in urls:
        try:
            resp = req.get(url, timeout=15, allow_redirects=True)
            if resp.status_code == 200 and len(resp.content) > 10000:
                img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                img.save(output_path)
                print(f"    Stock photo downloaded ({img.size})")
                return img
        except Exception as e:
            print(f"    Stock photo error: {e}")
    return None


IMAGE_SPACES = [
    {"name": _space_url("stabilityai/stable-diffusion-3.5-large"), "api_name": "/infer", "data_fn": lambda p: [p, "", 0, True, 1024, 1024, 7.5, 28]},
    {"name": _space_url("stabilityai/stable-diffusion-xl-base-1.0"), "api_name": "/infer", "data_fn": lambda p: [p, "", 0, True, 1024, 1024, 7.5, 28]},
    {"name": _space_url("black-forest-labs/FLUX.1-dev"), "api_name": "/infer", "data_fn": lambda p: [p, "", 0, True, 1024, 1024, 7.5, 28]},
]

VIDEO_SPACES = [
    {"name": _space_url("ozilion/text2video"), "api_name": "/generate_video", "data_fn": lambda p, d: [p, "", 40, float(d), 512, 512, 25, 7.5, -1]},
    {"name": _space_url("null002/genmo-mochi-1-preview"), "api_name": "/predict", "data_fn": lambda p, d: [p]},
]

SVD_SPACES = [
    _space_url("multimodalart/stable-video-diffusion"),
]


def _gc_call(space_name: str, api_name: str, data: list, timeout: int = 300):
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


def _gc_raw_http(space_name: str, api_name: str, data: list, timeout: int = 300) -> tuple:
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

        print(f"    Trying SD image generation...")
        img = _gradio_image(prompt)
        if img is None or img.size[0] < 100:
            print(f"    SD image failed, downloading real stock photo...")
            img = _download_stock_photo(prompt, svd_img_path)
            if img is None:
                print(f"    No image source works, aborting SVD")
                return False
        img = img.resize((1024, 576), Image.LANCZOS)
        print(f"    Image resized to 1024x576")
        img.save(svd_img_path)
        print(f"    Saved to {svd_img_path}")

        for space_name in SVD_SPACES:
            try:
                print(f"    Calling {space_name} /video...")
                result = _gc_call(space_name, "/video", [svd_img_path, 42, True, 127, 6], timeout=180)
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
            result = _gc_call(space["name"], space["api_name"], data, timeout=120)
            if result and len(result) >= 1:
                img_path = result[0]
                if isinstance(img_path, str) and Path(img_path).exists():
                    return Image.open(img_path).convert("RGB")
        except Exception as e:
            print(f"    Gradio image error: {e}")
    return None


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
