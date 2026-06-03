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

# Free Gradio Spaces for photorealistic image generation (no signup)
IMAGE_SPACES = [
    {
        "name": "stabilityai/stable-diffusion-3.5-large",
        "subdomain": "stabilityai-stable-diffusion-3-5-large",
        "fn_index": 0,
        "data_fn": lambda p: [p, "", 0, 1, 1024, 1024, 7.5, 28],
    },
]

# Free text-to-video Spaces (experimental)
VIDEO_SPACES = [
    {
        "name": "ozilion/text2video",
        "api_name": "/predict",
        "data_fn": lambda p, d: [p, "", 40, float(d), 512, 512, 25, 7.5, -1],
    },
    {
        "name": "markury/wan-2-1-t2v-1-3b-lycoris",
        "api_name": "/predict",
        "data_fn": lambda p, d: [p, 5.0, 33, 512, 512, 7.0, 25, -1],
    },
]


def _call_gradio_space(space_info, payload_data, timeout=180):
    subdomain = space_info["subdomain"] if "subdomain" in space_info else space_info["name"].replace("/", "-")
    base = f"https://{subdomain}.hf.space"
    api_name = space_info.get("api_name", "/predict")

    # First request to wake up Space
    try:
        req.get(base, timeout=15)
    except Exception:
        pass

    # Submit via queue API
    submit_url = f"{base}/gradio_api/call{api_name}"
    resp = req.post(submit_url, json={"data": payload_data, "fn_index": space_info.get("fn_index", 0)},
                    timeout=timeout)
    if resp.status_code != 200:
        return None

    result = resp.json()
    event_id = result.get("event_id")
    if not event_id:
        return None

    # Poll
    for _ in range(timeout // 2):
        time.sleep(2)
        poll = req.get(f"{submit_url}/{event_id}", timeout=30)
        if poll.status_code != 200:
            continue
        data = poll.json()
        ev = data.get("event", "")
        if ev == "complete":
            return data.get("output", {}).get("data", [])
        if ev == "error":
            print(f"    Space error: {data.get('output', {}).get('text', 'unknown')[:150]}")
            return None
    return None


def _hf_inference_api(prompt: str) -> Image.Image | None:
    """Generate photorealistic image via Hugging Face Inference API (free, no key needed)."""
    model = "stabilityai/stable-diffusion-3.5-large"
    url = f"https://api-inference.huggingface.co/models/{model}"

    headers = {"Content-Type": "application/json"}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"

    payload = {
        "inputs": prompt,
        "parameters": {
            "negative_prompt": "cartoon, drawing, illustration, anime",
            "width": 720,
            "height": 1280,
            "guidance_scale": 7.5,
            "num_inference_steps": 25,
        }
    }

    try:
        resp = req.post(url, headers=headers, json=payload, timeout=120)
        if resp.status_code == 200:
            img = Image.open(io.BytesIO(resp.content))
            if img and img.size[0] > 100:
                return img.convert("RGB")
        print(f"    HF Inference: {resp.status_code} {resp.text[:100]}")
    except Exception as e:
        print(f"    HF Inference exception: {e}")
    return None


def _gradio_image(prompt: str) -> Image.Image | None:
    """Generate photorealistic image via Gradio Space."""
    for space in IMAGE_SPACES:
        try:
            data = space["data_fn"](prompt)
            out = _call_gradio_space(space, data, timeout=120)
            if out and len(out) > 0:
                val = out[0]
                if isinstance(val, dict) and "url" in val:
                    resp = req.get(val["url"], timeout=60)
                    if resp.status_code == 200:
                        return Image.open(io.BytesIO(resp.content)).convert("RGB")
                elif isinstance(val, str) and val.startswith("http"):
                    resp = req.get(val, timeout=60)
                    if resp.status_code == 200:
                        return Image.open(io.BytesIO(resp.content)).convert("RGB")
        except Exception as e:
            print(f"    Gradio image error: {e}")
    return None


def generate_photorealistic_frames(prompt: str, w: int = 720, h: int = 1280,
                                    num_frames: int = 30, fps: int = 6) -> list[np.ndarray] | None:
    """Generate frames that look like realistic AI video.

    Strategy:
    1. Generate one photorealistic keyframe from the prompt
    2. Generate variations with weather/lighting keywords
    3. Interpolate between them with smooth camera motion
    """
    # If we have keyframes, interpolate to create smooth video
    frames_per_scene = num_frames // max(len(all_keyframes), 1)

    result = []
    for i, kf in enumerate(all_keyframes):
        for j in range(frames_per_scene):
            # Apply Ken Burns zoom/pan for camera motion
            progress = j / max(frames_per_scene - 1, 1)
            frame = apply_ken_burns(kf, progress, zoom_in=(i % 2 == 0))
            result.append(frame)

    # Pad to exact frame count
    while len(result) < num_frames:
        result.append(result[-1])

    return result[:num_frames]


def generate_via_space_video(prompt: str, output_path: str | Path, duration: int = 5) -> bool:
    """Try generating a real AI video via Gradio Spaces."""
    output_path = Path(output_path)
    for space in VIDEO_SPACES:
        try:
            data = space["data_fn"](prompt, duration)
            out = _call_gradio_space(space, data, timeout=180)
            if not out:
                continue
            # Parse video output
            for item in out:
                if isinstance(item, dict) and "video" in item:
                    url = item["video"]
                elif isinstance(item, str) and item.startswith("http"):
                    url = item
                elif isinstance(item, dict) and "url" in item:
                    url = item["url"]
                else:
                    continue
                resp = req.get(url, timeout=120)
                if resp.status_code == 200 and len(resp.content) > 5000:
                    output_path.write_bytes(resp.content)
                    print(f"  Video saved from {space['name']} ({len(resp.content)} bytes)")
                    return True
        except Exception:
            continue
    return False
