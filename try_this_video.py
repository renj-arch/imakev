"""Try This — one interactive brain hack per short. Fast, experiential, high retention."""

import sys, subprocess, time, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from moviepy import (
    VideoClip, AudioFileClip, ImageClip,
    concatenate_videoclips, CompositeAudioClip, concatenate_audioclips,
    CompositeVideoClip,
)
import config
from src.engagement import hook_overlays, fast_motion, comment_prompt_overlay, subscribe_end_card, branding_overlays, get_audio_duration, retention_prompt, countdown_overlay
from src.image_gen import gen_img

FONT_PATH = config.get_font()
W, H = config.VIDEO_WIDTH, config.VIDEO_HEIGHT




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


def make_title_card(img: Image.Image, hook: str) -> Image.Image:
    img = img.copy()
    overlay = Image.new("RGBA", (W, int(H * 0.3)), (0, 0, 0, 180))
    img.paste(overlay, (0, H - int(H * 0.3)), overlay)
    draw_text(img, "🧠 TRY THIS", 48, H - 240, center=True, color=(0, 255, 200))
    draw_text(img, hook.upper(), 32, H - 160, center=True)
    return img


def make_reveal_card(img: Image.Image, text: str) -> Image.Image:
    img = img.copy()
    overlay = Image.new("RGBA", (W, int(H * 0.35)), (0, 0, 0, 200))
    img.paste(overlay, (0, H - int(H * 0.35)), overlay)
    draw_text(img, "⚡", 80, H - 420, center=True)
    draw_text(img, text.upper(), 36, H - 280, center=True, color=(0, 255, 200))
    return img


def make_end_card(img: Image.Image) -> Image.Image:
    img = img.copy()
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 140))
    img.paste(overlay, (0, 0), overlay)
    draw_text(img, "SUBSCRIBE", 60, H // 2 - 80, center=True, color=(0, 255, 200))
    draw_text(img, "FOR MORE BRAIN HACKS", 30, H // 2, center=True)
    return img


motion_clip = fast_motion


def main():
    print("=" * 50)
    print("  TRY THIS — BRAIN HACK")
    print("=" * 50)

    from src.try_this import generate_try_this_script
    data = generate_try_this_script()

    HOOK = data["hook"]
    SETUP = data.get("setup", "")
    ACTION = data.get("action", "")
    REVEAL = data.get("reveal", "")
    EXPLANATION = data.get("explanation", "")
    PROMPT = data.get("prompt", "")
    IMAGE_STYLE = data.get("image_style", "minimal abstract design, brain illusion, 9:16")

    title = f"Try This: {HOOK[:50]}"

    temp_dir = config.TEMP_DIR / "try_this_video"
    temp_dir.mkdir(exist_ok=True)

    # TTS
    print("\n[1/4] Voiceover...")
    tts_script = f"{HOOK} {SETUP} {ACTION} {REVEAL} {EXPLANATION} {PROMPT}"
    tts_path = temp_dir / "narration.mp3"
    subprocess.run([sys.executable, "-m", "edge_tts", "--text", tts_script, "--voice", "en-US-GuyNeural", "--write-media", str(tts_path)], capture_output=True, text=True, timeout=120, check=True)
    total_dur = get_audio_duration(str(tts_path))
    print(f"  {total_dur:.1f}s")

    # Generate image
    print(f"\n[2/4] Generating image...")
    cached = temp_dir / "brain_hack.png"
    if cached.exists() and cached.stat().st_size > 50000:
        img = Image.open(cached)
    else:
        print("  Generating...", end=" ", flush=True)
        img = gen_img(IMAGE_STYLE)
        if img:
            img.save(cached)
            print("OK")
        else:
            print("fallback")
            arr = np.zeros((H, W, 3), dtype=np.uint8)
            for y in range(H):
                arr[y, :] = [int(10 + 30*(y/H)), int(5 + 15*(1-y/H)), int(20 + 40*(y/H))]
            img = Image.fromarray(arr)

    # Bake text
    print("\n[3/4] Baking text onto frames...")
    dur_hook = max(2.0, total_dur * 0.2)
    dur_setup = max(2.0, total_dur * 0.2)
    dur_action = max(2.0, total_dur * 0.15)
    dur_reveal = max(2.0, total_dur * 0.2)
    dur_explain = max(2.0, total_dur * 0.2)
    dur_end = 1.5

    clips = []

    # Hook card
    card = make_title_card(img, HOOK)
    clips.append(motion_clip(card, dur_hook))

    # Setup card
    if SETUP:
        card2 = make_reveal_card(img, SETUP)
        clips.append(fast_motion(card2, dur_setup, shake=True))

    # Action card
    if ACTION:
        card3 = make_reveal_card(img, ACTION)
        clips.append(fast_motion(card3, dur_action, shake=False))

    # Reveal card
    if REVEAL:
        card4 = make_reveal_card(img, REVEAL)
        clips.append(fast_motion(card4, dur_reveal, shake=True))

    # Explanation card
    if EXPLANATION:
        card5 = make_reveal_card(img, EXPLANATION)
        clips.append(fast_motion(card5, dur_explain, shake=False))

    # Overlays
    overlays = hook_overlays(2.0)
    overlays += countdown_overlay(start_time=max(total_dur * 0.3, 0.3), duration=2.0)
    overlays += retention_prompt(start_time=total_dur * 0.4, duration=2.0)
    overlays += comment_prompt_overlay(start_time=max(total_dur * 0.5, 0.5), duration=2.0)

    # End card
    clips.append(subscribe_end_card(img, dur_end))

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
    safe = HOOK.lower().replace(" ", "_").replace("?", "").replace("!", "").replace("'", "").replace(".", "").replace(",", "").replace(":", "")[:40]
    out = config.OUTPUT_DIR / f"try_this_{safe}.mp4"
    out.unlink(missing_ok=True)
    print(f"  {video_dur:.1f}s | {W}x{H}")
    t0 = time.time()
    final.write_videofile(str(out), fps=config.VIDEO_FPS, codec="libx264", audio_codec="aac", threads=4, preset="ultrafast", ffmpeg_params=["-movflags", "+faststart"], logger=None)
    final.close()
    t1 = time.time()
    print(f"\n  DONE in {t1-t0:.0f}s: {out}")
    print(f"  Size: {out.stat().st_size} bytes")
    data["title"] = title
    return out, data


if __name__ == "__main__":
    main()
