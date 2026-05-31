"""History Minute Shorts video generator — Pollinations.ai + TTS + baked-in Pillow text."""

import sys, subprocess, time, io, random
from pathlib import Path
from PIL import Image, ImageEnhance, ImageDraw, ImageFont
import numpy as np
import requests as req
from moviepy import (
    VideoClip, AudioFileClip, ImageClip,
    concatenate_videoclips, CompositeAudioClip, concatenate_audioclips,
)
import config

FONT_PATH = config.get_font()
W, H = config.VIDEO_WIDTH, config.VIDEO_HEIGHT


def gen_img(prompt: str) -> Image.Image | None:
    url = f"https://image.pollinations.ai/prompt/{req.utils.quote(prompt)}?width={config.VIDEO_WIDTH}&height={config.VIDEO_HEIGHT}&nofeed=true&seed={random.randint(0,999999)}&model=flux"
    try:
        r = req.get(url, timeout=120)
        if r.status_code == 200 and len(r.content) > 500:
            return Image.open(io.BytesIO(r.content)).convert("RGB")
    except:
        pass
    return None


def upscale(img: Image.Image) -> Image.Image:
    img = img.resize((W, H), Image.LANCZOS)
    img = ImageEnhance.Contrast(img).enhance(1.2)
    img = ImageEnhance.Color(img).enhance(1.2)
    return img


def draw_text(img: Image.Image, text: str, font_size: int, y: int, color=(255, 255, 255), stroke_color=(0, 0, 0), stroke_width: int = 2, center: bool = False, x: int = 30):
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
    except:
        font = ImageFont.load_default()
    lines = []
    for line in text.split("\n"):
        words = line.split()
        current = ""
        for w in words:
            test = f"{current} {w}".strip()
            bb = draw.textbbox((0, 0), test, font=font)
            if bb[2] - bb[0] > W - 60:
                lines.append(current)
                current = w
            else:
                current = test
        lines.append(current)

    for i, line in enumerate(lines):
        ly = y + i * (font_size + 8)
        if center:
            bb = draw.textbbox((0, 0), line, font=font)
            lx = (W - (bb[2] - bb[0])) // 2
        else:
            lx = x
        if stroke_width > 0:
            for dx in range(-stroke_width, stroke_width + 1):
                for dy in range(-stroke_width, stroke_width + 1):
                    if dx != 0 or dy != 0:
                        draw.text((lx + dx, ly + dy), line, font=font, fill=stroke_color)
        draw.text((lx, ly), line, font=font, fill=color)
    return img


def make_title_card(img: Image.Image, title: str) -> Image.Image:
    img = img.copy()
    overlay = Image.new("RGBA", (W, int(H * 0.3)), (0, 0, 0, 160))
    img.paste(overlay, (0, H - int(H * 0.3)), overlay)
    draw_text(img, title.upper(), 42, H - 220, center=True)
    draw_text(img, "⬇  HISTORY MINUTE  ⬇", 26, H - 120, color=(255, 200, 0), center=True)
    return img


def make_script_card(img: Image.Image, script: str) -> Image.Image:
    img = img.copy()
    overlay = Image.new("RGBA", (W, int(H * 0.4)), (0, 0, 0, 180))
    img.paste(overlay, (0, H - int(H * 0.4)), overlay)
    draw_text(img, script.upper(), 32, H - 360)
    return img


def make_end_card(img: Image.Image) -> Image.Image:
    img = img.copy()
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 120))
    img.paste(overlay, (0, 0), overlay)
    draw_text(img, "SUBSCRIBE", 60, H // 2 - 60, center=True, color=(255, 204, 0))
    draw_text(img, "FOR MORE HISTORY", 36, H // 2 + 20, center=True)
    return img


def motion_clip(img: Image.Image, dur: float) -> VideoClip:
    w, h = img.size
    def f(t):
        p = t / dur if dur > 0 else 1
        scale = 1.0 + p * 0.05
        cw, ch = int(w / scale), int(h / scale)
        ox, oy = (w - cw) // 2, (h - ch) // 2
        return np.array(img.crop((ox, oy, ox + cw, oy + ch)).resize((w, h), Image.LANCZOS))
    return VideoClip(f, duration=dur)


def main():
    print("=" * 50)
    print("  HISTORY MINUTE GENERATOR")
    print("=" * 50)

    from src.history_minute import generate_history_script
    data = generate_history_script()

    TITLE = data["title"]
    SCRIPT = data["script"]
    PROMPT = data["image_prompt"]

    temp_dir = config.TEMP_DIR / "history_video"
    temp_dir.mkdir(exist_ok=True)

    # TTS
    print("\n[1/4] Voiceover...")
    tts_script = data.get("tts_script", SCRIPT)
    tts_path = temp_dir / "narration.mp3"
    subprocess.run(
        [sys.executable, "-m", "edge_tts", "--text", tts_script, "--voice", "en-US-GuyNeural", "--write-media", str(tts_path)],
        capture_output=True, text=True, timeout=120, check=True,
    )
    audio = AudioFileClip(str(tts_path))
    total_dur = audio.duration
    audio.close()
    print(f"  {total_dur:.1f}s")

    # Generate image
    print(f"\n[2/4] Generating image...")
    cached = temp_dir / "history_img.png"
    if cached.exists() and cached.stat().st_size > 50000:
        img = Image.open(cached)
        print("  Cached")
    else:
        print(f"  Pollinations...", end=" ", flush=True)
        img = gen_img(PROMPT)
        if img:
            img = upscale(img)
            img.save(cached)
            print("OK")
        else:
            print("fallback")
            arr = np.zeros((H, W, 3), dtype=np.uint8)
            for y in range(H):
                arr[y, :] = [int(40 + 30*(y/H)), int(20 + 15*(1-y/H)), int(50 + 40*(y/H))]
            img = Image.fromarray(arr)

    # Bake text
    print("\n[3/4] Baking text onto frames...")

    title_card = make_title_card(img, TITLE)
    script_card = make_script_card(img, SCRIPT)
    end_card = make_end_card(img)

    clips = [
        motion_clip(title_card, 1.5),
        motion_clip(script_card, total_dur),
        motion_clip(end_card, 2.0),
    ]

    bg = concatenate_videoclips(clips, method="compose")
    final = bg

    video_dur = total_dur + 1.5 + 2.0
    audio_clip = AudioFileClip(str(tts_path))
    if video_dur > audio_clip.duration:
        silence = AudioFileClip(str(tts_path)).with_duration(video_dur - audio_clip.duration).with_volume_scaled(0)
        audio_clip = concatenate_audioclips([audio_clip, silence])
    music_paths = list(config.MUSIC_DIR.glob("*.mp3"))
    if music_paths:
        music = AudioFileClip(str(random.choice(music_paths))).with_duration(video_dur).with_volume_scaled(0.08)
        final = final.with_audio(CompositeAudioClip([audio_clip, music]))
    else:
        final = final.with_audio(audio_clip)

    # Render
    print("\n[4/4] Rendering...")
    safe_title = TITLE.lower().replace(" ", "_").replace("?", "").replace("!", "").replace("'", "").replace(".", "").replace(",", "").replace(":", "")[:50]
    out = config.OUTPUT_DIR / f"history_{safe_title}.mp4"
    out.unlink(missing_ok=True)
    print(f"  {video_dur:.1f}s | {W}x{H}")
    t0 = time.time()
    final.write_videofile(str(out), fps=config.VIDEO_FPS, codec="libx264", audio_codec="aac", threads=4, preset="ultrafast", ffmpeg_params=["-movflags", "+faststart"], logger=None)
    final.close()
    t1 = time.time()
    print(f"\n  DONE in {t1-t0:.0f}s: {out}")
    print(f"  Size: {out.stat().st_size} bytes")

    return out, data


if __name__ == "__main__":
    main()
