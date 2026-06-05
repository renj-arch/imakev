"""Storyboard video — narrative scenes with AI-illustrated frames.
Each narration sentence gets a custom 2D illustrated scene generated via Pollinations.
Style: simple 2D illustration, flat vector art, storyboard / explainer style."""

import sys, time, random, io, json, re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from moviepy import (
    VideoClip, AudioFileClip, CompositeAudioClip, concatenate_audioclips,
    CompositeVideoClip,
)
import config
from src.engagement import subscribe_end_card
from src.text_to_speech import generate_tts_with_timestamps

W, H = config.VIDEO_WIDTH, config.VIDEO_HEIGHT
FPS = config.VIDEO_FPS
_BG = (250, 250, 245)
_STROKE = (30, 30, 30)
_HIGHLIGHT = (200, 80, 60)


def _get_font(size: int = 36):
    try:
        return ImageFont.truetype(config.get_font(), size)
    except:
        return ImageFont.load_default()


def _generate_script(topic: str = "") -> dict:
    """Use OpenRouter LLM to generate a narrative story with scene descriptions."""
    from src.script_generator import _generate
    if not topic:
        topics = ["how humans accidentally created dogs", "how the microwave was discovered by accident",
                  "why the sky is blue", "how trees talk to each other", "why we dream",
                  "how coffee changed the world", "how money was invented",
                  "why cats purr", "how vaccines work", "why the ocean is salty"]
        topic = random.choice(topics)

    prompt = f"""Write a 30-second educational story about: {topic}

Write exactly 5 short narrative sentences. Each sentence should flow naturally into the next.

For each sentence, ALSO write a visual scene description for a simple 2D illustration.

Format EXACTLY like this (separate each scene with ---):

SCENE 1
NARRATION: [short narrative sentence, 6-12 words]
ILLUSTRATION: [description of a simple 2D drawing that illustrates this sentence, include colors, characters, setting, mood]

---

SCENE 2
NARRATION: [next sentence]
ILLUSTRATION: [next scene description]

---

etc for all 5 scenes.

Make the illustrations:
- Simple 2D flat style, like a children's book
- Include relevant characters, objects, background
- Night sky with moon and stars if the scene is at night
- Use clear visual metaphors
- Warm, friendly color palette"""

    system = "You write short educational narratives with matching visual scene descriptions for simple 2D illustrations."
    raw = _generate(prompt, temperature=0.8, max_tokens=2000, system=system)

    if not raw:
        return _fallback_script(topic)

    scenes = []
    current = {}
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("SCENE"):
            if current.get("narration") and current.get("illustration"):
                scenes.append(current)
            current = {}
        elif line.startswith("NARRATION:"):
            current["narration"] = line[len("NARRATION:"):].strip()
        elif line.startswith("ILLUSTRATION:"):
            current["illustration"] = line[len("ILLUSTRATION:"):].strip()

    if current.get("narration") and current.get("illustration"):
        scenes.append(current)

    if len(scenes) < 3:
        return _fallback_script(topic)

    title = f"The Story of {topic}"
    hook = f"Here's something amazing about {topic}..."
    tts_parts = [s["narration"] for s in scenes]
    prompts = [s["illustration"] for s in scenes]

    return {
        "title": title[:70],
        "niche": topic,
        "hook": hook,
        "scenes": scenes,
        "narration": tts_parts,
        "prompts": prompts,
        "tts_script": " ".join(tts_parts),
    }


def _fallback_script(topic: str) -> dict:
    """Fallback when LLM is unavailable."""
    fallbacks = {
        "dogs": [
            {"narration": "Nobody sat around a fire 150,000 years ago and thought about turning wolves into pets.",
             "illustration": "Simple 2D illustration of a caveman sitting on a rock beside a campfire under a starry night sky with moon and stars. The caveman has a dream bubble showing a wolf with a red X mark over it."},
            {"narration": "There was no plan, no selective breeding program, no intention at all.",
             "illustration": "A simple notepad or scroll with text scribbled on it and a big red X mark across everything, floating on a warm beige background."},
            {"narration": "But today there are over 900 million dogs on Earth in hundreds of varieties.",
             "illustration": "Simple globe showing continents with many tiny dog sketches in different shapes and sizes floating around it, colorful and playful style."},
            {"narration": "It happened because wolves that were less afraid of humans stuck around for food scraps.",
             "illustration": "A simple drawing of a wolf standing at the edge of a human settlement, with a small pile of bones near it, moonlight illuminating the scene."},
            {"narration": "Gentler wolves bred with gentler wolves, and over thousands of years, wolves became dogs.",
             "illustration": "A timeline showing a wolf transforming into a dog through several stages, with a heart symbol connecting them, simple evolution style."},
        ]
    }
    key = topic.lower().split()[0] if topic else "dogs"
    scenes = fallbacks.get(key, fallbacks["dogs"])
    title = f"The Story of How {topic.capitalize()} Happened"
    return {
        "title": title[:70],
        "niche": topic,
        "hook": f"Here's the surprising story of {topic}...",
        "scenes": scenes,
        "narration": [s["narration"] for s in scenes],
        "prompts": [s["illustration"] for s in scenes],
        "tts_script": " ".join(s["narration"] for s in scenes),
    }


def _generate_scene_image(prompt: str, w: int, h: int, cache_path: Path) -> Image.Image | None:
    """Generate a 2D illustration scene using Pollinations AI."""
    if cache_path.exists() and cache_path.stat().st_size > 5000:
        return Image.open(cache_path)

    style_prompt = f"simple 2D flat vector illustration, children's book style, colorful, clean: {prompt}"

    from src.image_gen import _try_pollinations
    img = _try_pollinations(style_prompt, w, h, "flux")
    if img is None:
        img = _try_pollinations(style_prompt, w, h, "turbo")
    if img is None:
        img = _try_pollinations(style_prompt, w, h, "sana")
    if img is None:
        img = _try_pollinations(style_prompt, w, h, "gptimage")

    if img:
        img.save(cache_path)
        return img
    return None


def _get_fallback_canvas(w: int, h: int, prompt: str) -> Image.Image:
    """Gradient background with prompt text when image generation fails."""
    img = Image.new("RGB", (w, h), (250, 250, 245))
    draw = ImageDraw.Draw(img)
    for i in range(h):
        t = i / h
        r = int(250 - t * 20)
        g = int(250 - t * 15)
        b = int(245 - t * 25)
        draw.line([(0, i), (w, i)], fill=(r, g, b))
    font = _get_font(24)
    words = prompt.split()[:8]
    text = " ".join(words)
    bb = draw.textbbox((0, 0), text, font=font)
    draw.text(((w - (bb[2] - bb[0])) // 2, h // 2 - 30), text, font=font, fill=(100, 100, 100))
    return img


def render_caption(frame: np.ndarray, words_in_fact: list[str], spoken_idx: int) -> np.ndarray:
    """Overlay word-by-word caption at the bottom."""
    img = Image.fromarray(frame)
    draw = ImageDraw.Draw(img)
    font = _get_font(32)

    if not words_in_fact or spoken_idx < 0:
        return np.array(img)

    bar_h = 70
    overlay = Image.new("RGBA", (W, bar_h), (0, 0, 0, 160))
    img.paste(overlay, (0, H - bar_h - 10), overlay)

    display = []
    for i, w in enumerate(words_in_fact[:spoken_idx + 1]):
        color = _HIGHLIGHT if i == spoken_idx else (255, 255, 255)
        display.append((w, color))

    x = 20
    y = H - bar_h + 15
    for w, color in display:
        bb = draw.textbbox((0, 0), " " + w + " ", font=font)
        ww = bb[2] - bb[0]
        if x + ww > W - 20:
            x = 20
            y += 38
        draw.text((x, y), " " + w + " ", font=font, fill=color)
        x += ww

    return np.array(img)


def find_word_range(text: str, full_text: str, words: list[dict]) -> tuple[int, int]:
    cleaned = re.sub(r"[^\w\s'-]", "", text).lower().strip()
    cleaned_words = [w for w in cleaned.split() if w]
    all_cleaned = [re.sub(r"[^\w\s'-]", "", w["text"]).lower().strip() for w in words]
    for start in range(len(all_cleaned)):
        match = True
        for j, fw in enumerate(cleaned_words):
            if start + j >= len(all_cleaned) or all_cleaned[start + j] != fw:
                match = False
                break
        if match:
            return start, start + len(cleaned_words) - 1
    return 0, len(words) - 1


def main():
    print("=" * 50)
    print("  STORYBOARD VIDEO — illustrated narrative scenes")
    print("=" * 50)

    topic = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    script_data = _generate_script(topic)
    TITLE = script_data["title"]
    SCENES = script_data["scenes"]
    PROMPTS = script_data["prompts"]
    NARRATIONS = script_data["narration"]
    NICHE = script_data.get("niche", "")

    if not SCENES:
        print("No scenes generated!")
        return None, script_data

    print(f"  Topic: {script_data['niche']}")
    print(f"  Scenes: {len(SCENES)}")

    temp_dir = config.TEMP_DIR / "storyboard"
    temp_dir.mkdir(exist_ok=True)

    print("\n[1/5] Generating TTS with word timestamps...")
    tts_script = " ".join(NARRATIONS)
    tts_path = temp_dir / "narration.mp3"
    words = generate_tts_with_timestamps(tts_script, tts_path)
    total_dur = words[-1]["end"] if words else 5.0
    print(f"  {total_dur:.1f}s | {len(words)} words | {len(SCENES)} scenes")

    print("\n[2/5] Generating scene illustrations via Pollinations...")
    scene_images = []
    for i, scene in enumerate(SCENES):
        prompt = scene.get("illustration", scene.get("prompt", ""))
        cache = temp_dir / f"scene_{i}.png"
        print(f"  Scene {i+1}/{len(SCENES)}: {scene['narration'][:50]}...")
        img = _generate_scene_image(prompt, W, H, cache)
        if img is None:
            print(f"    Pollinations failed, using fallback")
            img = _get_fallback_canvas(W, H, prompt)
        scene_images.append(np.array(img.resize((W, H), Image.LANCZOS)))

    print("\n[3/5] Building timeline...")
    scene_timeline = []
    for i, scene in enumerate(SCENES):
        w_start, w_end = find_word_range(scene["narration"], tts_script, words)
        s_start = words[w_start]["start"]
        s_end = words[w_end]["end"]
        scene_timeline.append({
            "narration": scene["narration"],
            "start": s_start,
            "end": s_end,
            "word_start": w_start,
            "word_end": w_end,
            "image": scene_images[i],
        })

    print("\n[4/5] Rendering...")
    empty_bg = np.full((H, W, 3), 245, dtype=np.uint8)

    def make_frame(t):
        # Title card
        if t < 1.5:
            p = min(t / 1.5, 1)
            img = Image.new("RGB", (W, H), _BG)
            draw = ImageDraw.Draw(img)
            font = _get_font(48)
            lines = []
            current = ""
            for w in TITLE.split():
                test = (current + " " + w).strip()
                bb = draw.textbbox((0, 0), test, font=font)
                if len(test) > 25 or (bb[2] - bb[0] > W - 80 and current):
                    lines.append(current)
                    current = w
                else:
                    current = test
            lines.append(current)
            y = H // 2 - 60
            for line in lines:
                bb = draw.textbbox((0, 0), line, font=font)
                draw.text(((W - (bb[2] - bb[0])) // 2, y), line, font=font, fill=_STROKE)
                y += 65
            result = np.array(img)
            if p < 1:
                alpha = int(255 * (p * p * (3 - 2 * p)))
                result = (empty_bg * (255 - alpha) + result * alpha) // 255
            return result.astype(np.uint8)

        # End card
        if t > total_dur:
            return empty_bg

        # Find active scene
        active = None
        for s in scene_timeline:
            if s["start"] <= t < s["end"]:
                active = s
                break
        if active is None:
            for s in reversed(scene_timeline):
                if t > s["end"]:
                    active = s
                    break
        if active is None:
            return empty_bg

        frame = active["image"].copy()

        # Caption
        fact_words = active["narration"].split()
        spoken_idx = -1
        for wi in range(active["word_start"], min(active["word_end"] + 1, len(words))):
            if words[wi]["start"] <= t:
                spoken_idx = wi - active["word_start"]
            else:
                break
        if spoken_idx >= 0:
            frame = render_caption(frame, fact_words, spoken_idx)

        return frame

    video_dur = total_dur + 1.5
    bg_clip = VideoClip(make_frame, duration=video_dur)

    audio_clip = AudioFileClip(str(tts_path))
    if video_dur > audio_clip.duration:
        silence = AudioFileClip(str(tts_path)).with_duration(video_dur - audio_clip.duration).with_volume_scaled(0)
        audio_clip = concatenate_audioclips([audio_clip, silence])

    end_card = subscribe_end_card(np.full((H, W, 3), 245, dtype=np.uint8), 1.5)
    end_card = end_card.with_start(total_dur)

    final = CompositeVideoClip([bg_clip, end_card], size=config.SHORTS_SIZE)

    music_paths = list(config.MUSIC_DIR.glob("*.mp3"))
    if music_paths:
        music = AudioFileClip(str(random.choice(music_paths))).with_duration(video_dur).with_volume_scaled(0.04)
        final = final.with_audio(CompositeAudioClip([audio_clip, music]))
    else:
        final = final.with_audio(audio_clip)

    print(f"\n[5/5] Rendering video...")
    safe = TITLE.lower().replace(" ", "_").replace("?", "").replace("!", "").replace("'", "").replace(".", "").replace(",", "").replace(":", "")[:50]
    out = config.OUTPUT_DIR / f"story_{safe}.mp4"
    out.unlink(missing_ok=True)
    print(f"  {video_dur:.1f}s | {W}x{H} | {FPS}fps | {len(SCENES)} scenes")
    t0 = time.time()
    final.write_videofile(str(out), fps=FPS, codec="libx264", audio_codec="aac", threads=4, preset="medium", ffmpeg_params=["-movflags", "+faststart", "-crf", "18"], logger=None)
    final.close()
    t1 = time.time()
    print(f"\n  DONE in {t1-t0:.0f}s: {out}")
    print(f"  Size: {out.stat().st_size:,} bytes")

    return out, script_data


if __name__ == "__main__":
    main()
