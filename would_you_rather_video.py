"""Would You Rather Shorts — image + baked text + TTS + music."""

import sys, subprocess, time, io, random
from pathlib import Path
from PIL import Image, ImageEnhance, ImageDraw, ImageFont
import numpy as np
import requests as req
from moviepy import VideoClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip
import config
from src.would_you_rather import generate_wyr_script

FONT_PATH = config.get_font()
W, H = config.VIDEO_WIDTH, config.VIDEO_HEIGHT


def gen_img(prompt):
    url = f"https://image.pollinations.ai/prompt/{req.utils.quote(prompt)}?width={W}&height={H}&nofeed=true&seed={random.randint(0,999999)}&model=flux"
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


def make_intro(img, hook):
    img = img.copy()
    overlay = Image.new("RGBA", (W, int(H*0.25)), (0,0,0,160))
    img.paste(overlay, (0, H-int(H*0.25)), overlay)
    draw_text(img, "WOULD YOU RATHER?", 52, H-180, center=True, color=(255,204,0))
    draw_text(img, hook.upper(), 32, H-100, center=True)
    return img


def make_choice_card(img, side, option, color):
    img = img.copy()
    overlay = Image.new("RGBA", (W, int(H*0.35)), (0,0,0,180))
    img.paste(overlay, (0, H-int(H*0.35)), overlay)
    draw_text(img, side, 44, H-380, center=True, color=color)
    draw_text(img, option.upper(), 36, H-290, center=True)
    return img


def make_split_card(img, a, b):
    img = img.copy()
    overlay = Image.new("RGBA", (W, H), (0,0,0,100))
    img.paste(overlay, (0,0), overlay)
    split = Image.new("RGBA", (1, H), (255,255,255,40))
    img.paste(split, (W//2, 0), split)
    draw_text(img, "A", 60, 80, center=False, x=W//4-30, color=(255,200,0))
    draw_text(img, a.upper(), 30, 160, center=False, x=20)
    draw_text(img, "B", 60, 80, center=False, x=3*W//4-30, color=(100,200,255))
    draw_text(img, b.upper(), 30, 160, center=False, x=W//2+20)
    draw_text(img, "WHICH ONE? COMMENT BELOW", 24, H-100, center=True, color=(255,200,0))
    return img


def make_end_card(img):
    img = img.copy()
    overlay = Image.new("RGBA", (W, H), (0,0,0,120))
    img.paste(overlay, (0,0), overlay)
    draw_text(img, "SUBSCRIBE", 60, H//2 - 60, center=True, color=(255,204,0))
    draw_text(img, "FOR MORE WOULD YOU RATHER", 32, H//2 + 20, center=True)
    return img


def motion_clip(img, dur):
    w, h = img.size
    def f(t):
        p = t / dur if dur > 0 else 1
        scale = 1.0 + p * 0.04
        cw, ch = int(w/scale), int(h/scale)
        ox, oy = (w-cw)//2, (h-ch)//2
        return np.array(img.crop((ox, oy, ox+cw, oy+ch)).resize((w,h), Image.LANCZOS))
    return VideoClip(f, duration=dur)


def main():
    print("="*50)
    print("  WOULD YOU RATHER GENERATOR")
    print("="*50)

    data = generate_wyr_script()
    A = data["option_a"]
    B = data["option_b"]
    HOOK = data["hook"]

    temp_dir = config.TEMP_DIR / "wyr"
    temp_dir.mkdir(exist_ok=True)

    print("\n[1/4] Voiceover...")
    tts_text = f"{HOOK} {A} or {B}. Which one would you choose? Comment below!"
    tts_path = temp_dir / "narration.mp3"
    subprocess.run([sys.executable, "-m", "edge_tts", "--text", tts_text, "--voice", "en-US-GuyNeural", "--write-media", str(tts_path)], capture_output=True, text=True, timeout=120, check=True)
    audio = AudioFileClip(str(tts_path))
    total_dur = audio.duration
    audio.close()
    dur_a = total_dur * 0.35
    dur_b = total_dur * 0.35
    dur_split = total_dur * 0.3
    print(f"  {total_dur:.1f}s")

    print("\n[2/4] Generating image...")
    cached = temp_dir / "bg.png"
    if cached.exists() and cached.stat().st_size > 50000:
        img = Image.open(cached)
    else:
        print("  Background...", end=" ", flush=True)
        prompt = f"vibrant colorful abstract background, two paths diverging, decision concept, bright cheerful, 9:16 vertical, {random.choice(['warm tones', 'cool tones', 'neon colors', 'pastel gradient'])}"
        img = gen_img(prompt)
        if img:
            img = upscale(img)
            img.save(cached)
            print("OK")
        else:
            print("fallback")
            arr = np.zeros((H, W, 3), dtype=np.uint8)
            for y in range(H):
                arr[y,:] = [int(40+100*(y/H)), int(80+60*(1-y/H)), int(160+80*(y/H))]
            img = Image.fromarray(arr)

    print("\n[3/4] Baking text...")
    intro = make_intro(img.copy(), HOOK)
    option_a = make_choice_card(img.copy(), "OPTION A", A, (255,200,0))
    option_b = make_choice_card(img.copy(), "OPTION B", B, (100,200,255))
    split = make_split_card(img.copy(), A, B)
    end = make_end_card(img.copy())

    clips = [
        motion_clip(intro, 1.5),
        motion_clip(option_a, dur_a),
        motion_clip(option_b, dur_b),
        motion_clip(split, dur_split),
        motion_clip(end, 2.0),
    ]
    final = concatenate_videoclips(clips, method="compose")
    audio_clip = AudioFileClip(str(tts_path))

    music_paths = list(config.MUSIC_DIR.glob("*.mp3"))
    if music_paths:
        music = AudioFileClip(str(random.choice(music_paths))).with_duration(final.duration).with_volume_scaled(0.06)
        final = final.with_audio(CompositeAudioClip([audio_clip, music]))
    else:
        final = final.with_audio(audio_clip)

    print("\n[4/4] Rendering...")
    safe_title = f"wyr_{A[:20].lower().replace(' ','_')}"
    out = config.OUTPUT_DIR / f"{safe_title}.mp4"
    out.unlink(missing_ok=True)
    print(f"  {final.duration:.1f}s | {W}x{H}")
    t0 = time.time()
    final.write_videofile(str(out), fps=config.VIDEO_FPS, codec="libx264", audio_codec="aac", threads=4, preset="ultrafast", ffmpeg_params=["-movflags", "+faststart"], logger=None)
    final.close()
    t1 = time.time()
    print(f"\n  DONE in {t1-t0:.0f}s: {out}")
    return out, data


if __name__ == "__main__":
    main()
