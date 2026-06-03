"""AI Video generation — tries free sources in order, no API key needed."""

import os, time, json
import requests as req
from pathlib import Path

SUPPORTED_SPACES = {
    "text2video": {
        "space_name": "ozilion/text2video",
        "api_name": "/predict",
        "params": {
            "fn_index": 0,
        },
    },
}

def _hf_space_generate(prompt: str, output_path: str | Path, duration: int = 5) -> bool:
    space_name = SUPPORTED_SPACES["text2video"]["space_name"]
    subdomain = space_name.replace("/", "-")
    base = f"https://{subdomain}.hf.space"
    api_url = f"{base}/gradio_api/call/predict"

    payload = {
        "data": [
            prompt,
            "",  # negative_prompt
            40,  # num_frames (5s @ 8fps)
            float(duration),
            512,  # width
            512,  # height
            25,   # num_inference_steps
            7.5,  # guidance_scale
            -1,   # seed (random)
        ]
    }

    try:
        resp = req.post(api_url, json=payload, timeout=30)
        if resp.status_code != 200:
            print(f"  HF Space error {resp.status_code}: {resp.text[:200]}")
            return False

        result = resp.json()
        event_id = result.get("event_id")
        if not event_id:
            print(f"  No event_id: {result}")
            return False

        # Poll for result
        for _ in range(120):
            time.sleep(2)
            poll = req.get(f"{api_url}/{event_id}", timeout=30)
            if poll.status_code != 200:
                continue
            data = poll.json()
            if data.get("event") == "complete":
                output_data = data.get("output", {}).get("data", [])
                if output_data and len(output_data) > 1 and output_data[1]:
                    url = output_data[1].get("value", {})
                    if isinstance(url, dict):
                        url = url.get("url", "")
                    if isinstance(url, str) and url.startswith("http"):
                        dl = req.get(url, timeout=120)
                        if dl.status_code == 200 and len(dl.content) > 1000:
                            Path(output_path).write_bytes(dl.content)
                            print(f"  HF Space video saved ({len(dl.content)} bytes)")
                            return True
                print(f"  HF Space done but no video URL in output: {json.dumps(data)[:300]}")
                return False
            elif data.get("event") == "error":
                err = data.get("output", {}).get("text", str(data))
                print(f"  HF Space error: {err[:200]}")
                return False

        print("  HF Space timed out")
        return False
    except Exception as e:
        print(f"  HF Space exception: {e}")
        return False


def _seedance_generate(prompt: str, output_path: str | Path, duration: int = 5) -> bool:
    """Seedance API — needs SEEDANCE_API_KEY in env, free daily credits."""
    api_key = os.getenv("SEEDANCE_API_KEY", "")
    if not api_key:
        return False

    print(f"  Submitting to Seedance: {prompt[:80]}...")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "seedance-2.0-fast",
        "prompt": prompt,
        "duration": duration,
        "aspect_ratio": "9:16",
    }

    try:
        resp = req.post("https://seedanceapi.org/v2/generate", headers=headers, json=payload, timeout=30)
        if resp.status_code not in (200, 201):
            print(f"  Seedance error {resp.status_code}: {resp.text[:200]}")
            return False
        data = resp.json()
        task_id = data.get("task_id") or data.get("id")
        if not task_id:
            return False

        for _ in range(18):
            time.sleep(10)
            s = req.get(f"https://seedanceapi.org/v2/status?task_id={task_id}", headers=headers, timeout=30)
            if s.status_code != 200:
                continue
            sd = s.json()
            status = (sd.get("status") or "").upper()
            if status == "SUCCESS":
                video_url = sd.get("video_url") or sd.get("output", {}).get("video_url", "")
                if video_url:
                    dl = req.get(video_url, timeout=120)
                    if dl.status_code == 200 and len(dl.content) > 1000:
                        Path(output_path).write_bytes(dl.content)
                        print(f"  Seedance video saved ({len(dl.content)} bytes)")
                        return True
                return False
            elif status == "FAILED":
                print(f"  Seedance failed: {sd.get('error', 'unknown')}")
                return False
        return False
    except Exception as e:
        print(f"  Seedance exception: {e}")
        return False


def generate_video(prompt: str, output_path: str | Path, duration: int = 5) -> bool:
    """Try multiple free video sources. Returns True if video was saved."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists():
        return True

    attempts = [
        ("Hugging Face Space (experimental)", lambda: _hf_space_generate(prompt, output_path, duration)),
        ("Seedance API (needs key)",         lambda: _seedance_generate(prompt, output_path, duration)),
    ]

    for label, fn in attempts:
        print(f"  Trying {label}...")
        if fn():
            return True
        print(f"  {label} failed")

    return False
