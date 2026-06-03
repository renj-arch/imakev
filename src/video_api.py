"""AI Video generation via Seedance API (free daily credits, needs key)."""

import os, time
import requests as req
from pathlib import Path


def generate_video(prompt: str, output_path: str | Path, duration: int = 5) -> bool:
    """Generate video via Seedance API. Needs SEEDANCE_API_KEY env var."""
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
            print(f"  Seedance error {resp.status_code}")
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
