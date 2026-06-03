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
        "api_name": "/infer",
        "data_fn": lambda p: [p, "", 0, True, 1024, 1024, 7.5, 28],
    },
]

# Free text-to-video Spaces (experimental)
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


def _gc_generate(space_name: str, api_name: str, data: list, timeout: int = 300) -> dict | None:
    try:
        from gradio_client import Client
        client = Client(space_name)
        job = client.submit(*data, api_name=api_name)
        result = job.result(timeout=timeout)
        if result and len(result) >= 2:
            video_part = result[0]
            if isinstance(video_part, dict) and "video" in video_part:
                return {"video": video_part["video"]}
        return None
    except Exception as e:
        print(f"    gradio_client error: {e}")
        return None


def generate_via_space_video(prompt: str, output_path: str | Path, duration: int = 5) -> bool:
    """Generate real AI video via Gradio Spaces (uses gradio_client)."""
    output_path = Path(output_path)
    for space in VIDEO_SPACES:
        try:
            data = space["data_fn"](prompt, duration)
            result = _gc_generate(space["name"], space["api_name"], data)
            if not result:
                continue
            url = result.get("video", "")
            if not url:
                continue
            resp = req.get(url, timeout=120)
            if resp.status_code == 200 and len(resp.content) > 5000:
                output_path.write_bytes(resp.content)
                print(f"  Video from {space['name']} ({len(resp.content)} bytes)")
                return True
        except Exception as e:
            print(f"    {space['name']} error: {e}")
    return False

def _hf_inference_api(prompt: str) -> Image.Image | None:
    """Generate photorealistic image via Hugging Face InferenceClient."""
    from huggingface_hub import InferenceClient
    client = InferenceClient(token=HF_TOKEN or None)
    try:
        img = client.text_to_image(
            prompt,
            model="stabilityai/stable-diffusion-3.5-large",
            height=1280,
            width=720,
            guidance_scale=7.5,
            num_inference_steps=25,
        )
        if img and img.size[0] > 100:
            return img.convert("RGB")
    except Exception as e:
        print(f"    HF InferenceClient: {e}")
    return None


def _gradio_image(prompt: str) -> Image.Image | None:
    """Generate photorealistic image via Gradio Space (uses gradio_client)."""
    for space in IMAGE_SPACES:
        try:
            data = space["data_fn"](prompt)
            result = _gc_generate_image(space["name"], space["api_name"], data)
            if result:
                return result
        except Exception as e:
            print(f"    Gradio image error: {e}")
    return None


def _gc_generate_image(space_name: str, api_name: str, data: list, timeout: int = 120) -> Image.Image | None:
    try:
        from gradio_client import Client
        client = Client(space_name)
        job = client.submit(*data, api_name=api_name)
        result = job.result(timeout=timeout)
        if result and len(result) >= 1:
            img_path = result[0]
            if isinstance(img_path, str) and Path(img_path).exists():
                return Image.open(img_path).convert("RGB")
        return None
    except Exception as e:
        print(f"    gradio_client error: {e}")
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
