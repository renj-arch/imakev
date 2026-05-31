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

FONT = "C:\\Windows\\Fonts\\impact.ttf"
if not Path(FONT).exists():
    FONT = "C:\\Windows\\Fonts\\arial.ttf"
W, H = config.VIDEO_WIDTH, config.VIDEO_HEIGHT

SCENES = [
    ("villain",    "anthropomorphic cat villain in dark cyberpunk alley, neon lights, dramatic cinematic, volumetric fog, glowing eyes, 9:16 vertical, highly detailed"),
    ("kidnapping", "surreal cinematic scene child floating upward in neon beam of light, magical realism, dreamlike atmosphere, glowing particles, ethereal, 9:16"),
    ("squad",      "three determined children with futuristic glowing bicycles, neon cyberpunk city background, holographic reflections, cinematic low angle, glowing rims, 9:16"),
    ("chase",      "bicycle squad racing through neon-lit curved city street, glowing energy trails, dynamic motion blur, cyberpunk aesthetic, particle effects, cinematic, 9:16"),
    ("finale",     "epic cinematic climax rescue squad closing in on cat villain, neon light explosion, dramatic, intense, cinematic movie still, 9:16, artstation"),
]

SUBTITLES = [
    "In the neon-lit shadows of the dream city, a mysterious cat villain emerges.",
    "A child is taken in a surreal moment of light and shadow.",
    "A brave rescue squad assembles, mounting their futuristic bicycles.",
    "The chase begins through impossible streets that bend and shift.",
    "In a final burst of speed, the rescue squad closes in. Justice prevails.",
]

TITLE = "CAT KIDNAPPING & BIKE RESCUE SQUAD"
CHAPTER = 1  # will be overridden by pipeline

SCRIPT = (
    "In the neon-lit shadows of the dream city, a mysterious cat villain emerges from the darkness. "
    "A child is taken in a surreal moment of light and shadow. "
    "A brave rescue squad assembles, mounting their futuristic bicycles. "
    "The chase begins through impossible streets that bend and shift. "
    "In a final burst of speed and courage, the rescue squad closes in. "
    "Justice prevails in the heart of the dream city."
)


def gen_img(prompt: str) -> Image.Image | None:
    """Generate image via Pollinations.ai (free)."""
    url = f"https://image.pollinations.ai/prompt/{req.utils.quote(prompt)}?width=1080&height=1920&nofeed=true&seed={random.randint(0,999999)}&model=flux"
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


def motion_clip(img: Image.Image, dur: float, shake=False) -> VideoClip:
    w, h = img.size
    def f(t):
        p = t / dur if dur > 0 else 1
        if shake:
            scale = 1.0 + p * 0.08
            cw, ch = int(w / scale), int(h / scale)
            sx = int(np.sin(p * 40) * cw * 0.02)
            sy = int(np.cos(p * 35) * ch * 0.02)
            ox = max(0, min((w - cw) // 2 + sx, w - cw))
            oy = max(0, min((h - ch) // 2 + sy, h - ch))
            return np.array(img.crop((ox, oy, ox + cw, oy + ch)).resize((w, h), Image.LANCZOS))
        scale = 1.0 + p * 0.15
        cw, ch = int(w / scale), int(h / scale)
        ox, oy = (w - cw) // 2, (h - ch) // 2
        return np.array(img.crop((ox, oy, ox + cw, oy + ch)).resize((w, h), Image.LANCZOS))
    return VideoClip(f, duration=dur)


def main():
    print("=" * 50)
    print("  CINEMATIC SHORT FILM GENERATOR")
    print("=" * 50)

    temp_dir = config.TEMP_DIR / "cinematic"
    temp_dir.mkdir(exist_ok=True)

    # Step 1: TTS
    print("\n[1/4] Voiceover...")
    tts_path = temp_dir / "narration.mp3"
    subprocess.run(
        [sys.executable, "-m", "edge_tts", "--text", SCRIPT, "--voice", "en-US-GuyNeural", "--write-media", str(tts_path)],
        capture_output=True, text=True, timeout=120, check=True,
    )
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

    # Title card (use first scene)
    title_img = images.get(scene_ids[0], Image.new("RGB", (W, H), (10, 5, 40)))
    clips.append(motion_clip(title_img, 2.5))
    title_txt = TextClip(text=TITLE, font=FONT, font_size=40, color="white", stroke_color="black", stroke_width=3, method="label").with_position(("center", "center")).with_duration(2.5)
    overlays.append(title_txt)

    # Scene clips
    ct = 2.5
    for i, (sid, sub) in enumerate(zip(scene_ids, SUBTITLES)):
        shake = i in (len(scene_ids)//2, len(scene_ids)-1)  # middle and last get shake cam
        if sid in images:
            clip = motion_clip(images[sid], dur, shake=shake)
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
        txt = TextClip(text=sub, font=FONT, font_size=32, color="white", stroke_color="black", stroke_width=2, method="label").with_position(("center", H-220)).with_start(ct + 0.3).with_duration(dur - 0.6)
        overlays.append(txt)
        clips.append(clip)
        ct += dur

    # End card (use last scene)
    end_img = images.get(scene_ids[-1], Image.new("RGB", (W, H), (10, 5, 40)))
    clips.append(motion_clip(end_img, 3.5))
    end_line1 = TextClip(text="TO BE CONTINUED...", font=FONT, font_size=44, color="white", stroke_color="black", stroke_width=3, method="label").with_position(("center", H//2 - 30)).with_duration(3.5).with_start(total_dur - 3.5)
    end_line2 = TextClip(text="SUBSCRIBE FOR CHAPTER " + str(CHAPTER + 1), font=FONT, font_size=32, color="#FFCC00", stroke_color="black", stroke_width=2, method="label").with_position(("center", H//2 + 30)).with_duration(3.5).with_start(total_dur - 3.5)
    overlays.extend([end_line1, end_line2])

    # Comment prompt (halfway)
    comment_txt = TextClip(text="Comment what happens next  👇", font=FONT, font_size=28, color="white", stroke_color="black", stroke_width=2, method="label").with_position(("center", H - 300)).with_duration(2.5).with_start(total_dur * 0.5)
    overlays.append(comment_txt)

    bg = concatenate_videoclips(clips, method="compose")
    bh = int(H * 0.08)
    top = ColorClip(color=(0, 0, 0), size=(W, bh)).with_position((0, 0)).with_duration(bg.duration)
    bot = ColorClip(color=(0, 0, 0), size=(W, bh)).with_position((0, H - bh)).with_duration(bg.duration)

    final = CompositeVideoClip([bg, top, bot] + overlays, size=config.SHORTS_SIZE)
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
    final.write_videofile(str(out), fps=24, codec="libx264", audio_codec="aac", threads=4, preset="medium", logger=None)
    final.close()
    print(f"\n  DONE: {out}")

if __name__ == "__main__":
    main()
