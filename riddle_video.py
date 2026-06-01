"""Riddle Shorts video generator — Pollinations.ai + TTS + baked-in Pillow text."""

import sys, subprocess, time, io, random
from pathlib import Path
from PIL import Image, ImageEnhance, ImageDraw, ImageFont
import numpy as np
import requests as req
from moviepy import (
    VideoClip, AudioFileClip, ImageClip,
    concatenate_videoclips, CompositeAudioClip, concatenate_audioclips,
    CompositeVideoClip,
)
import config
from src.riddles import generate_riddle_script
from src.engagement import hook_overlays, fast_motion, comment_prompt_overlay, subscribe_end_card, branding_overlays

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


def draw_text(img, text, font_size, y, color=(255, 255, 255), stroke_color=(0, 0, 0), stroke_width=2, center=False, x=30):
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


def make_hook_card(img, hook_text):
    img = img.copy()
    overlay = Image.new("RGBA", (W, int(H * 0.3)), (0, 0, 0, 160))
    img.paste(overlay, (0, H - int(H * 0.3)), overlay)
    draw_text(img, "🧠 RIDDLE TIME", 48, H - 240, center=True, color=(255, 204, 0))
    draw_text(img, hook_text.upper(), 32, H - 160, center=True)
    return img


def make_riddle_card(img, riddle):
    img = img.copy()
    overlay = Image.new("RGBA", (W, int(H * 0.5)), (0, 0, 0, 200))
    img.paste(overlay, (0, H - int(H * 0.5)), overlay)
    draw_text(img, "🤔", 80, 80, center=True)
    draw_text(img, riddle.upper(), 36, H - 500, center=True)
    draw_text(img, "⏸  Think about it...", 28, H - 120, center=True, color=(255, 200, 0))
    return img


def make_answer_card(img, answer, explanation):
    img = img.copy()
    overlay = Image.new("RGBA", (W, int(H * 0.5)), (0, 0, 0, 200))
    img.paste(overlay, (0, H - int(H * 0.5)), overlay)
    draw_text(img, "💡 ANSWER", 52, H - 480, center=True, color=(255, 204, 0))
    draw_text(img, answer.upper(), 44, H - 380, center=True)
    if explanation:
        draw_text(img, explanation, 28, H - 260, center=True)
    draw_text(img, "SUBSCRIBE FOR MORE", 26, H - 100, center=True)
    return img


motion_clip = fast_motion


def main():
    print("=" * 50)
    print("  RIDDLE VIDEO GENERATOR")
    print("=" * 50)

    data = generate_riddle_script()
    RIDDLE = data["riddle"]
    ANSWER = data["answer"]
    EXPLANATION = data.get("explanation", "")
    HOOK = data["hook"]

    temp_dir = config.TEMP_DIR / "riddle"
    temp_dir.mkdir(exist_ok=True)

    print("\n[1/4] Voiceover...")
    tts_text = f"{HOOK} {RIDDLE} ... The answer is {ANSWER}. {EXPLANATION}"
    tts_path = temp_dir / "narration.mp3"
    subprocess.run(
        [sys.executable, "-m", "edge_tts", "--text", tts_text, "--voice", "en-US-JennyNeural", "--write-media", str(tts_path)],
        capture_output=True, text=True, timeout=120, check=True,
    )
    audio = AudioFileClip(str(tts_path))
    total_dur = audio.duration
    audio.close()

    pause_before_answer = 1.5
    riddle_dur = max(total_dur * 0.55, 3.0)
    answer_dur = max(total_dur * 0.45 + pause_before_answer, 4.0)

    print(f"  {total_dur:.1f}s total | riddle {riddle_dur:.1f}s + answer {answer_dur:.1f}s")

    print("\n[2/4] Generating images...")
    riddle_img = None
    answer_img = None

    for prompt_key, label, target in [
        ("image_prompt_riddle", "Riddle", "riddle"),
        ("image_prompt_answer", "Answer", "answer"),
    ]:
        prompt = data.get(prompt_key, "")
        cached = temp_dir / f"{label.lower()}.png"
        if cached.exists() and cached.stat().st_size > 50000:
            img = Image.open(cached)
        else:
            print(f"  {label} image...", end=" ", flush=True)
            img = gen_img(prompt or "mysterious dark background, question marks, 9:16")
            if img:
                img = upscale(img)
                img.save(cached)
                print("OK")
            else:
                print("fallback")
                arr = np.zeros((H, W, 3), dtype=np.uint8)
                for y in range(H):
                    arr[y, :] = [int(30 + 50 * (y / H)), int(10 + 20 * (1 - y / H)), int(50 + 70 * (y / H))]
                img = Image.fromarray(arr)
        if target == "riddle":
            riddle_img = img
        else:
            answer_img = img

    if answer_img is None:
        answer_img = riddle_img

    print("\n[3/4] Baking text onto frames...")
    hook_card = make_hook_card(riddle_img, HOOK)
    riddle_card = make_riddle_card(riddle_img, RIDDLE)
    answer_card = make_answer_card(answer_img, ANSWER, EXPLANATION)

    riddle_clip = motion_clip(riddle_card, riddle_dur, shake=True)

    silence = AudioFileClip(str(tts_path)).with_duration(0).with_volume_scaled(0)
    pause_clip = VideoClip(lambda t: np.array(answer_card.resize((W, H))), duration=pause_before_answer)
    pause_clip = pause_clip.with_audio(silence)

    answer_clip = motion_clip(answer_card, answer_dur)

    overlays = hook_overlays(1.5)
    hook_with_overlays = CompositeVideoClip([motion_clip(hook_card, 1.5)] + overlays, size=config.SHORTS_SIZE)

    # Wrap answer clip with comment prompt overlay
    answer_composite = CompositeVideoClip([answer_clip, comment_prompt_overlay(start_time=0.5, duration=2.0)[0]], size=config.SHORTS_SIZE)

    raw_clips = [hook_with_overlays, riddle_clip, pause_clip, answer_composite]
    bg = concatenate_videoclips(raw_clips, method="compose")
    branding = branding_overlays(bg.duration)
    final = CompositeVideoClip([bg] + branding, size=config.SHORTS_SIZE) if branding else bg

    print("\n[4/4] Applying audio...")
    audio_riddle = AudioFileClip(str(tts_path))
    total_video_dur = 1.5 + riddle_dur + pause_before_answer + answer_dur
    # Pad narration with silence so moviepy doesn't read past end
    if total_video_dur > audio_riddle.duration:
        silence = AudioFileClip(str(tts_path)).with_duration(total_video_dur - audio_riddle.duration).with_volume_scaled(0)
        audio_riddle = concatenate_audioclips([audio_riddle, silence])

    music_paths = list(config.MUSIC_DIR.glob("*.mp3"))
    if music_paths:
        music = AudioFileClip(str(random.choice(music_paths))).with_duration(total_video_dur).with_volume_scaled(0.06)
        final = final.with_audio(CompositeAudioClip([audio_riddle, music]))
    else:
        final = final.with_audio(audio_riddle)

    safe_title = f"riddle_{RIDDLE[:30].lower().replace(' ', '_')}"
    out = config.OUTPUT_DIR / f"{safe_title}.mp4"
    out.unlink(missing_ok=True)
    print(f"  {total_video_dur:.1f}s | {W}x{H}")
    t0 = time.time()
    final.write_videofile(
        str(out), fps=config.VIDEO_FPS, codec="libx264", audio_codec="aac",
        threads=4, preset="ultrafast", ffmpeg_params=["-movflags", "+faststart"],
        logger=None,
    )
    final.close()
    t1 = time.time()
    print(f"\n  DONE in {t1 - t0:.0f}s: {out}")
    print(f"  Size: {out.stat().st_size} bytes")

    return out, data


if __name__ == "__main__":
    main()
