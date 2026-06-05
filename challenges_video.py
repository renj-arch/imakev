"""Fast-paced challenges & stunts video — countdown timers, high-energy text, dynamic pacing."""

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


def make_title_card(img: Image.Image, title: str) -> Image.Image:
    img = img.copy()
    overlay = Image.new("RGBA", (W, int(H * 0.4)), (0, 0, 0, 180))
    img.paste(overlay, (0, H - int(H * 0.4)), overlay)
    draw_text(img, "⚡ CHALLENGE ⚡", 52, H - 300, center=True, color=(255, 204, 0))
    draw_text(img, title.upper(), 38, H - 220, center=True)
    draw_text(img, "⬇  CAN YOU DO IT?  ⬇", 26, H - 120, center=True, color=(255, 200, 0))
    return img


def make_challenge_card(img: Image.Image, num: int, title: str) -> Image.Image:
    img = img.copy()
    overlay = Image.new("RGBA", (W, int(H * 0.4)), (0, 0, 0, 200))
    img.paste(overlay, (0, H - int(H * 0.4)), overlay)
    draw_text(img, f"#{num}", 80, H - 440, color=(255, 50, 50))
    draw_text(img, title.upper(), 40, H - 330, center=True)
    draw_text(img, "⬇  CAN YOU DO IT?  ⬇", 24, H - 120, center=True, color=(255, 200, 0))
    return img


def make_end_card(img: Image.Image) -> Image.Image:
    img = img.copy()
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 140))
    img.paste(overlay, (0, 0), overlay)
    draw_text(img, "SUBSCRIBE", 64, H // 2 - 80, center=True, color=(255, 204, 0))
    draw_text(img, "FOR MORE CHALLENGES", 36, H // 2, center=True)
    draw_text(img, "🔔 TURN ON NOTIFICATIONS 🔔", 28, H // 2 + 60, center=True, color=(255, 200, 0))
    return img


motion_clip = fast_motion


def main():
    print("=" * 50)
    print("  CHALLENGES & STUNTS VIDEO")
    print("=" * 50)

    from src.challenges import generate_challenges_script
    data = generate_challenges_script()

    TITLE = data["title"]
    HOOK = data["hook"]
    CHALLENGES = data["challenges"]
    PROMPTS = data["image_prompts"][:len(CHALLENGES)]

    temp_dir = config.TEMP_DIR / "challenges_video"
    temp_dir.mkdir(exist_ok=True)

    # TTS
    print("\n[1/4] Voiceover...")
    tts_script = data.get("tts_script", f"{HOOK} {' '.join(c['title'] + '. ' + c['description'] for c in CHALLENGES)}")
    tts_path = temp_dir / "narration.mp3"
    subprocess.run([sys.executable, "-m", "edge_tts", "--text", tts_script, "--voice", "en-US-GuyNeural", "--write-media", str(tts_path)], capture_output=True, text=True, timeout=120, check=True)
    total_dur = get_audio_duration(str(tts_path))
    print(f"  {total_dur:.1f}s | {len(CHALLENGES)} challenges")

    # Generate images
    print(f"\n[2/4] Generating {len(PROMPTS)} images...")
    images = {}
    for i, (challenge, prompt) in enumerate(zip(CHALLENGES, PROMPTS)):
        cached = temp_dir / f"challenge_{i}.png"
        if cached.exists() and cached.stat().st_size > 50000:
            img = Image.open(cached)
        else:
            print(f"  Image {i+1}/{len(PROMPTS)}...", end=" ", flush=True)
            img = gen_img(prompt)
            if img:
                img.save(cached)
                print("OK")
            else:
                print("fallback")
                arr = np.zeros((H, W, 3), dtype=np.uint8)
                for y in range(H):
                    arr[y, :] = [int(60 + 80*(y/H)), int(20 + 30*(1-y/H)), int(30 + 50*(y/H))]
                img = Image.fromarray(arr)
        images[i] = img

    # Bake text onto images
    print("\n[3/4] Baking text onto frames...")
    dur_per_challenge = total_dur / len(CHALLENGES) if CHALLENGES else total_dur

    # Title card
    title_img = make_title_card(images[0], TITLE)
    clips = [motion_clip(title_img, 1.0)]

    # Challenge cards
    for i, challenge in enumerate(CHALLENGES):
        img = images.get(i, images[0])
        card = make_challenge_card(img, i + 1, challenge["title"])
        shake = True
        clips.append(fast_motion(card, dur_per_challenge, shake=shake))

    # Hook overlays
    overlays = hook_overlays(2.5)
    overlays += countdown_overlay(start_time=max(total_dur * 0.2, 0.3), duration=2.0)
    overlays += retention_prompt(start_time=total_dur * 0.5, duration=2.0)
    overlays += comment_prompt_overlay(start_time=max(total_dur * 0.3, 0.5), duration=2.5)

    # Subscribe end card
    end_img = images.get(len(CHALLENGES) - 1, images[0])
    clips.append(subscribe_end_card(end_img, 1.5))

    bg = concatenate_videoclips(clips, method="compose")
    overlays += branding_overlays(bg.duration)
    final = CompositeVideoClip([bg] + overlays, size=config.SHORTS_SIZE)

    audio_clip = AudioFileClip(str(tts_path))
    video_dur = total_dur + 1.0
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
    out = config.OUTPUT_DIR / f"challenge_{safe_title}.mp4"
    out.unlink(missing_ok=True)
    print(f"  {total_dur + 1.0:.1f}s | {W}x{H}")
    t0 = time.time()
    final.write_videofile(str(out), fps=config.VIDEO_FPS, codec="libx264", audio_codec="aac", threads=4, preset="medium", ffmpeg_params=["-crf", "18", "-movflags", "+faststart"], logger=None)
    final.close()
    t1 = time.time()
    print(f"\n  DONE in {t1-t0:.0f}s: {out}")
    print(f"  Size: {out.stat().st_size} bytes")

    return out, data


if __name__ == "__main__":
    main()
