"""UPSC Concepts Shorts video — Pollinations.ai + TTS + baked-in Pillow text."""

import sys, subprocess, time, io, random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image, ImageEnhance, ImageDraw, ImageFont
import numpy as np
import requests as req
from moviepy import VideoClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, CompositeVideoClip
import config
from src.engagement import hook_overlays, fast_motion, comment_prompt_overlay, subscribe_end_card, branding_overlays
from src.upsc import generate_upsc_script

FONT_PATH = config.get_font()
W, H = config.VIDEO_WIDTH, config.VIDEO_HEIGHT


def gen_img(prompt: str) -> Image.Image | None:
    url = f"https://image.pollinations.ai/prompt/{req.utils.quote(prompt)}?width={config.VIDEO_WIDTH}&height={config.VIDEO_HEIGHT}&nofeed=true&seed={random.randint(0,999999)}&model=flux"
    try:
        r = req.get(url, timeout=45)
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


def draw_text(img, text, font_size, y, color=(255,255,255), stroke_color=(0,0,0), stroke_width=2, center=False, x=30):
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
            bb = draw.textbbox((0,0), test, font=font)
            if bb[2] - bb[0] > W - 60:
                lines.append(current)
                current = w
            else:
                current = test
        lines.append(current)
    for i, line in enumerate(lines):
        ly = y + i * (font_size + 8)
        if center:
            bb = draw.textbbox((0,0), line, font=font)
            lx = (W - (bb[2] - bb[0])) // 2
        else:
            lx = x
        if stroke_width > 0:
            for dx in range(-stroke_width, stroke_width+1):
                for dy in range(-stroke_width, stroke_width+1):
                    if dx != 0 or dy != 0:
                        draw.text((lx+dx, ly+dy), line, font=font, fill=stroke_color)
        draw.text((lx, ly), line, font=font, fill=color)
    return img


def make_title_card(img, text):
    img = img.copy()
    overlay = Image.new("RGBA", (W, int(H*0.3)), (0,0,0,160))
    img.paste(overlay, (0, H-int(H*0.3)), overlay)
    draw_text(img, text.upper(), 40, H-220, center=True)
    draw_text(img, "UPSC CONCEPT EXPLAINED", 26, H-120, center=True, color=(255,200,0))
    return img


def make_concept_card(img, topic, explanation):
    img = img.copy()
    overlay = Image.new("RGBA", (W, int(H*0.5)), (0,0,0,180))
    img.paste(overlay, (0, H-int(H*0.5)), overlay)
    draw_text(img, topic.upper(), 38, H-540, color=(255,200,0))
    draw_text(img, explanation, 26, H-450)
    return img


def make_end_card(img):
    img = img.copy()
    overlay = Image.new("RGBA", (W, H), (0,0,0,120))
    img.paste(overlay, (0,0), overlay)
    draw_text(img, "SUBSCRIBE", 60, H//2 - 60, center=True, color=(255,200,0))
    draw_text(img, "FOR MORE UPSC CONCEPTS", 32, H//2 + 20, center=True)
    return img


motion_clip = fast_motion


def main():
    print("="*50)
    print("  UPSC CONCEPTS GENERATOR")
    print("="*50)

    data = generate_upsc_script()
    TITLE = data["title"]
    TOPICS = data["topics"]
    EXPLANATIONS = data["explanations"]
    PROMPTS = data["image_prompts"]

    temp_dir = config.TEMP_DIR / "upsc"
    temp_dir.mkdir(exist_ok=True)

    print("\n[1/4] Voiceover...")
    tts_script = data["tts_script"]
    tts_path = temp_dir / "narration.mp3"
    subprocess.run([sys.executable, "-m", "edge_tts", "--text", tts_script, "--voice", "en-IN-PrabhatNeural", "--write-media", str(tts_path)], capture_output=True, text=True, timeout=120, check=True)
    audio = AudioFileClip(str(tts_path))
    total_dur = audio.duration
    audio.close()
    print(f"  {total_dur:.1f}s | {len(TOPICS)} concepts")

    print(f"\n[2/4] Generating {len(PROMPTS)} images (parallel)...")
    images = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        fut_to_i = {}
        for i, (t, prompt) in enumerate(zip(TOPICS, PROMPTS)):
            cached = temp_dir / f"upsc_{i}.png"
            if cached.exists() and cached.stat().st_size > 50000:
                images[i] = Image.open(cached)
                print(f"  Image {i+1}/{len(PROMPTS)}... cached")
            else:
                fut = pool.submit(gen_img, prompt)
                fut_to_i[fut] = i
        for fut in as_completed(fut_to_i):
            i = fut_to_i[fut]
            cached = temp_dir / f"upsc_{i}.png"
            img = fut.result()
            if img:
                img = upscale(img)
                img.save(cached)
                print(f"  Image {i+1}/{len(PROMPTS)}... OK")
            else:
                print(f"  Image {i+1}/{len(PROMPTS)}... fallback")
                arr = np.zeros((H, W, 3), dtype=np.uint8)
                for y in range(H):
                    arr[y,:] = [int(10+50*(y/H)), int(10+30*(1-y/H)), int(30+80*(y/H))]
                img = Image.fromarray(arr)
            images[i] = img

    print("\n[3/4] Baking text...")
    dur_per = total_dur / len(TOPICS)

    title_img = make_title_card(images[0], TITLE)
    clips = [motion_clip(title_img, 0.8)]

    for i, (t, e) in enumerate(zip(TOPICS, EXPLANATIONS)):
        img = images.get(i, images[0])
        card = make_concept_card(img, t, e)
        clips.append(fast_motion(card, dur_per, shake=i==len(TOPICS)-1))

    end_img = images.get(len(TOPICS)-1, images[0])
    clips.append(subscribe_end_card(end_img, 1.2))

    overlays = hook_overlays(1.8)
    overlays += comment_prompt_overlay(start_time=max(total_dur * 0.4, 0.5), duration=2.0)

    bg = concatenate_videoclips(clips, method="compose")
    overlays += branding_overlays(bg.duration)
    final = CompositeVideoClip([bg] + overlays, size=config.SHORTS_SIZE)
    audio_clip = AudioFileClip(str(tts_path))
    music_paths = list(config.MUSIC_DIR.glob("*.mp3"))
    if music_paths:
        music = AudioFileClip(str(random.choice(music_paths))).with_duration(total_dur + 0.8).with_volume_scaled(0.08)
        final = final.with_audio(CompositeAudioClip([audio_clip, music]))
    else:
        final = final.with_audio(audio_clip)

    print("\n[4/4] Rendering...")
    safe_title = TITLE.lower().replace(" ", "_").replace("?", "").replace("!", "").replace("'", "").replace(".","").replace(",","").replace(":","")[:50]
    out = config.OUTPUT_DIR / f"upsc_{safe_title}.mp4"
    out.unlink(missing_ok=True)
    print(f"  {total_dur + 0.8:.1f}s | {W}x{H}")
    t0 = time.time()
    final.write_videofile(str(out), fps=config.VIDEO_FPS, codec="libx264", audio_codec="aac", threads=4, preset="ultrafast", ffmpeg_params=["-movflags", "+faststart"], logger=None)
    final.close()
    t1 = time.time()
    print(f"\n  DONE in {t1-t0:.0f}s: {out}")
    return out, data


if __name__ == "__main__":
    main()
