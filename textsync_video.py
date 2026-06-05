"""Clean text-sync video — words appear as spoken, whiteboard style.
Pure text on white background, synced to narration word-by-word."""

import sys, time, random
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


def render_frame(words_in_fact: list[str], spoken_idx: int) -> np.ndarray:
    """Large centered text, current word highlighted, all previous visible."""
    img = Image.new("RGB", (W, H), _BG)
    draw = ImageDraw.Draw(img)

    if not words_in_fact or spoken_idx < 0:
        return np.array(img)

    font = _get_font(52)
    font_hl = _get_font(60)
    lh = 68

    # Build the text string up to spoken word, with a marker around current
    display_parts = []
    for i, w in enumerate(words_in_fact):
        if i < spoken_idx:
            display_parts.append((w, False))
        elif i == spoken_idx:
            display_parts.append((w, True))
        else:
            break

    # Lay out into centered lines
    lines = []  # each: list of (word, is_highlight)
    current_line = []
    current_is_hl = False
    for w, is_hl in display_parts:
        test_line = " ".join([x[0] for x in current_line] + [w])
        f = font_hl if is_hl else font
        bb = draw.textbbox((0, 0), test_line, font=f)
        if bb[2] - bb[0] > W - 60 and current_line:
            lines.append(current_line)
            current_line = [(w, is_hl)]
        else:
            current_line.append((w, is_hl))
    if current_line:
        lines.append(current_line)

    total_h = len(lines) * lh
    y = (H - total_h) // 2 - 60

    for line_parts in lines:
        # Build full line text to measure width
        line_text = " ".join(w for w, _ in line_parts)
        bb = draw.textbbox((0, 0), line_text, font=font)
        x = (W - (bb[2] - bb[0])) // 2

        cx = x
        for w, is_hl in line_parts:
            f = font_hl if is_hl else font
            color = _HIGHLIGHT if is_hl else _STROKE
            if is_hl:
                draw.text((cx, y - 4), w, font=f, fill=color)
            else:
                draw.text((cx, y), w, font=f, fill=color)
            bw = draw.textbbox((0, 0), w, font=f)
            cx += bw[2] - bw[0] + draw.textbbox((0, 0), " ", font=font)[2] - draw.textbbox((0, 0), " ", font=font)[0]
        y += lh

    return np.array(img)


def main():
    print("=" * 50)
    print("  TEXT-SYNC VIDEO — words appear as spoken")
    print("=" * 50)

    from src.facts import generate_fact_script
    fact_data = generate_fact_script()
    TITLE = fact_data["title"]
    FACTS = fact_data["facts"]
    HOOK = fact_data["hook"]

    temp_dir = config.TEMP_DIR / "textsync_video"
    temp_dir.mkdir(exist_ok=True)

    tts_script = fact_data.get("tts_script", f"{HOOK} {' '.join(FACTS)}")

    print("\n[1/4] Generating TTS with word timestamps...")
    tts_path = temp_dir / "narration.mp3"
    words = generate_tts_with_timestamps(tts_script, tts_path)
    total_dur = words[-1]["end"] if words else 5.0
    print(f"  {total_dur:.1f}s | {len(words)} words | {len(FACTS)} facts")

    print("\n[2/4] Extracting per-fact word ranges...")
    fact_infos = []
    for fact in FACTS:
        w_start, w_end = find_fact_word_range(fact, tts_script, words)
        fact_infos.append({
            "fact": fact,
            "word_start": w_start,
            "word_end": w_end,
            "start": words[w_start]["start"],
            "end": words[w_end]["end"],
        })

    print("\n[3/4] Rendering frames...")
    empty_bg = np.full((H, W, 3), 245, dtype=np.uint8)

    def make_frame(t):
        # Title card first 1.5s
        if t < 1.5:
            p = min(t / 1.5, 1)
            img = Image.new("RGB", (W, H), _BG)
            draw = ImageDraw.Draw(img)
            font = _get_font(52)
            sub_font = _get_font(24)

            alpha = int(255 * (p * p * (3 - 2 * p)))
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

            y = H // 2 - 80
            for line in lines:
                bb = draw.textbbox((0, 0), line, font=font)
                draw.text(((W - (bb[2] - bb[0])) // 2, y), line, font=font, fill=_STROKE)
                y += 70

            sub = "words synced to narration"
            bb = draw.textbbox((0, 0), sub, font=sub_font)
            draw.text(((W - (bb[2] - bb[0])) // 2, H - 200), sub, font=sub_font, fill=_HIGHLIGHT)

            result = np.array(img)
            if alpha < 255:
                result = (empty_bg * (255 - alpha) + result * alpha) // 255
            return result.astype(np.uint8)

        # End card
        if t > total_dur:
            return empty_bg

        # Find active fact
        active_fact = None
        active_fact_idx = -1
        for fi, fi_data in enumerate(fact_infos):
            if fi_data["start"] <= t < fi_data["end"]:
                active_fact = fi_data
                active_fact_idx = fi
                break

        if active_fact is None:
            for fi_data in reversed(fact_infos):
                if t > fi_data["end"]:
                    active_fact = fi_data
                    break

        if active_fact is None:
            return empty_bg

        fact_words = active_fact["fact"].split()
        spoken_idx = -1
        for wi in range(active_fact["word_start"], min(active_fact["word_end"] + 1, len(words))):
            if words[wi]["start"] <= t:
                spoken_idx = wi - active_fact["word_start"]
            else:
                break

        return render_frame(fact_words, spoken_idx)

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

    print(f"\n[4/4] Rendering...")
    safe_title = TITLE.lower().replace(" ", "_").replace("?", "").replace("!", "").replace("'", "").replace(".", "").replace(",", "").replace(":", "")[:50]
    out = config.OUTPUT_DIR / f"textsync_{safe_title}.mp4"
    out.unlink(missing_ok=True)
    print(f"  {video_dur:.1f}s | {W}x{H} | {FPS}fps | {len(words)} word-timed")
    t0 = time.time()
    final.write_videofile(str(out), fps=FPS, codec="libx264", audio_codec="aac", threads=4, preset="medium", ffmpeg_params=["-movflags", "+faststart", "-crf", "18"], logger=None)
    final.close()
    t1 = time.time()
    print(f"\n  DONE in {t1-t0:.0f}s: {out}")
    print(f"  Size: {out.stat().st_size:,} bytes")

    return out, fact_data


if __name__ == "__main__":
    main()
