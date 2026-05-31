import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from moviepy import (
    VideoClip,
    ImageClip,
    AudioFileClip,
    TextClip,
    CompositeVideoClip,
    concatenate_videoclips,
    ColorClip,
)
from moviepy.audio.fx import AudioLoop
import config


def _wrap_text(text: str, max_chars: int = 35) -> list[str]:
    words = text.split()
    lines, current_line = [], []
    for word in words:
        if len(" ".join(current_line + [word])) <= max_chars:
            current_line.append(word)
        else:
            lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
    return lines


def _get_font(size: int = 60) -> str:
    font_paths = list(config.FONTS_DIR.glob("*.ttf")) + list(config.FONTS_DIR.glob("*.otf"))
    if font_paths:
        return str(font_paths[0])
    windows_fonts = [
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\tahoma.ttf",
        r"C:\Windows\Fonts\calibri.ttf",
    ]
    for path in windows_fonts:
        if Path(path).exists():
            return path
    return "Arial"


def _create_caption_clip(text: str, duration: float, start_time: float) -> VideoClip:
    lines = _wrap_text(text, max_chars=32)
    display_text = "\n".join(lines)

    txt_clip = TextClip(
        text=display_text,
        font=_get_font(64),
        color="white",
        stroke_color="black",
        stroke_width=3,
        font_size=64,
        method="label",
    )

    txt_clip = txt_clip.with_position(("center", config.VIDEO_HEIGHT - 300))
    txt_clip = txt_clip.with_start(start_time).with_duration(duration)
    return txt_clip


def _get_random_background(query: str = "") -> VideoClip | None:
    bg_videos = list(config.BACKGROUNDS_DIR.glob("*.mp4")) + list(config.BACKGROUNDS_DIR.glob("*.mov"))
    bg_images = list(config.BACKGROUNDS_DIR.glob("*.jpg")) + list(config.BACKGROUNDS_DIR.glob("*.png"))

    if bg_videos:
        path = str(random.choice(bg_videos))
        clip = VideoClip.from_videofile(path)
        return clip

    if not bg_videos and query:
        from src.stock import download_stock_video
        print(f"  Downloading stock footage: {query}")
        out = config.TEMP_DIR / "stock_bg.mp4"
        result = download_stock_video(query, out)
        if result:
            clip = VideoClip.from_videofile(str(result))
            return clip

    if bg_images:
        path = str(random.choice(bg_images))
        img = ImageClip(path)
        img = img.resized(height=config.VIDEO_HEIGHT)
        w, h = img.size
        if w > config.VIDEO_WIDTH:
            x_center = (w - config.VIDEO_WIDTH) / 2
            img = img.cropped(x1=x_center, y1=0, x2=x_center + config.VIDEO_WIDTH, y2=h)
        return img

    return None


def _make_frame(t):
    arr = np.zeros((config.VIDEO_HEIGHT, config.VIDEO_WIDTH, 3), dtype=np.uint8)
    for y in range(config.VIDEO_HEIGHT):
        ratio = y / config.VIDEO_HEIGHT
        phase = t * 0.15
        r = int(abs(np.sin(ratio * 2 + phase)) * 40 + 20)
        g = int(abs(np.cos(ratio * 1.5 + phase * 0.7)) * 30 + 15)
        b = int(abs(np.sin(ratio * 1.8 + phase * 1.3)) * 35 + 25)
        arr[y, :, 0] = np.clip(r + np.random.randint(-2, 3, config.VIDEO_WIDTH), 0, 255).astype(np.uint8)
        arr[y, :, 1] = np.clip(g + np.random.randint(-2, 3, config.VIDEO_WIDTH), 0, 255).astype(np.uint8)
        arr[y, :, 2] = np.clip(b + np.random.randint(-2, 3, config.VIDEO_WIDTH), 0, 255).astype(np.uint8)
    return arr

def _create_gradient_background(duration: float) -> VideoClip:
    clip = VideoClip(_make_frame, duration=duration)
    return clip


def build_shorts_video(
    audio_path: Path,
    script: str,
    output_path: Path,
    caption_style: str = "bottom",
    search_query: str = "",
) -> Path:
    audio = AudioFileClip(str(audio_path))
    duration = audio.duration

    sentences = [s.strip() + "." for s in script.replace("!", ".").replace("?", ".").split(".") if s.strip()]
    if not sentences:
        sentences = [script]

    seg_duration = duration / max(len(sentences), 1)

    bg = _get_random_background(query=search_query)
    if bg is None:
        print("  No background footage found. Generating animated background.")
        bg = _create_gradient_background(duration)
    else:
        print("  Using stock footage background.")
    bg = bg.with_duration(duration)
    if hasattr(bg, "resized"):
        bg = bg.resized(height=config.VIDEO_HEIGHT)
        w, h = bg.size
        if w < config.VIDEO_WIDTH:
            bg = bg.resized(width=config.VIDEO_WIDTH)
            w, h = bg.size
        if w > config.VIDEO_WIDTH:
            x_center = (w - config.VIDEO_WIDTH) / 2
            bg = bg.cropped(x1=x_center, y1=0, x2=x_center + config.VIDEO_WIDTH, y2=h)
        if h > config.VIDEO_HEIGHT:
            y_center = (h - config.VIDEO_HEIGHT) / 2
            bg = bg.cropped(x1=0, y1=y_center, x2=config.VIDEO_WIDTH, y2=y_center + config.VIDEO_HEIGHT)

    clips = [bg]
    current_time = 0.0
    for i, sentence in enumerate(sentences):
        s_duration = seg_duration
        if i == len(sentences) - 1:
            s_duration = duration - current_time
        if s_duration <= 0:
            break
        cap = _create_caption_clip(sentence, s_duration, current_time)
        clips.append(cap)
        current_time += s_duration

    final = CompositeVideoClip(clips, size=config.SHORTS_SIZE)
    final = final.with_audio(audio)
    final = final.with_duration(duration)

    final.write_videofile(
        str(output_path),
        fps=config.VIDEO_FPS,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="medium",
        logger=None,
    )

    audio.close()
    final.close()

    return output_path
