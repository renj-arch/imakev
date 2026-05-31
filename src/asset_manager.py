import requests
from pathlib import Path
import config


PEXELS_API = "https://api.pexels.com/videos/search"
PEXELS_KEY = ""  # Optional: set your free Pexels API key


def download_background_video(query: str = "nature", orientation: str = "portrait") -> Path | None:
    if not PEXELS_KEY:
        return None

    headers = {"Authorization": PEXELS_KEY}
    params = {"query": query, "per_page": 5, "orientation": orientation}

    try:
        resp = requests.get(PEXELS_API, headers=headers, params=params, timeout=15)
        data = resp.json()

        for video in data.get("videos", []):
            for file in video.get("video_files", []):
                if file.get("height", 0) >= 1920 or file.get("width", 0) >= 1080:
                    dl = requests.get(file["link"], timeout=30)
                    out = config.BACKGROUNDS_DIR / f"{query}_{video['id']}.mp4"
                    out.write_bytes(dl.content)
                    return out
    except Exception:
        pass
    return None


def ensure_default_assets():
    if not list(config.BACKGROUNDS_DIR.iterdir()):
        print("No background assets found. Add video/image files to:")
        print(f"  {config.BACKGROUNDS_DIR}")
        print("You can download free stock footage from pexels.com or pixabay.com")
