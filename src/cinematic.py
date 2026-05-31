import re, json, random
from pathlib import Path
from datetime import datetime
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import (
    ImageClip, TextClip, CompositeVideoClip, AudioFileClip,
    concatenate_videoclips, ColorClip, VideoClip,
)
import config


def _safe(text: str) -> str:
    return re.sub(r"[^\x00-\x7F]+", "", text) if text else ""


def _get_font(size: int = 50) -> str:
    custom = list(config.FONTS_DIR.glob("*.ttf")) + list(config.FONTS_DIR.glob("*.otf"))
    if custom:
        return str(custom[0])
    defaults = [
        r"C:\Windows\Fonts\impact.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    ]
    for p in defaults:
        if Path(p).exists():
            return p
    return "Arial"


def _make_gradient(w: int, h: int, colors: list[tuple]) -> np.ndarray:
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    n = len(colors)
    for y in range(h):
        idx = min(int(y / h * (n - 1)), n - 2)
        t = (y / h * (n - 1)) - idx
        r = int(colors[idx][0] * (1 - t) + colors[idx + 1][0] * t)
        g = int(colors[idx][1] * (1 - t) + colors[idx + 1][1] * t)
        b = int(colors[idx][2] * (1 - t) + colors[idx + 1][2] * t)
        arr[y, :] = [r, g, b]
    return arr


def _add_text_overlay(frame: np.ndarray, text: str, position: str = "bottom") -> np.ndarray:
    img = Image.fromarray(frame)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(_get_font(45), 45)
    except Exception:
        font = ImageFont.load_default()

    w, h = img.size
    lines = []
    words = text.split()
    line = ""
    for word in words:
        test = line + " " + word if line else word
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > w - 80:
            lines.append(line)
            line = word
        else:
            line = test
    if line:
        lines.append(line)

    total_h = len(lines) * 55
    if position == "bottom":
        y_start = h - total_h - 80
    else:
        y_start = 80

    y = y_start
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        x = (w - tw) // 2
        for dx, dy in [(-2,-2),(-2,2),(2,-2),(2,2)]:
            draw.text((x+dx, y+dy), line, font=font, fill=(0, 0, 0, 255))
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
        y += 55

    return np.array(img)


def break_story_into_scenes(story: str) -> list[dict]:
    from src.script_generator import _generate_gemini
    prompt = f"""Break this story into 5-8 visual scenes. For each scene, return:
- scene: short name
- visual: detailed visual description (for image generation)
- text: subtitle/overlay text for this scene (1-2 lines, dramatic)
- mood: color mood (neon/cyan-magenta/dark/cinematic/ethereal)

Story: {story}

Return as JSON list: [{{"scene": "...", "visual": "...", "text": "...", "mood": "..."}}]"""
    try:
        result = _generate_gemini(prompt, temperature=0.7, max_tokens=1000)
        result = re.sub(r"```json|```", "", result).strip()
        scenes = json.loads(result)
        return scenes if isinstance(scenes, list) else []
    except Exception as e:
        print(f"  Scene parsing error: {e}")
        return []


MOOD_COLORS = {
    "neon": [(10, 0, 30), (200, 0, 100), (0, 200, 200)],
    "cyan-magenta": [(20, 0, 40), (255, 0, 128), (0, 255, 255)],
    "dark": [(5, 5, 15), (30, 10, 40), (10, 10, 30)],
    "cinematic": [(20, 15, 10), (80, 60, 40), (40, 30, 20)],
    "ethereal": [(10, 20, 40), (100, 150, 200), (200, 220, 255)],
}
DEFAULT_MOOD = [(10, 0, 30), (200, 0, 100), (0, 200, 200)]


def generate_cinematic_video(story: str, output_path: Path, music_path: Path | None = None) -> Path:
    print(f"[1/4] Breaking story into scenes...")
    scenes = break_story_into_scenes(story)
    if not scenes:
        scenes = [
            {"scene": "Opening", "visual": story[:100], "text": "A cinematic journey begins", "mood": "cinematic"},
            {"scene": "Climax", "visual": story[100:200], "text": "The adventure unfolds", "mood": "neon"},
            {"scene": "Resolution", "visual": story[200:300], "text": "Everything comes together", "mood": "ethereal"},
        ]
    print(f"  Generated {len(scenes)} scenes")

    print(f"[2/4] Generating visuals for each scene...")
    w, h = config.SHORTS_SIZE
    clips = []
    scene_duration = max(3.0, 15.0 / len(scenes))

    for i, scene in enumerate(scenes):
        mood = scene.get("mood", "neon").lower()
        colors = MOOD_COLORS.get(mood, DEFAULT_MOOD)
        frame = _make_gradient(w, h, colors)

        text = scene.get("text", scene.get("scene", ""))
        frame = _add_text_overlay(frame, text, "bottom" if len(text) > 30 else "top")

        clip = ImageClip(frame).with_duration(scene_duration)
        clips.append(clip)

        print(f"  Scene {i+1}: {_safe(scene.get('scene', ''))}")

    print(f"[3/4] Adding cinematic audio...")
    final = concatenate_videoclips(clips, method="compose")
    total_duration = final.duration

    if music_path and music_path.exists():
        audio = AudioFileClip(str(music_path)).with_duration(total_duration)
        if audio.duration < total_duration:
            audio = audio.loop(duration=total_duration)
        final = final.with_audio(audio)
    else:
        music_files = list(config.MUSIC_DIR.glob("*.mp3")) + list(config.MUSIC_DIR.glob("*.wav"))
        if music_files:
            m = random.choice(music_files)
            audio = AudioFileClip(str(m)).with_duration(total_duration)
            if audio.duration < total_duration:
                audio = audio.loop(duration=total_duration)
            final = final.with_audio(audio)

    print(f"[4/4] Rendering final video...")
    final.write_videofile(
        str(output_path),
        fps=config.VIDEO_FPS,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="medium",
        logger=None,
    )

    final.close()
    print(f"\nDone! Video saved to: {output_path}")
    return output_path
