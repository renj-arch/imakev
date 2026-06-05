"""Sketch-style explainer video — hand-drawn illustrations + narration-synced word captions.
Style inspired by AsapSCIENCE / whiteboard animation. Pure PIL, no external APIs."""

import sys, time, random, math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from moviepy import (
    VideoClip, AudioFileClip, ImageClip, TextClip,
    concatenate_videoclips, CompositeAudioClip, concatenate_audioclips,
    CompositeVideoClip,
)
import config
from src.engagement import hook_overlays, comment_prompt_overlay, subscribe_end_card, branding_overlays
from src.text_to_speech import generate_tts_with_timestamps
from src.sketch_artist import draw_sketch_for_phrase

W, H = config.VIDEO_WIDTH, config.VIDEO_HEIGHT
FPS = config.VIDEO_FPS
BRAND = config.BRAND_NAME
_BG = (250, 250, 245)
_STROKE = (30, 30, 30)
_HIGHLIGHT = (200, 80, 60)


def find_fact_word_range(fact: str, full_text: str, words: list[dict]) -> tuple[int, int]:
    import re
    fact_parts = [re.sub(r"[^\w\s'-]", "", w).lower().strip() for w in fact.split()]
    fact_parts = [w for w in fact_parts if w]
    all_parts = [re.sub(r"[^\w\s'-]", "", w["text"]).lower().strip() for w in words]
    for start in range(len(all_parts)):
        match = True
        for j, fw in enumerate(fact_parts):
            if start + j >= len(all_parts) or all_parts[start + j] != fw:
                match = False
                break
        if match:
            return start, start + len(fact_parts) - 1
    return 0, len(words) - 1


def extract_phrases(fact: str, max_phrases: int = 3) -> list[str]:
    import re
    normalized = fact.replace("\u2014", " ").replace("\u2013", " ").replace("  ", " ")
    for sep in [",", " but ", " and ", " because ", " while ", " which ", " that "]:
        parts = [p.strip().strip(".,!?;:'\"") for p in normalized.split(sep) if len(p.strip()) > 8]
        if len(parts) >= 2:
            return [p for p in parts[:max_phrases] if p]
    words = normalized.split()
    if len(words) > 6:
        mid = len(words) // 2
        return [" ".join(words[:mid]), " ".join(words[mid:])]
    return [fact]


def _get_font(size: int = 36):
    try:
        return ImageFont.truetype(config.get_font(), size)
    except:
        return ImageFont.load_default()


def draw_title_card(title: str) -> np.ndarray:
    img = Image.new("RGB", (W, H), _BG)
    draw = ImageDraw.Draw(img)
    font = _get_font(56)
    sub_font = _get_font(28)

    lines = []
    current = ""
    for w in title.split():
        test = (current + " " + w).strip()
        bb = draw.textbbox((0, 0), test, font=font)
        if bb[2] - bb[0] > W - 80:
            lines.append(current)
            current = w
        else:
            current = test
    lines.append(current)

    y = H // 2 - 80
    for line in lines:
        bb = draw.textbbox((0, 0), line, font=font)
        draw.text(((W - (bb[2] - bb[0])) // 2, y), line, font=font, fill=_STROKE)
        y += 70

    sub = "SWIPE FOR ILLUSTRATED FACTS"
    bb = draw.textbbox((0, 0), sub, font=sub_font)
    draw.text(((W - (bb[2] - bb[0])) // 2, H - 200), sub, font=sub_font, fill=_HIGHLIGHT)

    # Decorative line
    draw.line(_wobble([(W // 4, H - 240), (W * 3 // 4, H - 240)]), fill=_STROKE, width=2)

    return np.array(img)


def _wobble(points: list, strength: float = 1.5) -> list:
    return [(x + random.uniform(-1, 1) * strength, y + random.uniform(-1, 1) * strength) for x, y in points]


def render_marker_captions(frame: np.ndarray, fact_words: list[str], spoken_idx: int) -> np.ndarray:
    """Word-by-word captions in marker style — like AsapSCIENCE."""
    img = Image.fromarray(frame)
    draw = ImageDraw.Draw(img)
    font = _get_font(46)
    font_hl = _get_font(52)

    bar_h = 130
    overlay = Image.new("RGBA", (W, bar_h), (240, 238, 230, 200))
    img.paste(overlay, (0, H - bar_h - 30), overlay)

    # Top divider line
    draw.line(_wobble([(30, H - bar_h - 33), (W - 30, H - bar_h - 33)], 0.5), fill=_STROKE, width=2)

    y = H - bar_h + 15
    x = 35
    max_x = W - 35
    line_y = y

    for i, w in enumerate(fact_words):
        if i > spoken_idx:
            break
        is_current = (i == spoken_idx)
        f = font_hl if is_current else font
        color = _HIGHLIGHT if is_current else _STROKE
        display_w = " " + w + " "
        bb = draw.textbbox((0, 0), display_w, font=f)
        word_w = bb[2] - bb[0]
        if x + word_w > max_x:
            x = 35
            line_y += 58
        if is_current:
            # Underline current word
            draw.line(_wobble([(x, line_y + f.font.height), (x + word_w, line_y + f.font.height)], 0.5),
                      fill=_HIGHLIGHT, width=3)
        draw.text((x, line_y), display_w, font=f, fill=color)
        x += word_w

    return np.array(img)


def main():
    print("=" * 50)
    print("  SKETCH VIDEO — whiteboard style")
    print("=" * 50)

    from src.facts import generate_fact_script
    fact_data = generate_fact_script()
    TITLE = fact_data["title"]
    FACTS = fact_data["facts"]
    HOOK = fact_data["hook"]
    NICHE = fact_data.get("niche", "")

    temp_dir = config.TEMP_DIR / "sketch_video"
    temp_dir.mkdir(exist_ok=True)

    tts_script = fact_data.get("tts_script", f"{HOOK} {' '.join(FACTS)}")

    print("\n[1/5] Generating TTS with word timestamps...")
    tts_path = temp_dir / "narration.mp3"
    words = generate_tts_with_timestamps(tts_script, tts_path)
    total_dur = words[-1]["end"] if words else 5.0
    print(f"  {total_dur:.1f}s | {len(words)} words | {len(FACTS)} facts")

    print("\n[2/5] Extracting per-fact word ranges and phrases...")
    fact_infos = []
    for i, fact in enumerate(FACTS):
        w_start, w_end = find_fact_word_range(fact, tts_script, words)
        fact_start = words[w_start]["start"]
        fact_end = words[w_end]["end"]
        phrases = extract_phrases(fact, max_phrases=3)
        seg_dur = (fact_end - fact_start) / max(len(phrases), 1)
        segments = []
        for pi, phrase in enumerate(phrases):
            seg_start = fact_start + pi * seg_dur
            seg_end = seg_start + seg_dur if pi < len(phrases) - 1 else fact_end
            segments.append({"phrase": phrase, "start": seg_start, "end": seg_end, "image": None})
        fact_infos.append({
            "fact": fact,
            "word_start": w_start,
            "word_end": w_end,
            "start": fact_start,
            "end": fact_end,
            "segments": segments,
            "phrases": phrases,
        })

    print(f"\n[3/5] Drawing {sum(len(f['segments']) for f in fact_infos)} sketch illustrations...")
    for fi, fact_info in enumerate(fact_infos):
        for si, seg in enumerate(fact_info["segments"]):
            cached = temp_dir / f"s_{fi}_{si}.png"
            phrase = seg["phrase"]
            if cached.exists() and cached.stat().st_size > 5000:
                img = Image.open(cached)
            else:
                print(f"  Sketch {fi+1}/{len(FACTS)} phrase {si+1}: {phrase[:50]}...")
                img = draw_sketch_for_phrase(phrase, W, H)
                img.save(cached)
            seg["image"] = np.array(img.resize((W, H), Image.LANCZOS))
        fact_info["title_image"] = fact_info["segments"][0]["image"]

    print("\n[4/5] Rendering frames...")
    title_arr = draw_title_card(TITLE)

    def make_frame(t):
        # Title card
        if t < 1.0:
            p = min(t / 1.0, 1)
            alpha = int(255 * (p * p * (3 - 2 * p)))
            if alpha < 255:
                blank = np.full((H, W, 3), 245, dtype=np.uint8)
                result = blank * (255 - alpha) // 255 + title_arr * alpha // 255
                return result.astype(np.uint8)
            return title_arr

        # End card
        if t > total_dur:
            return np.full((H, W, 3), 248, dtype=np.uint8)

        # Find active fact and segment
        active_fact = None
        active_seg = None
        active_fact_idx = -1
        for fi, fi_data in enumerate(fact_infos):
            if fi_data["start"] <= t < fi_data["end"]:
                active_fact = fi_data
                active_fact_idx = fi
                for seg in fi_data["segments"]:
                    if seg["start"] <= t < seg["end"]:
                        active_seg = seg
                        break
                break

        if active_fact is None:
            for fi, fi_data in reversed(list(enumerate(fact_infos))):
                if t > fi_data["end"]:
                    active_fact = fi_data
                    active_seg = fi_data["segments"][-1]
                    break

        if active_fact is None or active_seg is None:
            return np.full((H, W, 3), 245, dtype=np.uint8)

        img_arr = active_seg["image"]
        frame = img_arr.copy()

        # Caption: words spoken so far
        fact_words = active_fact["fact"].split()
        spoken_idx = -1
        for wi in range(active_fact["word_start"], min(active_fact["word_end"] + 1, len(words))):
            if words[wi]["start"] <= t:
                spoken_idx = wi - active_fact["word_start"]
            else:
                break
        if spoken_idx >= 0:
            frame = render_marker_captions(frame, fact_words, spoken_idx)

        return frame

    video_dur = total_dur + 1.5
    bg_clip = VideoClip(make_frame, duration=video_dur)

    audio_clip = AudioFileClip(str(tts_path))
    if video_dur > audio_clip.duration:
        silence = AudioFileClip(str(tts_path)).with_duration(video_dur - audio_clip.duration).with_volume_scaled(0)
        audio_clip = concatenate_audioclips([audio_clip, silence])

    overlays = hook_overlays(1.8)
    overlays += comment_prompt_overlay(start_time=max(total_dur * 0.4, 0.5), duration=2.0)
    overlays += branding_overlays(bg_clip.duration)

    # End card
    end_arr = np.full((H, W, 3), 248, dtype=np.uint8)
    end_card = subscribe_end_card(end_arr, 1.5).with_start(total_dur)
    overlays.append(end_card)

    final = CompositeVideoClip([bg_clip] + overlays, size=config.SHORTS_SIZE)

    music_paths = list(config.MUSIC_DIR.glob("*.mp3"))
    if music_paths:
        music = AudioFileClip(str(random.choice(music_paths))).with_duration(video_dur).with_volume_scaled(0.06)
        final = final.with_audio(CompositeAudioClip([audio_clip, music]))
    else:
        final = final.with_audio(audio_clip)

    print(f"\n[5/5] Rendering video...")
    safe_title = TITLE.lower().replace(" ", "_").replace("?", "").replace("!", "").replace("'", "").replace(".", "").replace(",", "").replace(":", "")[:50]
    out = config.OUTPUT_DIR / f"sketch_{safe_title}.mp4"
    out.unlink(missing_ok=True)
    print(f"  {video_dur:.1f}s | {W}x{H} | {FPS}fps | {len(words)} word-timed segments")
    t0 = time.time()
    final.write_videofile(str(out), fps=FPS, codec="libx264", audio_codec="aac", threads=4, preset="medium", ffmpeg_params=["-movflags", "+faststart", "-crf", "18"], logger=None)
    final.close()
    t1 = time.time()
    print(f"\n  DONE in {t1-t0:.0f}s: {out}")
    print(f"  Size: {out.stat().st_size:,} bytes")

    return out, fact_data


if __name__ == "__main__":
    main()
