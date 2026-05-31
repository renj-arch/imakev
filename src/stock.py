import requests
from pathlib import Path
import config


PIXABAY_API = "https://pixabay.com/api/videos/"
PEXELS_API = "https://api.pexels.com/videos/search"


def _get_pixabay_key() -> str:
    key_file = config.ROOT_DIR / ".pixabay_key"
    if key_file.exists():
        return key_file.read_text().strip()
    return ""


def _download_from_pixabay(query: str, output_path: Path) -> Path | None:
    api_key = _get_pixabay_key()
    if not api_key:
        return None

    try:
        resp = requests.get(PIXABAY_API, params={"key": api_key, "q": query, "per_page": 3, "orientation": "vertical", "safesearch": "true"}, timeout=15)
        data = resp.json()
        for hit in data.get("hits", []):
            for quality in ["tiny", "small", "medium"]:
                vid = hit.get("videos", {}).get(quality)
                if vid and vid.get("url"):
                    dl = requests.get(vid["url"], timeout=60)
                    if len(dl.content) > 10000:
                        output_path.write_bytes(dl.content)
                        return output_path
    except Exception:
        pass
    return None


def download_stock_video(query: str, output_path: Path) -> Path | None:
    if result := _download_from_pixabay(query, output_path):
        return result
    return None


def try_download_from_url(url: str, output_path: Path) -> Path | None:
    try:
        resp = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
        if len(resp.content) > 10000:
            output_path.write_bytes(resp.content)
            return output_path
    except Exception:
        pass
    return None
