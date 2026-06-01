"""Cinematic Short Film — Pollinations.ai image generation + pipeline assembly."""

import sys, subprocess, time, io, random
from pathlib import Path
from PIL import Image, ImageEnhance
import numpy as np
import requests as req
from moviepy import (
    VideoClip, AudioFileClip, TextClip,
    CompositeVideoClip, concatenate_videoclips, ColorClip,
    CompositeAudioClip,
)
import config
from src.engagement import hook_overlays, fast_motion, comment_prompt_overlay, subscribe_end_card, branding_overlays

FONT = config.get_font()
W, H = config.VIDEO_WIDTH, config.VIDEO_HEIGHT

SCENES = [
    ("villain",    "anthropomorphic cat villain in dark cyberpunk alley, neon lights, dramatic cinematic, volumetric fog, glowing eyes, 9:16 vertical, highly detailed"),
    ("kidnapping", "surreal cinematic scene child floating upward in neon beam of light, magical realism, dreamlike atmosphere, glowing particles, ethereal, 9:16"),
    ("squad",      "three determined children with futuristic glowing bicycles, neon cyberpunk city background, holographic reflections, cinematic low angle, glowing rims, 9:16"),
    ("chase",      "bicycle squad racing through neon-lit curved city street, glowing energy trails, dynamic motion blur, cyberpunk aesthetic, particle effects, cinematic, 9:16"),
    ("finale",     "epic cinematic climax rescue squad closing in on cat villain, neon light explosion, dramatic, intense, cinematic movie still, 9:16, artstation"),
]

SUBTITLES = [
    "A mysterious cat villain emerges in the neon-lit shadows.",
    "A child taken in a surreal beam of light.",
    "The rescue squad assembles on futuristic bikes.",
    "The chase through streets that bend and shift.",
    "In a final burst of speed, justice prevails.",
]

TITLE = "CAT KIDNAPPING & BIKE RESCUE SQUAD"
CHAPTER = 1  # will be overridden by pipeline

SCRIPT = (
    "A mysterious cat villain emerges in the neon-lit shadows. "
    "A child taken in a surreal beam of light. "
    "The rescue squad assembles on futuristic bikes. "
    "The chase through streets that bend and shift. "
    "In a final burst of speed, justice prevails."
)


def gen_img(prompt: str) -> Image.Image | None:
    """Generate image via Pollinations.ai (free)."""
    url = f"https://image.pollinations.ai/prompt/{req.utils.quote(prompt)}?width={config.VIDEO_WIDTH}&height={config.VIDEO_HEIGHT}&nofeed=true&seed={random.randint(0,999999)}&model=flux"
    try:
        r = req.get(url, timeout=120)
        if r.status_code == 200 and len(r.content) > 500:
            return Image.open(io.BytesIO(r.content)).convert("RGB")
    except Exception as e:
        print(f"    Error: {e}")
    return None


def upscale(img: Image.Image) -> Image.Image:
    """Upscale + cinematic color grade."""
    img = img.resize((W, H), Image.LANCZOS)
    img = ImageEnhance.Contrast(img).enhance(1.3)
    img = ImageEnhance.Color(img).enhance(1.4)
    img = ImageEnhance.Sharpness(img).enhance(1.2)
    arr = np.array(img).astype(np.float32)
    # Vignette
    vx, vy = np.meshgrid(np.linspace(-1, 1, W), np.linspace(-1, 1, H))
    vig = np.clip(1 - (vx**2 + vy**2) * 0.35, 0.15, 1)
    for c in range(3):
        arr[:, :, c] *= vig
    # Chromatic aberration
    ca = 2
    r, b = arr[:, :, 0].copy(), arr[:, :, 2].copy()
    arr[ca:, :, 0] = r[:-ca, :]
    arr[:, ca:, 2] = b[:, :-ca]
    arr = np.clip(arr + np.random.normal(0, 3, arr.shape).astype(np.float32), 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


motion_clip = fast_motion


def main():
    print("=" * 50)
    print("  CINEMATIC SHORT FILM GENERATOR")
    print("=" * 50)

    temp_dir = config.TEMP_DIR / "cinematic"
    temp_dir.mkdir(exist_ok=True)

    # Step 1: TTS
    print("\n[1/4] Voiceover...")
    tts_path = temp_dir / "narration.mp3"
    subprocess.run([sys.executable, "-m", "edge_tts", "--text", SCRIPT, "--voice", "en-US-GuyNeural", "--write-media", str(tts_path)], capture_output=True, text=True, timeout=120, check=True)
    audio = AudioFileClip(str(tts_path))
    total_dur = audio.duration
    audio.close()
    print(f"  {total_dur:.1f}s")

    # Step 2: Generate images (skip if already cached)
    print(f"\n[2/4] Loading/generating {len(SCENES)} images...")
    images = {}
    for i, (sid, prompt) in enumerate(SCENES):
        cached = temp_dir / f"{sid}.png"
        if cached.exists() and cached.stat().st_size > 50000:
            img = Image.open(cached)
            images[sid] = img
            print(f"  [{i+1}/{len(SCENES)}] {sid} (cached)")
        else:
            print(f"  [{i+1}/{len(SCENES)}] {sid}...", end=" ", flush=True)
            img = gen_img(prompt)
            if img:
                img = upscale(img)
                img.save(cached)
                images[sid] = img
                print(f"OK")
            else:
                print("FAILED")

    # Step 3: Build clips
    print(f"\n[3/4] Assembling...")
    dur = total_dur / len(SCENES)
    clips = []
    overlays = []

    scene_ids = [s[0] for s in SCENES]

    # Hook overlays from engagement module
    overlays = hook_overlays(1.8)

    # Title card (use first scene) - shorter
    title_img = images.get(scene_ids[0], Image.new("RGB", (W, H), (10, 5, 40)))
    clips.append(motion_clip(title_img, 1.2))
    title_txt = TextClip(text=TITLE, font=FONT, font_size=36, color="white", stroke_color="black", stroke_width=3, method="label").with_position(("center", "center")).with_duration(1.2)
    overlays.append(title_txt)

    # Scene clips
    ct = 1.2
    for i, (sid, sub) in enumerate(zip(scene_ids, SUBTITLES)):
        shake = i in (len(scene_ids)//2, len(scene_ids)-1)
        if sid in images:
            clip = fast_motion(images[sid], dur, shake=shake, intensity=1.3)
        else:
            def fb(t, s=sid):
                arr = np.zeros((H, W, 3), dtype=np.uint8)
                for y in range(H):
                    p = y / H
                    arr[y, :] = [int(20 + 40 * p + abs(np.sin(t*0.5 + p*8))*30),
                                 int(10 + 20*(1-p) + abs(np.cos(t*0.3 + p*6))*20),
                                 int(30 + 50 * p + abs(np.sin(t*0.4 + p*7))*25)]
                return arr
            clip = VideoClip(fb, duration=dur)
        txt = TextClip(text=sub, font=FONT, font_size=30, color="white", stroke_color="black", stroke_width=2, method="label").with_position(("center", H-200)).with_start(ct + 0.2).with_duration(dur - 0.4)
        overlays.append(txt)
        clips.append(clip)
        ct += dur

    # Comment prompt
    overlays += comment_prompt_overlay(start_time=max(total_dur * 0.4, 0.5), duration=2.0)

    # End card (use LAST scene)
    end_img = images.get(scene_ids[-1], Image.new("RGB", (W, H), (10, 5, 40)))
    clips.append(subscribe_end_card(end_img, 1.5))
    # Loop-ready: replay first image
    loop_img = images.get(scene_ids[0], Image.new("RGB", (W, H), (10, 5, 40)))
    clips.append(fast_motion(loop_img, 0.5, intensity=0.5))
    end_text = TextClip(text="TO BE CONTINUED... CHAPTER " + str(CHAPTER + 1), font=FONT, font_size=30, color="#FFCC00", stroke_color="black", stroke_width=2, method="label").with_position(("center", H-100)).with_duration(2.0).with_start(total_dur - 2.0)
    overlays.append(end_text)

    bg = concatenate_videoclips(clips, method="compose")
    overlays += branding_overlays(bg.duration)
    final = CompositeVideoClip([bg] + overlays, size=config.SHORTS_SIZE)
    audio = AudioFileClip(str(tts_path))
    music = None
    music_paths = list(config.MUSIC_DIR.glob("*.mp3"))
    if music_paths:
        from moviepy.audio.fx import AudioFadeIn, AudioFadeOut
        music = AudioFileClip(str(random.choice(music_paths))).with_duration(total_dur).with_volume_scaled(0.10).with_effects([AudioFadeIn(0.5), AudioFadeOut(0.5)])
        final = final.with_audio(CompositeAudioClip([audio, music]))
    else:
        final = final.with_audio(audio)

    # Step 4: Render
    print(f"\n[4/4] Rendering...")
    safe_title = TITLE.lower().replace(" ", "_").replace("&", "and").replace("'", "")[:50]
    out = config.OUTPUT_DIR / f"{safe_title}.mp4"
    print(f"  {total_dur:.1f}s | {W}x{H}")
    final.write_videofile(str(out), fps=config.VIDEO_FPS, codec="libx264", audio_codec="aac", threads=4, preset="ultrafast", ffmpeg_params=["-movflags", "+faststart"], logger=None)
    final.close()
    print(f"\n  DONE: {out}")

if __name__ == "__main__":
    main()
