"""AI Video generation via Seedance API (free daily credits, no credit card)."""

import os, time, json
import requests as req
from pathlib import Path

BASE_URL = "https://seedanceapi.org/v2"
POLL_INTERVAL = 10
MAX_POLL_TIME = 180


def generate_video(prompt: str, output_path: str | Path, duration: int = 5) -> bool:
    api_key = os.getenv("SEEDANCE_API_KEY", "")
    if not api_key:
        print("  SEEDANCE_API_KEY not set — skipping Seedance video")
        return False

    print(f"  Submitting to Seedance API: {prompt[:80]}...")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "seedance-2.0-fast",
        "prompt": prompt,
        "duration": duration,
        "aspect_ratio": "9:16",
    }

    try:
        resp = req.post(f"{BASE_URL}/generate", headers=headers, json=payload, timeout=30)
        if resp.status_code not in (200, 201):
            print(f"  Seedance API error {resp.status_code}: {resp.text[:200]}")
            return False

        data = resp.json()
        task_id = data.get("task_id") or data.get("id")
        if not task_id:
            print(f"  No task_id in response: {data}")
            return False

        print(f"  Task submitted: {task_id}")

        for _ in range(MAX_POLL_TIME // POLL_INTERVAL):
            time.sleep(POLL_INTERVAL)
            status_resp = req.get(f"{BASE_URL}/status?task_id={task_id}", headers=headers, timeout=30)
            if status_resp.status_code != 200:
                continue
            status_data = status_resp.json()
            status = (status_data.get("status") or "").upper()

            if status == "SUCCESS":
                video_url = status_data.get("video_url") or status_data.get("output", {}).get("video_url", "")
                if not video_url:
                    print(f"  No video URL in success response")
                    return False
                print(f"  Downloading video...")
                dl = req.get(video_url, timeout=120)
                if dl.status_code == 200 and len(dl.content) > 1000:
                    Path(output_path).write_bytes(dl.content)
                    print(f"  Video saved: {output_path}")
                    return True
                else:
                    print(f"  Download failed: {dl.status_code} {len(dl.content)} bytes")
                    return False

            elif status == "FAILED":
                err = status_data.get("error", "unknown")
                print(f"  Generation failed: {err}")
                return False

        print("  Timed out waiting for video")
        return False

    except Exception as e:
        print(f"  Seedance API exception: {e}")
        return False
