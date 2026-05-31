"""Fact-based Shorts video generator - Pollinations.ai + TTS + baked-in Pillow text."""

import sys, subprocess, time, io, random
from pathlib import Path
from PIL import Image, ImageEnhance, ImageDraw, ImageFont
import numpy as np
import requests as req
from moviepy import (
    VideoClip, AudioFileClip, ImageClip,
    concatenate_videoclips, CompositeAudioClip,
)
import config

FONT_PATH = config.get_font()
W, H = config.VIDEO_WIDTH, config.VIDEO_HEIGHT

CURRENT_FACTS = []
CURRENT_NICHE = ""


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
    """Bake text onto image with Pillow (fast, no per-frame rendering)."""
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
    draw = ImageDraw.Draw(img)
    # Dark overlay at bottom
    overlay = Image.new("RGBA", (W, int(H * 0.3)), (0, 0, 0, 160))
    img.paste(overlay, (0, H - int(H * 0.3)), overlay)
    draw_text(img, title.upper(), 44, H - 220, center=True)
    draw_text(img, "⬇  SWIPE FOR FACTS  ⬇", 28, H - 120, color=(255, 200, 0), center=True)
    return img


def make_fact_card(img: Image.Image, num: int, fact: str) -> Image.Image:
    img = img.copy()
    # Dark gradient overlay at bottom
    overlay = Image.new("RGBA", (W, int(H * 0.35)), (0, 0, 0, 180))
    img.paste(overlay, (0, H - int(H * 0.35)), overlay)
    draw_text(img, f"#{num}", 72, H - 420, color=(255, 204, 0))
    draw_text(img, fact.upper(), 36, H - 320)
    return img


def make_end_card(img: Image.Image) -> Image.Image:
    img = img.copy()
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 120))
    img.paste(overlay, (0, 0), overlay)
    draw_text(img, "SUBSCRIBE", 60, H // 2 - 60, center=True, color=(255, 204, 0))
    draw_text(img, "FOR MORE AMAZING FACTS", 36, H // 2 + 20, center=True)
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
    global CURRENT_FACTS, CURRENT_NICHE

    print("=" * 50)
    print("  FACT VIDEO GENERATOR")
    print("=" * 50)

    from src.facts import generate_fact_script
    fact_data = generate_fact_script()
    CURRENT_FACTS = fact_data["facts"]
    CURRENT_NICHE = fact_data["niche"]

    TITLE = fact_data["title"]
    FACTS = fact_data["facts"]
    PROMPTS = fact_data["image_prompts"][:len(FACTS)]
    HOOK = fact_data["hook"]

    temp_dir = config.TEMP_DIR / "fact_video"
    temp_dir.mkdir(exist_ok=True)

    # TTS - natural narration: hook + each fact as a sentence
    print("\n[1/4] Voiceover...")
    tts_script = fact_data.get("tts_script", f"{HOOK} {' '.join(FACTS)}")
    tts_path = temp_dir / "narration.mp3"
    subprocess.run(
        [sys.executable, "-m", "edge_tts", "--text", tts_script, "--voice", "en-US-GuyNeural", "--write-media", str(tts_path)],
        capture_output=True, text=True, timeout=120, check=True,
    )
    audio = AudioFileClip(str(tts_path))
    total_dur = audio.duration
    audio.close()
    print(f"  {total_dur:.1f}s | {len(FACTS)} facts")

    # Generate images
    print(f"\n[2/4] Generating {len(PROMPTS)} images (if not cached)...")
    images = {}
    for i, (fact, prompt) in enumerate(zip(FACTS, PROMPTS)):
        cached = temp_dir / f"fact_{i}.png"
        if cached.exists() and cached.stat().st_size > 50000:
            img = Image.open(cached)
        else:
            print(f"  Image {i+1}/{len(PROMPTS)}...", end=" ", flush=True)
            img = gen_img(prompt)
            if img:
                img = upscale(img)
                img.save(cached)
                print("OK")
            else:
                print("fallback")
                arr = np.zeros((H, W, 3), dtype=np.uint8)
                for y in range(H):
                    arr[y, :] = [int(20 + 40*(y/H)), int(10 + 20*(1-y/H)), int(40 + 60*(y/H))]
                img = Image.fromarray(arr)
        images[i] = img

    # Bake text onto images with Pillow
    print("\n[3/4] Baking text onto frames...")
    dur_per_fact = total_dur / len(FACTS) if FACTS else total_dur

    # Title card
    title_img = make_title_card(images[0], TITLE)
    clips = [motion_clip(title_img, 1.5)]

    # Fact cards
    for i, fact in enumerate(FACTS):
        img = images.get(i, images[0])
        card = make_fact_card(img, i + 1, fact)
        clips.append(motion_clip(card, dur_per_fact))

    # End card
    end_img = images.get(len(FACTS) - 1, images[0])
    end_card = make_end_card(end_img)
    clips.append(motion_clip(end_card, 2.0))

    bg = concatenate_videoclips(clips, method="compose")
    final = bg

    audio_clip = AudioFileClip(str(tts_path))
    music_paths = list(config.MUSIC_DIR.glob("*.mp3"))
    if music_paths:
        music = AudioFileClip(str(random.choice(music_paths))).with_duration(total_dur + 1.5).with_volume_scaled(0.08)
        final = final.with_audio(CompositeAudioClip([audio_clip, music]))
    else:
        final = final.with_audio(audio_clip)

    # Render
    print("\n[4/4] Rendering...")
    safe_title = TITLE.lower().replace(" ", "_").replace("?", "").replace("!", "").replace("'", "").replace(".", "").replace(",", "").replace(":", "")[:50]
    out = config.OUTPUT_DIR / f"facts_{safe_title}.mp4"
    out.unlink(missing_ok=True)
    print(f"  {total_dur + 1.5:.1f}s | {W}x{H}")
    t0 = time.time()
    final.write_videofile(str(out), fps=config.VIDEO_FPS, codec="libx264", audio_codec="aac", threads=4, preset="ultrafast", ffmpeg_params=["-movflags", "+faststart"], logger=None)
    final.close()
    t1 = time.time()
    print(f"\n  DONE in {t1-t0:.0f}s: {out}")
    print(f"  Size: {out.stat().st_size} bytes")

    return out, fact_data


if __name__ == "__main__":
    main()
