"""Helper to download free stock videos into assets/backgrounds/

Get a FREE Pixabay API key: https://pixabay.com/api/docs/ (click "Get API key")
Then run: python setup_stock.py YOUR_PIXABAY_KEY

Or manually download vertical MP4s into assets/backgrounds/
Recommended free sources: pixabay.com, pexels.com, mixkit.co
"""

import sys, requests
from pathlib import Path
import config


PIXABAY_API = "https://pixabay.com/api/videos/"

NICHES = {
    "cat": ["cat", "kitten", "tabby+cat", "cute+cat", "ginger+cat"],
    "dog": ["puppy", "dog", "cute+dog"],
    "nature": ["forest", "sunset", "ocean", "waterfall", "nature"],
    "cute": ["kitten", "puppy", "baby+animal", "cute+pet"],
    "city": ["city+skyline", "street", "night+city"],
    "food": ["cooking", "food", "dessert", "coffee"],
}


def download_batch(api_key: str, niche: str = "cat", count: int = 3):
    terms = NICHES.get(niche, [niche])
    downloaded = 0
    for term in terms:
        if downloaded >= count:
            break
        print(f"Searching: {term}...")
        try:
            resp = requests.get(PIXABAY_API, params={"key": api_key, "q": term, "per_page": 5, "orientation": "vertical", "safesearch": "true"}, timeout=15)
            data = resp.json()
            for hit in data.get("hits", []):
                for quality in ["tiny", "small", "medium"]:
                    vid = hit.get("videos", {}).get(quality)
                    if vid and vid.get("url"):
                        url = vid["url"]
                        ext = url.rsplit(".", 1)[-1].split("?")[0]
                        out = config.BACKGROUNDS_DIR / f"{niche}_{hit['id']}_{quality}.{ext}"
                        if not out.exists():
                            print(f"  Downloading {quality}...")
                            dl = requests.get(url, timeout=60)
                            out.write_bytes(dl.content)
                            print(f"  Saved: {out.name} ({len(dl.content)//1024}KB)")
                            downloaded += 1
                        else:
                            downloaded += 1
                        break
                if downloaded >= count:
                    break
        except Exception as e:
            print(f"  Error: {e}")
    print(f"\nDownloaded {downloaded} videos to {config.BACKGROUNDS_DIR}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python setup_stock.py YOUR_PIXABAY_API_KEY [niche]")
        print("Example: python setup_stock.py 12345678-abc123def cat")
        print("\nGet a free API key at: https://pixabay.com/api/docs/")
        return
    api_key = sys.argv[1]
    niche = sys.argv[2] if len(sys.argv) > 2 else "cat"
    download_batch(api_key, niche)


if __name__ == "__main__":
    main()
