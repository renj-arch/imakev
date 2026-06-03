"""Generate photorealistic video frames via free image APIs + motion compositing."""

import os, time, io, json, base64, random
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


IMAGE_SPACES = [
    {
        "name": "stabilityai/stable-diffusion-3.5-large",
        "api_name": "/infer",
        "data_fn": lambda p: [p, "", 0, True, 1024, 1024, 7.5, 28],
    },
]

VIDEO_SPACES = [
    {
        "name": "ozilion/text2video",
        "api_name": "/generate_video",
        "data_fn": lambda p, d: [p, "", 40, float(d), 512, 512, 25, 7.5, -1],
    },
    {
        "name": "null002/genmo-mochi-1-preview",
        "api_name": "/predict",
        "data_fn": lambda p, d: [p],
    },
]


def _gc_call(space_name: str, api_name: str, data: list, timeout: int = 300):
    """Call a Gradio Space and return the raw result tuple."""
    from gradio_client import Client
    print(f"    Loading Space {space_name}...")
    t0 = time.time()
    client = Client(space_name, verbose=False)
    print(f"    Space loaded in {time.time()-t0:.1f}s")
    print(f"    Calling api_name={api_name}...")
    t0 = time.time()
    job = client.submit(*data, api_name=api_name)
    print(f"    Job submitted, waiting for result...")
    result = job.result(timeout=timeout)
    print(f"    Result received in {time.time()-t0:.1f}s")
    return result


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
