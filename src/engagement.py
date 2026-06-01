"""Shared hook, fast-motion, and visual retention utilities for all video types."""

import html, random, re, time
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import VideoClip, TextClip, CompositeVideoClip, ColorClip, ImageClip
import config

FONT = config.get_font()
W, H = config.VIDEO_WIDTH, config.VIDEO_HEIGHT
CHANNEL_NAME = "Dingdong"
CHANNEL_HANDLE = "@dingdong"

LOGO_PATH = Path(__file__).resolve().parent.parent / "dingdong_logo.png"

# Channel logo: load once and cache
_LOGO_CACHE = None
def _create_channel_logo(size: int = 120) -> np.ndarray:
    global _LOGO_CACHE
    if _LOGO_CACHE is not None:
        return _LOGO_CACHE
    if LOGO_PATH.exists():
        img = Image.open(LOGO_PATH).convert("RGBA")
        img = img.resize((size, size), Image.LANCZOS)
        _LOGO_CACHE = np.array(img)
        return _LOGO_CACHE
    return np.zeros((size, size, 4), dtype=np.uint8)


def branding_overlays(duration: float) -> list:
    """Full-duration channel branding: logo + subscribe bar at bottom."""
    logo = _create_channel_logo(70)
    logo_clip = ImageClip(logo, duration=duration, is_mask=False)
    logo_clip = logo_clip.with_position((W - 90, H - 110)).with_duration(duration).with_start(0.0)
    name = TextClip(text=CHANNEL_HANDLE, font=FONT, font_size=14, color="#FFCC00",
                    stroke_color="black", stroke_width=1, method="label")
    name = name.with_position((W - 87, H - 32)).with_duration(duration).with_start(0.0)
    return [logo_clip, name]


def channel_watermark_overlay(duration: float) -> list:
    """Channel logo watermark in bottom-right throughout video."""
    logo = _create_channel_logo(80)
    logo_clip = ImageClip(logo, duration=duration, is_mask=False)
    logo_clip = logo_clip.with_position((W - 100, H - 120)).with_duration(duration).with_start(0.0)
    name = TextClip(text=CHANNEL_HANDLE, font=FONT, font_size=16, color="#FFCC00",
                    stroke_color="black", stroke_width=1, method="label")
    name = name.with_position((W - 95, H - 35)).with_duration(duration).with_start(0.0)
    return [logo_clip, name]


def hook_overlays(duration: float = 2.0) -> list:
    """Return eye-catching hook overlay clips for the first few seconds."""
    hooks = [
        ("⚠️ WATCH TILL THE END", "#FF4444"),
        ("👀 THIS IS CRAZY", "#FFCC00"),
        ("😱 YOU WON'T BELIEVE THIS", "#FF6600"),
        ("🔥 MIND-BLOWING", "#00FF88"),
        ("💥 WAIT FOR IT", "#FF00FF"),
    ]
    text, color = random.choice(hooks)
    main = TextClip(text=text, font=FONT, font_size=52, color=color,
                    stroke_color="black", stroke_width=3, method="label")
    main = main.with_position(("center", H // 2 - 60)).with_duration(duration).with_start(0.0)

    sub = TextClip(text="swipe up for more ▶", font=FONT, font_size=26, color="white",
                   stroke_color="black", stroke_width=2, method="label")
    sub = sub.with_position(("center", H // 2 + 10)).with_duration(duration).with_start(0.0)

    # Bottom bar "SUBSCRIBE" teaser
    bar_arr = np.zeros((50, W, 3), dtype=np.uint8)
    bar = ImageClip(bar_arr, duration=duration).with_position((0, H - 50)).with_start(0.0).with_opacity(0.7)
    sub_text = TextClip(text="🔔 SUBSCRIBE FOR MORE", font=FONT, font_size=22, color="#FFCC00",
                        stroke_color="black", stroke_width=1, method="label")
    sub_text = sub_text.with_position(("center", H - 42)).with_duration(duration).with_start(0.0)
    return [main, sub, bar, sub_text]


def fast_motion(img_array: np.ndarray, dur: float, shake: bool = False, intensity: float = 1.0) -> VideoClip:
    """Create a fast-zoom Ken Burns clip from a numpy array or PIL Image."""
    from PIL import Image
    if isinstance(img_array, Image.Image):
        w, h = img_array.size
    else:
        h, w = img_array.shape[:2]

    def f(t):
        p = t / dur if dur > 0 else 1
        scale = 1.0 + p * 0.18 * intensity
        cw, ch = int(w / scale), int(h / scale)
        if shake:
            sx = int(np.sin(p * 50) * cw * 0.03 * intensity)
            sy = int(np.cos(p * 45) * ch * 0.03 * intensity)
        else:
            sx = sy = 0
        ox = max(0, min((w - cw) // 2 + sx, w - cw))
        oy = max(0, min((h - ch) // 2 + sy, h - ch))
        arr = img_array if isinstance(img_array, np.ndarray) else np.array(img_array)
        return arr[oy:oy + ch, ox:ox + cw].copy()
    return VideoClip(lambda t: f(t), duration=dur)


def countdown_overlay(start_time: float, duration: float = 2.0) -> list:
    """Floating countdown bar that creates urgency."""
    count_text = TextClip(text="⏱ Only 30 seconds!", font=FONT, font_size=28, color="#FFCC00",
                          stroke_color="black", stroke_width=2, method="label")
    count_text = count_text.with_position((10, 100)).with_duration(duration).with_start(start_time)
    return [count_text]


def comment_prompt_overlay(start_time: float, duration: float = 2.5) -> list:
    """Prompt asking viewers to comment."""
    prompts = [
        "Comment what you think 👇",
        "Type your answer below 💬",
        "Which one surprised you? ⬇️",
        "Drop a fact in the comments 🗣️",
        "Did you know this? Comment! 💭",
    ]
    text = random.choice(prompts)
    txt = TextClip(text=text, font=FONT, font_size=28, color="white",
                   stroke_color="black", stroke_width=2, method="label")
    txt = txt.with_position(("center", H - 250)).with_duration(duration).with_start(start_time)
    return [txt]


def add_watermark(video_path: str) -> str:
    """Post-process: add channel watermark to rendered video using ffmpeg overlay."""
    import subprocess, os
    from pathlib import Path
    p = Path(video_path)
    out_path = str(p.with_stem(p.stem + "_branded"))
    logo = _create_channel_logo(100)
    logo_path = str(p.parent / "_watermark.png")
    Image.fromarray(logo).save(logo_path)
    cmd = [
        "ffmpeg", "-i", video_path, "-i", logo_path,
        "-filter_complex", "[0:v][1:v]overlay=W-w-20:H-h-20:format=auto",
        "-codec:a", "copy", "-y", out_path
    ]
    subprocess.run(cmd, capture_output=True, timeout=120)
    if Path(out_path).exists():
        os.replace(out_path, video_path)
    if Path(logo_path).exists():
        Path(logo_path).unlink()
    return video_path


def text_to_ssml(text: str) -> str:
    """Convert plain text to expressive SSML with emphasis, pauses, and pitch variation."""
    safe = html.escape(text)
    parts = re.split(r'([.?!]+)', safe)
    ssml_parts = []
    for i in range(0, len(parts) - 1, 2):
        sentence = parts[i].strip()
        punct = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if not sentence:
            continue
        pitch_var = random.choice(["+0%", "+5%", "+8%", "-3%", "+3%", "-5%"])
        rate_var = random.choice(["+0%", "+5%", "+10%", "-5%", "+8%"])
        words = sentence.split()
        if len(words) >= 3:
            first = " ".join(words[:2])
            rest = " ".join(words[2:])
            ssml_sentence = f"<emphasis level='moderate'>{first}</emphasis> {rest}{punct}"
        else:
            ssml_sentence = f"{sentence}{punct}"
        if "?" in punct:
            ssml_sentence = ssml_sentence.replace("?", "<break time='0.4s'/>?")
        if "!" in punct:
            ssml_sentence = ssml_sentence.replace("!", "<break time='0.3s'/>!")
        ssml_parts.append(
            f"<prosody pitch='{pitch_var}' rate='{rate_var}'>{ssml_sentence}</prosody>"
        )
    ssml = "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'>"
    ssml += " ".join(ssml_parts)
    ssml += "<break time='0.8s'/></speak>"
    return ssml


def _verify_mp3(path: Path) -> bool:
    """Check file has valid MP3 header (ID3 tag or MPEG frame sync)."""
    if path.stat().st_size < 500:
        return False
    data = path.read_bytes()[:4]
    if data[:2] == b"ID":
        return True
    if data[0] == 0xff and (data[1] & 0xe0) == 0xe0:
        return True
    return False


def generate_voiceover_ssml(script: str, voice: str, tts_path: str, timeout: int = 120):
    """Generate TTS using edge_tts with SSML for expressiveness. Retries on failure."""
    import subprocess, sys
    temp_ssml = Path(str(tts_path) + ".ssml")
    ssml = text_to_ssml(script)
    temp_ssml.write_text(ssml, encoding="utf-8")

    for attempt in range(3):
        try:
            subprocess.run(
                [sys.executable, "-m", "edge_tts", "--file", str(temp_ssml),
                 "--voice", voice, "--write-media", str(tts_path)],
                capture_output=True, text=True, timeout=timeout, check=True
            )
            if _verify_mp3(Path(tts_path)):
                temp_ssml.unlink(missing_ok=True)
                return True
            print(f"  SSML attempt {attempt+1}: invalid MP3, retrying...")
        except Exception as e:
            print(f"  SSML attempt {attempt+1} failed ({e}), retrying...")
        time.sleep(1)

    # Fallback to plain text
    print("  SSML failed, falling back to plain edge_tts")
    for attempt in range(3):
        try:
            subprocess.run(
                [sys.executable, "-m", "edge_tts", "--text", script,
                 "--voice", voice, "--write-media", str(tts_path)],
                capture_output=True, text=True, timeout=timeout, check=True
            )
            if _verify_mp3(Path(tts_path)):
                return True
            print(f"  Plain TTS attempt {attempt+1}: invalid MP3, retrying...")
        except Exception as e:
            print(f"  Plain TTS attempt {attempt+1} failed ({e}), retrying...")
        time.sleep(1)

    raise RuntimeError("edge_tts failed to generate valid MP3 after 6 attempts")


def pad_audio_to_61s(tts_path: str) -> float:
    """Stretch TTS audio to at least 61s via resampling for long-form ad revenue. Returns duration."""
    from moviepy import AudioFileClip, AudioClip
    import numpy as np
    audio = AudioFileClip(tts_path)
    dur = audio.duration
    if dur < 61 and dur > 5:
        samples = audio.to_soundarray(fps=22050)
        if samples.ndim == 1:
            samples = samples[:, None]
        target_frames = int(22050 * 61)
        orig_frames = samples.shape[0]
        x = np.arange(orig_frames)
        xp = np.linspace(0, orig_frames - 1, target_frames)
        stretched = np.column_stack([np.interp(xp, x, samples[:, ch]) for ch in range(samples.shape[1])])
        stretched_clip = AudioClip(lambda t: stretched[int(t * 22050) % target_frames], duration=61, fps=22050)
        stretched_clip.write_audiofile(str(tts_path), fps=22050, logger=None)
        dur = 61
        print(f"  Stretched {audio.duration:.1f}s → 61s (long-form minimum)")
    audio.close()
    return dur


def subscribe_end_card(img_array, duration: float = 1.5) -> VideoClip:
    """End card with subscribe appeal on given image."""
    clip = fast_motion(img_array, duration, shake=False, intensity=0.6)
    dim = np.zeros((H, W, 3), dtype=np.uint8)
    dim.fill(20)
    dark = ImageClip(dim, duration=duration).with_opacity(0.6)
    txt1 = TextClip(text="SUBSCRIBE 🔔", font=FONT, font_size=52, color="#FFCC00",
                    stroke_color="black", stroke_width=3, method="label")
    txt1 = txt1.with_position(("center", H // 2 - 40)).with_duration(duration)
    txt2 = TextClip(text="FOR DAILY SHORTS", font=FONT, font_size=30, color="white",
                    stroke_color="black", stroke_width=2, method="label")
    txt2 = txt2.with_position(("center", H // 2 + 20)).with_duration(duration)
    return CompositeVideoClip([clip, dark, txt1, txt2], size=config.SHORTS_SIZE)
