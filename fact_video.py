"""Fact-based Shorts video — image + cinematic camera + professional overlays."""

import sys, subprocess, time, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from moviepy import (
    VideoClip, AudioFileClip, ImageClip, TextClip,
    concatenate_videoclips, CompositeAudioClip, concatenate_audioclips,
    CompositeVideoClip,
)
import config
from src.engagement import hook_overlays, comment_prompt_overlay, subscribe_end_card, branding_overlays, get_audio_duration
from src.image_gen import gen_img
from src.cinematic import (
    apply_camera_move, enhance_frame, render_professional_caption,
    render_brand_overlay,
)

FONT_PATH = config.get_font()
W, H = config.VIDEO_WIDTH, config.VIDEO_HEIGHT
FPS = config.VIDEO_FPS
BRAND = config.BRAND_NAME

CURRENT_FACTS = []
CURRENT_NICHE = ""


def make_title_card(img: Image.Image, title: str) -> Image.Image:
    img = img.copy()
    draw = ImageDraw.Draw(img)
    overlay = Image.new("RGBA", (W, int(H * 0.3)), (0, 0, 0, 160))
    img.paste(overlay, (0, H - int(H * 0.3)), overlay)
    try:
        font = ImageFont.truetype(FONT_PATH, 44)
    except:
        font = ImageFont.load_default()
    bb = draw.textbbox((0, 0), title.upper(), font=font)
    draw.text(((W - (bb[2] - bb[0])) // 2, H - 220), title.upper(), font=font, fill=(255, 255, 255))
    try:
        font2 = ImageFont.truetype(FONT_PATH, 28)
    except:
        font2 = ImageFont.load_default()
    bb2 = draw.textbbox((0, 0), "⬇  SWIPE FOR FACTS  ⬇", font=font2)
    draw.text(((W - (bb2[2] - bb2[0])) // 2, H - 120), "⬇  SWIPE FOR FACTS  ⬇", font=font2, fill=(255, 200, 0))
    return img


def make_fact_card(img: Image.Image, num: int, fact: str) -> Image.Image:
    img = img.copy()
    draw = ImageDraw.Draw(img)
    overlay = Image.new("RGBA", (W, int(H * 0.35)), (0, 0, 0, 180))
    img.paste(overlay, (0, H - int(H * 0.35)), overlay)
    try:
        font = ImageFont.truetype(FONT_PATH, 72)
    except:
        font = ImageFont.load_default()
    draw.text((30, H - 420), f"#{num}", font=font, fill=(255, 204, 0))
    try:
        font2 = ImageFont.truetype(FONT_PATH, 36)
    except:
        font2 = ImageFont.load_default()
    lines = []
    words = fact.split()
    current = ""
    for w in words:
        test = f"{current} {w}".strip()
        bb = draw.textbbox((0, 0), test, font=font2)
        if bb[2] - bb[0] > W - 60:
            lines.append(current)
            current = w
        else:
            current = test
    lines.append(current)
    for i, line in enumerate(lines):
        draw.text((30, H - 320 + i * 44), line.upper(), font=font2, fill=(255, 255, 255))
    return img


def main():
    global CURRENT_FACTS, CURRENT_NICHE

    print("=" * 50)
    print("  FACTS VIDEO")
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

    print("\n[1/4] Voiceover...")
    tts_script = fact_data.get("tts_script", f"{HOOK} {' '.join(FACTS)}")
    tts_path = temp_dir / "narration.mp3"
    subprocess.run([sys.executable, "-m", "edge_tts", "--text", tts_script, "--voice", "en-US-GuyNeural", "--write-media", str(tts_path)], capture_output=True, text=True, timeout=120, check=True)
    total_dur = get_audio_duration(str(tts_path))
    print(f"  {total_dur:.1f}s | {len(FACTS)} facts")

    print(f"\n[2/4] Generating {len(PROMPTS)} images...")
    images = {}
    for i, (fact, prompt) in enumerate(zip(FACTS, PROMPTS)):
        cached = temp_dir / f"fact_{i}.png"
        if cached.exists() and cached.stat().st_size > 50000:
            img = Image.open(cached)
        else:
            print(f"  Image {i+1}/{len(PROMPTS)}...", end=" ", flush=True)
            img = gen_img(prompt)
            if img:
                img.save(cached)
                print("OK")
            else:
                print("procedural")
                from src.image_gen import _generate_scene
                img = _generate_scene(W, H, prompt)
        images[i] = img

    print("\n[3/4] Assembling clips...")
    dur_per_fact = total_dur / max(len(FACTS), 1)
    move_types = ["ken_burns_in", "ken_burns_out", "pan_right", "pan_left", "dolly_in", "dolly_out"]
    clips = []

    title_img = make_title_card(images[0], TITLE)
    title_arr = np.array(title_img)
    title_frames = []
    for i in range(max(8, int(0.8 * FPS))):
        p = i / max(7, 1)
        f = apply_camera_move(title_arr, p, "ken_burns_in", W, H)
        f = enhance_frame(f, color_grade="dramatic", vignette=True)
        if BRAND:
            f = render_brand_overlay(f, BRAND)
        title_frames.append(f)
    def make_title(t):
        return title_frames[min(int(t / (0.8 / len(title_frames))), len(title_frames) - 1)]
    clips.append(VideoClip(make_title, duration=0.8))

    for i, (fact, prompt) in enumerate(zip(FACTS, PROMPTS)):
        img = images.get(i, images[0])
        card = make_fact_card(img, i + 1, fact)
        arr = np.array(card)
        move = move_types[(i + 1) % len(move_types)]
        nf = max(8, int(dur_per_fact * FPS))
        scene_frames = []
        for j in range(nf):
            p = j / max(nf - 1, 1)
            f = apply_camera_move(arr, p, move, W, H)
            f = enhance_frame(f, color_grade="dramatic", vignette=True)
            if BRAND:
                f = render_brand_overlay(f, BRAND)
            scene_frames.append(f)
        def make_scene(t, frames=scene_frames):
            idx = min(int(t / (dur_per_fact / len(frames))), len(frames) - 1)
            return frames[idx]
        clips.append(VideoClip(make_scene, duration=dur_per_fact))

    end_arr = np.zeros((H, W, 3), dtype=np.uint8)
    clips.append(subscribe_end_card(end_arr, 1.5))

    bg = concatenate_videoclips(clips, method="compose")
    overlays = hook_overlays(1.8)
    overlays += comment_prompt_overlay(start_time=max(total_dur * 0.4, 0.5), duration=2.0)
    overlays += branding_overlays(bg.duration)
    final = CompositeVideoClip([bg] + overlays, size=config.SHORTS_SIZE)

    audio_clip = AudioFileClip(str(tts_path))
    video_dur = total_dur + 1.5
    if video_dur > audio_clip.duration:
        silence = AudioFileClip(str(tts_path)).with_duration(video_dur - audio_clip.duration).with_volume_scaled(0)
        audio_clip = concatenate_audioclips([audio_clip, silence])
    music_paths = list(config.MUSIC_DIR.glob("*.mp3"))
    if music_paths:
        music = AudioFileClip(str(random.choice(music_paths))).with_duration(video_dur).with_volume_scaled(0.08)
        final = final.with_audio(CompositeAudioClip([audio_clip, music]))
    else:
        final = final.with_audio(audio_clip)

    print("\n[4/4] Rendering...")
    safe_title = TITLE.lower().replace(" ", "_").replace("?", "").replace("!", "").replace("'", "").replace(".","").replace(",","").replace(":","")[:50]
    out = config.OUTPUT_DIR / f"facts_{safe_title}.mp4"
    out.unlink(missing_ok=True)
    print(f"  {video_dur:.1f}s | {W}x{H} | {FPS}fps")
    t0 = time.time()
    final.write_videofile(str(out), fps=FPS, codec="libx264", audio_codec="aac", threads=4, preset="medium", ffmpeg_params=["-movflags", "+faststart", "-crf", "18"], logger=None)
    final.close()
    t1 = time.time()
    print(f"\n  DONE in {t1-t0:.0f}s: {out}")
    print(f"  Size: {out.stat().st_size:,} bytes")

    return out, fact_data


if __name__ == "__main__":
    main()
