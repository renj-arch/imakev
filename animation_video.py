"""AI Animation video — generates animated video from any prompt using Pollinations.ai frames."""

import sys, subprocess, time, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from moviepy import (
    VideoClip,
    AudioFileClip,
    concatenate_videoclips,
    CompositeAudioClip,
    CompositeVideoClip,
)
import config
from src.animation_gen import generate_animation_script
from src.engagement import (
    hook_overlays,
    fast_motion,
    comment_prompt_overlay,
    subscribe_end_card,
    branding_overlays,
    get_audio_duration,
)
from src.image_gen import gen_img

FONT_PATH = config.get_font()
W, H = config.VIDEO_WIDTH, config.VIDEO_HEIGHT


def draw_text(
    img,
    text,
    font_size,
    y,
    color=(255, 255, 255),
    stroke_color=(0, 0, 0),
    stroke_width=2,
    center=False,
    x=30,
):
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
    except Exception:
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


def make_frame_card(img, caption, i, total):
    img = img.copy()
    bottom_bar = Image.new("RGBA", (W, int(H * 0.25)), (0, 0, 0, 160))
    img.paste(bottom_bar, (0, H - int(H * 0.25)), bottom_bar)

    top_bar = Image.new("RGBA", (W, int(H * 0.12)), (0, 0, 0, 100))
    img.paste(top_bar, (0, 0), top_bar)

    draw_text(img, f"AI ANIMATION", 26, 18, center=True, color=(0, 200, 255))
    draw_text(img, caption, 32, H - 260, stroke_width=2)
    prog = f"{'#' * (i + 1)}{'-' * (total - i - 1)}"
    draw_text(img, prog, 18, H - 60, center=True, color=(100, 200, 255), stroke_width=1)
    return img


def make_title_card(img, text):
    img = img.copy()
    overlay = Image.new("RGBA", (W, int(H * 0.35)), (0, 0, 0, 180))
    img.paste(overlay, (0, H - int(H * 0.35)), overlay)
    draw_text(img, text.upper(), 40, H - 260, center=True)
    draw_text(img, "AI GENERATED ANIMATION", 24, H - 120, center=True, color=(0, 200, 255))
    return img


def make_end_card(img):
    img = img.copy()
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 120))
    img.paste(overlay, (0, 0), overlay)
    draw_text(img, "SUBSCRIBE", 60, H // 2 - 60, center=True, color=(0, 200, 255))
    draw_text(img, "FOR MORE AI ANIMATIONS", 32, H // 2 + 20, center=True)
    return img


def main():
    print("=" * 50)
    print("  AI ANIMATION GENERATOR")
    print("=" * 50)

    user_prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    if not user_prompt:
        print("  No prompt provided — auto-generating one...")
        try:
            from src.script_generator import _generate
            raw = _generate(
                "Suggest a single visually interesting subject for an AI animation video. "
                "Examples: 'a cat exploring a neon city', 'a dragon flying over mountains', "
                "'a jellyfish glowing in the deep ocean'. Return ONLY the subject, 3-10 words.",
                temperature=0.9, max_tokens=30,
                system="You suggest creative subjects for AI animation.",
            )
            user_prompt = raw.strip().strip('"').strip("'") if raw else ""
        except Exception:
            user_prompt = ""
        if not user_prompt:
            user_prompt = random.choice([
                "a duck swimming in a pond",
                "a cat exploring a neon city",
                "a dragon flying over mountains",
                "a jellyfish glowing in the deep ocean",
                "a fox in an enchanted forest",
                "a hummingbird drinking nectar",
            ])
        print(f"  Auto-generated prompt: {user_prompt}")

    data = generate_animation_script(user_prompt)
    TITLE = data["title"]
    SUBJECT = data["subject"]
    PROMPTS = data["frame_prompts"]

    temp_dir = config.TEMP_DIR / "animation"
    temp_dir.mkdir(exist_ok=True)

    print(f"\n[1/4] Voiceover: {SUBJECT}")
    tts_script = data["tts_script"]
    tts_path = temp_dir / "narration.mp3"
    subprocess.run(
        [sys.executable, "-m", "edge_tts", "--text", tts_script, "--voice", "en-US-GuyNeural", "--write-media", str(tts_path)],
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )
    total_dur = get_audio_duration(str(tts_path))
    print(f"  {total_dur:.1f}s | {len(PROMPTS)} frames")

    print(f"\n[2/4] Generating {len(PROMPTS)} animation frames...")
    images = {}
    for i, prompt in enumerate(PROMPTS):
        cached = temp_dir / f"anim_{i}.png"
        if cached.exists() and cached.stat().st_size > 50000:
            img = Image.open(cached)
            print(f"  Frame {i+1}/{len(PROMPTS)}... cached")
        else:
            print(f"  Frame {i+1}/{len(PROMPTS)}...", end=" ", flush=True)
            img = gen_img(prompt)
            if img:
                img.save(cached)
                print("OK")
            else:
                print("fallback")
                arr = np.zeros((H, W, 3), dtype=np.uint8)
                for y in range(H):
                    t = y / H
                    arr[y, :] = [
                        int(80 + 120 * (1 - abs(t - 0.5) * 2)),
                        int(40 + 80 * (1 - abs(t - 0.5) * 2)),
                        int(160 + 80 * (1 - abs(t - 0.5) * 2)),
                    ]
                img = Image.fromarray(arr)
        images[i] = img

    print("\n[3/4] Composing animation...")
    dur_per = total_dur / len(PROMPTS)

    title_img = make_title_card(images[0], TITLE)
    clips = [fast_motion(title_img, 0.8, shake=False, intensity=0.4)]

    captions = [
        f"Witness {SUBJECT}...",
        f"Amazing details of {SUBJECT}",
        f"The beauty of {SUBJECT}",
        f"{SUBJECT} in motion",
        f"Capturing {SUBJECT}",
        f"Mesmerizing {SUBJECT}",
        f"Nature's wonder: {SUBJECT}",
        f"{SUBJECT} revealed",
    ]

    for i in range(len(PROMPTS)):
        img = images.get(i, images[0])
        caption = captions[i % len(captions)]
        card = make_frame_card(img, caption, i, len(PROMPTS))
        shake = i == len(PROMPTS) - 1
        clips.append(fast_motion(card, dur_per, shake=shake, intensity=0.6))

    end_img = images.get(len(PROMPTS) - 1, images[0])
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
    safe_title = (
        SUBJECT.lower()
        .replace(" ", "_")
        .replace("?", "")
        .replace("!", "")
        .replace("'", "")
        .replace(".", "")
        .replace(",", "")
        .replace(":", "")
    )[:50]
    out = config.OUTPUT_DIR / f"animation_{safe_title}.mp4"
    out.unlink(missing_ok=True)
    print(f"  {total_dur + 0.8:.1f}s | {W}x{H}")
    t0 = time.time()
    final.write_videofile(
        str(out),
        fps=config.VIDEO_FPS,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="ultrafast",
        ffmpeg_params=["-movflags", "+faststart"],
        logger=None,
    )
    final.close()
    t1 = time.time()
    print(f"\n  DONE in {t1 - t0:.0f}s: {out}")
    return out, data


if __name__ == "__main__":
    main()
