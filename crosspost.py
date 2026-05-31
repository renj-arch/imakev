"""Cross-platform video posting (optional, for extra reach)."""

from pathlib import Path
import config


def post_to_tiktok(video_path: str, description: str):
    """Open TikTok upload page in browser (manual upload required)."""
    import subprocess, webbrowser
    webbrowser.open("https://www.tiktok.com/upload/")
    print("  TikTok upload page opened. Drag the video in:")
    print(f"    {video_path}")
    print(f"    Caption: {description[:100]}")


def post_to_instagram(video_path: str, description: str):
    """Open Instagram in browser (manual upload required)."""
    import webbrowser
    webbrowser.open("https://www.instagram.com/")
    print("  Instagram opened. Upload the reel manually:")
    print(f"    {video_path}")
    print(f"    Caption: {description[:100]}")


def post_all(video_path: str, description: str):
    """Open all platforms for manual upload."""
    print("\nCross-platform posting (open tabs for upload):")
    post_to_tiktok(video_path, description)
    post_to_instagram(video_path, description)


if __name__ == "__main__":
    mp4s = sorted(Path("output").glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if mp4s:
        post_all(str(mp4s[0]), "Cinematic Short Film #shorts")
