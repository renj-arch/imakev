"""How It Works — Zack D. Films style: 1 topic, 45-60s, deep voice, cinematic."""

import sys, subprocess, time, io, random
from pathlib import Path
from PIL import Image, ImageEnhance, ImageDraw, ImageFont
import numpy as np
import requests as req
from moviepy import VideoClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, concatenate_audioclips, CompositeVideoClip
import config
from src.how_it_works import generate_howitworks_script
from src.engagement import hook_overlays, fast_motion, comment_prompt_overlay, subscribe_end_card, branding_overlays, get_audio_duration, generate_voiceover_ssml

FONT_PATH = config.get_font()
W, H = config.VIDEO_WIDTH, config.VIDEO_HEIGHT


def gen_img(prompt):
    url = f"https://image.pollinations.ai/prompt/{req.utils.quote(prompt)}?width={config.VIDEO_WIDTH}&height={config.VIDEO_HEIGHT}&nofeed=true&seed={random.randint(0,999999)}&model=flux"
    try:
        r = req.get(url, timeout=120)
        if r.status_code == 200 and len(r.content) > 500:
            return Image.open(io.BytesIO(r.content)).convert("RGB")
    except:
        pass
    return None


def upscale(img):
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


def make_intro_card(img, topic):
    img = img.copy()
    overlay = Image.new("RGBA", (W, H), (0,0,0,180))
    img.paste(overlay, (0,0), overlay)
    draw_text(img, topic.upper(), 48, H//2 - 80, center=True, color=(255,200,0))
    return img


def make_explanation_card(img, text_segment):
    img = img.copy()
    overlay = Image.new("RGBA", (W, int(H*0.45)), (0,0,0,180))
    img.paste(overlay, (0, H-int(H*0.45)), overlay)
    draw_text(img, text_segment, 28, H-480)
    return img


def make_end_card(img):
    img = img.copy()
    overlay = Image.new("RGBA", (W, H), (0,0,0,120))
    img.paste(overlay, (0,0), overlay)
    draw_text(img, "SUBSCRIBE 🔔", 56, H//2 - 60, center=True, color=(255,200,0))
    draw_text(img, "FOR MORE", 36, H//2 + 20, center=True)
    return img


motion_clip = fast_motion


def main():
    print("="*50)
    print("  HOW IT WORKS — ZACK D. STYLE")
    print("="*50)

    data = generate_howitworks_script()
    TITLE = data["title"]
    TOPIC = data["topics"][0]
    EXPLANATION = data["explanations"][0]

    temp_dir = config.TEMP_DIR / "how_it_works"
    temp_dir.mkdir(exist_ok=True)

    # Generate 3 varied visual prompts for the same topic
    visual_prompts = [
        f"cinematic close-up detailed shot: {TOPIC}, cross-section view, dramatic lighting, photorealistic, 9:16 vertical, dark background",
        f"macro extreme close-up: {TOPIC}, inner mechanism visible, glowing highlights, industrial design, detailed texture, 9:16 vertical, cinematic",
        f"dramatic product shot: {TOPIC}, isolated on dark background, studio lighting, reflection, highly detailed texture, 9:16 vertical, professional",
    ]
    data["image_prompts"] = visual_prompts

    print("\n[1/4] Voiceover...")
    tts_script = data["tts_script"]
    tts_path = temp_dir / "narration.mp3"
    generate_voiceover_ssml(tts_script, "en-US-ChristopherNeural", str(tts_path))
    total_dur = get_audio_duration(str(tts_path))
    print(f"  {total_dur:.1f}s | ~{len(tts_script.split())} words")

    print(f"\n[2/4] Generating {len(visual_prompts)} images...")
    images = []
    for i, prompt in enumerate(visual_prompts):
        cached = temp_dir / f"how_{i}.png"
        if cached.exists() and cached.stat().st_size > 50000:
            img = Image.open(cached)
            print(f"  Image {i+1}/{len(visual_prompts)}... cached")
        else:
            print(f"  Image {i+1}/{len(visual_prompts)}...", end=" ", flush=True)
            img = gen_img(prompt)
            if img:
                img = upscale(img)
                img.save(cached)
                print("OK")
            else:
                print("fallback")
                arr = np.zeros((H, W, 3), dtype=np.uint8)
                for y in range(H):
                    arr[y,:] = [int(30+100*(y/H)), int(60+80*(1-y/H)), int(100+120*(y/H))]
                img = Image.fromarray(arr)
        images.append(img)

    print("\n[3/4] Baking text...")

    # Split explanation into segments for varied visuals
    sentences = EXPLANATION.replace(". ", ".|||").split("|||")
    sentences = [s.strip() for s in sentences if s.strip()]
    num_segments = min(len(sentences), 3)

    clips = []

    # Intro — show first image with title
    intro_img = make_intro_card(images[0], TOPIC)
    clips.append(motion_clip(intro_img, 1.2))

    # Explanation segments — cycle through images
    for i in range(num_segments):
        img_idx = min(i, len(images) - 1)
        seg = sentences[i] + "." if not sentences[i].endswith(".") else sentences[i]
        card = make_explanation_card(images[img_idx], seg)
        dur = max(total_dur / max(num_segments, 1), 2.0)
        clips.append(fast_motion(card, dur, shake=False))

    # End card
    end_img = images[-1]
    clips.append(subscribe_end_card(end_img, 1.5))

    overlays = hook_overlays(2.0)
    overlays += comment_prompt_overlay(start_time=max(total_dur * 0.5, 1.0), duration=2.5)

    bg = concatenate_videoclips(clips, method="compose")
    overlays += branding_overlays(bg.duration)
    final = CompositeVideoClip([bg] + overlays, size=config.SHORTS_SIZE)
    audio_clip = AudioFileClip(str(tts_path))
    video_dur = bg.duration
    if video_dur > audio_clip.duration:
        silence = AudioFileClip(str(tts_path)).with_duration(video_dur - audio_clip.duration).with_volume_scaled(0)
        audio_clip = concatenate_audioclips([audio_clip, silence])
    music_paths = list(config.MUSIC_DIR.glob("*.mp3"))
    if music_paths:
        music = AudioFileClip(str(random.choice(music_paths))).with_duration(video_dur).with_volume_scaled(0.06)
        final = final.with_audio(CompositeAudioClip([audio_clip, music]))
    else:
        final = final.with_audio(audio_clip)

    print("\n[4/4] Rendering...")
    safe_title = TITLE.lower().replace(" ", "_").replace("?", "").replace("!", "").replace("'", "").replace(".","").replace(",","").replace(":","")[:50]
    out = config.OUTPUT_DIR / f"how_{safe_title}.mp4"
    out.unlink(missing_ok=True)
    print(f"  {video_dur:.1f}s | {W}x{H}")
    t0 = time.time()
    final.write_videofile(str(out), fps=config.VIDEO_FPS, codec="libx264", audio_codec="aac", threads=4, preset="ultrafast", ffmpeg_params=["-movflags", "+faststart"], logger=None)
    final.close()
    t1 = time.time()
    print(f"\n  DONE in {t1-t0:.0f}s: {out}")
    return out, data


if __name__ == "__main__":
    main()